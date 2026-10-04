# Tech Stack Architecture

## Core Technologies
- **Language**: Python 3.11+
- **Video Engine**: FFmpeg (libx264, aac, complex filtergraphs, drawbox, colorbalance, eq, unsharp, vignette, trim, setpts)
- **Subtitle System**: Advanced SubStation Alpha (ASS v4.00+) with dynamic kinetic styles (`viral_karaoke`, `cyber_glow`, `anime_shrine`, `cinematic_minimal`)
- **Audio Processing**: Librosa / soundfile / procedural beat grid analysis for onset detection, BPM calculation, and drop snapping
- **Cloud Execution**: GitHub Actions (`ubuntu-latest` runner) via `.github/workflows/daily_edit.yml`
- **Footage Sourcing**:
  - Primary: Google Drive Direct Chunked Streaming (`core/gdrive_manager.py`)
  - Secondary: Public scenepacks via yt-dlp & Archive.org (`core/public_api_fetcher.py`)
  - Fallback: SmartDownloader multi-engine (`core/smart_downloader.py`)
- **Metadata & LLM Intelligence**:
  - OpenCode CLI (`opencode/deepseek-v4-flash-free`)
  - NVIDIA NIM API (`nvidia/nemotron-3-super-550b-instruct`)
  - Curated non-repeating viral concept catalog (`CHARACTER_VIRAL_CONCEPTS` in `core/quote_ai.py`)
- **Publishing**: YouTube Data API v3 (`publishers/youtube_publisher.py`) with OAuth2 refresh token exchange and resumable media upload

## File Layout
```
anidoc-ai-automation/
├── .agents/
│   ├── skills/             # 21 domain editing & engineering skills
│   ├── data/               # Seeded competitor radar, creator baselines, channel profile
│   └── memory/             # RAM context.md, patterns.md, tech-stack.md, USER.md
├── .github/workflows/
│   └── daily_edit.yml      # Cloud runner for daily scheduled & manual rendering
├── assets/
│   ├── audio/phonk/        # High-energy Phonk tracks
│   └── fonts/              # Custom fonts (TheBoldFont, Komika, Montserrat, etc.)
├── config/
│   └── settings.py         # Canvas, CC presets, API keys, paths
├── core/
│   ├── beat_detector.py    # Phonk beat & drop analysis
│   ├── clip_manager.py     # Character themes, color mapping, scenepack slicing
│   ├── effects_engine.py   # FFmpeg filter chains, CC color grading, velocity
│   ├── gdrive_manager.py   # Google Drive episode selector & action energy slicer
│   ├── quote_ai.py         # AI quote, title, tag & description generator
│   ├── subtitle_stylizer.py# Kinetic ASS subtitle generation
│   ├── timestamp_loader.py # Episode metadata & combat scene indexer
│   ├── title_driven_selector.py # Intent-based scene retrieval
│   └── video_assembler.py  # Master 4K assembly and rendering pipeline
├── episodes_metadata/      # Detailed JSON scene timestamps for 26 combat episodes
├── publishers/
│   └── youtube_publisher.py# YouTube Data API v3 Shorts uploader
├── main.py                 # CLI entrypoint
└── test_*.py               # Automated unit tests
```
