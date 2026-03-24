"""
LangGraph orchestrator for BookWiz Phase 1 + 2.

State flows:
  Auto:   detect_genre → character_agent → scene_agent → image_agent → scrapbook_agent → END
  Manual: detect_genre → character_agent → scene_agent [interrupt] →
          (user selects scenes) → image_agent → scrapbook_agent → END

Checkpointing is in-memory (MemorySaver). Swap for PostgresSaver if persistence
across server restarts becomes necessary.
"""
from __future__ import annotations

import json
import traceback
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agents.character_agent import run_character_agent
from agents.image_agent import run_image_agent
from agents.scene_agent import run_scene_agent
from agents.scrapbook_agent import run_scrapbook_agent
from db.supabase_client import get_client

_ANALYSIS_SYSTEM = (
    "You are a private literary analysis assistant. "
    "The user has uploaded their own personal copy of a book for private reading analysis only. "
    "Analyse the text and return structured JSON as instructed. "
    "Do not reproduce extended copyrighted passages."
)


# ── State ─────────────────────────────────────────────────────────────────────

class BookWizState(TypedDict):
    book_id: str
    profile_id: str
    genre: str
    raw_text_chunks: list[str]
    characters: list[dict]
    scenes: list[dict]
    character_assets: list[dict]
    scene_assets: list[dict]
    scrapbook: dict
    user_preferences: dict
    mode: str                   # "auto" | "manual"
    current_step: str
    error: str | None


# ── Genre detection ───────────────────────────────────────────────────────────

VALID_GENRES = [
    "romance", "fantasy", "fiction", "thriller", "mystery",
    "biography", "non-fiction", "self-help", "classic", "other",
]

_GENRE_PROMPT = """You are a book genre classifier.

Read the following excerpts from the beginning of a book and classify it into exactly ONE genre from this list:
romance, fantasy, fiction, thriller, mystery, biography, non-fiction, self-help, classic, other

Respond with a single JSON object, nothing else:
{{"genre": "<genre>", "confidence": <0-1>, "reasoning": "<one sentence>"}}

Book excerpts:
{text}
"""


def detect_genre(state: BookWizState) -> dict:
    chunks = state["raw_text_chunks"]
    sample = "\n\n---\n\n".join(chunks[:3])[:6000]

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    response = llm.invoke([
        SystemMessage(content=_ANALYSIS_SYSTEM),
        HumanMessage(content=_GENRE_PROMPT.format(text=sample)),
    ])

    try:
        result = json.loads(response.content)
        genre = result.get("genre", "fiction").lower()
        if genre not in VALID_GENRES:
            genre = "fiction"
    except Exception:
        genre = "fiction"

    try:
        db = get_client()
        db.table("books").update({
            "genre": genre,
            "current_step": "Identifying characters…",
        }).eq("id", state["book_id"]).execute()
    except Exception as e:
        print(f"[orchestrator] Failed to write genre to DB: {e}")

    return {"genre": genre, "current_step": "genre_detected"}


# ── Agent nodes ───────────────────────────────────────────────────────────────

def character_node(state: BookWizState) -> dict:
    try:
        db = get_client()
        db.table("books").update({"current_step": "Extracting scenes…"}).eq("id", state["book_id"]).execute()
    except Exception:
        pass
    characters = run_character_agent(
        book_id=state["book_id"],
        genre=state["genre"],
        chunks=state["raw_text_chunks"],
    )
    return {"characters": characters, "current_step": "characters_extracted"}


def scene_node(state: BookWizState) -> dict:
    try:
        db = get_client()
        db.table("books").update({"current_step": "Ranking emotional moments…"}).eq("id", state["book_id"]).execute()
    except Exception:
        pass
    scenes = run_scene_agent(
        book_id=state["book_id"],
        genre=state["genre"],
        chunks=state["raw_text_chunks"],
        user_preferences=state.get("user_preferences", {}),
        mode=state.get("mode", "manual"),
    )
    return {"scenes": scenes, "current_step": "scenes_extracted"}


def image_node(state: BookWizState) -> dict:
    db = get_client()
    try:
        db.table("books").update({
            "visual_status": "generating_images",
            "current_step": "Generating character portraits…",
        }).eq("id", state["book_id"]).execute()
    except Exception:
        pass

    # Use only approved scenes (manual mode) or all scenes (auto mode)
    scenes = state.get("scenes", [])
    approved = [s for s in scenes if s.get("user_approved") is True]
    scenes_for_images = approved if approved else scenes

    assets = run_image_agent(
        book_id=state["book_id"],
        genre=state["genre"],
        characters=state.get("characters", []),
        scenes=scenes_for_images,
    )

    try:
        db.table("books").update({
            "visual_status": "generating_scrapbook",
            "current_step": "Assembling your scrapbook…",
        }).eq("id", state["book_id"]).execute()
    except Exception:
        pass

    return {
        "character_assets": assets["character_assets"],
        "scene_assets": assets["scene_assets"],
        "current_step": "images_generated",
    }


def scrapbook_node(state: BookWizState) -> dict:
    scenes = state.get("scenes", [])
    approved = [s for s in scenes if s.get("user_approved") is True]
    scenes_for_scrapbook = approved if approved else scenes

    scrapbook = run_scrapbook_agent(
        book_id=state["book_id"],
        genre=state["genre"],
        characters=state.get("characters", []),
        scenes=scenes_for_scrapbook,
    )

    try:
        db = get_client()
        db.table("books").update({
            "visual_status": "visuals_complete",
            "current_step": "Your scrapbook is ready",
        }).eq("id", state["book_id"]).execute()
    except Exception:
        pass

    return {"scrapbook": scrapbook, "current_step": "scrapbook_generated"}


# ── Graph construction ────────────────────────────────────────────────────────

def _build_graph(manual_mode: bool = False) -> Any:
    builder = StateGraph(BookWizState)

    builder.add_node("detect_genre", detect_genre)
    builder.add_node("character_agent", character_node)
    builder.add_node("scene_agent", scene_node)
    builder.add_node("image_agent", image_node)
    builder.add_node("scrapbook_agent", scrapbook_node)

    builder.set_entry_point("detect_genre")
    builder.add_edge("detect_genre", "character_agent")
    builder.add_edge("character_agent", "scene_agent")
    builder.add_edge("scene_agent", "image_agent")
    builder.add_edge("image_agent", "scrapbook_agent")
    builder.add_edge("scrapbook_agent", END)

    checkpointer = MemorySaver()

    if manual_mode:
        # Pause after scenes so user can approve/reject before images are generated
        return builder.compile(
            checkpointer=checkpointer,
            interrupt_after=["scene_agent"],
        )
    return builder.compile(checkpointer=checkpointer)


_auto_graph = None
_manual_graph = None


def get_graph(mode: str = "auto"):
    global _auto_graph, _manual_graph
    if mode == "manual":
        if _manual_graph is None:
            _manual_graph = _build_graph(manual_mode=True)
        return _manual_graph
    if _auto_graph is None:
        _auto_graph = _build_graph(manual_mode=False)
    return _auto_graph


# ── Public API ────────────────────────────────────────────────────────────────

def start_pipeline(
    book_id: str,
    profile_id: str,
    chunks: list[str],
    user_preferences: dict,
    mode: str = "manual",
) -> dict:
    graph = get_graph(mode)
    thread_id = book_id

    initial_state = BookWizState(
        book_id=book_id,
        profile_id=profile_id,
        genre="",
        raw_text_chunks=chunks,
        characters=[],
        scenes=[],
        character_assets=[],
        scene_assets=[],
        scrapbook={},
        user_preferences=user_preferences,
        mode=mode,
        current_step="started",
        error=None,
    )

    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(initial_state, config=config)
    return result


def resume_scene_selection(book_id: str) -> dict:
    """Resume after user approves scenes — runs image_agent + scrapbook_agent."""
    graph = get_graph("manual")
    config = {"configurable": {"thread_id": book_id}}
    result = graph.invoke(None, config=config)
    return result
