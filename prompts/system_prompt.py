"""
System Prompts and Templates for AniDoc AI Documentary Engine
Implements the full 6-State Pipeline from Chad Grow's viral video.
"""

MASTER_SYSTEM_PROMPT = """You are AniDoc's AI Video Engine — an expert AI documentary director and scriptwriter.
Your purpose is to produce high-retention, cinematic 2D animated documentary videos.
Channel Identity: AniDoc — Real events. Hidden facts. Untold realities. Cinematic 2D animated documentary storytelling.
No exaggeration. No noise. Only what actually happened.

CORE RULES:
1. Always follow the exact State requested.
2. Ground all historical, espionage, political, and crime narratives in documented facts and verified records.
3. For scripts: Clean continuous prose, no section headers, no audio tags, 100% voiceover ready.
4. For image prompts: 16:9 aspect ratio mandatory, Semi-realistic 2D illustration style, warm muted palette, single-source dramatic lighting.
5. High tension, curiosity gaps, and dramatic pacing.
"""

STATE1_TOPICS_PROMPT = """Generate 10 viral documentary video topics tailored for a high-RPM faceless 2D documentary channel.
Language requested: {language}

Divide the 10 topics strictly into these 5 categories (2 topics each):
■ HISTORICAL CRIME & UNDERWORLD (e.g. Mafia syndicates, notorious kingpins, historic heists)
1. [Topic Title + 1-line hook]
2. [Topic Title + 1-line hook]

■ ESPIONAGE & SECRET MISSIONS (e.g. RAW/IB undercover ops, spy networks, jailbreaks)
3. [Topic Title + 1-line hook]
4. [Topic Title + 1-line hook]

■ POLITICAL HISTORY & POWER DYNAMICS (e.g. Coups, geopolitical crises, declassified state secrets)
5. [Topic Title + 1-line hook]
6. [Topic Title + 1-line hook]

■ UNTOLD REAL EVENTS & MYSTERIES (e.g. Hijackings, missing flights, covert military operations)
7. [Topic Title + 1-line hook]
8. [Topic Title + 1-line hook]

■ FRESH VERIFIED INVESTIGATIVE NEWS (Recent high-stakes events backed by official records)
9. [Topic Title + 1-line hook]
10. [Topic Title + 1-line hook]

Output the topics cleanly and conclude by asking the user to select a number or provide custom instructions.
"""

STATE2_SCRIPT_PROMPT = """You are generating the complete cinematic documentary script for the chosen topic:
Topic: "{topic}"
Language: {language}
Target Length: {target_length} (Aim for 2,500 to 4,000 words for a deep 12-15 minute documentary, or proportionally detailed).

First output the Style DNA analysis table:
- NICHE: Documentary True Crime / Espionage / Political History
- TARGET AUDIENCE: 18-45 curious about power, crime, espionage & national security
- HOOK TYPE: Date + City/Location + Sensory Detail -> Immediate Stakes
- SCRIPT FLOW: Hook (30s) -> Background (2 min) -> Inciting Incident -> Escalation (8-10 min) -> Climax -> Resolution -> Macro Significance -> Documentary CTA
- TONE: Authoritative, serious, grave, investigative cinematic narrator
- ESTIMATED WORDS: [Calculated word count]

Then immediately output the FULL SCRIPT adhering to these strict rules:
1. CLEAN PROSE ONLY: Do NOT use markdown headers (#, ##), do NOT use scene markers (SCENE 1), and do NOT use audio tags ([MUSIC], [SFX]). Pure narrative text ready for voiceover.
2. HOOK: Open mid-action in the very first 3 sentences with a specific date, city, and sensory detail.
3. RETENTION & TENSION: Insert a twist, escalation, or new revelation every 90-120 seconds. Mark major tension peaks with [TENSION PEAK].
4. ENDING: Conclude with historical/macro significance and an authoritative documentary-style subscribe call-to-action.

After the script, provide the word count and estimated video duration at 50 WPM (slow/dramatic), 100 WPM (documentary standard), and 160 WPM (fast).
"""

STATE3_IMAGE_PROMPTS_PROMPT = """Analyze the following documentary script and generate standalone 2D Illustration Image Prompts in batches of 20.

SCRIPT:
\"\"\"
{script}
\"\"\"

VISUAL STYLE REQUIREMENTS (ANIDOC DNA):
- Art Style: Semi-realistic 2D illustration, clean vector outlines, no noisy textures, accurate human anatomy, expressive South Asian / relevant ethnicity features.
- Color Palette: Warm muted tones (amber, khaki, dusty olive, deep navy, charcoal black). Warm skin tones. Desaturated backgrounds.
- Lighting: Single-source dramatic lighting (amber streetlamp, moonlight, single bulb, overhead spotlight, strong side-light) with deep cinematic shadows.
- Camera Framing: Alternate between medium-close portrait shots (chest up) and wide establishing shots.
- Aspect Ratio: "16:9 aspect ratio" MUST be included in every single prompt.
- Standalone Format: Every prompt must independently describe Subject, Attire, Environment, Lighting, Mood, Camera angle, and Art Style.

Format your output as:
Batch 1 of {total_batches} (Prompts 1 to 20):
```
1. [Prompt 1: Single paragraph, no line breaks inside]

2. [Prompt 2: Single paragraph, no line breaks inside]
...
20. [Prompt 20: Single paragraph, no line breaks inside]
```
"""

STATE4_MOTION_PROMPTS_PROMPT = """For each of the generated image prompts below, generate a subtle cinematic Video Motion Prompt optimized for AI video generators (Google Veo 3 / Flow AI, Kling AI, Runway Gen-3, or Luma Dream Machine).

IMAGE PROMPTS:
\"\"\"
{image_prompts}
\"\"\"

For each image, provide:
Image [N] — Video Motion Prompt:
- Starting Frame: [Brief summary of static image]
- Camera Motion: [Subtle camera move: slow push-in / gentle left-to-right pan / slow tilt / subtle zoom]
- Environmental Dynamics: [Subtle drifting smoke / flickering lamp / rain drops / dust particles in light beam]
- Duration: 3-5 seconds
- Mood / Pacing: Slow cinematic documentary pace
"""

STATE5_THUMBNAIL_PROMPT = """Generate 5 viral, high-CTR thumbnail concepts for this documentary topic:
Topic: "{topic}"
Script Summary / Core Stakes: "{script_summary}"

THUMBNAIL DNA:
1. Headline Text: Bold Hindi in Devanagari (or bold English) with 1 intense power word in RED or YELLOW. (e.g. 'खौफ', 'धोखा', 'रहस्य', 'सीक्रेट', 'मास्टरमाइंड').
2. Composition: Split screen — dramatic dark left (smoke, rain, spotlight) + contextual right (parliament, map, crime scene).
3. Main Characters: 1-2 large illustrated figures (chest up) with intense, shocked, or calculating expressions.
4. Badge: '2D ANIMATION' badge in yellow rounded rectangle with bold black text at bottom center.
5. Image Prompt: Full standalone text-to-image prompt (16:9) to generate the background illustration in Flux / Midjourney.

Output 5 complete thumbnail concepts.
"""

STATE6_SEO_PROMPT = """Generate a complete high-ranking YouTube SEO Package for this documentary:
Topic: "{topic}"
Script Summary: "{script_summary}"
Language: {language}

Output:
1. TITLE OPTIONS (5 variants):
   - Option 1 (Curiosity Gap): [...]
   - Option 2 (Shocking Revelation): [...]
   - Option 3 (Investigative 'How / Why'): [...]
   - Option 4 (Viral Hook): [...]
   - Option 5 (Punchy Short Title): [...]

2. YOUTUBE DESCRIPTION:
   - 150-200 words in authoritative documentary tone, rich with target keywords, timestamps placeholders, and subscribe CTA.

3. VIRAL HASHTAGS (15):
   - All 15 hashtags on a single line (e.g. #2DDocumentary #TrueCrimeHindi ...)

4. YOUTUBE SEARCH TAGS (30):
   - Comma-separated list of 30 high-volume search tags (balanced mix of Hindi, Hinglish, and English terms).
"""
