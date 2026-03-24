"""
Guardrails utility — loads GUARDRAILS.md and applies content safety rules.

All agents call:
  - get_prompt_guardrails(genre)     → inject into LLM system prompts
  - sanitise_description(text, genre) → clean character/scene text before DB write
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

# ── Load GUARDRAILS.md once ───────────────────────────────────────────────────

_GUARDRAILS_PATH = Path(__file__).parent.parent.parent / "guardrails.md"


@lru_cache(maxsize=1)
def _load_raw() -> str:
    try:
        return _GUARDRAILS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def get_prompt_guardrails(genre: str) -> str:
    """
    Return a prompt-injectable guardrail block for the given genre.
    Includes universal rules + genre-specific rules.
    """
    raw = _load_raw()
    if not raw:
        return _FALLBACK_GUARDRAIL

    # Always include universal rules section
    universal = _extract_section(raw, "Universal Rules")

    # Include genre-specific section if it exists
    genre_map = {
        "romance":      "Romance",
        "fiction":      "Fiction",
        "fantasy":      "Fantasy",
        "thriller":     "Thriller",
        "mystery":      "Thriller",      # shares section
        "biography":    "Biography",
        "non-fiction":  "Biography",
        "self-help":    "Self-Help",
        "classic":      "Fiction",
        "other":        "Fiction",
    }
    section_name = genre_map.get(genre.lower(), "Fiction")
    genre_section = _extract_section(raw, section_name)

    # Always include the Prompt Engineering Rules
    prompt_rules = _extract_section(raw, "Prompt Engineering Rules")

    parts = ["=== CONTENT GUARDRAILS ==="]
    if universal:
        parts.append(universal)
    if genre_section:
        parts.append(f"GENRE-SPECIFIC ({genre.upper()}):\n{genre_section}")
    if prompt_rules:
        parts.append(prompt_rules)
    parts.append("=== END GUARDRAILS ===")

    return "\n\n".join(parts)


def sanitise_description(text: str, genre: str) -> str:
    """
    Apply keyword replacements to ensure character/scene descriptions
    are safe for all audiences before DB write and image generation.
    Romance-specific: preserve emotional truth, remove explicit language.
    """
    if not text:
        return text

    result = text
    for pattern, replacement in _REPLACEMENTS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Romance-specific: replace any remaining intimate physical descriptors
    if genre.lower() in ("romance", "fiction", "classic"):
        for pattern, replacement in _ROMANCE_EXTRAS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result.strip()


def get_image_safety_suffix(genre: str) -> str:
    """Append to every image generation prompt."""
    base = (
        "Safe for all audiences. No nudity. No sexual content. "
        "No graphic violence or gore. No disturbing imagery. "
        "Avoid: explicit content, graphic injury, sexual suggestion. "
        "Style: cinematic, atmospheric, emotionally evocative. "
        "Imply rather than depict where content is sensitive."
    )
    if genre.lower() == "romance":
        base += (
            " Convey emotional intimacy through body language, expression, and atmosphere only. "
            "Characters fully clothed. No physical contact beyond hand-holding or an embrace."
        )
    return base


# ── Replacement tables ────────────────────────────────────────────────────────

_REPLACEMENTS: list[tuple[str, str]] = [
    # Explicit sexual language → neutral
    (r"\bseductive\b", "confident"),
    (r"\bsensual\b", "expressive"),
    (r"\balluring\b", "compelling"),
    (r"\bsultry\b", "warm"),
    (r"\bprovocative\b", "striking"),
    (r"\berotic\b", "emotionally charged"),
    (r"\bsexual tension\b", "charged emotional tension"),
    (r"\bsex scene\b", "intimate moment"),
    (r"\bmaking love\b", "tender connection"),
    (r"\bpassionate kiss\b", "meaningful moment"),
    (r"\bnaked\b", "unguarded"),
    (r"\bnude\b", "natural"),
    (r"\bexplicit\b", "vivid"),
    (r"\bsexy\b", "attractive"),
    # Violence language → atmospheric
    (r"\bgraphic violence\b", "intense confrontation"),
    (r"\bgore\b", "aftermath"),
    (r"\bbloody\b", "harrowing"),
    (r"\btorture\b", "ordeal"),
    (r"\bmutilat\w*\b", "wounded"),
]

_ROMANCE_EXTRAS: list[tuple[str, str]] = [
    (r"\bbody\b(?=.*desire)", "presence"),
    (r"\bhot\b(?=.*touch|.*kiss|.*breath)", "warm"),
    (r"\bdesire\b", "longing"),
    (r"\blust\b", "yearning"),
    (r"\barouse\w*\b", "moved"),
    (r"\bpassion\b", "emotion"),
    (r"\bintimate\b", "quiet"),
]

_FALLBACK_GUARDRAIL = (
    "CONTENT SAFETY: Never generate sexual content, graphic violence, nudity, "
    "or disturbing imagery. Preserve emotional truth through atmosphere and implication. "
    "All output must be safe for general audiences."
)


# ── Section extractor ─────────────────────────────────────────────────────────

def _extract_section(text: str, keyword: str) -> str:
    """Extract a markdown section containing `keyword` in its heading."""
    lines = text.split("\n")
    in_section = False
    section_lines: list[str] = []

    for line in lines:
        if re.search(rf"#+\s.*{re.escape(keyword)}", line, re.IGNORECASE):
            in_section = True
            section_lines = []
            continue
        if in_section:
            # Stop at the next same-or-higher level heading
            if re.match(r"^#{1,3}\s", line) and section_lines:
                break
            section_lines.append(line)

    return "\n".join(section_lines).strip()
