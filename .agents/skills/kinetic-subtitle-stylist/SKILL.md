---
name: kinetic-subtitle-stylist
description: Dynamic Typography & Subtitle Specialist specializing in Advanced SubStation Alpha (ASS) karaoke effects, glow shaders, spring bounces, and YouTube Shorts safe-zone layout.
---

# Kinetic Subtitle & Typography Stylist

Use this skill when designing, generating, or debugging kinetic subtitles, monologue overlays, or ASS/SSA subtitle scripts for anime edits.

## 1. YouTube Shorts Safe-Zone Positioning (CRITICAL)

Subtitles placed incorrectly get covered by YouTube Shorts UI overlays:
- **Top 15% Dead Zone**: Channel header, search button, back button.
- **Bottom 25% Dead Zone**: Channel name, subscription button, audio track disc, title description, progress bar.
- **Right 20% Dead Zone**: Like, Comment, Share, Remix, Sound button stack.

### Correct Placement Formula:
In a 1080x1920 canvas with centered 16:9 widescreen video (y: 656px to 1264px):
- Place dialogue text centered within the active frame: `Alignment=2` (bottom-centered of active box) with `MarginV=110 – 140px` above the bottom letterbox border.
- Subtitle lines must NEVER extend past `MarginL=80px` and `MarginR=180px`.

---

## 2. Dynamic Kinetic ASS Presets

### Preset A: `viral_karaoke` (Default Top Retention)
Word-by-word active glow with subtle spring bounce on pronunciation:
```ass
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KaraokeActive,TheBoldFont,64,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1.5,0,1,4,2,2,80,180,120,1
```
Spring animation tag on active word:
```ass
{\t(0,100,\fscx115\fscy115)\t(100,200,\fscx100\fscy100)}
```

### Preset B: `cyber_glow` (Phonk & Tech Style)
Cyan-neon outer glow with sharp italic typography:
```ass
Style: CyberGlow,Montserrat Black,58,&H00FFFF00,&H00D2FF00,&H00090D16,&H0000D2FF,-1,1,0,0,100,100,2.0,0,1,3,4,2,80,180,120,1
```

### Preset C: `anime_shrine` (Sukuna & Dark Fantasy)
Crimson blood stroke with gothic/impact font weight:
```ass
Style: AnimeShrine,Komika Axis,62,&H00FFFFFF,&H002233FF,&H00180000,&H90000000,-1,0,0,0,100,100,1.0,0,1,4,3,2,80,180,120,1
```

---

## 3. Pacing & Readability Rules

1. **Max 3-5 Words Per Screen**:
   - Long sentences cause drop-off. Break quotes into rapid 2-4 word bursts synced to the speaker's cadence.
2. **Punctuation Stripping**:
   - Strip full stops (`.`) and trailing commas (`,`) from viral subtitles. Keep question marks (`?`) and exclamation marks (`!`) for emotional emphasis.
3. **Contrast Verification**:
   - Always include a dark outline (`Outline=3-4`) and soft shadow (`Shadow=2-3`). White text without outline disappears on light backgrounds (lightning, explosions).
