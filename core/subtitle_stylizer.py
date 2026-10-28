"""
Dynamic High-Retention ASS Subtitle Stylizer for Anime & Marvel Shorts.
Features Word-by-Word Karaoke Highlighting, Kinetic Pops, and Safe-Zone Framing.

Fixes applied:
- Subtitle margin_v increased from 380 to 180 (safe zone above phone chrome)
- Removed ugly [CHARACTER] badge from top of screen
- Font size bumped for all presets (more punchy, reference-style look)
- WrapStyle set to 1 (wraps before cutting off right edge)
- Text wraps within safe margins (MarginL/R widened to 80)
- Bigger outline (5.5 → 7.0) for readability on any background
"""
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import VIDEO_WIDTH, VIDEO_HEIGHT

def format_ass_timestamp(seconds: float) -> str:
    """Formats float seconds into ASS timestamp format: H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


SUBTITLE_STYLE_PRESETS = {
    "spur_hook": {
        "font": "Bebas Neue",
        "fontsize": 68,
        "primary": "&H00FFFFFF",         # Pure Crisp White
        "active_word": "&H001E27FF",     # Crimson Red Highlight (&HAABBGGRR in ASS)
        "outline": "&H00000000",         # Deep Solid Black Outline
        "shadow": "&HA0000000",          # Dark Drop Shadow
        "outline_width": 7.5,
        "shadow_depth": 4.0,
        "alignment": 8,                  # Top-Center (Upper Third Header Zone)
        "margin_v": 200,                 # 200px from top of 1080x1920 canvas
        "margin_lr": 80,
    },
    "viral_karaoke": {
        "font": "Arial",
        "fontsize": 64,                  # Proportional for 1:1 square canvas
        "primary": "&H00FFFFFF",
        "active_word": "&H002BF5FF",     # Bright Cyan Active
        "outline": "&H00000000",
        "shadow": "&H90000000",
        "outline_width": 6.0,
        "shadow_depth": 3.5,
        "alignment": 2,                  # Bottom-center
        "margin_v": 85,                  # Sits in lower third of square
        "margin_lr": 60,
    },
    "cyber_glow": {
        "font": "Arial",
        "fontsize": 64,
        "primary": "&H00FFFFFF",
        "active_word": "&H00FFFF00",     # Neon Cyan Active
        "outline": "&H00FF55D2",
        "shadow": "&H99000000",
        "outline_width": 6.0,
        "shadow_depth": 3.5,
        "alignment": 2,
        "margin_v": 85,
        "margin_lr": 60,
    },
    "anime_shrine": {
        "font": "Arial",
        "fontsize": 66,
        "primary": "&H00FFFFFF",
        "active_word": "&H003333FF",     # Blood Crimson Active
        "outline": "&H00000000",
        "shadow": "&H99000088",
        "outline_width": 6.0,
        "shadow_depth": 3.5,
        "alignment": 2,
        "margin_v": 85,
        "margin_lr": 60,
    },
    "cinematic_minimal": {
        "font": "Arial",
        "fontsize": 58,
        "primary": "&H00FFFFFF",
        "active_word": "&H00E0E0E0",
        "outline": "&H00000000",
        "shadow": "&H60000000",
        "outline_width": 5.0,
        "shadow_depth": 2.5,
        "alignment": 2,
        "margin_v": 85,
        "margin_lr": 60,
    }
}


EMPHASIS_KEYWORDS = {
    "DEADLY", "BATTLES", "DUTY", "CLIMAX", "SUN", "HINOKAMI", "GOD", "SHRINE",
    "PURPLE", "STRONGEST", "CURSE", "OBLITERATED", "SEVERED", "DEMON", "PURE",
    "CALAMITY", "POWER", "FATAL", "FLAME", "AWAKENED", "KILLER", "MASSACRE",
    "BLOOD", "DRAGON", "DESTRUCTION", "CINEMA", "TEENAGERS", "FIGHT", "BRO",
    "SLAYER", "HOLLOW", "DOMAIN", "EXPANSION", "FIRE", "RED", "SOUL", "MALEVOLENT",
    "DEATH", "VOICES", "INFINITY", "THUNDER", "LIGHTNING", "AURA", "RAGE",
    "SURVIVE", "SURVIVES", "DEFEAT", "WIN", "WINS", "STRONGER", "WEAK", "WARRIOR",
    "COLDEST", "CRAZIEST", "BEAST", "GENIUS", "CHAOS", "GODSPEED", "1V1",
    "SOLO", "DEADLIEST", "PRIME", "BEST", "PEAK", "PRODIGY", "POISON", "UNTOUCHABLE"
}


def _format_spur_line(words: List[str], red_hex: str, white_hex: str) -> str:
    """Formats words into 2 lines with red keyword emphasis matching the reference edit."""
    formatted = []
    has_red = False
    for w in words:
        clean = w.strip(".,!?:;\"'").upper()
        if clean in EMPHASIS_KEYWORDS:
            formatted.append(r"{\c" + red_hex + r"&}" + w.upper() + r"{\c" + white_hex + r"&}")
            has_red = True
        else:
            formatted.append(w.upper())
    if not has_red and words:
        last = words[-1]
        formatted[-1] = r"{\c" + red_hex + r"&}" + last.upper() + r"{\c" + white_hex + r"&}"

    if len(words) > 4:
        mid = len(words) // 2
        return " ".join(formatted[:mid]) + r"\N" + " ".join(formatted[mid:])
    return " ".join(formatted)


def generate_kinetic_subtitles(
    quote_text: str,
    start_time: float = 0.2,
    end_time: float = 6.8,
    output_ass_path: Optional[Path] = None,
    style_preset: str = "spur_hook",
    primary_color: Optional[str] = None,
    active_color: Optional[str] = None,
    glow_color: Optional[str] = None,
    character_name: str = "SPIDER-MAN",
    chunk_size: int = 3,
    drop_time: Optional[float] = None,
    face_y: Optional[float] = None
) -> Path:
    """
    Generates dynamic high-retention ASS subtitles for YouTube Shorts (Phase 5).
    Features:
    - Short caption chunks (2-3 words per chunk, 0.8s - 1.6s duration)
    - Face avoidance: automatically moves subtitles away from detected character faces
    - YouTube Shorts safe zone padding (clear of right UI icons and bottom seek bar)
    - Animated entrances and exits (\fad(80,80) with kinetic pop)
    - Important-word emphasis with accent color highlighting
    - Full karaoke mode support
    """
    output_ass_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = SUBTITLE_STYLE_PRESETS.get(style_preset, SUBTITLE_STYLE_PRESETS["spur_hook"]).copy()
    if primary_color:
        cfg["primary"] = primary_color
    if active_color:
        cfg["active_word"] = active_color
    if glow_color:
        cfg["outline"] = glow_color

    # Shorts safe zone margins
    margin_lr = max(90, cfg.get("margin_lr", 80))

    # Face avoidance: adapt alignment based on character face position
    alignment = cfg["alignment"]
    margin_v = cfg["margin_v"]
    if face_y is not None:
        if face_y < 0.45:
            # Face is in upper third -> put captions in lower third safe zone
            alignment = 2
            margin_v = 220
        else:
            # Face is in lower third/center -> put captions in upper third safe zone
            alignment = 8
            margin_v = 240

    words = [w.strip() for w in quote_text.strip().split() if w.strip()]
    if not words:
        words = ["HONORED", "ONE"]

    total_dur = max(0.6, end_time - start_time)

    ass_header = f"""[Script Info]
Title: AniDoc High-Retention Kinetic Subtitles
ScriptType: v4.00+
WrapStyle: 1
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: {VIDEO_WIDTH}
PlayResY: {VIDEO_HEIGHT}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BaseText,{cfg['font']},{cfg['fontsize']},{cfg['primary']},&H00000000,{cfg['outline']},{cfg['shadow']},-1,0,0,0,100,100,2,0,1,{cfg['outline_width']},{cfg['shadow_depth']},{alignment},{margin_lr},{margin_lr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []

    # Calculate short caption chunks (2-3 words per chunk)
    chunks: List[List[str]] = []
    chunk_len = max(2, min(3, chunk_size))
    for i in range(0, len(words), chunk_len):
        chunks.append(words[i:i + chunk_len])

    if not chunks:
        chunks = [words]

    dur_per_chunk = min(1.6, max(0.75, total_dur / len(chunks)))

    if style_preset == "viral_karaoke":
        # Karaoke word-by-word timing within short chunks
        word_dur = total_dur / len(words)
        for chunk_idx, chunk_words in enumerate(chunks):
            base_idx = chunk_idx * chunk_len
            for word_in_chunk_idx, active_word in enumerate(chunk_words):
                global_word_idx = base_idx + word_in_chunk_idx
                w_start = start_time + (global_word_idx * word_dur)
                w_end = min(end_time, w_start + word_dur)

                ts_start = format_ass_timestamp(w_start)
                ts_end = format_ass_timestamp(w_end)

                line_parts = []
                for j, w in enumerate(chunk_words):
                    w_clean = w.strip(".,!?:;\"'").upper()
                    is_emphasized = w_clean in EMPHASIS_KEYWORDS
                    if j == word_in_chunk_idx:
                        line_parts.append(
                            f"{{\\fad(60,60)\\c{cfg['active_word']}\\t(0,80,\\fscx115\\fscy115)\\t(80,160,\\fscx100\\fscy100)}}{w.upper()}{{\\rBaseText}}"
                        )
                    elif is_emphasized:
                        line_parts.append(f"{{\\c{cfg['active_word']}}}{w.upper()}{{\\rBaseText}}")
                    else:
                        line_parts.append(f"{{\\c{cfg['primary']}}}{w.upper()}")

                events.append(f"Dialogue: 1,{ts_start},{ts_end},BaseText,,0,0,0,,{' '.join(line_parts)}")
    else:
        # Dynamic short statement chunks with animated entrance/exit & keyword emphasis
        for idx, chunk_words in enumerate(chunks):
            c_start = start_time + (idx * dur_per_chunk)
            c_end = min(end_time, c_start + dur_per_chunk)
            if c_start >= end_time:
                break

            ts_start = format_ass_timestamp(c_start)
            ts_end = format_ass_timestamp(c_end)

            formatted_words = []
            for w in chunk_words:
                w_clean = w.strip(".,!?:;\"'").upper()
                if w_clean in EMPHASIS_KEYWORDS or (len(chunk_words) == 1):
                    formatted_words.append(
                        f"{{\\c{cfg['active_word']}\\t(0,90,\\fscx114\\fscy114)\\t(90,180,\\fscx100\\fscy100)}}{w.upper()}{{\\rBaseText}}"
                    )
                else:
                    formatted_words.append(w.upper())

            chunk_line = " ".join(formatted_words)
            # Animated entrance/exit with smooth 80ms alpha fade
            events.append(
                f"Dialogue: 1,{ts_start},{ts_end},BaseText,,0,0,0,,{{\\fad(80,80)\\t(0,90,\\fscx106\\fscy106)\\t(90,180,\\fscx100\\fscy100)}}{chunk_line}"
            )

    full_ass = ass_header + "\n".join(events) + "\n"
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(full_ass)

    return output_ass_path
            
    full_ass = ass_header + "\n".join(events) + "\n"
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(full_ass)
        
    return output_ass_path
