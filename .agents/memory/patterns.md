# Architectural Patterns & Lessons Learned

## 1. Zero Cross-Universe Contamination (CRITICAL)
- **Pitfall**: When an edit for a JJK character is triggered while Google Drive only has Demon Slayer episodes, fallback routines must NEVER pick a file from another universe.
- **Rule**:
  1. `get_file_universe(filename)` returns `'demonslayer'`, `'jjk'`, or `'marvel'`.
  2. In `pick_best_file_for_character()`, filter `files` by `get_file_universe(f['name']) == char_universe`.
  3. If no files match the character's universe in Drive, return `None` (triggers fallback to public scenepacks via yt-dlp/Archive.org). Never fall back to `eligible_files = files`.
  4. Slicer entry point `slice_action_moments_from_source()` asserts matching universe and throws `ValueError` if a mismatch is detected.

## 2. Filename-to-Episode Code Matching
- **Pitfall**: Matching `Demon_Slayer_..._S01_E24.mp4` fell through to `S01E24` because `DS_S01E24` had no timestamp metadata file.
- **Rule**:
  - Always separate filename parsing into dedicated branches (`is_ds and not is_jjk` vs `is_jjk and not is_ds`).
  - Demon Slayer filenames return `DS_...` format and never fall through to JJK codes.

## 3. SEO Metadata & Description Sanitization
- **Rule**:
  - Every title, tag set, and description must be screened against cross-universe keyword sets (`DEMONSLAYER_KEYWORDS`, `JJK_KEYWORDS`, `MARVEL_KEYWORDS`).
  - Titles: Must not contain names or keywords from any other franchise.
  - Tags: Max 12 sanitized tags. Cross-universe tags are stripped, and canonical tags (`#demonslayer`, `#kimetsunoyaiba` or `#jjk`, `#jujutsukaisen`) are always prepended.
  - Descriptions: Use `format_anime_description()` to format:
    - Official series title in English & Japanese (`Demon Slayer: Kimetsu no Yaiba (鬼滅の刃)` or `Jujutsu Kaisen (呪術廻戦)`)
    - Character name and iconic dialogue quote
    - Copyright attribution (ufotable / MAPPA) under Fair Use (Section 107)

## 4. Video & Audio Assembly Standards
- **Framing**: Centered 16:9 widescreen letterbox (1080x608 active frame, 656px top/bottom bars) in 1080x1920 portrait canvas. Matches viral reference AMV formats.
- **Duration**: 60.0s full duration for YouTube Shorts watch-time maximization.
- **Framerate**: 24fps native (source anime is 24fps).
- **Audio & Beat Sync**: Phonk BGM (128-142 BPM) analyzed for beat grid; primary drop mapped to 4.2-6.0s. Cuts are beat-synced with subtle velocity slow-mo on non-drop intros and sharp cuts on the drop.
- **Color Grading (CC)**: Dual-tone cinematic dark grading with crushed blacks, muted saturation (0.65-0.75), unsharp sharpening (1.2-1.3), and character energy color highlights.

## 5. Device Constraint (Termux on Android Phone)
- Physical phone with ~1.2GB RAM free.
- NEVER run full FFmpeg 4K 60-second video renders or heavy builds locally in Termux.
- Local work: Unit tests with mocks/short synthetic test renders, config updates, code edits.
- Cloud work: All production renders, heavy video processing, and YouTube uploads run in GitHub Actions CI/CD (`daily_edit.yml`).
