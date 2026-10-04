---
name: anime-color-grading-director
description: 4K HDR Color Grading & Visual Tone Director specializing in moody anime color correction, crushed blacks, dual-tone lighting, and character energy highlights.
---

# Anime 4K HDR Color Grading Director

Use this skill when designing, tuning, or auditing color grading (CC) filters for anime edits, scene compilations, and 4K Phonk AMVs.

## The Viral Anime Look: "Dark Cinematic Moody"

Amateur anime edits look washed-out, overly bright, or cartoonishly oversaturated. Professional 4K viral AMVs follow the **Dark Cinematic Moody** aesthetic:

1. **Crushed Blacks & Rich Contrast**:
   - Contrast bumped to `1.35 – 1.45`.
   - Brightness pulled down slightly to `-0.06 – -0.08` to eliminate flat washed-out grey tones.
   - Gamma compressed to `0.82 – 0.85` for deep, cinematic shadows.
2. **Controlled Muted Saturation with Isolated Energy**:
   - Overall saturation pulled back to `0.65 – 0.75` (desaturating skin tones and backgrounds to look realistic and gritty).
   - Character energy effects (flames, lightning, cursed energy, void purple) stand out in vivid contrast against the dark background.
3. **Double Unsharp Mask (The 4K HDR Illusion)**:
   - `unsharp=5:5:1.2:5:5:0.0` sharply delineates ink lines and eye contours without creating ringing artifacts.
4. **Vignetting**:
   - `vignette=PI/3.8` darkens outer frame edges, naturally focusing viewer attention on the center character action.

---

## Franchise & Character Presets Matrix

### 1. Jujutsu Kaisen Universe
- **Gojo Satoru (`jjk_void`)**:
  - Cool blue / void violet dual-tone.
  - `colorbalance=rs=-0.15:gs=0.05:bs=0.20:rm=-0.08:gm=0.02:bm=0.12`
  - Text highlight: Cyan (`#00D2FF`) / Eyes Six Eyes glow.
- **Ryomen Sukuna (`sukuna_shrine` / `sukuna_crimson`)**:
  - Warm crimson / blood red shadow tone.
  - `colorbalance=rs=0.22:gs=-0.06:bs=-0.14:rm=0.15:gm=-0.04:bm=-0.08`
  - Text highlight: Crimson (`#FF2233`) / Blood shrine aura.
- **Toji Fushiguro (`cyber_phonk`)**:
  - Deep slate grey / electric blue metallic grading.
  - `contrast=1.40`, `brightness=-0.08`, `saturation=0.65`.

### 2. Demon Slayer (Kimetsu no Yaiba) Universe
- **Tanjiro Kamado (`hinokami_flame`)**:
  - Warm solar orange / ember red tone.
  - `colorbalance=rs=0.20:gs=-0.04:bs=-0.12:rm=0.14:gm=-0.02:bm=-0.06`
  - Text highlight: Solar flame (`#FF6611`).
- **Kyojuro Rengoku (`flame_hashira`)**:
  - Blazing amber / crimson saturation.
  - `contrast=1.38`, `brightness=-0.07`, `saturation=0.75`.
- **Zenitsu Agatsuma (`thunder_gold`)**:
  - Lightning electric gold with cool shadows.
  - `colorbalance=rs=0.12:gs=0.08:bs=-0.15:rm=0.08:gm=0.05:bm=-0.10`
  - Text highlight: Lightning gold (`#FFD700`).
- **Giyu Tomioka (`water_breathing`)**:
  - Deep oceanic cobalt with calm desaturated highlights.
  - `colorbalance=rs=-0.18:gs=0.02:bs=0.22:rm=-0.10:gm=0.02:bm=0.14`.
- **Inosuke Hashibira (`beast_breathing`)**:
  - Indigo / wild cyan dual-tone.
  - `colorbalance=rs=-0.12:gs=0.04:bs=0.18:rm=-0.08:gm=0.02:bm=0.12`.

---

## Standard FFmpeg Filterchain Assembly

```bash
eq=contrast=1.38:brightness=-0.07:saturation=0.70:gamma=0.84,colorbalance=rs=0.20:gs=-0.05:bs=-0.15,unsharp=5:5:1.2:5:5:0.0,vignette=PI/3.8
```
