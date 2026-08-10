# Step-by-Step Workflow Guide: 2D Documentary AI Channel

This guide walks you through operating the **AniDoc AI Automation System** both manually (using the free web tools shown in the video) and fully automatically using our Python pipeline.

---

## Method 1: The Automated 1-Click Pipeline (Recommended)

Our codebase automates the entire 6-state pipeline with one command.

### 1. Setup Environment
```bash
cd ~/anidoc-ai-automation
cp .env.example .env
# Edit .env and insert your API keys (OpenRouter, NVIDIA, Claude, ElevenLabs, etc.)
pip install -r requirements.txt
```

### 2. Run the Interactive CLI
```bash
python cli.py
```
This gives you an interactive menu to:
- Generate 10 viral topics
- Write the full 3,000–4,500 word Hindi documentary script
- Generate 20-frame batch image prompts (AniDoc 2D Style)
- Generate video motion prompts (Veo / Kling / FFmpeg)
- Synthesize voiceovers using Edge-TTS or ElevenLabs
- Download generated 2D illustrations via Pollinations AI / Flux
- Render the complete final animated documentary video with subtitles and background music
- Generate viral thumbnail images with text & yellow badge overlay
- Export YouTube SEO package (Title, Description, Tags, Hashtags)

### 3. Run the Modern Web Dashboard
```bash
python server.py
```
Open your browser at `http://localhost:8080` to access the visual production studio.

---

## Method 2: The Manual Free Tools Workflow (As shown in Chad Grow's Video)

If you prefer to operate the web tools manually step-by-step:

### Step 1: Script & Prompt Generation in Claude AI
1. Go to [Claude.ai](https://claude.ai) (Free or Pro).
2. Upload the `prompts/anidoc_magical_prompt.md` file (or paste its contents).
3. Type `start` or `video banao`.
4. Claude will output 10 viral topic ideas. Pick one by typing its number.
5. Claude will perform the **Style DNA Analysis** and generate the full 3,000–4,500 word Hindi script.
6. Reply `next` to receive batch image prompts (20 prompts per batch in 16:9 format).

### Step 2: Voiceover Generation
1. Copy the clean script text from State 2.
2. Go to **ElevenLabs** ([elevenlabs.io](https://elevenlabs.io)) or run `python -m generators.voiceover_generator --input script.txt --provider edge` (free unlimited).
3. Select an authoritative, deep male narrator voice (e.g., Adam, George, or Edge-TTS `hi-IN-MadhurNeural`).
4. Download the generated `.mp3` audio.

### Step 3: 2D Illustration Generation
1. Copy the 20-prompt batch from State 3.
2. Open **Nano Banana Pro**, **Pollinations AI**, or **Midjourney**.
3. Paste each prompt into the generator with aspect ratio `--ar 16:9`.
4. Save images in numerical order (`01.png`, `02.png`, ...).

### Step 4: Motion Animation (Optional)
1. For dynamic scenes, upload the generated 2D image into **Flow AI (Google Veo 3.1 Fast)** or **Kling AI**.
2. Paste the corresponding motion prompt from State 4 (e.g., *"slow push-in, subtle smoke drift"*).
3. Export 3–5 second `.mp4` video clips.

### Step 5: Final Video Assembly & Subtitles
1. Import all images / clips and the voiceover audio into **CapCut**, **DaVinci Resolve**, or run our automated renderer:
   ```bash
   python main.py --assemble --project my_project
   ```
2. Add subtle background suspense music at -22 dB.
3. Auto-generate captions with styled Devanagari font (bold yellow/white).

### Step 6: Thumbnail Design & YouTube Upload
1. Generate the thumbnail image using Claude's State 5 prompt.
2. Overlay bold Hindi text with 1 red keyword.
3. Add the yellow `2D ANIMATION` badge at bottom center.
4. Copy the Title, Description, and Tags from State 6 and publish to YouTube!
