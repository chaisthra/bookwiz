"""
Scene Extraction Agent (SEA) — Phase 1

GPT-4o — feeling-first extraction.
Finds scenes that give chills, cause tears, refuse to leave the reader's head.

Genre-conditional:
- Fiction/Romance/Fantasy/Thriller: emotional character moments, tension peaks,
  relationship turning points, atmospheric beauty
- Biography: life-defining decisions, pivotal human experiences, triumph/loss
- Non-fiction/Self-help: ideas that hit hard, paradigm shifts, moments of clarity
"""
from __future__ import annotations

import json
import traceback

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from db.supabase_client import get_client

_SYSTEM = (
    "You are a private literary analysis assistant. "
    "The user has uploaded their own personal copy of a book solely for private reading analysis. "
    "Your role is to identify emotionally significant moments and analyse them. "
    "Never reproduce extended copyrighted passages — instead describe and paraphrase scenes "
    "in your own analytical language. Always return valid JSON as instructed."
)

# ── Prompts ───────────────────────────────────────────────────────────────────

_SCENE_PROMPT = """You are reading a {genre} book and finding its most emotionally powerful moments.

Your job: find scenes that FEEL significant — not just plot-important.
Look for:
- Moments that give chills or raise goosebumps
- Scenes that could make a reader cry
- Moments that refuse to leave the head after the book is finished
- Visceral beauty, aching tension, gut-punch revelations, quiet devastating truth

Genre guidance:
- romance/fantasy/fiction/thriller/mystery/classic: emotional character moments,
  relationship turning points, atmospheric beauty, dread or longing
- biography/non-fiction: pivotal life decisions, moments of triumph or crushing loss,
  defining human experiences
- self-help: ideas that land like a revelation, paradigm shifts, moments of uncomfortable truth

Taste preferences to apply (if any): {taste_hints}

Read all excerpts and return the top 6 most emotionally powerful moments as JSON array.
Each item:
{{
  "scene_index": <integer, 1-based order in the book>,
  "title": "Short evocative title for this scene (5 words max)",
  "mood": "one word: tender | devastating | triumphant | terrifying | aching | electric | haunting | joyful | defiant | quiet",
  "emotional_context": "One sentence explaining WHY this scene hits hard",
  "characters_present": ["name1", "name2"],
  "quote": "A 1-2 sentence paraphrase in your own words capturing the emotional peak of this scene — do not reproduce copyrighted text",
  "context_snippet": "2-3 sentences of context setting up this scene",
  "emotional_weight_score": <float 0.0-1.0, higher = more emotionally powerful>
}}

Sort by emotional_weight_score descending. Return ONLY valid JSON.

Book excerpts:
{text}
"""

# ── helpers ───────────────────────────────────────────────────────────────────

def _taste_hints(preferences: dict) -> str:
    if not preferences:
        return "none provided"
    tropes = preferences.get("tropes", [])
    emotional = preferences.get("emotional_fingerprint", {})
    genres = preferences.get("genres", [])
    parts = []
    if genres:
        parts.append(f"Preferred genres: {', '.join(genres)}")
    if tropes:
        parts.append(f"Loved tropes: {', '.join(tropes[:5])}")
    if emotional:
        parts.append(f"Emotional preferences: {json.dumps(emotional)}")
    return "; ".join(parts) if parts else "none provided"


def _safe_json(text: str) -> list:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        inner = parts[1] if len(parts) > 1 else text
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()
    return json.loads(text)


# ── main ──────────────────────────────────────────────────────────────────────

def _sample_chunks(chunks: list[str], max_chunks: int = 40) -> list[str]:
    """
    Return at most max_chunks chunks sampled evenly across the book.
    Always includes the first and last chunk to capture opening/closing scenes.
    """
    n = len(chunks)
    if n <= max_chunks:
        return chunks
    # Evenly spaced indices across the full range
    step = n / max_chunks
    indices = sorted(set(int(i * step) for i in range(max_chunks)))
    return [chunks[i] for i in indices]


def run_scene_agent(
    book_id: str,
    genre: str,
    chunks: list[str],
    user_preferences: dict,
    mode: str = "manual",
) -> list[dict]:
    gpt = ChatOpenAI(model="gpt-4o", temperature=0.4)

    # Sample the book to at most 40 chunks (4 batches × 10) to keep latency under 2 min.
    # Sampling is spread evenly so all narrative phases are covered.
    sampled = _sample_chunks(chunks, max_chunks=40)
    print(f"[scene_agent] Processing {len(sampled)}/{len(chunks)} chunks ({len(sampled)//10 + 1} batches)")

    batch_size = 10
    all_candidates: list[dict] = []

    for i in range(0, len(sampled), batch_size):
        batch = sampled[i : i + batch_size]
        text = "\n\n---\n\n".join(batch)

        response = gpt.invoke([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=_SCENE_PROMPT.format(
                genre=genre,
                taste_hints=_taste_hints(user_preferences),
                text=text,
            )),
        ])
        try:
            batch_scenes = _safe_json(response.content)
            all_candidates.extend(batch_scenes)
        except Exception as e:
            print(f"[scene_agent] Failed to parse batch {i//batch_size} JSON: {e}")
            print(f"[scene_agent] Raw response: {response.content[:500]}")
            continue

    # Re-rank by emotional_weight_score, keep top 6
    all_candidates.sort(
        key=lambda s: float(s.get("emotional_weight_score", 0)), reverse=True
    )
    top_scenes = all_candidates[:6]

    db = get_client()
    stored: list[dict] = []

    # Delete any previously extracted scenes for this book before inserting fresh ones
    # (ensures idempotency on retry without needing a unique constraint on scene_index)
    try:
        db.table("scenes").delete().eq("book_id", book_id).execute()
    except Exception as e:
        print(f"[scene_agent] Failed to clear old scenes for book {book_id}: {e}")

    for scene in top_scenes:
        record = {
            "book_id": book_id,
            "scene_index": scene.get("scene_index"),
            "title": scene.get("title", ""),
            "mood": scene.get("mood", ""),
            "emotional_context": scene.get("emotional_context", ""),
            "characters_present": scene.get("characters_present", []),
            "quote": scene.get("quote", ""),
            "context_snippet": scene.get("context_snippet", ""),
            "emotional_weight_score": scene.get("emotional_weight_score", 0.0),
            "user_approved": None,  # set after user selection in manual mode
        }

        try:
            result = db.table("scenes").insert(record).execute()
            if result.data:
                record["id"] = result.data[0]["id"]
        except Exception as e:
            print(f"[scene_agent] DB insert failed for scene '{record.get('title')}': {e}")
            print(traceback.format_exc())
            record["db_error"] = str(e)

        stored.append(record)

    return stored
