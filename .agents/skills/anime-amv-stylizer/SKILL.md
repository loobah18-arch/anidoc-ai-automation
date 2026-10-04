---
name: anime-amv-stylizer
description: Elite Anime AMV & 4K Phonk Video Editor specializing in beat-synced cuts, bass drop timing, velocity ramping, camera zoom punches, and visual impact effects.
---

# Anime AMV & Phonk Editing Stylizer

Use this skill when designing, reviewing, or enhancing anime scene edits, AMVs, or phonk video montages for YouTube Shorts and TikTok.

## Core Editing Architecture (60.0s Narrative Arc)

Top-performing viral anime edits follow a strict 5-part physiological tension-and-release curve:

1. **The Hook (0.0s – 3.5s)**:
   - High-tension opening: Character dialogue quote or dramatic close-up.
   - Pacing: 0.85x subtle slow-motion to create anticipation.
   - Framing: Centered 16:9 widescreen letterbox (1080x608 active frame, 656px top/bottom black bars).
2. **The Inhale Pause (3.5s – 4.2s)**:
   - Brief 0.3s–0.5s audio dip / silence or sound effect (blade unsheathing, footstep, deep breath).
   - Video cut directly to the character's eye flash or weapon release.
3. **The Primary Drop (4.2s – 25.0s)**:
   - Hard bass impact (Phonk 808 drop) perfectly locked to the sword strike or technique activation.
   - Rapid beat-synced cuts (0.4s – 1.2s per cut) matching snare/kick onsets.
   - Velocity profile: 1.0x straight cuts on the drop (NO velocity smoothing on drop frames; snappy impact).
4. **The Counter-Attack / Secondary Climax (25.0s – 48.0s)**:
   - Secondary drop with varied camera angles (switch between wide combat and close-up dynamic impact).
   - Occasional single-frame beat flashes on heavy bass hits.
5. **The Finisher (48.0s – 60.0s)**:
   - Final decisive strike (e.g. Hinokami Kagura decapitation, Hollow Purple obliteration, Malevolent Shrine screen cut).
   - Dissolve or hard cut to black on the final bass reverb.

---

## Velocity & Timing Rules

| Segment Role | Target Speed | Optical Scale | FFmpeg Filter |
| :--- | :--- | :--- | :--- |
| **Intro / Tension** | 0.85x | 1.02x | `setpts=(1/0.85)*PTS,scale=1.02*iw:1.02*ih` |
| **Drop Impact** | 1.00x | 1.00x | `setpts=PTS-STARTPTS` (Straight snappy cut) |
| **Rapid Barrage** | 1.25x | 1.00x | `setpts=(1/1.25)*PTS` |
| **Climax Impact** | 0.70x -> 1.5x | 1.04x -> 1.00x | Anticipation slow-mo into speed strike |

### The Golden Rule of Drop Cuts
- Never place a slow-motion ramp ON the drop impact frame. Slow down BEFORE the hit (anticipation), snap at 1.0x or 1.25x ON the hit.

---

## FFmpeg Visual Impact Effects

### 1. Subtle Beat Flash (White Exposure Burst)
Used sparingly on major drop hits (max 3 times per 60s video to avoid strobe fatigue):
```bash
drawbox=x=0:y=0:w=iw:h=ih:color=white@0.35:t=fill:enable='between(t,DROP_TIME,DROP_TIME+0.08)'
```

### 2. Camera Punch-In Zoom
Creates perceived impact without shaking the UI letterbox:
```bash
scale=1.03*iw:1.03*ih,crop=iw/1.03:ih/1.03
```

### 3. Widescreen Letterbox Active Geometry
Guarantees 100% active frame visibility without edge distortion:
```bash
scale=1080:608:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black
```
