"""
Image Generation Agent — feature/gemini-emotional-engine

Uses Gemini image generation (gemini-2.0-flash-preview-image-generation) instead of DALL-E 3.
Character portraits are generated first, then used as reference images when generating
scene images — ensuring visual consistency across the scrapbook.

Parallel generation via ThreadPoolExecutor.
All prompts include safety guardrails suffix.
"""
from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from db.supabase_client import get_client
from utils.gemini_client import fetch_image_bytes, generate_portrait, generate_scene_image
from utils.guardrails import get_image_safety_suffix


# ── Prompt builders ───────────────────────────────────────────────────────────

def _character_prompt(character: dict, genre: str) -> str:
    attrs = character.get("attributes") or {}
    traits = character.get("inferred_traits") or {}
    outfits = character.get("scene_outfits") or {}
    role = traits.get("role", "character")
    archetype = traits.get("emotional_archetype", "")
    outfit = outfits.get("default", "")

    parts = [f"A photorealistic 3D-rendered cinematic portrait of {character['name']}, the {role} of a {genre} story."]

    phys = []
    if attrs.get("build"):                phys.append(attrs["build"] + " build")
    if attrs.get("height"):               phys.append(attrs["height"])
    if attrs.get("skin_tone"):            phys.append(attrs["skin_tone"] + " skin")
    if attrs.get("hair"):                 phys.append(attrs["hair"] + " hair")
    if attrs.get("eyes"):                 phys.append(attrs["eyes"] + " eyes")
    if attrs.get("distinguishing_features"):
        phys.append(attrs["distinguishing_features"])
    if phys:
        parts.append("Physical appearance: " + ", ".join(phys) + ".")

    if outfit:
        parts.append(f"Wearing: {outfit}.")
    if archetype:
        parts.append(f"Emotional essence: {archetype}.")

    if character.get("is_real_person"):
        parts.append(
            "Realistic portrait, natural lighting, historically accurate appearance. "
            "No text, no watermarks."
        )
    else:
        parts.append(
            "Single character, three-quarter portrait angle, dramatic cinematic lighting, "
            f"moody atmospheric background suggesting {genre} genre, photorealistic, "
            "Unreal Engine 5 quality 3D render, shallow depth of field, editorial photography. "
            "No text. No watermarks. No other people in frame."
        )

    parts.append(get_image_safety_suffix(genre))
    return " ".join(parts)


def _scene_prompt(scene: dict, genre: str, character_names: list[str] | None = None) -> str:
    mood = scene.get("mood", "emotional")
    title = scene.get("title", "")
    emotional_context = scene.get("emotional_context", "")
    chars = scene.get("characters_present") or []

    parts = [f"A photorealistic 3D-rendered cinematic still from a {genre} story."]
    if title:
        parts.append(f"Scene title: {title}.")
    if emotional_context:
        parts.append(f"What is happening: {emotional_context}")

    if character_names:
        parts.append(f"The character(s) in this scene should visually match the provided reference portraits exactly: {', '.join(character_names)}.")
    elif chars:
        parts.append(f"Characters present: {', '.join(chars)}.")
    else:
        parts.append("Abstract emotional representation, no specific characters.")

    parts.append(
        f"{mood.capitalize()}-infused lighting, {genre} visual world, "
        "Unreal Engine 5 quality photorealistic 3D render, rich cinematic color grading "
        "matching the emotional tone. Wide or medium shot, atmospheric environmental storytelling. "
        "No text. No watermarks."
    )
    parts.append(get_image_safety_suffix(genre))
    return " ".join(parts)


# ── Storage helpers ───────────────────────────────────────────────────────────

def _upload_to_storage(db, book_id: str, sub_path: str, image_bytes: bytes) -> str:
    storage_path = f"{book_id}/{sub_path}"
    db.storage.from_("book-assets").upload(
        path=storage_path,
        file=image_bytes,
        file_options={"content-type": "image/png", "upsert": "true"},
    )
    return db.storage.from_("book-assets").get_public_url(storage_path)


def _update_step(db, book_id: str, step: str):
    try:
        db.table("books").update({"current_step": step}).eq("id", book_id).execute()
    except Exception:
        pass


# ── Character portrait generation (sequential — builds reference library) ─────

def _generate_portrait(db, book_id: str, char: dict, genre: str) -> dict | None:
    char_id = char.get("id")
    if not char_id:
        return None

    prompt = _character_prompt(char, genre)
    print(f"[image_agent] Portrait: '{char['name']}'")

    image_bytes = generate_portrait(prompt, size="1K", aspect_ratio="2:3")
    if not image_bytes:
        print(f"[image_agent] No portrait bytes for '{char['name']}'")
        return None

    try:
        public_url = _upload_to_storage(db, book_id, f"characters/{char_id}.png", image_bytes)
        db.table("characters").update({
            "portrait_url": public_url,
            "visual_profile": {"portrait_prompt": prompt, "portrait_url": public_url},
        }).eq("id", char_id).execute()

        asset_row = {
            "book_id": book_id,
            "scene_id": None,
            "asset_type": "portrait",
            "file_url": public_url,
        }
        res = db.table("assets").insert(asset_row).execute()
        if res.data:
            asset_row["id"] = res.data[0]["id"]

        # Return both the asset and the image bytes for use as reference
        return {"asset": asset_row, "portrait_bytes": image_bytes, "char_name": char["name"]}

    except Exception as e:
        print(f"[image_agent] Storage/DB failed for '{char['name']}': {e}")
        print(traceback.format_exc())
        return None


# ── Scene image generation (parallel) ────────────────────────────────────────

def _generate_scene_image(
    db,
    book_id: str,
    scene: dict,
    genre: str,
    portrait_map: dict[str, bytes],
) -> dict | None:
    scene_id = scene.get("id")
    if not scene_id:
        return None

    chars_present = scene.get("characters_present") or []
    reference_bytes: list[bytes] = []
    matched_names: list[str] = []

    for name in chars_present:
        # Match character name case-insensitively
        for key, img_bytes in portrait_map.items():
            if key.lower() == name.lower() or name.lower() in key.lower():
                reference_bytes.append(img_bytes)
                matched_names.append(key)
                break

    prompt = _scene_prompt(scene, genre, character_names=matched_names if matched_names else None)
    print(f"[image_agent] Scene: '{scene.get('title')}' | refs={len(reference_bytes)}")

    image_bytes = generate_scene_image(
        prompt,
        reference_images=reference_bytes,
        size="1K",
        aspect_ratio="16:9",
    )
    if not image_bytes:
        print(f"[image_agent] No scene bytes for '{scene.get('title')}'")
        return None

    try:
        public_url = _upload_to_storage(db, book_id, f"scenes/{scene_id}.png", image_bytes)
        db.table("scenes").update({"image_url": public_url}).eq("id", scene_id).execute()

        asset_row = {
            "book_id": book_id,
            "scene_id": scene_id,
            "asset_type": "scene_image",
            "file_url": public_url,
        }
        res = db.table("assets").insert(asset_row).execute()
        if res.data:
            asset_row["id"] = res.data[0]["id"]

        return asset_row

    except Exception as e:
        print(f"[image_agent] Storage/DB failed for scene '{scene.get('title')}': {e}")
        print(traceback.format_exc())
        return None


# ── Main ──────────────────────────────────────────────────────────────────────

def run_image_agent(
    book_id: str,
    genre: str,
    characters: list[dict],
    scenes: list[dict],
) -> dict:
    """
    1. Generate character portraits sequentially (builds portrait reference library).
    2. Generate scene images in parallel, injecting portrait bytes as reference images.
    Returns {"character_assets": [...], "scene_assets": [...]}.
    """
    db = get_client()
    char_total = len(characters)
    scene_total = len(scenes)
    character_assets: list[dict] = []
    scene_assets: list[dict] = []

    # portrait_map: character name → raw portrait bytes (for reference injection)
    portrait_map: dict[str, bytes] = {}

    # ── Phase 1: Character portraits (sequential — each portrait used as reference) ──
    for idx, char in enumerate(characters, 1):
        _update_step(db, book_id, f"Generating character portraits… ({idx}/{char_total})")
        result = _generate_portrait(db, book_id, char, genre)
        if result:
            character_assets.append(result["asset"])
            portrait_map[result["char_name"]] = result["portrait_bytes"]

    # Also load any existing portrait URLs that we may have missed (idempotency)
    for char in characters:
        name = char.get("name", "")
        if name not in portrait_map and char.get("portrait_url"):
            img_bytes = fetch_image_bytes(char["portrait_url"])
            if img_bytes:
                portrait_map[name] = img_bytes

    # ── Phase 2: Scene images (parallel) ─────────────────────────────────────
    _update_step(db, book_id, f"Generating scene images… (0/{scene_total})")
    completed = 0

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_scene = {
            executor.submit(_generate_scene_image, db, book_id, scene, genre, portrait_map): scene
            for scene in scenes
            if scene.get("id")
        }

        for future in as_completed(future_to_scene):
            completed += 1
            _update_step(db, book_id, f"Generating scene images… ({completed}/{scene_total})")
            result = future.result()
            if result:
                scene_assets.append(result)

    return {"character_assets": character_assets, "scene_assets": scene_assets}
