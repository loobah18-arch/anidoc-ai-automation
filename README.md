# 🎬 AniDoc AI Automation: 2D Documentary Channel Engine ($9,987/Month Blueprint)

[![License: MIT](https://img.shields.io/badge/License-MIT-amber.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![YouTube Automation](https://img.shields.io/badge/YouTube-Automation-red.svg)](https://youtube.com)
[![Voiceover: Edge--TTS & ElevenLabs](https://img.shields.io/badge/Voiceover-Neural%20TTS-green.svg)](https://github.com/rany2/edge-tts)
[![Visual Engine: Flux 2D](https://img.shields.io/badge/Visuals-Flux%202D%2016%3A9-orange.svg)](https://pollinations.ai)

An autonomous, production-grade AI engine designed to generate viral **faceless 2D animated documentary videos** in Hindi and English. Directly replicates the high-retention cinematic storytelling formula used by **AniDoc**, **Dhruv Rathee**, **MagnatesMedia**, and **Project Nightfall**.

Based on **Chad Grow's viral blueprint**: *"Claude Ai + YouTube = $9,987/Month (FREE Plan) | Create Viral 2D Documentary Videos"* ([Watch on YouTube](https://youtu.be/qJkC05DjVlA)).

---

## 🌟 Key Features

- **⚡ Full 6-State Pipeline Orchestrator**:
  1. **State 1 — Topic Selection**: 10 high-retention viral topics categorized across Underworld, RAW/IB Espionage, Political History, Mysteries, and Fresh Verified News.
  2. **State 2 — Style DNA Scriptwriting**: Deep 3,000–4,500 word voiceover-ready cinematic script with mid-action hooks, tension peaks (`[TENSION PEAK]`), and curiosity gaps.
  3. **State 3 — Batch 2D Image Prompts**: Standalone 16:9 illustration prompts in batches of 20 (warm muted palette, single-source dramatic lighting, South Asian anatomy).
  4. **State 4 — Video Motion Prompts**: Camera moves (slow push-in, subtle pan, particle dynamics) for Kling AI / Veo 3 / Runway.
  5. **State 5 — High-CTR Thumbnails**: 5 concepts with Devanagari bold text, split composition, and the signature yellow `2D ANIMATION` badge.
  6. **State 6 — YouTube SEO Package**: 5 title variants, 200-word SEO description, 15 viral hashtags, and 30 search tags.
- **🎙️ Zero-Cost Automated Voiceover**: Built-in Microsoft Edge Neural TTS (`hi-IN-MadhurNeural`, `en-US-ChristopherNeural`) with zero API fees, plus optional ElevenLabs API support.
- **🎨 100% Free High-Res 2D Visual Generator**: Directly interfaces with the Pollinations AI Flux engine for instant 16:9 illustration rendering.
- **🎥 Automated FFmpeg Video Assembler**: Auto-animates frames with smooth Ken Burns camera moves, synchronizes voiceovers, mixes suspense background music, and burns styled Devanagari subtitles.
- **🌐 Interactive Web Dashboard**: Dark-mode glassmorphic web studio running locally at `http://localhost:8080`.
- **💻 Rich Interactive CLI**: Terminal interface for single-state testing and 1-click autonomous batch generation.

---

## 🏗️ Repository Architecture

```
anidoc-ai-automation/
├── core/                              # The 6-State Pipeline Engine
│   ├── state1_topics.py               # 10 Viral topics generator
│   ├── state2_script.py               # Deep cinematic scriptwriter
│   ├── state3_image_prompts.py        # 2D Illustration batch prompts
│   ├── state4_motion_prompts.py       # Camera motion & dynamics prompts
│   ├── state5_thumbnails.py           # 5 High-CTR thumbnail concepts
│   ├── state6_seo_package.py          # YouTube SEO & Metadata package
│   └── pipeline.py                    # Master pipeline orchestrator
│
├── generators/                        # Media Generation Subsystems
│   ├── llm_provider.py                # Multi-LLM adapter (Claude, OpenRouter, NVIDIA, OpenAI)
│   ├── voiceover_generator.py         # Free Edge-TTS & ElevenLabs synthesizer
│   ├── image_generator.py             # Free Flux 16:9 2D illustration generator
│   ├── motion_generator.py            # FFmpeg Ken Burns motion generator
│   └── subtitle_generator.py          # Synchronized SRT & ASS subtitle generator
│
├── renderers/                         # Video Assembly & Graphics
│   ├── video_assembler.py             # Video, audio, BGM & subtitle stitching engine
│   └── thumbnail_designer.py          # Thumbnail designer with badge & text overlay
│
├── web/                               # Modern Web Dashboard
│   ├── index.html                     # Sleek dark-mode glassmorphic UI
│   ├── style.css                      # Ultra-premium responsive stylesheet
│   └── app.js                         # State manager & live media previewer
│
├── docs/                              # Deep Documentation & Video Breakdown
│   ├── VIDEO_TRANSLATION_AND_BREAKDOWN.md  # Full English translation of Chad Grow's video
│   ├── WORKFLOW_GUIDE.md                   # Step-by-step master guide for all tools
│   └── MONETIZATION_STRATEGY.md            # Scaling to $9,987/month guide
│
├── examples/sample_project/           # Complete reference output project
├── cli.py                             # Interactive CLI
├── main.py                            # Headless / scriptable runner
└── server.py                          # Web dashboard backend server
```

---

## 🚀 Quickstart Guide

### 1. Installation

```bash
# Clone or navigate to the repository
cd ~/anidoc-ai-automation

# Install Python requirements
pip install -r requirements.txt
```

### 2. Configure Environment (Optional for API Keys)
Copy `.env.example` to `.env` and add your preferred provider keys (OpenRouter, NVIDIA, Claude, OpenAI, or ElevenLabs):
```bash
cp .env.example .env
```
*(Note: If no keys are provided, the system automatically uses zero-cost free fallback endpoints and free Microsoft Edge Neural TTS!)*

---

## 🎮 How to Run

### Mode A: Interactive Rich CLI
```bash
python cli.py
```
Provides an interactive menu to run any individual state, write custom scripts, synthesize voiceovers, or execute a 1-click autonomous run.

### Mode B: Modern Web Studio Dashboard
```bash
python server.py
```
Open `http://localhost:8080` in your browser to access the complete visual studio.

### Mode C: Headless 1-Click Automation
```bash
# Generate full 6-state package + render 1080p video
python main.py --topic "The 1971 PAF Prison Escape" --language Hindi --render
```

---

## 📊 Complete English Breakdown of Chad Grow's Video

For an extensive, deep translation and analysis of Chad Grow's video (*"Claude Ai + YouTube = $9,987/Month"*), refer to [`docs/VIDEO_TRANSLATION_AND_BREAKDOWN.md`](docs/VIDEO_TRANSLATION_AND_BREAKDOWN.md).

### The 6 Core Rules of the AniDoc Engine:
1. **Pacing**: Short, punchy sentences (max 2 clauses), alternating fast bursts with slow dramatic pauses.
2. **Hook**: Open mid-action with a specific date, location, and sensory detail within the first 3 sentences.
3. **Retention**: Inject an escalation, twist, or revelation every 90–120 seconds (`[TENSION PEAK]`).
4. **Visual Consistency**: Semi-realistic 2D illustration, clean vector outlines, warm muted palette (amber, khaki, navy), single-source dramatic lighting, mandatory 16:9 aspect ratio.
5. **Thumbnails**: Bold Devanagari headline with 1 red/yellow keyword, split composition, and the yellow `'2D ANIMATION'` badge.
6. **Clean Output**: Pure continuous prose without stage directions or music brackets, 100% voiceover ready.

---

## 💰 Monetization & Scaling Blueprint

For details on how documentary channels scale to **$5,000 – $10,000+/month** via high CPMs ($5–$15 RPM), mid-roll optimization, sponsorships (VPNs, trading platforms), and YouTube Shorts funneling, see [`docs/MONETIZATION_STRATEGY.md`](docs/MONETIZATION_STRATEGY.md).

---

## 📜 License
Released under the [MIT License](LICENSE).
