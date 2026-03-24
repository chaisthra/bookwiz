"""
Seed taste profile from taste_profile_seed.json into Supabase.

Usage:
    cd bookWiz/backend
    python ../scripts/seed_taste_profile.py

It will list existing profiles and ask which one to update.
The full JSON from taste_profile_seed.json is written into profiles.taste_profile.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add backend to path so db imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from db.supabase_client import get_client  # noqa: E402

SEED_FILE = Path(__file__).parent.parent / "taste_profile_seed.json"


def main():
    if not SEED_FILE.exists():
        print(f"[seed] ERROR: {SEED_FILE} not found.")
        sys.exit(1)

    taste_profile = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    reader_name = taste_profile.get("reader_name", "unknown")
    books_count = taste_profile.get("books_processed", "?")
    print(f"\n[seed] Loaded taste profile for: {reader_name} ({books_count} books processed)")
    print(f"[seed] prompt_injection_template: {'YES' if taste_profile.get('prompt_injection_template') else 'NO'}\n")

    db = get_client()

    # List available profiles
    profiles = db.table("profiles").select("id,name").execute().data
    if not profiles:
        print("[seed] No profiles found in Supabase. Create a profile first via the app.")
        sys.exit(1)

    print("Available profiles:")
    for i, p in enumerate(profiles):
        print(f"  [{i}] {p['id']} — {p.get('name', '(unnamed)')}")

    choice = input("\nEnter index to update (or paste profile_id directly): ").strip()

    if choice.isdigit():
        idx = int(choice)
        if idx >= len(profiles):
            print("[seed] Invalid index.")
            sys.exit(1)
        profile_id = profiles[idx]["id"]
    else:
        profile_id = choice

    print(f"\n[seed] Writing taste profile to profiles.taste_profile for id={profile_id} …")

    result = (
        db.table("profiles")
        .update({"taste_profile": taste_profile})
        .eq("id", profile_id)
        .execute()
    )

    if result.data:
        print(f"[seed] Done. {reader_name}'s emotional fingerprint is now live in BookWiz.")
    else:
        print(f"[seed] WARNING: No rows updated. Check that profile_id '{profile_id}' exists.")


if __name__ == "__main__":
    main()
