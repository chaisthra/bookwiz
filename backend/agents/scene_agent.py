"""
Scene Extraction Agent — feature/gemini-emotional-engine

Step 1: Gemini 2.5 Flash reads the FULL book text in one call and returns 12 scene candidates.
Step 2: GPT-5.4 re-ranks candidates to top 6 using the reader's taste profile.

No chunking. No batching. One fast pass, then one emotional curation pass.
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
from utils.taste_profile import get_prompt_injection_template, get_taste_profile

_GEMINI_SYSTEM = (
    "You are a private literary analysis assistant. "
    "The user has uploaded their own personal copy of a book solely for private reading analysis. "
    "Identify emotionally significant scenes and describe them analytically in your own words. "
    "Never reproduce extended copyrighted passages. Always return valid JSON as instructed."
)

_GPT_SYSTEM = (
    "You are a deeply empathetic literary curator. "
    "Your job is to select scenes that will resonate most powerfully with a specific reader's "
    "emotional fingerprint. You rank by felt resonance, not plot importance. "
    "Return valid JSON only."
)

# ── Prompts ────────────────────────────────────────────────────────────────────

_GEMINI_EXTRACT_PROMPT = """You are reading a {genre} book. Find the 12 most emotionally powerful moments.

Look for:
- Moments that give chills or raise goosebumps
- Scenes that could make a reader cry
- Gut-punch revelations, quiet devastating truth
- Visceral beauty, aching tension, defiant triumph
- Atmospheric beauty that lingers long after reading

Genre guidance:
- romance/fantasy/fiction/thriller/mystery/classic: emotional character moments,
  relationship turning points, dread or longing
- biography/non-fiction: pivotal life decisions, triumph, crushing loss
- self-help: ideas that land like revelation, uncomfortable truths

Return a JSON array of exactly 12 items. Each item:
{{
  "scene_index": <integer, 1-based chronological order>,
  "title": "Evocative 5-word-max title",
  "mood": "tender | devastating | triumphant | terrifying | aching | electric | haunting | joyful | defiant | quiet",
  "emotional_context": "One sentence: WHY this scene hits hard",
  "characters_present": ["name1", "name2"],
  "quote": "1-2 sentence paraphrase in your own analytical words capturing the emotional peak — never reproduce copyrighted text",
  "context_snippet": "2-3 sentences setting up this scene",
  "emotional_weight_score": <float 0.0-1.0>
}}

Sort by emotional_weight_score descending. Return ONLY valid JSON array.

FULL BOOK TEXT:
{text}
"""

_GPT_RERANK_PROMPT = """You are selecting which 6 of these 12 scenes will hit hardest for THIS specific reader.

HOW THIS READER READS:
{taste_profile}

SCENE CANDIDATES (from a {genre} book):
{candidates_json}

Apply the reader's sensibility above to choose the 6 scenes that will land most truthfully for her.
Prioritise: emotional cost, mutuality, the moment before the dramatic peak, earned endings.
Deprioritise: grand gestures, intensity without depth, one-sided emotional arcs.
If no taste profile is provided, select purely by emotional weight score.

Return a JSON array of exactly 6 scene objects — same structure as input, preserving all fields.
Sort by predicted resonance for this reader. Return ONLY valid JSON array.
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_json(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        inner = parts[1] if len(parts) > 1 else text
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()
    return json.loads(text)


# ── Main ──────────────────────────────────────────────────────────────────────

def run_scene_agent(
    book_id: str,
    genre: str,
    chunks: list[str],
    user_preferences: dict,
    mode: str = "manual",
    full_text: str = "",
    profile_id: str = "",
) -> list[dict]:
    """
    Step 1: Gemini 2.5 Flash — extract 12 candidates from full book (1 API call).
    Step 2: GPT-5.4 — re-rank to top 6 using reader taste profile (1 API call).
    """
    # Build full text if not supplied by orchestrator
    if not full_text:
        full_text = "\n\n".join(chunks)

    # Truncate to ~900k chars to stay within 1M token limit safely
    full_text = full_text[:900_000]

    gemini = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        google_api_key=os.environ["GEMINI_API_KEY"],
    )

    gpt = ChatOpenAI(model="gpt-5.4", temperature=0.4)

    # ── Step 1: Gemini full-book extraction ───────────────────────────────────
    print(f"[scene_agent] Step 1: Gemini 2.5 Flash full-book extraction ({len(full_text):,} chars)")
    try:
        gemini_response = gemini.invoke([
            SystemMessage(content=_GEMINI_SYSTEM),
            HumanMessage(content=_GEMINI_EXTRACT_PROMPT.format(
                genre=genre,
                text=full_text,
            )),
        ])
        candidates = _safe_json(gemini_response.content)
        print(f"[scene_agent] Gemini returned {len(candidates)} candidates")
    except Exception as e:
        print(f"[scene_agent] Gemini extraction failed: {e}")
        print(traceback.format_exc())
        candidates = []

    if not candidates:
        print("[scene_agent] No candidates — returning empty")
        return []

    # ── Step 2: GPT-5.4 re-ranking with taste profile ─────────────────────────
    taste = {}
    if profile_id:
        taste = get_taste_profile(profile_id)
    if not taste and user_preferences:
        taste = user_preferences

    taste_text = get_prompt_injection_template(taste) if taste else "No taste profile available — rank by emotional weight."
    print(f"[scene_agent] Step 2: GPT-5.4 re-ranking with taste profile")

    try:
        gpt_response = gpt.invoke([
            SystemMessage(content=_GPT_SYSTEM),
            HumanMessage(content=_GPT_RERANK_PROMPT.format(
                taste_profile=taste_text,
                genre=genre,
                candidates_json=json.dumps(candidates, indent=2),
            )),
        ])
        top_scenes = _safe_json(gpt_response.content)[:6]
        print(f"[scene_agent] GPT-5.4 selected {len(top_scenes)} scenes")
    except Exception as e:
        print(f"[scene_agent] GPT-5.4 re-ranking failed: {e} — falling back to score sort")
        candidates.sort(key=lambda s: float(s.get("emotional_weight_score", 0)), reverse=True)
        top_scenes = candidates[:6]

    # ── Persist to DB ─────────────────────────────────────────────────────────
    db = get_client()

    try:
        db.table("scenes").delete().eq("book_id", book_id).execute()
    except Exception as e:
        print(f"[scene_agent] Failed to clear old scenes: {e}")

    stored: list[dict] = []
    for scene in top_scenes:
        record = {
            "book_id": book_id,
            "scene_index": scene.get("scene_index"),
            "title": scene.get("title", ""),
            "mood": scene.get("mood", ""),
            "emotional_context": sanitise_description(scene.get("emotional_context", ""), genre),
            "characters_present": scene.get("characters_present", []),
            "quote": sanitise_description(scene.get("quote", ""), genre),
            "context_snippet": sanitise_description(scene.get("context_snippet", ""), genre),
            "emotional_weight_score": scene.get("emotional_weight_score", 0.0),
            "user_approved": None,
        }
        try:
            result = db.table("scenes").insert(record).execute()
            if result.data:
                record["id"] = result.data[0]["id"]
        except Exception as e:
            print(f"[scene_agent] DB insert failed for '{record.get('title')}': {e}")
            record["db_error"] = str(e)

        stored.append(record)

    return stored
