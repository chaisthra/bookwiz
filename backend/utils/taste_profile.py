"""
Taste Profile utility — loads a reader's emotional fingerprint from Supabase
and formats it for injection into scene extraction prompts.

When no profile exists (pre-journal-upload), returns graceful defaults so
the pipeline still works without a taste profile.
"""
from __future__ import annotations

import json
from functools import lru_cache

from db.supabase_client import get_client

_EMPTY_PROFILE = {
    "emotional_triggers": [],
    "what_they_ignore": [],
    "how_they_classify_love": [],
    "narrative_values": [],
    "what_they_notice_others_miss": [],
    "recurring_phrases": [],
    "the_question_they_read_with": "",
}


def get_taste_profile(profile_id: str) -> dict:
    """
    Load taste profile from user_profiles table for the given profile_id.
    Returns empty profile dict if none found.
    """
    try:
        db = get_client()
        result = (
            db.table("user_profiles")
            .select("taste_profile")
            .eq("profile_id", profile_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0].get("taste_profile") or _EMPTY_PROFILE
    except Exception as e:
        print(f"[taste_profile] Failed to load profile for {profile_id}: {e}")
    return _EMPTY_PROFILE


def format_for_prompt(taste: dict) -> str:
    """
    Format the taste profile dict as a readable prompt block.
    Returns empty string if no meaningful data present.
    """
    if not taste or taste == _EMPTY_PROFILE:
        return ""

    parts: list[str] = []

    triggers = taste.get("emotional_triggers", [])
    if triggers:
        parts.append(f"What moves this reader: {'; '.join(triggers)}")

    ignores = taste.get("what_they_ignore", [])
    if ignores:
        parts.append(f"What she ignores: {'; '.join(ignores)}")

    love = taste.get("how_they_classify_love", [])
    if love:
        parts.append(f"How she reads love: {'; '.join(love)}")

    values = taste.get("narrative_values", [])
    if values:
        parts.append(f"What she believes good storytelling does: {'; '.join(values)}")

    notices = taste.get("what_they_notice_others_miss", [])
    if notices:
        parts.append(f"What she notices that others miss: {'; '.join(notices)}")

    phrases = taste.get("recurring_phrases", [])
    if phrases:
        parts.append(f"Her own language for what she loves: {'; '.join(phrases[:5])}")

    question = taste.get("the_question_they_read_with", "")
    if question:
        parts.append(f'The question she always reads with: "{question}"')

    return "\n".join(parts) if parts else ""
