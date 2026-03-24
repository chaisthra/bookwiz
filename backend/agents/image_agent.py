"""
Image Generation Agent — Phase 2

Generates character portrait images and scene mood images using DALL-E 3,
uploads them to Supabase Storage bucket "book-assets", and stores URLs in
the assets table + shortcut columns on characters/scenes.

DALL-E 3 rate limits:
  Tier 1: 1 img/min  → sleep 62s between calls
  Tier 2: 5 img/min  → sleep 12s between calls

We assume Tier 1 by default (conservative). Set IMAGE_RATE_LIMIT_SLEEP=12
in the environment to use Tier 2 timing.
"""
from __future__ import annotations

import os
import time
import traceback

import httpx
from openai import OpenAI, BadRequestError, RateLimitError

from db.supabase_client import get_client

_RATE_SLEEP = int(os.environ.get("IMAGE_RATE_LIMIT_SLEEP", "5"))


# ── Prompt builders ───────────────────────────────────────────────────────────

def _character_prompt(character: dict, genre: str) -> str:
    attrs = character.get("attributes") or {}
    traits = character.get("inferred_traits") or {}
    outfits = character.get("scene_outfits") or {}
    role = traits.get("role", "character")
    archetype = traits.get("emotional_archetype", "")
    outfit = outfits.get("default", "")

    parts = [f"A cinematic portrait of {character['name']}, the {role} of a {genre} story."]

    phys = []
    if attrs.get("build"):     phys.append(attrs["build"] + " build")
    if attrs.get("height"):    phys.append(attrs["height"])
    if attrs.get("skin_tone"): phys.append(attrs["skin_tone"] + " skin")
    if attrs.get("hair"):      phys.append(attrs["hair"] + " hair")
    if attrs.get("eyes"):      phys.append(attrs["eyes"] + " eyes")
    if attrs.get("distinguishing_features"):
        phys.append(attrs["distinguishing_features"])
    if phys:
        parts.append("Physical appearance: " + ", ".join(phys) + ".")

    if outfit:
        parts.append(f"Wearing: {outfit}.")
    if archetype:
        parts.append(f"Emotional essence: {archetype}.")

    style = (
        "Single character, three-quarter portrait angle, dramatic cinematic lighting, "
        f"moody atmospheric background suggesting {genre} genre, photorealistic, "
        "high detail, shallow depth of field, editorial photography quality. "
        "No text, no watermarks, no other people in frame."
    )
    if character.get("is_real_person"):
        style = (
            "Realistic portrait, natural lighting, historically accurate appearance. "
            "No text, no watermarks."
        )
    parts.append(style)
    return " ".join(parts)


def _scene_prompt(scene: dict, genre: str) -> str:
    mood = scene.get("mood", "emotional")
    title = scene.get("title", "")
    emotional_context = scene.get("emotional_context", "")
    chars = scene.get("characters_present") or []

    parts = [f"A cinematic still image from a {genre} story."]
    if title:
        parts.append(f"Scene: {title}.")
    if emotional_context:
        parts.append(f"What is happening: {emotional_context}")

    if chars:
        if len(chars) == 1:
            parts.append(f"Character present: {chars[0]}.")
        else:
            parts.append(f"Characters present: {', '.join(chars)}.")
    else:
        parts.append("Abstract emotional representation, no specific characters.")

    parts.append(
        f"{mood.capitalize()}-infused lighting, {genre} visual world, "
        "painterly cinematic quality, rich color grading matching the emotional tone. "
        "Wide or medium shot, atmospheric environmental storytelling. "
        "No text. No watermarks."
    )
    return " ".join(parts)


# ── Storage helpers ───────────────────────────────────────────────────────────

def _download_image(url: str) -> bytes:
    """Download image bytes from a DALL-E temporary URL."""
    resp = httpx.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def _upload_to_storage(db, book_id: str, sub_path: str, image_bytes: bytes) -> str:
    """Upload bytes to Supabase Storage and return the public URL."""
    storage_path = f"{book_id}/{sub_path}"
    db.storage.from_("book-assets").upload(
        path=storage_path,
        file=image_bytes,
        file_options={"content-type": "image/png", "upsert": "true"},
    )
    return db.storage.from_("book-assets").get_public_url(storage_path)


# ── Main ──────────────────────────────────────────────────────────────────────

def run_image_agent(
    book_id: str,
    genre: str,
    characters: list[dict],
    scenes: list[dict],
) -> dict:
    """
    Generate portrait images for characters and mood images for scenes.
    Returns {"character_assets": [...], "scene_assets": [...]}.
    Failed individual images are skipped; the pipeline never fails entirely here.
    """
    client = OpenAI()
    db = get_client()

    char_total = len(characters)
    scene_total = len(scenes)
    character_assets: list[dict] = []
    scene_assets: list[dict] = []

    # ── Character portraits ───────────────────────────────────────────────────
    for idx, char in enumerate(characters, 1):
        char_id = char.get("id")
        if not char_id:
            continue

        _update_step(db, book_id, f"Generating character portraits… ({idx}/{char_total})")
        prompt = _character_prompt(char, genre)
        print(f"[image_agent] Portrait for '{char['name']}' ({idx}/{char_total})")

        try:
            response = _dalle_with_retry(client, prompt, size="1024x1024")
            image_bytes = _download_image(response.data[0].url)
            public_url = _upload_to_storage(db, book_id, f"characters/{char_id}.png", image_bytes)

            # Update character row
            db.table("characters").update({
                "portrait_url": public_url,
                "visual_profile": {"portrait_prompt": prompt, "portrait_url": public_url},
            }).eq("id", char_id).execute()

            # Insert asset record
            asset_row = {
                "book_id": book_id,
                "scene_id": None,
                "asset_type": "portrait",
                "file_url": public_url,
            }
            res = db.table("assets").insert(asset_row).execute()
            if res.data:
                asset_row["id"] = res.data[0]["id"]
            character_assets.append(asset_row)

        except BadRequestError as e:
            print(f"[image_agent] DALL-E content policy for '{char['name']}': {e}")
        except Exception as e:
            print(f"[image_agent] Failed portrait for '{char['name']}': {e}")
            print(traceback.format_exc())

        time.sleep(_RATE_SLEEP)

    # ── Scene images ──────────────────────────────────────────────────────────
    for idx, scene in enumerate(scenes, 1):
        scene_id = scene.get("id")
        if not scene_id:
            continue

        _update_step(db, book_id, f"Generating scene images… ({idx}/{scene_total})")
        prompt = _scene_prompt(scene, genre)
        print(f"[image_agent] Scene image for '{scene.get('title', scene_id)}' ({idx}/{scene_total})")

        try:
            response = _dalle_with_retry(client, prompt, size="1792x1024")
            image_bytes = _download_image(response.data[0].url)
            public_url = _upload_to_storage(db, book_id, f"scenes/{scene_id}.png", image_bytes)

            # Update scene row
            db.table("scenes").update({"image_url": public_url}).eq("id", scene_id).execute()

            # Insert asset record
            asset_row = {
                "book_id": book_id,
                "scene_id": scene_id,
                "asset_type": "scene_image",
                "file_url": public_url,
            }
            res = db.table("assets").insert(asset_row).execute()
            if res.data:
                asset_row["id"] = res.data[0]["id"]
            scene_assets.append(asset_row)

        except BadRequestError as e:
            print(f"[image_agent] DALL-E content policy for scene '{scene.get('title')}': {e}")
        except Exception as e:
            print(f"[image_agent] Failed scene image for '{scene.get('title')}': {e}")
            print(traceback.format_exc())

        time.sleep(_RATE_SLEEP)

    return {"character_assets": character_assets, "scene_assets": scene_assets}


def _dalle_with_retry(client: OpenAI, prompt: str, size: str):
    """Call DALL-E 3 with one rate-limit retry."""
    try:
        return client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="hd",
            style="vivid",
            n=1,
        )
    except RateLimitError:
        print("[image_agent] Rate limited — waiting 65s then retrying…")
        time.sleep(65)
        return client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="hd",
            style="vivid",
            n=1,
        )


def _update_step(db, book_id: str, step: str):
    try:
        db.table("books").update({"current_step": step}).eq("id", book_id).execute()
    except Exception:
        pass
