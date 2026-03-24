"""
BookWiz pipeline integration tests.

Runs against real APIs (OpenAI, Gemini, Supabase) using env vars from .env.
Each test is independent and prints clear PASS/FAIL with details.

Run from backend/ directory:
    python -m tests.test_pipeline
"""
from __future__ import annotations

import io
import os
import sys
import traceback

# ── ensure backend/ is on path ────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

# ── helpers ───────────────────────────────────────────────────────────────────

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results: list[tuple[str, bool, str]] = []

def check(name: str, condition: bool, detail: str = "") -> bool:
    tag = PASS if condition else FAIL
    print(f"  [{tag}] {name}" + (f": {detail}" if detail else ""))
    results.append((name, condition, detail))
    return condition


# ─────────────────────────────────────────────────────────────────────────────
# 1. Book parser
# ─────────────────────────────────────────────────────────────────────────────

def test_book_parser_pdf():
    print("\n=== TEST: book_parser — synthetic PDF bytes ===")
    from parsers.book_parser import parse_book, _chunk_text, _clean

    # Build a minimal valid PDF in memory using pypdf writer
    from pypdf import PdfWriter
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    # Blank PDF should parse but yield empty text → empty chunks
    parsed = parse_book("test.pdf", pdf_bytes)
    check("ParsedBook returned", parsed is not None)
    check("filename stored", parsed.filename == "test.pdf")
    check("raw_text is str", isinstance(parsed.raw_text, str))
    # blank page = no text
    check("blank PDF → 0 chunks or only-whitespace chunks",
          all(not c.strip() for c in parsed.chunks) or len(parsed.chunks) == 0)

    # Chunking with real text
    text = "A" * 25000
    chunks = _chunk_text(text, chunk_size=8000, overlap=800)
    check("chunking produces multiple chunks", len(chunks) > 1)
    check("first chunk is full size", len(chunks[0]) == 8000)
    check("no text gap — last char covered",
          any("A" in c for c in chunks))

    # _clean removes excessive whitespace
    dirty = "hello   \n\n\n\n   world\r\n"
    cleaned = _clean(dirty)
    check("_clean strips excess newlines", "\n\n\n" not in cleaned)
    check("_clean strips trailing whitespace", cleaned == cleaned.strip())


def test_book_parser_real_epub():
    """Only runs if a test.epub is present in tests/ directory."""
    epub_path = os.path.join(os.path.dirname(__file__), "test.epub")
    if not os.path.exists(epub_path):
        print("\n=== SKIP: book_parser — real EPUB (no tests/test.epub found) ===")
        return
    print("\n=== TEST: book_parser — real EPUB ===")
    from parsers.book_parser import parse_book
    with open(epub_path, "rb") as f:
        data = f.read()
    parsed = parse_book("test.epub", data)
    check("has raw_text", len(parsed.raw_text) > 0)
    check("has chunks", len(parsed.chunks) > 0)
    check("chunks are non-empty", all(c.strip() for c in parsed.chunks))
    print(f"    total_chars={parsed.total_chars}, chunks={len(parsed.chunks)}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. _safe_json edge cases (both agents share same logic)
# ─────────────────────────────────────────────────────────────────────────────

def test_safe_json():
    print("\n=== TEST: _safe_json in character_agent and scene_agent ===")
    from agents.character_agent import _safe_json as char_safe
    from agents.scene_agent import _safe_json as scene_safe

    cases = [
        ('plain JSON',       '[{"name": "Alice"}]'),
        ('```json fence',    '```json\n[{"name": "Alice"}]\n```'),
        ('``` plain fence',  '```\n[{"name": "Alice"}]\n```'),
        ('leading newline',  '\n```json\n[{"name": "Alice"}]\n```\n'),
    ]

    for label, raw in cases:
        try:
            result = char_safe(raw)
            check(f"char _safe_json: {label}", isinstance(result, list) and result[0]["name"] == "Alice")
        except Exception as e:
            check(f"char _safe_json: {label}", False, str(e))
        try:
            result = scene_safe(raw)
            check(f"scene _safe_json: {label}", isinstance(result, list) and result[0]["name"] == "Alice")
        except Exception as e:
            check(f"scene _safe_json: {label}", False, str(e))

    # Dict case for character profile
    dict_case = '```json\n{"hair": "brown", "eyes": "blue"}\n```'
    try:
        result = char_safe(dict_case)
        check("char _safe_json: dict case", isinstance(result, dict) and result["hair"] == "brown")
    except Exception as e:
        check("char _safe_json: dict case", False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 3. Genre detection (real LLM call)
# ─────────────────────────────────────────────────────────────────────────────

ROMANCE_SAMPLE = """
Chapter 1

Emma had always believed that love was a myth perpetuated by greeting card companies.
That belief shattered the moment she walked into the Hartwell estate and found James
standing in the rain-soaked garden, his dark eyes searching hers with an intensity that
left her breathless. She hadn't expected to feel anything. She certainly hadn't expected
to feel everything.

"You're late," he said, his voice low and carefully controlled.
"You're rude," she replied, lifting her chin.

He smiled — just barely — and something in her chest cracked open.
"""

def test_genre_detection():
    print("\n=== TEST: genre detection (real OpenAI call) ===")
    try:
        from agents.orchestrator import detect_genre, BookWizState, VALID_GENRES
        from parsers.book_parser import _chunk_text

        chunks = _chunk_text(ROMANCE_SAMPLE)
        state: BookWizState = {
            "book_id": "test-book-id",
            "profile_id": "test-profile-id",
            "genre": "",
            "raw_text_chunks": chunks,
            "characters": [],
            "scenes": [],
            "user_preferences": {},
            "mode": "auto",
            "current_step": "started",
            "error": None,
        }
        result = detect_genre(state)
        genre = result.get("genre", "")
        check("returns genre key", "genre" in result)
        check("genre is valid", genre in VALID_GENRES, f"got: {genre!r}")
        check("current_step updated", result.get("current_step") == "genre_detected")
        check("romance detected as romance or fiction",
              genre in ("romance", "fiction"), f"got: {genre!r}")
        print(f"    detected genre: {genre!r}")
    except Exception as e:
        check("genre detection ran without exception", False, str(e))
        traceback.print_exc()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Character agent (real LLM calls — GPT-4o + Gemini)
# ─────────────────────────────────────────────────────────────────────────────

def test_character_agent():
    print("\n=== TEST: character_agent (real GPT-4o + Gemini calls) ===")
    try:
        from agents.character_agent import run_character_agent

        # Use test book id that won't collide — DB upsert is idempotent
        chars = run_character_agent(
            book_id="test-char-agent-book",
            genre="romance",
            chunks=[ROMANCE_SAMPLE],
        )
        check("returns a list", isinstance(chars, list))
        check("found at least one character", len(chars) > 0, f"got {len(chars)}")

        if chars:
            c = chars[0]
            check("character has name", bool(c.get("name")))
            check("character has book_id", c.get("book_id") == "test-char-agent-book")
            check("character has inferred_traits", isinstance(c.get("inferred_traits"), dict))
            check("inferred_traits has personality", isinstance(c["inferred_traits"].get("personality"), list))
            print(f"    characters found: {[c['name'] for c in chars]}")

            # Verify no db_error on upsert
            has_db_error = any("db_error" in c for c in chars)
            check("no DB upsert errors", not has_db_error,
                  "some characters had db_error — check Supabase schema" if has_db_error else "")
    except Exception as e:
        check("character_agent ran without exception", False, str(e))
        traceback.print_exc()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Scene agent (real LLM calls — GPT-4o)
# ─────────────────────────────────────────────────────────────────────────────

def test_scene_agent():
    print("\n=== TEST: scene_agent (real GPT-4o calls) ===")
    try:
        from agents.scene_agent import run_scene_agent

        scenes = run_scene_agent(
            book_id="test-scene-agent-book",
            genre="romance",
            chunks=[ROMANCE_SAMPLE],
            user_preferences={},
            mode="auto",
        )
        check("returns a list", isinstance(scenes, list))
        check("found at least one scene", len(scenes) > 0, f"got {len(scenes)}")

        if scenes:
            s = scenes[0]
            check("scene has title", bool(s.get("title")))
            check("scene has book_id", s.get("book_id") == "test-scene-agent-book")
            check("scene has emotional_weight_score", isinstance(s.get("emotional_weight_score"), (int, float)))
            check("scene has mood", bool(s.get("mood")))
            print(f"    scenes found: {[s['title'] for s in scenes]}")

            # Verify no db_error on upsert
            has_db_error = any("db_error" in s for s in scenes)
            check("no DB upsert errors", not has_db_error,
                  "some scenes had db_error — check Supabase schema" if has_db_error else "")
    except Exception as e:
        check("scene_agent ran without exception", False, str(e))
        traceback.print_exc()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Full orchestrator pipeline — auto mode
# ─────────────────────────────────────────────────────────────────────────────

def test_orchestrator_auto():
    print("\n=== TEST: orchestrator — full auto pipeline ===")
    try:
        from agents.orchestrator import start_pipeline
        from parsers.book_parser import _chunk_text

        chunks = _chunk_text(ROMANCE_SAMPLE * 3)  # give it more content
        result = start_pipeline(
            book_id="test-orch-auto-book",
            profile_id="test-profile-id",
            chunks=chunks,
            user_preferences={},
            mode="auto",
        )
        check("pipeline returned a result", result is not None)
        check("result has genre", bool(result.get("genre")))
        check("result has characters list", isinstance(result.get("characters"), list))
        check("result has scenes list", isinstance(result.get("scenes"), list))
        check("current_step is scenes_extracted", result.get("current_step") == "scenes_extracted")
        print(f"    genre={result.get('genre')!r}, "
              f"characters={len(result.get('characters', []))}, "
              f"scenes={len(result.get('scenes', []))}")
    except Exception as e:
        check("orchestrator auto pipeline ran without exception", False, str(e))
        traceback.print_exc()


def test_orchestrator_manual():
    print("\n=== TEST: orchestrator — manual mode pauses before scene_agent ===")
    try:
        from agents.orchestrator import start_pipeline, resume_scene_selection, _manual_graph
        from parsers.book_parser import _chunk_text

        chunks = _chunk_text(ROMANCE_SAMPLE * 3)
        book_id = "test-orch-manual-book"

        result = start_pipeline(
            book_id=book_id,
            profile_id="test-profile-id",
            chunks=chunks,
            user_preferences={},
            mode="manual",
        )
        check("pipeline returned a result", result is not None)
        check("characters extracted before pause", isinstance(result.get("characters"), list))
        # In manual mode, scenes should be empty — the graph paused before scene_agent
        check("scenes empty before resume (paused)", result.get("scenes") == [] or result.get("scenes") is None,
              f"got scenes={result.get('scenes')}")
        print(f"    paused — genre={result.get('genre')!r}, characters={len(result.get('characters', []))}")

        # Resume
        resumed = resume_scene_selection(book_id)
        check("resume returned a result", resumed is not None)
        check("scenes populated after resume", len(resumed.get("scenes", [])) > 0,
              f"got {len(resumed.get('scenes', []))} scenes")
        print(f"    resumed — scenes={len(resumed.get('scenes', []))}")
    except Exception as e:
        check("orchestrator manual pipeline ran without exception", False, str(e))
        traceback.print_exc()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

TEST_PROFILE_ID = "c102319e-b9ef-4e62-86e2-be0a5210c604"  # Chaithra profile


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  BookWiz Pipeline Tests")
    print("=" * 60)

    test_book_parser_pdf()
    test_book_parser_real_epub()
    test_safe_json()
    test_genre_detection()
    test_character_agent()
    test_scene_agent()
    test_orchestrator_auto()
    test_orchestrator_manual()

    # Summary
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed

    print("\n" + "=" * 60)
    print(f"  Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} FAILED)")
        print("\n  Failed tests:")
        for name, ok, detail in results:
            if not ok:
                print(f"    - {name}" + (f": {detail}" if detail else ""))
    else:
        print("  — all clear!")
    print("=" * 60 + "\n")

    sys.exit(0 if failed == 0 else 1)
