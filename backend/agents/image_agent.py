"""
Image Generation Agent

Portraits  → client.images.generate(model="gpt-image-1.5")
Scene images → client.images.edit(model="gpt-image-1.5", image=[portrait_bytes...])
               with input_fidelity="high" for character consistency
Fallback   → client.images.generate(model="dall-e-3") if gpt-image-1.5 fails
"""
from __future__ import annotations

import base64
import io
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

from db.supabase_client import get_client
from utils.gemini_client import fetch_image_bytes
from utils.guardrails import get_image_safety_suffix

_PORTRAIT_MODEL = "gpt-image-1.5"
_FALLBACK_MODEL = "dall-e-3"


# ── Core generation ───────────────────────────────────────────────────────────

def _generate(prompt: str, size: str = "1024x1024") -> bytes | None:
    """Generate image from scratch — portraits and fallback."""
    client = OpenAI()
    try:
        res = client.images.generate(
            model=_PORTRAIT_MODEL,
            prompt=prompt,
            size=size,
            quality="high",
            n=1,
        )
        b64 = res.data[0].b64_json
        return base64.b64decode(b64) if b64 else None
    except Exception as e:
        print(f"[image_agent] gpt-image-1.5 generate failed: {e}")
        return _dalle3_fallback(prompt, size)


def _edit_with_references(
    prompt: str,
    reference_bytes: list[bytes],
    size: str = "1536x1024",
) -> bytes | None:
    """
    Generate scene image using character portraits as reference images.
    Uses client.images.edit() with input_fidelity="high" for character consistency.
    Falls back to generate() if edit fails.
    """
    client = OpenAI()
    # Wrap each portrait as a named file-like object
    images = [
        ("image", (f"char_{i}.png", io.BytesIO(b), "image/png"))
        for i, b in enumerate(reference_bytes)
    ]
    try:
        res = client.images.edit(
            model=_PORTRAIT_MODEL,
            image=[io.BytesIO(b) for b in reference_bytes],
            prompt=prompt,
            size=size,
            quality="high",
            input_fidelity="high",
        )
        b64 = res.data[0].b64_json
        return base64.b64decode(b64) if b64 else None
    except Exception as e:
        print(f"[image_agent] images.edit failed: {e} — falling back to generate()")
        return _generate(prompt, size)


def _dalle3_fallback(prompt: str, size: str) -> bytes | None:
    """DALL-E 3 fallback when gpt-image-1.5 is unavailable."""
    import httpx
    client = OpenAI()
    # DALL-E 3 only supports specific sizes
    dalle_size = "1792x1024" if "x1024" in size and size != "1024x1024" else "1024x1024"
    try:
        res = client.images.generate(
            model=_FALLBACK_MODEL,
            prompt=prompt,
            size=dalle_size,
            quality="hd",
            style="vivid",
            n=1,
        )
        url = res.data[0].url
        if url:
            r = httpx.get(url, timeout=60)
            r.raise_for_status()
            print(f"[image_agent] DALL-E 3 fallback succeeded")
            return r.content
    except Exception as e:
        print(f"[image_agent] DALL-E 3 fallback also failed: {e}")
    return None


# ── Prompt builders ───────────────────────────────────────────────────────────

def _character_prompt(character: dict, genre: str) -> str:
    attrs     = character.get("attributes") or {}
    traits    = character.get("inferred_traits") or {}
    outfit    = (character.get("scene_outfits") or {}).get("default", "")
    role      = traits.get("role", "character")
    archetype = traits.get("emotional_archetype", "")

    parts = [f"A photorealistic cinematic portrait of {character['name']}, the {role} of a {genre} story."]

    phys = []
    if attrs.get("build"):                   phys.append(attrs["build"] + " build")
    if attrs.get("height"):                  phys.append(attrs["height"])
    if attrs.get("skin_tone"):               phys.append(attrs["skin_tone"] + " skin")
    if attrs.get("hair"):                    phys.append(attrs["hair"] + " hair")
    if attrs.get("eyes"):                    phys.append(attrs["eyes"] + " eyes")
    if attrs.get("distinguishing_features"): phys.append(attrs["distinguishing_features"])
    if phys:
        parts.append("Physical appearance: " + ", ".join(phys) + ".")
    if outfit:
        parts.append(f"Wearing: {outfit}.")
    if archetype:
        parts.append(f"Emotional essence: {archetype}.")

    parts.append(
        "Single character, three-quarter portrait angle, dramatic cinematic lighting, "
        f"moody atmospheric background suggesting {genre} genre, photorealistic, "
        "high detail, shallow depth of field. No text. No watermarks. No other people."
    )
    parts.append(get_image_safety_suffix(genre))
    return " ".join(parts)


def _scene_prompt(scene: dict, genre: str, ref_names: list[str]) -> str:
    mood    = scene.get("mood", "emotional")
    title   = scene.get("title", "")
    context = scene.get("emotional_context", "")
    chars   = scene.get("characters_present") or []

    parts = [f"A photorealistic cinematic still from a {genre} story."]
    if title:
        parts.append(f"Scene: {title}.")
    if context:
        parts.append(f"What is happening: {context}")

    if ref_names:
        parts.append(
            f"The characters in this scene ({', '.join(ref_names)}) must visually match "
            "the provided reference portraits exactly — same face, hair, clothing style."
        )
    elif chars:
        parts.append(f"Characters present: {', '.join(chars)}.")
    else:
        parts.append("Abstract emotional representation, no specific characters.")

    parts.append(
        f"{mood.capitalize()}-infused lighting, {genre} visual world, "
        "rich cinematic color grading matching the emotional tone. "
        "Wide or medium shot, atmospheric environmental storytelling. "
        "No text. No watermarks."
    )
    parts.append(get_image_safety_suffix(genre))
    return " ".join(parts)


# ── Storage helper ────────────────────────────────────────────────────────────

def _upload(db, book_id: str, sub_path: str, image_bytes: bytes) -> str:
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


# ── Single-item generation ────────────────────────────────────────────────────

def _do_portrait(db, book_id: str, char: dict, genre: str) -> dict | None:
    char_id = char.get("id")
    if not char_id:
        return None

    print(f"[image_agent] Portrait: '{char.get('name')}'")
    prompt      = _character_prompt(char, genre)
    image_bytes = _generate(prompt, size="1024x1024")
    if not image_bytes:
        return None

    try:
        url = _upload(db, book_id, f"characters/{char_id}.png", image_bytes)
        db.table("characters").update({
            "portrait_url": url,
            "visual_profile": {"portrait_prompt": prompt, "portrait_url": url},
        }).eq("id", char_id).execute()

        asset_row = {"book_id": book_id, "scene_id": None, "asset_type": "portrait", "file_url": url}
        res = db.table("assets").insert(asset_row).execute()
        if res.data:
            asset_row["id"] = res.data[0]["id"]

        return {"asset": asset_row, "portrait_bytes": image_bytes, "char_name": char["name"]}
    except Exception as e:
        print(f"[image_agent] Storage/DB error for '{char.get('name')}': {e}")
        print(traceback.format_exc())
        return None


def _do_scene_image(
    db, book_id: str, scene: dict, genre: str, portrait_map: dict[str, bytes]
) -> dict | None:
    scene_id = scene.get("id")
    if not scene_id:
        return None

    # Collect portrait bytes for characters in this scene
    chars_present = scene.get("characters_present") or []
    ref_bytes: list[bytes] = []
    ref_names: list[str]   = []
    for name in chars_present:
        for key, img_bytes in portrait_map.items():
            if key.lower() == name.lower() or name.lower() in key.lower():
                ref_bytes.append(img_bytes)
                ref_names.append(key)
                break

    print(f"[image_agent] Scene: '{scene.get('title')}' | {len(ref_bytes)} reference portrait(s)")
    prompt = _scene_prompt(scene, genre, ref_names)

    if ref_bytes:
        # Use images.edit() with portrait references for character consistency
        image_bytes = _edit_with_references(prompt, ref_bytes, size="1536x1024")
    else:
        # No character references — plain generate
        image_bytes = _generate(prompt, size="1536x1024")

    if not image_bytes:
        return None

    try:
        url = _upload(db, book_id, f"scenes/{scene_id}.png", image_bytes)
        db.table("scenes").update({"image_url": url}).eq("id", scene_id).execute()

        asset_row = {"book_id": book_id, "scene_id": scene_id, "asset_type": "scene_image", "file_url": url}
        res = db.table("assets").insert(asset_row).execute()
        if res.data:
            asset_row["id"] = res.data[0]["id"]
        return asset_row
    except Exception as e:
        print(f"[image_agent] Storage/DB error for scene '{scene.get('title')}': {e}")
        print(traceback.format_exc())
        return None


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_image_agent(
    book_id: str,
    genre: str,
    characters: list[dict],
    scenes: list[dict],
) -> dict:
    db = get_client()
    char_total  = len(characters)
    scene_total = len(scenes)
    character_assets: list[dict] = []
    scene_assets: list[dict]     = []
    portrait_map: dict[str, bytes] = {}  # name → raw bytes for reference injection

    # Phase 1: Portraits (sequential — builds reference library)
    for idx, char in enumerate(characters, 1):
        _update_step(db, book_id, f"Generating character portraits… ({idx}/{char_total})")
        result = _do_portrait(db, book_id, char, genre)
        if result:
            character_assets.append(result["asset"])
            portrait_map[result["char_name"]] = result["portrait_bytes"]

    # Load any existing portraits not regenerated (idempotency)
    for char in characters:
        name = char.get("name", "")
        if name not in portrait_map and char.get("portrait_url"):
            img_bytes = fetch_image_bytes(char["portrait_url"])
            if img_bytes:
                portrait_map[name] = img_bytes

    # Phase 2: Scene images (parallel, with portrait references)
    _update_step(db, book_id, f"Generating scene images… (0/{scene_total})")
    completed = 0

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_do_scene_image, db, book_id, scene, genre, portrait_map): scene
            for scene in scenes if scene.get("id")
        }
        for future in as_completed(futures):
            completed += 1
            _update_step(db, book_id, f"Generating scene images… ({completed}/{scene_total})")
            asset = future.result()
            if asset:
                scene_assets.append(asset)

    return {"character_assets": character_assets, "scene_assets": scene_assets}


# ── Public regeneration helpers ───────────────────────────────────────────────

def regenerate_single_portrait(book_id: str, char: dict, genre: str) -> str | None:
    db     = get_client()
    result = _do_portrait(db, book_id, char, genre)
    return result["asset"]["file_url"] if result else None


def regenerate_single_scene_image(
    book_id: str, scene: dict, genre: str, characters: list[dict]
) -> str | None:
    db = get_client()
    portrait_map: dict[str, bytes] = {}
    for char in characters:
        name = char.get("name", "")
        url  = char.get("portrait_url", "")
        if name and url:
            img_bytes = fetch_image_bytes(url)
            if img_bytes:
                portrait_map[name] = img_bytes
    asset = _do_scene_image(db, book_id, scene, genre, portrait_map)
    return asset["file_url"] if asset else None
