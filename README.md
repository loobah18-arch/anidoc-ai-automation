# ⚡ AniDoc 4K Phonk / Scene Edit Automation & Studio Suite (Marvel & Jujutsu Kaisen)

Automated high-retention 9:16 vertical Short video generator and interactive web video editor for **Marvel Cinematic Universe (MCU)** and **Jujutsu Kaisen (JJK)** phonk & velocity edits.

---

## 🌟 Key Features

- **🎧 Popular Phonk BGM Library:** Curated popular Phonk background music (Brazilian Phonk Montagem, Tokyo Drift Phonk, Dark Shadow Phonk, Cyberpunk Synthesizer Wave, Gigachad Sigma Phonk) with automatic internet downloading.
- **🌐 Public API & GitHub Repo Clip Ingestion:** Download and ingest real 4K/1080p anime and MCU clips directly from public GitHub repositories, open endpoints, and automated scenepack streamers with action slicing.
- **✨ Kinetic Word-by-Word Karaoke Subtitles:** High-retention subtitle engine with vibrant active-word color pops (Gold, Cyan, Blood Red), dynamic scaling bounce (`\fscx115\fscy115`), character top badges, and multiple preset styles (`viral_karaoke`, `cyber_glow`, `anime_shrine`, `cinematic_minimal`).
- **🎨 4K HDR Color Grade (CC):** Cinematic contrast curves, lifted saturation, unsharp edge clarity, and cinematic vignette presets (`marvel_hdr`, `jjk_void`, `sukuna_shrine`, `cyber_phonk`).
- **💥 Impact Beat Flashes & Velocity Punch-ins:** Dynamic zoom punch-ins and momentary white screen burst flash overlays timed to heavy drops.
- **🖥️ AniDoc Web Studio Video Editor:** Interactive dark-mode web application for live clip previews, audio waveform picking, subtitle styling, 1-click 4K rendering, and instant YouTube Shorts publishing.
- **🚀 Automated YouTube Auto-Publisher:** Directly publishes 9:16 Shorts to YouTube Data API v3 on a twice-daily automated schedule via GitHub Actions.

---

## 🎬 Supported Universes & Characters

| Universe | Characters | Iconic Color Themes |
| :--- | :--- | :--- |
| **Marvel** | Spider-Man, Iron Man, Thor, Thanos, Wolverine, Loki | Crimson Red, Gold, Electric Blue, Cosmic Violet |
| **Jujutsu Kaisen** | Gojo Satoru, Ryomen Sukuna, Toji Fushiguro, Yuji Itadori, Megumi | Hollow Purple, Malevolent Blood Red, Deep Slate |

---

## 🛠️ Local Usage

### 1. Launch AniDoc Web Studio Video Editor
```bash
python main.py --studio
# Or:
python studio/server.py --port 7860
```
Open `http://127.0.0.1:7860` in your browser to access the complete video editor suite!

### 2. Render 4K Edits via CLI
```bash
# Generate a Gojo Satoru edit with Brazilian Phonk & Karaoke Subtitles
python main.py --character gojo --phonk brazilian_phonk_montagem --subtitle-style viral_karaoke --duration 22.0

# Generate a Spider-Man Marvel edit with Cyber Glow subtitles
python main.py --character spiderman --phonk tokyo_drift_phonk --subtitle-style cyber_glow --duration 20.0

# Render and upload to YouTube as public Short
python main.py --universe jjk --duration 22.0 --upload --upload-to youtube --privacy public

# Render and upload to Google Drive instead of YouTube
python main.py --character gojo --duration 22.0 --upload --upload-to gdrive

# Render and upload to BOTH YouTube and Google Drive
python main.py --character sukuna --duration 22.0 --upload --upload-to both
```

### 3. Manage Phonk Music Library
```bash
# List all downloaded phonk tracks
python scripts/download_phonk.py --list

# Download full popular phonk catalog from internet
python scripts/download_phonk.py --all
```

### 4. Fetch Clips & Scenepacks
```bash
# Fetch and slice clips for a character
python scripts/fetch_clips.py --character gojo

# Pull clips from a public GitHub repository
python scripts/fetch_clips.py --github-repo loobah18-arch/anidoc-ai-automation --character spiderman
```

### 5. Run Test Suite
```bash
python test_pipeline.py
```

---

## 🔐 Upload Configuration

### YouTube Upload Setup
To upload videos to YouTube, configure these environment variables or GitHub Secrets:
- `YOUTUBE_CLIENT_ID` - OAuth2 Client ID
- `YOUTUBE_CLIENT_SECRET` - OAuth2 Client Secret
- `YOUTUBE_REFRESH_TOKEN` - OAuth2 Refresh Token

### Google Drive Upload Setup
To upload videos to Google Drive, configure:
- `GDRIVE_CREDENTIALS` - Service Account JSON or OAuth2 credentials
- `GDRIVE_UPLOAD_FOLDER_ID` - (Optional) Folder ID where videos will be uploaded

**Getting Google Drive Credentials:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Drive API
4. Create credentials (Service Account or OAuth2)
5. Download the JSON credentials file
6. Set `GDRIVE_CREDENTIALS` to the JSON content or file path

---

## 🤖 GitHub Actions Workflow
The automated workflow runs twice daily at `06:30 UTC` and `18:30 UTC` via [`.github/workflows/daily_edit.yml`](.github/workflows/daily_edit.yml).

**Workflow Dispatch Inputs:**
- `universe` - Choose marvel, jjk, or random
- `character` - Specific character to feature
- `phonk` - Background music track
- `upload` - Whether to upload the rendered video
- `upload_to` - Destination: youtube, gdrive, or both
- `gdrive_upload_folder` - Google Drive folder ID for uploads
