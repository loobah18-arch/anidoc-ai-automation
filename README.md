# ⚡ AniDoc 4K Phonk / Scene Edit Automation Engine (Marvel & Jujutsu Kaisen)

Automated high-retention 9:16 vertical Short video generator for **Marvel Cinematic Universe (MCU)** and **Jujutsu Kaisen (JJK)** phonk & velocity edits.

---

## 🌟 Key Features

- **⚡ Beat-Drop & Onset Detection:** Slices action clips and scene transitions precisely on every heavy bass drop and transient spike.
- **🎨 4K HDR Color Grade (CC):** Cinematic contrast curves, lifted saturation, unsharp edge clarity, and cinematic vignette presets (`marvel_hdr`, `jjk_void`, `sukuna_shrine`, `cyber_phonk`).
- **💥 Impact Beat Flashes & Velocity Punch-ins:** Dynamic zoom punch-ins and momentary white screen burst flash overlays timed to heavy drops.
- **✨ Glowing Kinetic Typography:** Dynamic centered `.ass` subtitles with neon outline and word-by-word pulse animations.
- **🧠 AI Quote & SEO Generator:** Generates viral monologue quotes, titles, descriptions, and hashtags using NVIDIA Nemotron 3 Ultra / DeepSeek v4 with procedural fallback.
- **🚀 Automated YouTube Auto-Publisher:** Directly publishes 9:16 Shorts to YouTube Data API v3 on a twice-daily automated schedule via GitHub Actions.

---

## 🎬 Supported Universes & Characters

| Universe | Characters | Iconic Color Themes |
| :--- | :--- | :--- |
| **Marvel** | Spider-Man, Iron Man, Thor, Thanos, Loki, Captain America, Wolverine | Crimson Red, Gold, Electric Blue, Cosmic Violet |
| **Jujutsu Kaisen** | Gojo Satoru, Ryomen Sukuna, Toji Fushiguro, Yuji Itadori | Hollow Purple, Malevolent Blood Red, Deep Slate |

---

## 🛠️ Local Usage

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Render a 4K Edit
```bash
# Generate a Spider-Man edit
python main.py --character spiderman --duration 22.0

# Generate a Gojo Satoru edit
python main.py --character gojo --duration 22.0

# Generate a random JJK edit and upload to YouTube
python main.py --universe jjk --duration 22.0 --upload
```

### 3. Run Test Suite
```bash
python test_pipeline.py
```

---

## 🤖 GitHub Actions Workflow
The workflow runs twice daily at `06:30 UTC` and `18:30 UTC` via [`.github/workflows/daily_edit.yml`](.github/workflows/daily_edit.yml).
