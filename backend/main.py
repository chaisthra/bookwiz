"""
BookWiz FastAPI backend — Phase 1 + 2
"""
from __future__ import annotations

import asyncio
import traceback
from datetime import datetime, timezone
from functools import partial

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

load_dotenv()

from agents.orchestrator import resume_scene_selection, start_pipeline
from db.supabase_client import get_client
from parsers.book_parser import parse_book


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="BookWiz API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/profiles")
def list_profiles():
    db = get_client()
    result = db.table("profiles").select("*").execute()
    return result.data


@app.post("/upload")
async def upload_book(
    file: UploadFile = File(...),
    profile_id: str = Form(...),
    mode: str = Form("manual"),
):
    db = get_client()

    filename = file.filename or ""
    if not (filename.lower().endswith(".pdf") or filename.lower().endswith(".epub")):
        raise HTTPException(400, "Only PDF and EPUB files are supported.")

    data = await file.read()

    try:
        parsed = parse_book(filename, data)
    except Exception as e:
        raise HTTPException(422, f"Failed to parse book: {e}")

    non_empty = [c for c in parsed.chunks if c.strip()]
    if not non_empty:
        raise HTTPException(422, "The file appears empty or image-only. Please upload a text-based PDF or EPUB.")

    profile_result = db.table("profiles").select("taste_profile").eq("id", profile_id).execute()
    if not profile_result.data:
        raise HTTPException(404, f"Profile '{profile_id}' not found.")
    taste_profile = profile_result.data[0]["taste_profile"] or {}

    book_record = {
        "profile_id": profile_id,
        "title": filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " "),
        "status": "processing",
    }
    book_result = db.table("books").insert(book_record).execute()
    book_id = book_result.data[0]["id"]

    loop = asyncio.get_running_loop()
    loop.create_task(
        _run_pipeline(book_id, profile_id, non_empty, taste_profile, mode)
    )

    return {"book_id": book_id, "status": "processing", "mode": mode}


async def _run_pipeline(
    book_id: str,
    profile_id: str,
    chunks: list[str],
    taste_profile: dict,
    mode: str,
):
    db = get_client()
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            partial(
                start_pipeline,
                book_id=book_id,
                profile_id=profile_id,
                chunks=chunks,
                user_preferences=taste_profile,
                mode=mode,
            ),
        )
        # Manual mode: paused after scene_agent, waiting for user scene selection
        # Auto mode: ran all the way through including image + scrapbook generation
        new_status = "awaiting_scene_selection" if mode == "manual" else "complete"
        db.table("books").update({
            "status": new_status,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", book_id).execute()
    except Exception as e:
        print(f"[Pipeline ERROR] book_id={book_id}: {e}")
        print(traceback.format_exc())
        db.table("books").update({
            "status": "failed",
            "error_message": str(e),
        }).eq("id", book_id).execute()


@app.get("/books")
def list_books(profile_id: str):
    db = get_client()
    result = (
        db.table("books")
        .select("*")
        .eq("profile_id", profile_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@app.get("/books/{book_id}")
def get_book(book_id: str):
    db = get_client()

    book = db.table("books").select("*").eq("id", book_id).execute()
    if not book.data:
        raise HTTPException(404, "Book not found")

    characters = db.table("characters").select("*").eq("book_id", book_id).execute()
    scenes = (
        db.table("scenes")
        .select("*")
        .eq("book_id", book_id)
        .order("emotional_weight_score", desc=True)
        .execute()
    )

    return {
        "book": book.data[0],
        "characters": characters.data,
        "scenes": scenes.data,
    }


@app.get("/books/{book_id}/visual-status")
def get_visual_status(book_id: str):
    db = get_client()
    result = db.table("books").select("visual_status,current_step").eq("id", book_id).execute()
    if not result.data:
        raise HTTPException(404, "Book not found")
    return result.data[0]


@app.get("/books/{book_id}/progress")
async def progress_stream(book_id: str):
    """
    SSE endpoint — streams book status and current_step every 2 seconds.
    Client receives: { status, visual_status, current_step }
    Stream ends when status is 'complete', 'failed', or visual_status is 'visuals_complete'.
    """
    import json as _json

    db = get_client()

    async def event_generator():
        terminal_statuses = {"complete", "failed", "awaiting_scene_selection"}
        terminal_visual = {"visuals_complete", "visuals_failed"}

        while True:
            result = db.table("books").select(
                "status,visual_status,current_step"
            ).eq("id", book_id).execute()

            if not result.data:
                yield {"data": _json.dumps({"error": "book not found"})}
                break

            row = result.data[0]
            yield {"data": _json.dumps(row)}

            # Stop streaming when pipeline reaches a terminal state
            if row.get("status") in terminal_statuses:
                break
            if row.get("visual_status") in terminal_visual:
                break

            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())


@app.get("/books/{book_id}/scrapbook")
def get_scrapbook(book_id: str):
    db = get_client()

    sb = db.table("scrapbooks").select("*").eq("book_id", book_id).execute()
    if not sb.data:
        raise HTTPException(404, "Scrapbook not yet generated")

    characters = db.table("characters").select("*").eq("book_id", book_id).execute()
    scenes = (
        db.table("scenes")
        .select("*")
        .eq("book_id", book_id)
        .order("emotional_weight_score", desc=True)
        .execute()
    )

    return {
        "scrapbook": sb.data[0],
        "characters": characters.data,
        "scenes": scenes.data,
    }


class ScrapbookUpdate(BaseModel):
    layout: dict | None = None
    finalised: bool | None = None


@app.patch("/books/{book_id}/scrapbook")
def update_scrapbook(book_id: str, update: ScrapbookUpdate):
    db = get_client()
    patch = {}
    if update.layout is not None:
        patch["layout"] = update.layout
    if update.finalised is not None:
        patch["finalised"] = update.finalised
    if not patch:
        raise HTTPException(400, "Nothing to update")
    db.table("scrapbooks").update(patch).eq("book_id", book_id).execute()
    return {"status": "updated"}


@app.post("/books/{book_id}/generate-visuals")
async def generate_visuals(book_id: str):
    """
    For manual mode: trigger image + scrapbook generation after user approves scenes.
    For auto mode: images are generated automatically in the pipeline — this endpoint
    is a no-op but returns the current visual_status.
    """
    db = get_client()
    book = db.table("books").select("status,visual_status").eq("id", book_id).execute()
    if not book.data:
        raise HTTPException(404, "Book not found")

    b = book.data[0]
    # Auto mode already ran images; manual mode needs a resume
    if b["visual_status"] in ("generating_images", "generating_scrapbook"):
        return {"status": "already_generating"}
    if b["visual_status"] == "visuals_complete":
        return {"status": "visuals_complete"}

    # Set status immediately so the frontend shows progress
    db.table("books").update({"visual_status": "generating_images"}).eq("id", book_id).execute()

    loop = asyncio.get_running_loop()
    loop.create_task(_run_visuals(book_id))

    return {"status": "generating"}


async def _run_visuals(book_id: str):
    """
    Run image_agent + scrapbook_agent directly for already-complete books.
    Used by POST /books/{id}/generate-visuals (on-demand, no LangGraph resume needed).
    """
    from agents.image_agent import run_image_agent
    from agents.scrapbook_agent import run_scrapbook_agent

    db = get_client()
    try:
        loop = asyncio.get_running_loop()

        # Fetch current book data
        book_row = db.table("books").select("genre").eq("id", book_id).execute()
        genre = book_row.data[0]["genre"] if book_row.data else "fiction"

        characters = db.table("characters").select("*").eq("book_id", book_id).execute().data
        scenes_q = (
            db.table("scenes")
            .select("*")
            .eq("book_id", book_id)
            .order("emotional_weight_score", desc=True)
            .execute()
        )
        all_scenes = scenes_q.data
        approved = [s for s in all_scenes if s.get("user_approved") is True]
        scenes = approved if approved else all_scenes

        # Run image generation
        await loop.run_in_executor(
            None,
            partial(run_image_agent, book_id=book_id, genre=genre,
                    characters=characters, scenes=scenes),
        )

        # Run scrapbook generation
        await loop.run_in_executor(
            None,
            partial(run_scrapbook_agent, book_id=book_id, genre=genre,
                    characters=characters, scenes=scenes),
        )

        db.table("books").update({
            "visual_status": "visuals_complete",
            "current_step": "Your scrapbook is ready",
        }).eq("id", book_id).execute()

    except Exception as e:
        print(f"[Visuals ERROR] book_id={book_id}: {e}")
        print(traceback.format_exc())
        db.table("books").update({"visual_status": "visuals_failed"}).eq("id", book_id).execute()


@app.post("/books/{book_id}/characters/{char_id}/regenerate-portrait")
async def regenerate_portrait(book_id: str, char_id: str):
    """Regenerate portrait image for a single character."""
    from agents.image_agent import regenerate_single_portrait
    db = get_client()

    char_row = db.table("characters").select("*").eq("id", char_id).execute()
    if not char_row.data:
        raise HTTPException(404, "Character not found")
    book_row = db.table("books").select("genre").eq("id", book_id).execute()
    genre = book_row.data[0]["genre"] if book_row.data else "fiction"

    loop = asyncio.get_running_loop()
    url = await loop.run_in_executor(
        None,
        partial(regenerate_single_portrait, book_id=book_id, char=char_row.data[0], genre=genre),
    )
    if not url:
        raise HTTPException(500, "Image generation failed")
    return {"portrait_url": url}


@app.post("/books/{book_id}/scenes/{scene_id}/regenerate-image")
async def regenerate_scene_image_endpoint(book_id: str, scene_id: str):
    """Regenerate scene image for a single scene."""
    from agents.image_agent import regenerate_single_scene_image
    db = get_client()

    scene_row = db.table("scenes").select("*").eq("id", scene_id).execute()
    if not scene_row.data:
        raise HTTPException(404, "Scene not found")
    book_row = db.table("books").select("genre").eq("id", book_id).execute()
    genre = book_row.data[0]["genre"] if book_row.data else "fiction"
    characters = db.table("characters").select("*").eq("book_id", book_id).execute().data

    loop = asyncio.get_running_loop()
    url = await loop.run_in_executor(
        None,
        partial(regenerate_single_scene_image,
                book_id=book_id, scene=scene_row.data[0], genre=genre, characters=characters),
    )
    if not url:
        raise HTTPException(500, "Image generation failed")
    return {"image_url": url}


@app.post("/books/{book_id}/regenerate/portraits")
async def regenerate_all_portraits(book_id: str):
    """Regenerate all character portraits for a book (background task)."""
    db = get_client()
    book_row = db.table("books").select("genre").eq("id", book_id).execute()
    if not book_row.data:
        raise HTTPException(404, "Book not found")
    db.table("books").update({"current_step": "Regenerating portraits…"}).eq("id", book_id).execute()
    loop = asyncio.get_running_loop()
    loop.create_task(_run_regenerate_portraits(book_id))
    return {"status": "regenerating"}


async def _run_regenerate_portraits(book_id: str):
    from agents.image_agent import regenerate_single_portrait
    db = get_client()
    try:
        book_row = db.table("books").select("genre").eq("id", book_id).execute()
        genre = book_row.data[0]["genre"] if book_row.data else "fiction"
        characters = db.table("characters").select("*").eq("book_id", book_id).execute().data
        loop = asyncio.get_running_loop()
        for i, char in enumerate(characters, 1):
            db.table("books").update({"current_step": f"Regenerating portrait {i}/{len(characters)}…"}).eq("id", book_id).execute()
            await loop.run_in_executor(
                None,
                partial(regenerate_single_portrait, book_id=book_id, char=char, genre=genre),
            )
        db.table("books").update({"current_step": "Portraits regenerated"}).eq("id", book_id).execute()
    except Exception as e:
        print(f"[regen portraits] {e}")


@app.post("/books/{book_id}/regenerate/scene-images")
async def regenerate_all_scene_images(book_id: str):
    """Regenerate all scene images for a book (background task)."""
    db = get_client()
    if not db.table("books").select("id").eq("id", book_id).execute().data:
        raise HTTPException(404, "Book not found")
    db.table("books").update({"current_step": "Regenerating scene images…"}).eq("id", book_id).execute()
    loop = asyncio.get_running_loop()
    loop.create_task(_run_regenerate_scene_images(book_id))
    return {"status": "regenerating"}


async def _run_regenerate_scene_images(book_id: str):
    from agents.image_agent import regenerate_single_scene_image
    db = get_client()
    try:
        book_row = db.table("books").select("genre").eq("id", book_id).execute()
        genre = book_row.data[0]["genre"] if book_row.data else "fiction"
        characters = db.table("characters").select("*").eq("book_id", book_id).execute().data
        scenes = db.table("scenes").select("*").eq("book_id", book_id).execute().data
        loop = asyncio.get_running_loop()
        for i, scene in enumerate(scenes, 1):
            db.table("books").update({"current_step": f"Regenerating scene image {i}/{len(scenes)}…"}).eq("id", book_id).execute()
            await loop.run_in_executor(
                None,
                partial(regenerate_single_scene_image,
                        book_id=book_id, scene=scene, genre=genre, characters=characters),
            )
        db.table("books").update({"current_step": "Scene images regenerated"}).eq("id", book_id).execute()
    except Exception as e:
        print(f"[regen scene images] {e}")


@app.get("/books/{book_id}/scenes/next")
def get_next_scenes(book_id: str, offset: int = 0):
    db = get_client()
    scenes = (
        db.table("scenes")
        .select("*")
        .eq("book_id", book_id)
        .is_("user_approved", "null")
        .order("emotional_weight_score", desc=True)
        .range(offset, offset + 3)
        .execute()
    )
    return {"scenes": scenes.data, "offset": offset}


class SceneSelection(BaseModel):
    approved_ids: list[str]
    rejected_ids: list[str]
    free_text: str | None = None


@app.post("/books/{book_id}/scenes/select")
async def select_scenes(book_id: str, selection: SceneSelection):
    db = get_client()

    if selection.approved_ids:
        db.table("scenes").update({"user_approved": True}).in_("id", selection.approved_ids).execute()
    if selection.rejected_ids:
        db.table("scenes").update({"user_approved": False}).in_("id", selection.rejected_ids).execute()

    if selection.free_text:
        db.table("books").update({"status": "free_text_requested"}).eq("id", book_id).execute()
        return {"status": "free_text_noted"}

    # Resume graph: runs image_agent + scrapbook_agent
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, partial(resume_scene_selection, book_id))
        db.table("books").update({
            "status": "complete",
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", book_id).execute()
    except Exception as e:
        print(f"[Resume ERROR] book_id={book_id}: {e}")
        print(traceback.format_exc())
        raise HTTPException(500, f"Failed to resume pipeline: {e}")

    return {"status": "complete", "approved": selection.approved_ids}
