# BookWiz

Upload any book (PDF or EPUB). Get AI-extracted characters with portraits, emotionally ranked scenes with generated images, and a personalised scrapbook — all themed to the book's genre and your reading taste.

**GitHub:** https://github.com/chaisthra/bookwiz

---

## Important — Copyright Disclaimer

> **BookWiz is a personal reading analysis tool. It does not host, distribute, reproduce, or share book content.**

By uploading a file to BookWiz, you confirm that:

- You own the file or have a legal right to use it for personal analysis (e.g. a purchased eBook, a DRM-free copy you own, or a public-domain work).
- You are using BookWiz **solely for private, personal use** — not to reproduce, distribute, or circumvent copyright protection on any work.
- You understand that uploading copyrighted material you do not own, or using this tool to extract and redistribute protected content, may violate copyright law in your jurisdiction.

**BookWiz, its developers, and contributors accept no responsibility or liability for:**
- Any copyright infringement resulting from files uploaded by users
- Any unauthorised duplication, redistribution, or commercial use of book content processed through this tool
- Any legal consequences arising from a user's choice to upload a file they do not have the right to use

BookWiz is explicitly designed **against** reproducing copyrighted text — all AI agents are instructed to paraphrase and describe in their own words, never to quote extended passages. The tool does not store the raw book text beyond the duration of a single processing session.

**We do not support, encourage, or enable piracy, unauthorised copying, or any use that violates an author's or publisher's rights. Use this tool responsibly and at your own discretion.**

---

## What it does

1. **Upload** a PDF or EPUB
2. **Genre detection** — GPT-4o classifies the book into one of 10 genres
3. **Character extraction** — GPT-5.4 identifies up to 8 characters; Gemini 2.5 Flash builds deep profiles (physical appearance, personality, emotional archetype) using the full book as context
4. **Scene extraction** — Gemini 2.5 Flash reads the whole book in one call and finds 12 emotionally powerful moments; GPT-5.4 re-ranks them to the top 6 using your personal taste profile
5. **Visual generation** — `gpt-image-1.5` generates cinematic character portraits; scene images are generated with those portraits as reference images for character consistency (DALL-E 3 as fallback)
6. **Scrapbook assembly** — GPT-4o designs an aesthetic brief (colour palette, typography, layout, lighting mood) and the scrapbook page renders it all

There are two processing modes:

| Mode | Behaviour |
|---|---|
| **Manual** | Pipeline pauses after scene extraction — you approve/reject scenes, then visuals are generated for your picks |
| **Auto** | Pipeline runs end-to-end; AI picks the top 6 scenes automatically |

---

## Architecture

```
bookWiz/
├── backend/                  Python · FastAPI
│   ├── main.py               All REST endpoints + SSE progress stream
│   ├── agents/
│   │   ├── orchestrator.py   LangGraph state machine (the pipeline)
│   │   ├── character_agent.py GPT-5.4 identify → Gemini 2.5 Flash profile
│   │   ├── scene_agent.py    Gemini 2.5 Flash extract → GPT-5.4 re-rank
│   │   ├── image_agent.py    gpt-image-1.5 portraits + scene images
│   │   └── scrapbook_agent.py GPT-4o aesthetic brief + layout
│   ├── parsers/
│   │   └── book_parser.py    PDF (pypdf) + EPUB (ebooklib) → text chunks
│   ├── db/
│   │   └── supabase_client.py Singleton Supabase client
│   └── utils/
│       ├── gemini_client.py  Gemini image generation client (alt. image path)
│       ├── guardrails.py     Content safety — keyword replacements + genre rules
│       └── taste_profile.py  Reader emotional fingerprint → prompt injection
│
├── frontend/                 Next.js 15 · React 19 · TypeScript · Tailwind
│   └── src/
│       ├── app/
│       │   ├── page.tsx              Home — hero + book library
│       │   └── books/[id]/
│       │       ├── page.tsx          Book detail — status, characters, scenes
│       │       └── scrapbook/page.tsx Scrapbook view
│       ├── components/
│       │   ├── BookCard.tsx          Book thumbnail with genre gradient + delete
│       │   ├── CharacterCard.tsx     Portrait + traits + key quote
│       │   ├── SceneCard.tsx         Scene image + mood + emotional score bar
│       │   ├── SceneSelector.tsx     Manual mode scene approval UI
│       │   ├── UploadZone.tsx        Drag-and-drop upload + mode toggle
│       │   ├── Navbar.tsx            Fixed nav bar
│       │   └── Toast.tsx             Toast notifications
│       └── lib/
│           ├── api.ts                All API calls to backend (typed)
│           └── supabase.ts           Supabase client (frontend)
│
├── scripts/
│   ├── seed_taste_profile.py  Write taste_profile_seed.json into Supabase
│   └── test_gemini_image.py   Standalone Gemini image generation test
│
├── taste_profile_seed.json    Example reader emotional fingerprint
├── guardrails.md              Content safety rules loaded at runtime
├── start.sh                   One-command startup (Windows paths — see below)
└── .env.example               All required environment variables
```

---

## AI models used

| Model | Provider | Used for |
|---|---|---|
| `gpt-5.4` | OpenAI | Character identification, scene re-ranking |
| `gpt-4o` | OpenAI | Genre detection, scrapbook aesthetic brief |
| `gpt-image-1.5` | OpenAI | Character portraits, scene images with reference portraits |
| `dall-e-3` | OpenAI | Image generation fallback |
| `gemini-2.5-flash` | Google | Full-book character profiling + scene extraction (1M context) |
| `gemini-2.5-flash-image` | Google | Alternative image generation client (in `utils/gemini_client.py`) |

---

## Database schema (Supabase / PostgreSQL)

| Table | Key columns |
|---|---|
| `profiles` | `id`, `profile_name`, `taste_profile` (JSONB), `is_default` |
| `books` | `id`, `profile_id`, `title`, `genre`, `status`, `visual_status`, `current_step` |
| `characters` | `id`, `book_id`, `name`, `attributes` (JSONB), `inferred_traits` (JSONB), `portrait_url` |
| `scenes` | `id`, `book_id`, `title`, `mood`, `emotional_weight_score`, `user_approved`, `image_url` |
| `scrapbooks` | `id`, `book_id`, `aesthetic_brief` (JSONB), `layout` (JSONB), `finalised` |
| `assets` | `id`, `book_id`, `scene_id`, `asset_type`, `file_url` |

Storage bucket: `book-assets` (public, path: `{book_id}/characters/{char_id}.png`, `{book_id}/scenes/{scene_id}.png`)

---

## How the pipeline is wired

```
POST /upload
  → parse_book()          extract text from PDF/EPUB
  → start_pipeline()      kick off LangGraph graph in background task
      detect_genre        GPT-4o → writes genre to DB
      character_agent     GPT-5.4 identify → Gemini profile per char → upsert to DB
      scene_agent         Gemini extract 12 → GPT-5.4 re-rank to 6 → insert to DB
      [manual: PAUSE]     book.status = "awaiting_scene_selection"
      image_agent         portraits (sequential) → scene images (parallel, 3 workers)
      scrapbook_agent     aesthetic brief → layout → insert to DB
  → book.status = "complete" | "awaiting_scene_selection"

GET /books/{id}/progress  (SSE)
  → streams {status, visual_status, current_step} every 2s until terminal state
  → frontend uses EventSource to live-update without polling

POST /books/{id}/scenes/select  (manual mode resume)
  → marks approved/rejected scenes in DB
  → resume_scene_selection() → continues LangGraph from image_agent

POST /books/{id}/generate-visuals
  → runs image_agent + scrapbook_agent directly (for already-complete books or re-runs)

POST /books/{id}/characters/{char_id}/regenerate-portrait
POST /books/{id}/scenes/{scene_id}/regenerate-image
POST /books/{id}/regenerate/portraits           (all, background)
POST /books/{id}/regenerate/scene-images        (all, background)

DELETE /books/{id}
  → deletes characters, scenes, scrapbook, assets rows + storage files
```

The frontend makes all API calls through the Next.js rewrite proxy (`/api/backend/*` → `http://localhost:8000/*`), set in `next.config.ts`. The SSE stream connects directly to the backend URL (`NEXT_PUBLIC_BACKEND_URL`) because `EventSource` cannot use Next.js rewrites.

---

## Taste profile

`taste_profile_seed.json` holds a reader's emotional fingerprint — what they look for in books, emotional triggers, narrative values, what they ignore. This gets injected into the GPT-5.4 scene re-ranking prompt so scene selection is personalised to the reader, not just by raw emotional weight score.

To seed it into Supabase:

```bash
cd backend
source bookwiz/bin/activate
python ../scripts/seed_taste_profile.py
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Supabase project with the schema above
- API keys: OpenAI, Google Gemini

### 1. Clone and configure environment

```bash
# Copy example env files
cp .env.example backend/.env
cp .env.example frontend/.env.local
```

Fill in `backend/.env`:
```
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

Fill in `frontend/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### 2. Backend — Python virtual environment

```bash
cd backend
python -m venv bookwiz
source bookwiz/bin/activate      # macOS / Linux
# bookwiz\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 3. Backend — run

```bash
cd backend
source bookwiz/bin/activate
uvicorn main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

### 4. Frontend — install and run

```bash
cd frontend
npm install
npm run dev
```

App available at `http://localhost:3000`

### 5. (Optional) Seed your taste profile

```bash
cd backend
source bookwiz/bin/activate
python ../scripts/seed_taste_profile.py
```

---

## Content safety

`guardrails.md` is loaded at runtime by `utils/guardrails.py`. It contains:
- Universal rules (applied to all genres)
- Genre-specific rules (romance, fantasy, thriller, biography, self-help)
- Prompt engineering rules

All character descriptions and scene text pass through `sanitise_description()` before writing to the database. All image prompts have a safety suffix appended via `get_image_safety_suffix()`. Romance/intimacy language is replaced with emotional equivalents; graphic violence is softened to atmospheric.

---

## Key design decisions

- **Gemini 1M context** — the full book text (up to ~900k chars) is passed in a single call to Gemini 2.5 Flash for both character profiling and scene extraction. No chunking, no batching — one pass gives global narrative context.
- **Reference image injection** — `gpt-image-1.5`'s `images.edit()` with `input_fidelity="high"` is used for scene images, with character portraits as reference inputs. This keeps character faces, hair, and clothing consistent across all scene images.
- **LangGraph checkpoint** — the pipeline is a LangGraph `StateGraph` with `MemorySaver`. Manual mode uses `interrupt_after=["scene_agent"]` to pause and wait for user input before continuing to image generation.
- **SSE instead of polling** — `/books/{id}/progress` is a Server-Sent Events endpoint. The frontend opens one `EventSource` connection per book page and receives live step-by-step updates without hammering the database.
- **Taste profile injection** — the reader's emotional fingerprint from Supabase is injected directly into the GPT-5.4 re-ranking prompt as a `prompt_injection_template` string, making scene selection personal.

---

## Notes

- `start.sh` uses Windows paths (`venv/Scripts/uvicorn`). On macOS/Linux use `bookwiz/bin/uvicorn` or run the backend manually as shown above.
- The `PERPLEXITY_API_KEY` in `.env.example` is not currently used by any agent — it was reserved for a future discovery feature.
- The `Discover` and `My Books` nav links currently point to `/` — they are placeholders for future routes.
- `gemini_client.py` (`generate_portrait`, `generate_scene_image`) is a fully functional Gemini image client but is not in the main pipeline — `image_agent.py` uses `gpt-image-1.5` directly. The Gemini client is available as a drop-in alternative.
