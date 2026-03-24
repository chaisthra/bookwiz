"""
Character Agent (CA) — Phase 1

GPT-4o handles emotional inference and personality.
Gemini Flash handles structured JSON extraction of physical attributes.

Genre-conditional logic:
- Fiction / Fantasy / Romance / Classic / Thriller / Mystery:
    Infer appearance from emotional truth, archetype, language used around them.
    Never ask the user — fill gaps from context.
- Biography / Non-fiction / Self-help:
    Flag as real people (is_real_person=True).
    Physical descriptions come from text; visual lookup deferred to Phase 2.
"""
from __future__ import annotations

import json
import os
import traceback

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from db.supabase_client import get_client

_SYSTEM = (
    "You are a private literary analysis assistant. "
    "The user has uploaded their own personal copy of a book solely for private reading analysis. "
    "Your role is to identify and profile characters based on the text. "
    "Never reproduce extended copyrighted passages — describe and paraphrase in your own words. "
    "Always return valid JSON as instructed."
)

# ── Prompts ───────────────────────────────────────────────────────────────────

_IDENTIFY_PROMPT = """You are analysing a {genre} book to extract its significant characters or key people.

Read these excerpts and identify every character/person who matters to the story or argument.
For biography/non-fiction: these are real people — flag them as real.
For fiction/fantasy/romance/thriller: these are fictional — infer everything from context and emotional truth.

Respond with a JSON array. Each item:
{{
  "name": "Character name",
  "is_real_person": true/false,
  "role": "protagonist | antagonist | mentor | love_interest | supporting | subject | author | other",
  "first_appearance_hint": "brief description of the context where they first appear"
}}

Only list characters with meaningful presence. Maximum 8.

Book excerpts:
{text}
"""

_PROFILE_PROMPT = """You are building a deep character profile for a {genre} book.

Character: {name}
Role: {role}
Is real person: {is_real_person}

Using ALL excerpts provided, build this character's complete profile.
For fiction/fantasy/romance: infer physical appearance from emotional truth, archetype, how others react to them,
and language used around them. Fill every gap — do not leave fields blank.
For biography/non-fiction: extract factual descriptions from text only.

Respond with a single JSON object:
{{
  "physical": {{
    "hair": "...",
    "eyes": "...",
    "build": "...",
    "skin_tone": "...",
    "height": "...",
    "distinguishing_features": "..."
  }},
  "style": "Overall fashion/clothing aesthetic in one sentence",
  "personality": ["trait1", "trait2", "trait3", "trait4"],
  "emotional_archetype": "How this character FEELS to the reader — one evocative sentence",
  "inferred_traits": {{
    "primary_wound": "...",
    "core_desire": "...",
    "how_others_see_them": "..."
  }},
  "key_quote": "A 1-sentence paraphrase in your own words of the moment that most reveals this character's inner world — do not reproduce copyrighted text"
}}

Book excerpts (focus on scenes where {name} appears):
{text}
"""

# ── helpers ───────────────────────────────────────────────────────────────────

def _relevant_chunks(name: str, chunks: list[str], max_chunks: int = 6) -> list[str]:
    """Return chunks most likely to contain this character."""
    scored = [(c, c.lower().count(name.lower())) for c in chunks]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:max_chunks]]


def _safe_json(text: str) -> dict | list:
    text = text.strip()
    # Strip markdown code fences if present (handles ```json ... ``` or ``` ... ```)
    if text.startswith("```"):
        parts = text.split("```")
        # parts[1] is the content inside the first pair of fences
        inner = parts[1] if len(parts) > 1 else text
        # strip optional language tag on the same line as the opening fence
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()
    return json.loads(text)


# ── main ──────────────────────────────────────────────────────────────────────

def run_character_agent(
    book_id: str,
    genre: str,
    chunks: list[str],
) -> list[dict]:
    gpt = ChatOpenAI(model="gpt-4o", temperature=0.3)
    gemini = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.2,
        google_api_key=os.environ["GEMINI_API_KEY"],
    )

    # Step 1 — identify characters using first 5 chunks
    sample = "\n\n---\n\n".join(chunks[:5])
    identify_response = gpt.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=_IDENTIFY_PROMPT.format(genre=genre, text=sample)),
    ])
    try:
        character_list = _safe_json(identify_response.content)
    except Exception as e:
        print(f"[character_agent] Failed to parse character list JSON: {e}")
        print(f"[character_agent] Raw response: {identify_response.content[:500]}")
        return []

    characters: list[dict] = []
    db = get_client()

    for char_meta in character_list:
        name = char_meta.get("name", "")
        if not name:
            continue

        # Step 2 — build deep profile using Gemini Flash (faster + cheaper for structured extraction)
        relevant = _relevant_chunks(name, chunks)
        text_sample = "\n\n---\n\n".join(relevant)

        profile_response = gemini.invoke([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=_PROFILE_PROMPT.format(
                genre=genre,
                name=name,
                role=char_meta.get("role", "other"),
                is_real_person=char_meta.get("is_real_person", False),
                text=text_sample,
            )),
        ])
        try:
            profile = _safe_json(profile_response.content)
        except Exception as e:
            print(f"[character_agent] Failed to parse profile JSON for '{name}': {e}")
            print(f"[character_agent] Raw response: {profile_response.content[:500]}")
            profile = {}

        character = {
            "book_id": book_id,
            "name": name,
            "is_real_person": char_meta.get("is_real_person", False),
            "attributes": profile.get("physical", {}),
            "scene_outfits": {"default": profile.get("style", "")},
            "visual_profile": {},  # populated in Phase 2
            "inferred_traits": {
                "personality": profile.get("personality", []),
                "emotional_archetype": profile.get("emotional_archetype", ""),
                "role": char_meta.get("role", "other"),
                "key_quote": profile.get("key_quote", ""),
                **profile.get("inferred_traits", {}),
            },
        }

        # Upsert to Supabase
        try:
            result = (
                db.table("characters")
                .upsert(character, on_conflict="book_id,name")
                .execute()
            )
            if result.data:
                character["id"] = result.data[0]["id"]
        except Exception as e:
            print(f"[character_agent] DB upsert failed for '{name}': {e}")
            print(traceback.format_exc())
            character["db_error"] = str(e)

        characters.append(character)

    return characters
