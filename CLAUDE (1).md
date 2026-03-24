# 📚 Book Visualization Engine — Claude Code Project Context

## What This Project Is
A personal multi-agent web app that transforms any book — fiction, non-fiction, biography, thriller, fantasy, literary, self-help, or any written text — into a beautiful digital scrapbook. Outputs include character portraits, emotional scene images, an animated video highlight reel, key quotes, and a mood board. All tailored to the owner's personal taste profile.

**Owner:** Chaithra  
**Stack:** Next.js + LangGraph + GPT-4o + Gemini + Supabase  
**Development Tool:** Claude Code  
**Current Phase:** Phase 1  

---

## Core Principle — Genre Agnostic
This system works for **any book or written text**. Do not hardcode assumptions for romance or fiction only.

Examples of valid inputs:
- A fantasy novel → visualise characters and world-building scenes
- A biography → visualise the subject's life moments and emotional turning points
- A thriller → visualise tension scenes and key characters
- A non-fiction narrative → visualise key ideas, people, and pivotal moments
- A literary classic → visualise characters, settings, and emotional arcs
- A self-help book → visualise key ideas, transformative moments, and impactful frameworks

The agents must adapt their logic based on what kind of book they are processing. A biography has no fictional characters but has real people. A non-fiction book may have ideas as the "protagonist" rather than people. The emotional engine should find what *matters* in the text regardless of genre. **Always detect genre first and adapt all agent logic accordingly.**

---

## Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Next.js (App Router) | Netflix-style UI, card-based interactions |
| Agent Orchestration | LangGraph (Python) | StateGraph, conditional edges, human-in-the-loop |
| Primary LLM | GPT-4o (OpenAI) | Emotional intelligence, scene picking, character analysis |
| Worker LLM | Gemini 1.5 Flash | Structured extraction subtasks inside agents |
| Image Generation | Gemini Imagen | Realistic photo-style character and scene images |
| Video Generation | Gemini Video | Animate and stitch images into highlight reel |
| Audio Generation | Gemini Audio | Mood-matched music + spoken emotional dialogue lines |
| Database | Supabase (via MCP) | All DB operations via Supabase MCP only |
| Web Search | Perplexity API | Fact-checking, Pinterest scraping, BookTok trends |
| Book Ingestion | pypdf (PDF) + ebooklib (EPUB) | Parse and chunk book text |
| Email / Kindle Delivery | SMTP | Send books to Kindle personal email address |
| Social Posting | Pinterest API + Social APIs | Auto-post scrapbook assets to Pinterest boards |

---

## Database — Supabase via MCP

**Always use the Supabase MCP connection for all database operations.**  
Do not write raw SQL migrations manually — use the MCP tools to create tables, insert data, and query.

### Core Tables

**users**
- id, name, taste_profile (jsonb), created_at
- Stores Chaithra's evolving preference model — seeded from ChatGPT reading journal exports, updated after every book and every scene selection

**books**
- id, title, author, genre, file_path, processed_at, status, series_id (nullable)
- Tracks every book uploaded and its processing state

**series**
- id, series_name, books (jsonb array), character_continuity (jsonb)
- Locks character visual profiles across a series — ensures appearance consistency

**characters**
- id, book_id, name, is_real_person (bool), attributes (jsonb), scene_outfits (jsonb), visual_profile (jsonb), inferred_traits (jsonb)
- Full character knowledge graph per book — includes both described and emotionally inferred traits

**scenes**
- id, book_id, scene_id, emotional_context, characters_present (jsonb), quote, emotional_weight_score, user_approved (bool)
- All extracted scenes with metadata and user selection history

**assets**
- id, book_id, scene_id (nullable), asset_type (image/video/audio/quote/moodboard/portrait), file_url, created_at
- Registry of all generated assets

**scrapbooks**
- id, book_id, layout (jsonb), aesthetic_brief (jsonb), posted_pinterest (bool), posted_social (bool), finalised (bool), created_at
- Final assembled scrapbook per book

**discovery_history**
- id, user_id, book_title, author, match_score, match_reasoning, acquired (bool), sent_to_kindle (bool), created_at
- Tracks all books browsed in Discovery Mode

**social_archive**
- id, book_id, platform, post_url, assets_posted (jsonb), posted_at
- Log of all social/Pinterest posts — prevents duplicate posting

---

## LangGraph Architecture

```
User Uploads Book (PDF/EPUB)
            ↓
    [Orchestrator Node]  ← LangGraph StateGraph
    Detects genre, initialises state, routes to agents
            ↓
  ┌──────────────────────────────────────────┐
  ↓            ↓           ↓                 ↓
[CA]         [SEA]        [AD]             [DA]
Character    Scene      Aesthetic        Discovery
Agent      Extractor    Director          Agent
  ↓            ↓           ↓
  └──────────────────────────────────────────┘
                           ↓
                        [VGA]
                 Visual Generator Agent
                           ↓
             ┌─────────────────────────┐
             ↓                         ↓
       Scrapbook Output          Social Archive
  (Images, Video, Quotes)    (Pinterest, Social)
```

**LangGraph State Object carries:**
- book_id, genre, raw_text_chunks
- characters (knowledge graph)
- scenes (extracted list with IDs)
- aesthetic_brief
- user_preferences (from taste profile)
- asset_registry
- mode (auto / manual)
- current_step

**Key LangGraph patterns used:**
- `StateGraph` — shared state across all nodes
- `interrupt_before` — pauses graph for user input at scene selection and image QA steps
- Conditional edges — branches for auto vs manual mode, retry on failure
- Checkpointing — saves state so long-running pipelines can resume if interrupted

---

## The Five Agents — Full Detail

---

### Agent 1: Character Agent (CA)

**Brain:** GPT-4o (emotional inference) + Gemini Flash (structured extraction)

**Job:** Build a complete visual and emotional profile of every significant character or person in the book.

**Extraction targets:**
- Physical appearance — hair, eyes, build, skin tone, distinguishing features
- Style and fashion — mapped per scene (Scene ID → outfit)
- Personality implied traits — inferred from text and reactions
- Emotional archetype — how they feel to the reader
- Role in the story/narrative

**Genre-specific logic:**
- **Fiction/Fantasy:** infer appearance from emotional truth when descriptions are incomplete. Fill gaps using the character's archetype, how others react to them, and the language used around them. Never ask the user to fill gaps — the imagination fills it, the agent should do the same.
- **Biography/Non-fiction:** use real-world web search to find factual descriptions of real people. Cross-reference historical records, cultural context, and era-accurate details.
- **Self-help:** extract key thinkers, authors, or example figures mentioned as characters or subjects.

**Series Continuity Rule:**
- If the book belongs to a series, check `series` table first
- Lock existing character visual profiles — never re-generate them
- Add new characters introduced in later books without altering established ones

**Accuracy Check:**
- Web search to verify period-accurate clothing, cultural details, historical accuracy
- Flag any conflicts before passing to Visual Generator

**Output:** Character Knowledge Graph (JSON) → stored in Supabase `characters` table

---

### Agent 2: Scene Extraction Agent (SEA)

**Brain:** GPT-4o

**Job:** Surface scenes based on *feeling* — not plot significance.

**What it looks for (Feeling-First):**
- Scenes that give chills
- Scenes that cause tears
- Scenes that refuse to leave the reader's head
- Moments of visceral emotional impact — beauty that aches, tension that lingers, gut-punch revelations

**Genre-specific logic:**
- **Fiction:** emotional character moments, atmospheric scenes, relationship turning points
- **Biography:** life-defining decisions, pivotal human experiences, moments of triumph or loss
- **Non-fiction:** ideas or revelations that hit hard, moments of clarity or shock, paradigm shifts
- **Thriller/Mystery:** tension peaks, shocking reveals, moments of dread

**Taste Profile Application:**
- Trained on Chaithra's ChatGPT reading journal exports (vectorised preference data in Supabase)
- Learns from every user selection and rejection — updates preference model in `users` table
- Gets smarter about her specific emotional fingerprint with every book processed

**Feedback Loop (Manual Mode):**
- Presents 4 scene cards at a time (title, mood, short context snippet, key quote)
- User selects which resonate
- Free-text escape hatch always available: "none of these, here's what I want"
- Another round of 4 if needed — user can proceed when satisfied

**Auto Mode:** Top scenes selected silently based on taste profile — no user input

**Output:** Ranked list of Scene IDs with emotional context, character tags, quotes → stored in Supabase `scenes` table

---

### Agent 3: Aesthetic Director Agent (AD)

**Brain:** Gemini 1.5 Pro + Perplexity web search

**Job:** Define the visual language of each scrapbook before any asset is generated. Quality control for all agent outputs.

**What it determines per book:**
- Overall aesthetic mood (gothic, dark academia, sun-drenched, cinematic noir, cottagecore, brutalist, maximalist, minimalist, vintage editorial, etc.)
- Colour palette — primary, secondary, accent
- Texture and collage style (raw mixed media, layered editorial, painterly, clean digital)
- Typography mood for quote cards
- Music genre and emotional tone for video
- Layout grid structure for the scrapbook
- Mood board composition style

**Every book gets its own unique aesthetic — no two scrapbooks look alike.**

**Genre-specific logic:**
- **Fiction/Fantasy:** extrapolate from tone, world-building language, and setting descriptions
- **Biography:** research the actual era, location, and culture of the subject's life — make it period-accurate
- **Non-fiction:** reflect the intellectual tone — is it urgent, contemplative, revolutionary, scientific?

**Quality Control Role:**
- Reviews Character Agent outputs — flags factual inaccuracies before generation
- Reviews Scene Extraction outputs — checks tonal and contextual consistency
- Approves final Aesthetic Brief before anything goes to Visual Generator

**Output:** Aesthetic Brief (structured JSON) — palette, mood, style, layout, music direction → stored in `scrapbooks` table

---

### Agent 4: Visual Generator Agent (VGA)

**Brain:** Gemini Imagen + Gemini Video + Gemini Audio

**Job:** Generate all visual assets and assemble the scrapbook.

**Assets generated:**

| Asset | Tool | Details |
|---|---|---|
| Character portraits | Gemini Imagen | Realistic photo-style, guided by character profile + aesthetic brief |
| Scene images | Gemini Imagen | 3-4 key scenes, emotionally accurate, collage-y texture |
| Animated video | Gemini Video | Existing images animated + stitched in emotional arc order |
| Background audio | Gemini Audio | Mood-matched score from aesthetic brief |
| Spoken dialogue clips | Gemini Audio / TTS | Short key emotional lines spoken — adds narrative weight to video |
| Quote cards | Gemini Imagen | Styled typographically per aesthetic brief |
| Mood board | Gemini Imagen | Collage-y, raw, Pinterest-energy composition |

**Video assembly logic:**
- Source = already-generated scene images (no new scenes rendered for video)
- Animated and stitched in emotional arc order (setup → peak → resonance)
- Gemini auto-audio as base score
- Short spoken dialogues layered in (key emotional lines, not full narration)
- Duration: ~60-90 seconds
- Future (Phase 4): full voice acting via ElevenLabs TTS API

**Scrapbook Assembly — Human QA Step:**
- Agent places assets into predefined layout slots from Aesthetic Brief
- User does final manual QA — adjust positioning, swap distorted images, reorder
- Never auto-finalise without user approval — prevents broken layouts in final output
- Layout slot types defined per aesthetic category

**Social Archive:**
- Auto-formats scrapbook for Pinterest board posting (one board per book)
- Formats highlight video + quote cards for Instagram/social
- Logs all posted assets in `social_archive` table — no duplicate posts

**Output:** Complete asset bundle → URLs stored in `assets` table

---

### Agent 5: Discovery Agent (DA)

**Brain:** GPT-4o + Perplexity web search + Gemini Flash

**Job:** Help decide if an unread book is worth reading — Netflix-style browsable experience.

**Discovery signals:**
- BookTok/Bookstagram trending data (web search)
- Book excerpt — first chapter for taste-testing
- Series and author similarity to books already processed
- Trope identification — fresh takes on familiar tropes flagged explicitly
- Pinterest aesthetic scraping for the book's visual world

**Personalised Match Meter:**
- Scores the book as a % match for Chaithra's taste profile
- Always shows *why* — specific reasoning, not generic labels
- Example: *"You tend to love morally complex female leads and slow-burn emotional tension. This book has both, with a gothic aesthetic you respond strongly to."*
- Score improves as taste profile grows over time

**Book Acquisition Flow (Beta — Personal Use Only):**
- Web scrape OceanOfPDF.com for available file
- Retrieve and download file
- Auto-send to Kindle via Kindle's unique personal email address (SMTP)
- Future public version: replace scraping with Amazon affiliate links

**Output:** Aesthetic preview card, match score + reasoning, acquisition option → stored in `discovery_history` table

---

## User Interaction Modes

### ⚡ Auto Mode
```
Upload Book → Genre detected → All agents run silently → ~5 mins → Full scrapbook delivered → Approve Pinterest post
```

### 🎛️ Manual Mode
```
Step 1 → Taste profile active — confirm or adjust
Step 2 → 4 scene cards shown — which resonate? [free-text escape hatch available]
Step 3 → Character cards shown — do they feel right?
Step 4 → Images generated — review, flag distorted ones
Step 5 → Video ready — watch? [yes / skip]
Step 6 → Adjust scrapbook layout manually
Step 7 → Post to Pinterest? [yes / no / choose assets]
```

### 🔍 Discovery Mode
```
Netflix-style visual card browsing
→ Click book → aesthetic preview + match score + reasoning
→ Read excerpt → confirm interest
→ Send to Kindle [optional]
```

---

## UI Philosophy
- **Clean card-based UI** — tap and go, no forced explanations
- **Free-text escape hatch** always available at every step
- **No chatbot interface** required — user should never have to explain themselves
- **Netflix-style browsing** for Discovery Mode — visual first, gorgeous
- **Mobile-friendly** — usable at 3am on a phone without friction
- **Stunning aesthetic UI** — the interface itself should feel like the product

---

## Output — The Digital Scrapbook

| Asset | Description |
|---|---|
| 🎨 Mood Board | Collage-y, raw, Pinterest-energy — unique per book |
| 👤 Character Portraits | Realistic photo-style, 3-4 key characters |
| 🖼️ Scene Images | 3-4 key emotional scenes |
| 📽️ Video Highlights | ~60-90 sec animated reel + AI music + spoken emotional lines |
| 💬 Quote Cards | Key emotional lines styled per aesthetic, shareable |
| 📓 Full Scrapbook | All assets in layout — user QA before finalising |
| 📌 Pinterest Board | Auto-posted, one board per book — personal visual archive |

---

## Success & Failure Conditions

### ✅ Success
- Characters match their emotional truth — even when descriptions are incomplete
- Scenes feel genuinely significant emotionally, not just narratively
- Scrapbook aesthetic unmistakably matches the book's tone
- Series characters look consistent across all books
- Auto Mode completes in under 5 minutes
- Discovery Mode surfaces a book the user actually wants to read

### ❌ Zero-Tolerance Failures
- Wrong attributes assigned to wrong characters
- Emotionally flat or incorrect scene interpretation
- Agent pipeline stalls and produces no output
- Character appearance inconsistent across a series
- Genre assumptions breaking the pipeline (e.g. looking for fictional characters in a biography)

### ⚠️ Acceptable — System is Learning
- Missing a scene the user loved — recoverable via feedback loop
- Aesthetic not perfectly matching — user can nudge via text box
- Match meter score feels slightly off — improves with more books processed

---

## Phased Rollout

---

### 🔵 Phase 1 — Foundation (Current)

**Goal:** Get the core pipeline working end-to-end for one book.

**Scope:**
1. PDF/EPUB file upload and parsing (pypdf + ebooklib)
2. Genre detection — classify as fiction / biography / non-fiction / thriller / etc.
3. Character Agent → extract profiles → store in Supabase `characters` table
4. Scene Extraction Agent → extract top 4 emotional scenes → store in Supabase `scenes` table
5. Simple Next.js UI — character cards and scene cards displayed cleanly
6. Manual Mode scene selection — 4 cards at a time, free-text escape hatch
7. Supabase MCP wired for all DB operations
8. Basic taste profile seeded from ChatGPT reading journal export

**Do not scope creep into image generation during Phase 1.**

---

### 🟡 Phase 2 — Full Scrapbook

**Goal:** Complete the visual output pipeline — the full scrapbook experience.

**Scope:**
1. Aesthetic Director Agent — aesthetic brief generated per book using book tone + web search references
2. Visual Generator Agent — character portraits and scene images via Gemini Imagen
3. Mood board generation — collage-y, raw, Pinterest-energy aesthetic
4. Animated video via Gemini Video — images stitched + Gemini audio score + spoken key dialogue lines
5. Quote cards generated and styled per aesthetic brief
6. Scrapbook layout assembly — predefined layout slots, user manual QA step before finalising
7. Auto Mode — full silent pipeline end-to-end, no interruptions, ~5 min target
8. Pinterest auto-posting — one board per book, logs to `social_archive` table
9. Social media formatting for Instagram/other platforms
10. Taste model begins evolving — every user selection and rejection updates `users.taste_profile`

---

### 🟠 Phase 3 — Discovery

**Goal:** Netflix-style book discovery experience for unread books.

**Scope:**
1. Discovery Agent built and wired
2. Netflix-style browse UI — visual card grid, book covers, aesthetic previews
3. BookTok/Bookstagram trend data integration via Perplexity web search
4. Personalised match meter — % score with specific written reasoning per book
5. Book excerpt taste-testing — first chapter viewable in-app
6. Series and author similarity matching based on processed book history
7. OceanOfPDF scraper — find and retrieve book file (personal beta use only)
8. Kindle email delivery — SMTP send to Kindle personal address
9. Discovery history stored and browsable in Supabase
10. Future public version note: swap OceanOfPDF scraper for Amazon affiliate links

---

### 🔴 Phase 4 — Polish, Voice & Scale

**Goal:** Production quality, voice features, and optional public release readiness.

**Scope:**
1. Series memory fully hardened — character continuity tested across 3+ book series
2. Voice narration in videos via ElevenLabs TTS API — full spoken narration option
3. Full character dialogue voice acting — distinct voices per character archetype
4. OpenClaw integration for background automations:
   - Kindle delivery confirmation via Telegram
   - Pinterest posting notifications
   - Scrapbook ready alerts
5. Genre expansion — fully validated and tested for biography, self-help, classics, non-fiction
6. Performance optimisation — Auto Mode reliably under 5 minutes for any book length
7. Multi-user support infrastructure (if going public):
   - User authentication
   - Isolated taste profiles per user
   - Separate Supabase schemas or row-level security
8. Amazon affiliate links replacing OceanOfPDF scraping for any public version
9. Mobile app wrapper — React Native or PWA (web-first logic already complete by this phase)
10. Aesthetic reference library — curated and tagged reference sets per genre for Aesthetic Director

---

## Development Rules for Claude Code

1. **Always use Supabase MCP** for all database operations — no raw SQL files unless explicitly asked
2. **Genre detection first** — every pipeline run starts with genre classification before any agent runs
3. **LangGraph state** must always carry: book_id, genre, characters, scenes, aesthetic_brief, user_preferences, asset_registry, mode
4. **Human-in-the-loop** pause points use LangGraph's `interrupt_before`
5. **Phase discipline** — do not build Phase 2 features while Phase 1 is incomplete
6. **Never assume fiction** — all agent prompts must have genre-conditional logic
7. **Character gap-filling** is done emotionally and contextually, not by asking the user
8. **All asset URLs** go into the `assets` Supabase table immediately on generation
9. **Free-text escape hatch** must be present at every user-facing step in Manual Mode
10. **Test with a real book** at the end of every phase — not synthetic data

---

## Extra Context the Agents Need

- **Chaithra's ChatGPT reading journal exports** — foundational taste data, to be parsed and vectorised into `users.taste_profile` on first run
- **Kindle personal email address** — stored securely in user settings for book delivery
- **Pinterest developer credentials** — for auto-posting scrapbooks
- **Previously processed books** — stored in Supabase so series continuity is maintained across sessions
- **Aesthetic reference library** — curated visual references per genre for the Aesthetic Director (to be built in Phase 4)
