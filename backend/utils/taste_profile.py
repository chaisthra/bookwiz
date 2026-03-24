"""
Taste Profile utility — loads a reader's emotional fingerprint from Supabase
and formats it for injection into scene extraction prompts.

Reads from the `profiles` table (taste_profile JSONB column).
When no profile exists, returns graceful defaults so the pipeline still works.
"""
from __future__ import annotations

from db.supabase_client import get_client

_EMPTY_PROFILE: dict = {}


def get_taste_profile(profile_id: str) -> dict:
    """
    Load taste profile JSON from profiles.taste_profile for the given profile_id.
    Returns empty dict if none found.
    """
    try:
        db = get_client()
        result = (
            db.table("profiles")
            .select("taste_profile")
            .eq("id", profile_id)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0].get("taste_profile") or _EMPTY_PROFILE
    except Exception as e:
        print(f"[taste_profile] Failed to load profile for {profile_id}: {e}")
    return _EMPTY_PROFILE


def get_prompt_injection_template(taste: dict) -> str:
    """
    Return the rich prompt_injection_template string from the taste profile.
    This is the pre-written opinionated instruction string generated from the
    reading journal — far richer than format_for_prompt().
    Falls back to format_for_prompt() if template not present.
    """
    if not taste:
        return ""
    template = taste.get("prompt_injection_template", "")
    if template:
        return template
    return format_for_prompt(taste)


def format_for_prompt(taste: dict) -> str:
    """
    Format the taste profile dict as a readable prompt block.
    Used as fallback when prompt_injection_template is not set.
    Returns empty string if no meaningful data present.
    """
    if not taste:
        return ""

    parts: list[str] = []

    question = taste.get("the_question_she_reads_with", "") or taste.get("the_question_they_read_with", "")
    if question:
        parts.append(f'The question she always reads with: "{question}"')

    triggers = taste.get("emotional_triggers", [])
    if triggers:
        parts.append(f"What moves this reader: {'; '.join(triggers)}")

    ignores = taste.get("what_she_ignores", []) or taste.get("what_they_ignore", [])
    if ignores:
        parts.append(f"What she ignores: {'; '.join(ignores)}")

    values = taste.get("narrative_values", [])
    if values:
        parts.append(f"What she believes good storytelling does: {'; '.join(values)}")

    notices = taste.get("what_she_notices_that_others_miss", []) or taste.get("what_they_notice_others_miss", [])
    if notices:
        parts.append(f"What she notices that others miss: {'; '.join(notices)}")

    phrases = taste.get("recurring_phrases_in_her_own_words", []) or taste.get("recurring_phrases", [])
    if phrases:
        parts.append(f"Her own words for what she loves: {'; '.join(phrases[:5])}")

    return "\n".join(parts) if parts else ""
