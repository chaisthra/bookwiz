"""
Minimal test script for Gemini image generation.

Run from bookWiz root:
    python scripts/test_gemini_image.py
"""
import os
import sys
from pathlib import Path

# Load .env from backend directory
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

# Add backend to sys.path so backend modules are importable if needed
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from google import genai
from google.genai import types

OUTPUT_PATH = Path(__file__).parent / "test_output.png"

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("FAILURE: GEMINI_API_KEY not found in environment / backend/.env")
        sys.exit(1)

    print(f"GEMINI_API_KEY loaded: {api_key[:8]}...{api_key[-4:]}")
    print("Calling gemini-2.5-flash-image ...")

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[types.Part.from_text(text="A simple red apple on a white background")],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="1:1", image_size="1K"),
            ),
        )

        # Look for image data in the response parts
        image_saved = False
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                OUTPUT_PATH.write_bytes(part.inline_data.data)
                print(f"SUCCESS: Image saved to {OUTPUT_PATH}")
                image_saved = True
                break
            elif hasattr(part, "text") and part.text:
                print(f"  [text part]: {part.text[:200]}")

        if not image_saved:
            print("FAILURE: Response received but contained no image data.")
            print(f"  Full response: {response}")

    except Exception as e:
        error_str = str(e)
        print(f"FAILURE: {type(e).__name__}: {error_str}")

        # Surface quota / billing details if present
        quota_keywords = ["quota", "billing", "limit", "resource_exhausted", "429", "RESOURCE_EXHAUSTED"]
        if any(kw.lower() in error_str.lower() for kw in quota_keywords):
            print("\n--- Quota / Billing info detected in error ---")
            print(error_str)
            print("----------------------------------------------")
            print("Check: https://aistudio.google.com/app/apikey (quota limits)")
            print("Check: https://console.cloud.google.com/billing (billing account)")

        # Print full traceback for any other error
        import traceback
        print("\n--- Full traceback ---")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
