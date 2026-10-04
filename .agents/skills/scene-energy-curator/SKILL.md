---
name: scene-energy-curator
description: Combat Scene Selection & Action Energy Curator specializing in extracting peak battle climaxes, volume energy thresholding, and narrative pacing from raw anime episodes.
---

# Scene Energy & Combat Moment Curator

Use this skill when selecting, timestamping, slicing, or curating raw anime footage (Google Drive, MKV/MP4 files) to extract peak viral action clips while filtering out static dialogue filler.

## 1. Action Energy Detection (Audio & Motion Thresholding)

Raw anime episodes are 80% dialogue / exposition and 20% high-energy combat. To produce a viral 4K edit:

1. **Volume Energy Slicing**:
   - Combat moments exhibit significant loudness jumps (-16 LUFS to -6 LUFS) driven by swords clashing, explosions, power screams, and heavy SFX.
   - Use FFmpeg volume analysis to scan for high-energy RMS windows:
     ```bash
     ffmpeg -i episode.mp4 -vn -af "volumedetect" -f null -
     ```
2. **Action Score Thresholds**:
   - `0.85 – 1.00 (Tier S - Climax / Finisher)`: Hand-to-hand combat, Domain Expansion activation, Hinokami Kagura dance, Blood Demon Art explosions.
   - `0.70 – 0.84 (Tier A - Mid-Fight Clashes)`: Rapid sword exchanges, running / speed blitzing, impact kicks.
   - `< 0.60 (Tier C - Reject)`: Static talking heads, character walking, still reaction shots.

---

## 2. 60-Second Segment Allocation & Clip Variety

Never repeat the exact same angle or character pose sequentially. Maintain visual rhythm by alternating cut types:

| Timestamp Window | Segment Type | Visual Focus | Example (Demon Slayer) | Example (JJK) |
| :--- | :--- | :--- | :--- | :--- |
| **0.0s – 3.5s** | Hook Scene | Close-up eye flash or stance | Inosuke head tilt / snort | Gojo blindfold slide |
| **3.5s – 5.0s** | Anticipation | Slow motion breath / charge | Blade unsheathing | Hand sign formation |
| **5.0s – 20.0s** | Combat Barrage | Rapid dynamic clash cuts (0.8s) | Beast Breathing dual slashes | Yuji & Todo swap hits |
| **20.0s – 35.0s** | Technique Climax | Mid-shot energy wave | Seventh Form spatial awareness | Divergent Fist impact |
| **35.0s – 50.0s** | Counter-Attack | Opponent reaction / clash | Gyutaro flying sickles | Mahito soul transformation |
| **50.0s – 60.0s** | Finisher | Peak animation money-shot | Final decapitation strike | Black Flash 120% potential |

---

## 3. Strict Episode-to-Universe Boundary Checks

Before slicing any file:
1. Verify the filename universe matches the character universe using `get_file_universe()`.
2. Reject files containing opposing franchise keywords.
3. Track timestamp history in `gdrive_edit_history.json` to prevent re-slicing identical scene offsets on consecutive runs.
