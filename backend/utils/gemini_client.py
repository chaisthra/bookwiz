"""
Gemini Image Generation client — Phase 2 (revised).

Uses google-genai SDK with gemini-3.1-flash-image-preview.
Supports reference image injection for character consistency across scenes.
"""
from __future__ import annotations

import base64
import os
import time
import traceback

import httpx

_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def generate_portrait(
    prompt: str,
    size: str = "1K",
    aspect_ratio: str = "2:3",
) -> bytes | None:
    """
    Generate a character portrait image.
    Returns raw PNG bytes or None on failure.
    """
    return _generate(prompt, size=size, aspect_ratio=aspect_ratio, reference_images=[])


def generate_scene_image(
    prompt: str,
    reference_images: list[bytes],
    size: str = "1K",
    aspect_ratio: str = "16:9",
) -> bytes | None:
    """
    Generate a scene image with optional character reference images
    for visual consistency.
    Returns raw PNG bytes or None on failure.
    """
    return _generate(prompt, size=size, aspect_ratio=aspect_ratio,
                     reference_images=reference_images)


def _generate(
    prompt: str,
    size: str,
    aspect_ratio: str,
    reference_images: list[bytes],
    retries: int = 5,
) -> bytes | None:
    from google import genai
    from google.genai import types

    client = _get_client()
    model = "gemini-2.0-flash-preview-image-generation"

    # Build contents list: text prompt + optional reference images
    contents: list = []
    for img_bytes in reference_images:
        contents.append(
            types.Part.from_bytes(data=img_bytes, mime_type="image/png")
        )
    contents.append(types.Part.from_text(text=prompt))

    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio=aspect_ratio,
            image_size=size,
        ),
    )

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data
            print(f"[gemini_client] No image in response — text: {response.text[:200] if response.text else 'none'}")
            return None

        except Exception as e:
            err = str(e)
            if "SAFETY" in err.upper() or "policy" in err.lower():
                print(f"[gemini_client] Safety block on attempt {attempt+1}: {err[:200]}")
                prompt = _add_safety_prefix(prompt)
                contents = []
                for img_bytes in reference_images:
                    contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
                contents.append(types.Part.from_text(text=prompt))
            elif "429" in err or "quota" in err.lower() or "rate" in err.lower():
                print(f"[gemini_client] Rate limited — falling back to DALL-E 3")
                return None   # caller will use DALL-E fallback
            else:
                print(f"[gemini_client] Error on attempt {attempt+1}: {err[:300]}")
                print(traceback.format_exc())
                if attempt == retries - 1:
                    return None

    return None


def _add_safety_prefix(prompt: str) -> str:
    return (
        "Create a tasteful, safe-for-all-audiences, non-sexual, non-violent image. "
        + prompt
    )


def fetch_image_bytes(url: str) -> bytes | None:
    """Download image from a URL (e.g. Supabase Storage public URL)."""
    try:
        resp = httpx.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f"[gemini_client] Failed to fetch image from {url}: {e}")
        return None
