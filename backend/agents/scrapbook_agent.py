"""
Scrapbook Agent — Phase 2

Uses GPT-4o to generate an aesthetic_brief (color palette, typography, layout style)
based on the book's genre, characters, and scene moods.
Inserts/upserts a record into the scrapbooks table.
"""
from __future__ import annotations

import json
import traceback
from collections import Counter

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from db.supabase_client import get_client

_SYSTEM = (
    "You are a creative director specialising in literary visual identity. "
    "You design the aesthetic language for book scrapbooks — color, typography, layout, mood. "
    "Always return valid JSON as instructed."
)

_BRIEF_PROMPT = """You are designing the visual identity for a {genre} book's scrapbook.

Book summary:
- Genre: {genre}
- Characters (name → emotional archetype):
{char_lines}
- Key scene moods: {mood_list}
- Dominant emotional texture: {dominant_mood}

Design a complete aesthetic brief. Return ONLY this JSON object, nothing else:
{{
  "overall_vibe": "2-3 word evocative descriptor (e.g. 'dark academia', 'sun-drenched longing')",
  "color_palette": {{
    "primary": "#hex",
    "secondary": "#hex",
    "accent": "#hex",
    "background": "#hex",
    "text": "#hex"
  }},
  "typography_mood": "one of: serif-classical | handwritten-intimate | editorial-bold | minimal-clean | gothic-ornate",
  "layout_style": "one of: editorial-grid | collage-layered | centered-minimal | film-strip | polaroid-scatter",
  "texture": "paper/material texture feel in one phrase (e.g. 'aged parchment with ink bleed')",
  "lighting_mood": "one of: golden-hour | candlelit | overcast | neon-dusk | stark-daylight | moonlit",
  "image_filter": "brief post-processing instruction (e.g. 'warm sepia tones, grain overlay')",
  "quote_card_style": "how quote cards should look in one sentence",
  "moodboard_composition": "how the scrapbook layout assembles — one sentence"
}}
"""

_FALLBACK_BRIEF = {
    "overall_vibe": "cinematic darkness",
    "color_palette": {
        "primary": "#c8a84b",
        "secondary": "#2a2a2a",
        "accent": "#c9a0a0",
        "background": "#141414",
        "text": "#e5e5e5",
    },
    "typography_mood": "serif-classical",
    "layout_style": "editorial-grid",
    "texture": "matte black with subtle grain",
    "lighting_mood": "candlelit",
    "image_filter": "desaturated with warm shadow tones",
    "quote_card_style": "dark card with gold left border and serif italic text",
    "moodboard_composition": "characters across the top, scenes below in a 2-column grid",
}


def _build_default_layout(characters: list[dict], scenes: list[dict], layout_style: str) -> dict:
    return {
        "version": 1,
        "sections": [
            {"id": "characters", "display": "grid", "order": 1},
            {"id": "scenes", "display": layout_style, "order": 2},
        ],
        "character_slots": [
            {"character_id": c.get("id"), "position": i, "size": "normal"}
            for i, c in enumerate(characters)
        ],
        "scene_slots": [
            {
                "scene_id": s.get("id"),
                "position": i,
                "size": "full" if i == 0 else "half",
            }
            for i, s in enumerate(scenes)
        ],
    }


def run_scrapbook_agent(
    book_id: str,
    genre: str,
    characters: list[dict],
    scenes: list[dict],
) -> dict:
    db = get_client()

    # Build prompt inputs
    role_priority = ["protagonist", "love_interest", "antagonist", "mentor", "supporting", "other"]
    sorted_chars = sorted(
        characters,
        key=lambda c: role_priority.index(c.get("inferred_traits", {}).get("role", "other"))
        if c.get("inferred_traits", {}).get("role", "other") in role_priority
        else 99,
    )
    char_lines = "\n".join(
        f"  - {c['name']}: {c.get('inferred_traits', {}).get('emotional_archetype', 'unknown')}"
        for c in sorted_chars[:6]
    )

    moods = [s.get("mood", "") for s in scenes if s.get("mood")]
    mood_list = ", ".join(moods) if moods else "varied"
    dominant_mood = Counter(moods).most_common(1)[0][0] if moods else "emotional"

    gpt = ChatOpenAI(model="gpt-4o", temperature=0.6)
    try:
        response = gpt.invoke([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=_BRIEF_PROMPT.format(
                genre=genre,
                char_lines=char_lines,
                mood_list=mood_list,
                dominant_mood=dominant_mood,
            )),
        ])
        text = response.content.strip()
        if text.startswith("```"):
            parts = text.split("```")
            inner = parts[1] if len(parts) > 1 else text
            if inner.startswith("json"):
                inner = inner[4:]
            text = inner.strip()
        aesthetic_brief = json.loads(text)
    except Exception as e:
        print(f"[scrapbook_agent] Failed to generate aesthetic brief: {e}")
        print(traceback.format_exc())
        aesthetic_brief = _FALLBACK_BRIEF

    layout_style = aesthetic_brief.get("layout_style", "editorial-grid")
    layout = _build_default_layout(characters, scenes, layout_style)

    record = {
        "book_id": book_id,
        "aesthetic_brief": aesthetic_brief,
        "layout": layout,
        "posted_pinterest": False,
        "posted_social": False,
        "finalised": False,
    }

    try:
        # Upsert — on_conflict requires a unique constraint on book_id
        # Use delete+insert pattern instead to avoid needing a constraint
        db.table("scrapbooks").delete().eq("book_id", book_id).execute()
        result = db.table("scrapbooks").insert(record).execute()
        if result.data:
            record["id"] = result.data[0]["id"]
    except Exception as e:
        print(f"[scrapbook_agent] DB write failed: {e}")
        print(traceback.format_exc())

    return record
