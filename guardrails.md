# 🛡️ GUARDRAILS.md — Book Visualization Engine Content Safety

## Purpose
This file defines the content guardrails for all agents in the Book Visualization Engine. These rules apply to every stage of the pipeline — scene extraction, character profiling, image generation, video generation, audio generation, and quote selection.

The goal is simple: **keep the essence of every book intact while making the output safe, tasteful, and enjoyable for all audiences.** A murder mystery should feel tense and atmospheric. A war biography should feel heavy and real. A dark fantasy should feel ominous and powerful. None of these require gore, explicit content, or shock value to achieve their emotional impact.

**The golden rule: Emotion over Explicitness. Always.**

---

## Universal Rules — Apply to All Genres

These rules are non-negotiable across every book, every genre, every agent.

### ❌ Never Generate or Describe
- Sexual or sexually suggestive content of any kind — including implied, partial, or "tasteful" nudity in a sexual context
- Graphic depictions of blood, wounds, mutilation, or bodily harm
- Torture — visual or descriptive
- Sexual violence or non-consensual scenarios of any kind
- Explicit drug use shown approvingly or in glamorised detail
- Content that sexualises or romanticises harm to any person

### ✅ Always Preserve
- The emotional weight of a scene — tension, grief, dread, rage, love, despair
- The narrative importance of a dark moment — it can be shown to *matter* without being shown graphically
- The atmosphere and tone the author created
- The character's humanity — even villains, even in their worst moments
- The reader's imagination — sometimes what is *implied* is more powerful than what is shown

---

## Genre-Specific Guardrails

---

### 📖 Fiction — General (Literary, Contemporary, Classics)

**Sensitive areas:** Intimacy, abuse, mental health, addiction, death

**Rules:**
- Romantic or intimate scenes → show emotional connection, closeness, atmosphere. No explicit physical depiction. A couple close together, soft lighting, emotional tension — that is enough.
- Abuse or trauma scenes → show the emotional aftermath, not the act. A character's expression, body language, a quiet room — convey what happened without depicting it.
- Death of a character → show grief, stillness, the moment *before* or *after*. Not the act of dying in graphic detail.
- Mental health or addiction → portray with dignity and emotional truth. No glamorisation, no shock imagery.

---

### 🗡️ Fantasy / Dark Fantasy / Mythology

**Sensitive areas:** Battle scenes, dark magic, creature violence, sacrifice rituals

**Rules:**
- Battle scenes → cinematic framing, wide shots, atmospheric chaos. No close-up gore, no severed body parts, no pools of blood.
- Creature violence → show the scale and terror of the creature. Show the reaction of the human. Do not visualise the moment of bodily harm.
- Dark magic or rituals → lean into atmosphere — smoke, shadow, unnatural light, dread. Avoid explicit sacrifice imagery.
- Death in fantasy → a fallen warrior can be shown with dignity. Honour the emotional weight without graphic wound detail.
- Villains → can be visually imposing, menacing, powerful. Do not make them grotesque beyond what serves the story's atmosphere.

---

### 🔪 Thriller / Mystery / Crime

**Sensitive areas:** Murder scenes, crime scenes, psychological horror, violence

**Rules:**
- Murder or crime scenes → the *presence* of the event, not the act. A dark room, a door ajar, a character's reaction, an empty space where someone was — these are more powerful than explicit imagery.
- Crime investigation → evidence, atmosphere, emotional tension of the detective or protagonist. No graphic recreation of the crime.
- Psychological horror → lean fully into this. Dread, paranoia, isolation, unease — all fair game. Disturbing atmosphere without disturbing imagery.
- Chase or fight scenes → dynamic, tense, kinetic energy. No gratuitous injury detail.
- The reveal of a killer or twist → emotional and atmospheric. Let the weight of the moment do the work.

---

### ⚔️ Historical Fiction / War / Military

**Sensitive areas:** Combat, atrocities, historical violence, death on scale

**Rules:**
- War scenes → convey the chaos, the cost, the human experience of it. Wide atmospheric shots. Never zoomed-in gore or injury.
- Historical atrocities (genocide, slavery, persecution) → treat with gravity and respect. Show the human cost through faces, settings, silences. Never exploit or sensationalise.
- Executions or historical punishment → the moment *before*, the weight of the scene, the emotional impact on witnesses. Not the act itself.
- Soldiers or combatants → their humanity comes first. Exhaustion, fear, determination — these are the visuals. Not violence.

---

### 👻 Horror (Psychological, Gothic, Supernatural)

**Sensitive areas:** Body horror, monsters, death, psychological distress

**Rules:**
- Atmosphere is everything in horror — lean into shadow, isolation, the uncanny, dread, the unknown.
- Monsters or supernatural entities → terrifying through presence, scale, and wrongness. Not through explicit physical gore.
- Body horror → imply distortion or wrongness atmospherically. Do not render it explicitly.
- Death in horror → what makes horror powerful is what the audience *imagines*. Show the before and after. Not the act.
- Psychological horror → fully supported. Paranoia, hallucination, dissociation — all can be visualised atmospherically and powerfully.

---

### 🕵️ Spy / Action / Adventure

**Sensitive areas:** Fight scenes, weapons, explosions, enemy kills

**Rules:**
- Fight scenes → dynamic, fast, kinetic. Hero-centric framing. No injury close-ups.
- Weapons → can be present and prominent. Not aimed at the camera in a threatening real-world way, and not shown causing explicit harm.
- Explosions, chases, escapes → full energy and spectacle. Cinematic. Not aftermath carnage.
- Enemy kills → the act can be implied or shown at distance. Not shown in graphic detail.

---

### 💔 Romance / Erotica Adjacent (Literary Romance, Slow Burn, etc.)

**Sensitive areas:** Physical intimacy, passion, sexual tension

**Rules:**
- Emotional intimacy → fully supported. Two characters close together, tension, longing, a look, a touch — all of this is the heart of romance and should be visualised beautifully.
- Physical intimacy → fade to atmosphere. A closed door, morning light through curtains, rumpled fabric, a character's expression in the moment *before*. Never explicit.
- Sensual tension → clothing, proximity, eye contact, setting. This is tasteful and powerful. Keep it there.
- Never generate nudity, partial nudity in a sexual context, or any explicit sexual imagery under any circumstances.
- If a book contains explicitly sexual scenes (e.g. erotica genre) → skip those scenes entirely for visualisation. Flag to user: *"This scene was skipped as it falls outside the app's content guidelines. We've selected an alternative emotionally significant scene instead."*

---

### 📜 Biography / Non-Fiction / Memoir

**Sensitive areas:** Real people, real trauma, real historical events, real violence

**Rules:**
- All universal rules apply with extra weight — these are real people.
- Traumatic real events (assault, war, persecution, illness, death) → handled with dignity, respect, and emotional truth. Never sensationalised.
- Real historical figures in difficult moments → show their humanity, not their suffering in graphic detail.
- Controversial figures → depicted factually and atmospherically. No political commentary added by the app.
- Subjects who experienced violence → the emotional truth of their experience is shown. The act of violence is not.

---

### 🧠 Self-Help / Philosophy / Ideas-Driven Non-Fiction

**Sensitive areas:** Sensitive case studies, mental health, trauma-informed content

**Rules:**
- Case studies of trauma, abuse, or hardship → show insight and transformation. Not the raw traumatic event.
- Mental health content → always depicted with dignity. No imagery that could be interpreted as glorifying or trivialising mental illness, self-harm, or crisis.
- Dark ideas or philosophical content → can be depicted atmospherically as thought and reflection. Not as disturbing imagery.

---

## Character Portrayal Rules

Applies to the Character Agent and all visual generation.

- Characters can be depicted as powerful, menacing, dark, morally complex, or villainous — their visual portrayal should serve the story.
- No character should be depicted in a sexualised way — regardless of how they are described in the source text. If a book describes a character in explicit terms, the agent must reframe to emotional and aesthetic characterisation only.
- Real people (biography, non-fiction) → depicted respectfully and accurately. No fabricated expressions of distress, violence, or intimacy.
- Age ambiguity → if a character's age is unclear or contested, always default to depicting them as an adult. If they are canonically a minor, they are depicted strictly as a young person in age-appropriate, non-sexualised context.
- Villains → can be visually imposing and atmospheric. Not grotesque for shock value alone.

---

## Scene Selection Rules

Applies to the Scene Extraction Agent.

- Scenes involving explicit sexual content → **skip entirely.** Replace with the next most emotionally significant scene and notify the user.
- Scenes involving extreme graphic violence → **reframe.** Extract the emotional core of the scene (the dread, the loss, the shock) and represent that — not the graphic action itself.
- Scenes involving sexual violence → **skip entirely.** These scenes are never visualised. The emotional aftermath of trauma can be represented with sensitivity if it is a significant part of a character's arc.
- Scenes involving child harm of any kind → **skip entirely and immediately.** No exceptions.

When a scene is skipped, always:
1. Notify the user: *"This scene was skipped as it falls outside the app's content guidelines."*
2. Offer the next best alternative scene automatically.

---

## Quote Selection Rules

Applies to quote card generation.

- Quotes that are sexually explicit → reframe or skip. Find an adjacent quote that captures the emotional moment without the explicit language.
- Quotes containing slurs or hate language → skip. Find the emotional truth of the passage in adjacent text.
- Quotes depicting graphic violence in visceral detail → paraphrase or find an adjacent line that carries the emotional weight without the graphic specificity.

---

## Prompt Engineering Rules for Generation Agents

All prompts sent to Gemini Imagen, Gemini Video, and Gemini Audio must include the following guardrail instructions:

```
Style: cinematic, atmospheric, emotionally evocative
Avoid: gore, blood, graphic injury, nudity, sexual content, 
explicit violence, disturbing body imagery
Tone: [book-specific tone from aesthetic brief]
Approach: imply rather than depict where content is sensitive
```

If Gemini returns a generation that violates these guardrails:
1. Do not show it to the user
2. Log the failed generation attempt
3. Retry with a more conservative prompt
4. If retry also fails, skip the asset and notify the user

---

## Summary — The Guardrail Philosophy

| Content Type | Approach |
|---|---|
| Sexual / explicit intimacy | Never depicted. Fade to atmosphere. |
| Graphic violence / gore | Never depicted. Show emotional weight instead. |
| Murder / death scenes | Before or after. Never the act in graphic detail. |
| Psychological horror | Fully supported — atmosphere, dread, unease. |
| Dark themes (trauma, war, abuse) | Emotional truth, never exploitation. |
| Villains and dark characters | Powerful and atmospheric. Not grotesque. |
| Real people | Respectful, factual, dignified. |
| Minors | Age-appropriate, non-sexualised. Always. |
| Sexually explicit scenes | Skipped. User notified. Alternative offered. |
| Child harm of any kind | Skipped immediately. No exceptions. |

---

*These guardrails exist not to sanitise great literature — but to honour it.*  
*The most powerful moments in any book live in the emotional truth, not the explicit detail.*  
*This app visualises what the reader *felt* — not just what was written.*