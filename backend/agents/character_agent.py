"""
Character Agent — feature/gemini-emotional-engine

GPT-5.4 identifies characters from the full book text.
Gemini 2.5 Flash builds a deep profile using full book context.

Genre-conditional logic:
- Fiction / Fantasy / Romance / Classic / Thriller / Mystery:
    Infer appearance from emotional truth, archetype, language used around them.
- Biography / Non-fiction / Self-help:
    Flag as real people (is_real_person=True). Use text descriptions only.
"""
from __future__ import annotations

import json
import os
import traceback

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from db.supabase_client import get_client
from utils.guardrails import sanitise_description

_GPT_SYSTEM = (
    "You are a private literary analysis assistant. "
    "The user has uploaded their own personal copy of a book solely for private reading analysis. "
    "Identify and profile characters based on the text. "
    "Never reproduce extended copyrighted passages — describe and paraphrase in your own words. "
    "Always return valid JSON as instructed."
)

_GEMINI_SYSTEM = (
    "You are building a detailed character profile for a literary analysis tool. "
    "Use the full book text to build the richest possible profile. "
    "Be specific about physical appearance, emotional truth, and narrative role. "
    "Never reproduce extended copyrighted text. Return valid JSON only."
)

# ── Prompts ───────────────────────────────────────────────────────────────────

_IDENTIFY_PROMPT = """You are analysing a {genre} book to extract its significant characters.

Read the full book text and identify every character/person who matters to the story.
For biography/non-fiction: these are real people — flag them as real.
For fiction/fantasy/romance/thriller: these are fictional — infer everything from context.

Respond with a JSON array. Each item:
{{
  "name": "Character name",
  "is_real_person": true/false,
  "role": "protagonist | antagonist | mentor | love_interest | supporting | subject | author | other",
  "first_appearance_hint": "brief context of where they first appear"
}}

Only list characters with meaningful presence. Maximum 8 characters.
Return ONLY valid JSON array.

FULL BOOK TEXT:
{text}
"""

_PROFILE_PROMPT = """Build a deep character profile for this character in a {genre} book.

Character: {name}
Role: {role}
Is real person: {is_real_person}

Read the full book and build this character's complete profile.
For fiction/fantasy/romance: infer physical appearance from emotional truth, archetype,
how others react to them, and language used around them. Fill every gap.
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

Return ONLY valid JSON.

FULL BOOK TEXT:
{text}
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_json(text: str) -> dict | list:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        inner = parts[1] if len(parts) > 1 else text
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()
    return json.loads(text)


# ── Main ──────────────────────────────────────────────────────────────────────

def run_character_agent(
    book_id: str,
    genre: str,
    chunks: list[str],
    full_text: str = "",
) -> list[dict]:
    """
    Step 1: GPT-5.4 identifies characters from full book text.
    Step 2: Gemini 2.5 Flash builds deep profile per character using full book context.
    """
    if not full_text:
        full_text = "\n\n".join(chunks)

    full_text = full_text[:900_000]

    gpt = ChatOpenAI(model="gpt-5.4", temperature=0.2)
    gemini = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.2,
        google_api_key=os.environ["GEMINI_API_KEY"],
    )

    # Step 1 — Identify characters with GPT-5.4
    print(f"[character_agent] Step 1: GPT-5.4 identifying characters ({len(full_text):,} chars)")
    try:
        identify_response = gpt.invoke([
            SystemMessage(content=_GPT_SYSTEM),
            HumanMessage(content=_IDENTIFY_PROMPT.format(genre=genre, text=full_text)),
        ])
        character_list = _safe_json(identify_response.content)
        print(f"[character_agent] Found {len(character_list)} characters")
    except Exception as e:
        print(f"[character_agent] Failed to parse character list: {e}")
        print(f"[character_agent] Raw: {getattr(identify_response, 'content', '')[:500]}")
        return []

    characters: list[dict] = []
    db = get_client()

    for char_meta in character_list:
        name = char_meta.get("name", "")
        if not name:
            continue

        # Step 2 — Build deep profile with Gemini 2.5 Flash
        print(f"[character_agent] Step 2: Gemini building profile for '{name}'")
        try:
            profile_response = gemini.invoke([
                SystemMessage(content=_GEMINI_SYSTEM),
                HumanMessage(content=_PROFILE_PROMPT.format(
                    genre=genre,
                    name=name,
                    role=char_meta.get("role", "other"),
                    is_real_person=char_meta.get("is_real_person", False),
                    text=full_text,
                )),
            ])
            profile = _safe_json(profile_response.content)
        except Exception as e:
            print(f"[character_agent] Failed profile for '{name}': {e}")
            profile = {}

        # Sanitise all free-text fields before DB write
        emotional_archetype = sanitise_description(
            profile.get("emotional_archetype", ""), genre
        )
        key_quote = sanitise_description(profile.get("key_quote", ""), genre)
        style = sanitise_description(profile.get("style", ""), genre)

        inferred = profile.get("inferred_traits", {})
        for k in inferred:
            inferred[k] = sanitise_description(str(inferred[k]), genre)

        character = {
            "book_id": book_id,
            "name": name,
            "is_real_person": char_meta.get("is_real_person", False),
            "attributes": profile.get("physical", {}),
            "scene_outfits": {"default": style},
            "visual_profile": {},
            "inferred_traits": {
                "personality": profile.get("personality", []),
                "emotional_archetype": emotional_archetype,
                "role": char_meta.get("role", "other"),
                "key_quote": key_quote,
                **inferred,
            },
        }

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
