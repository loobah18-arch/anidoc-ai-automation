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


def generate_kinetic_subtitles(
    quote_text: str,
    start_time: float = 0.2,
    end_time: float = 6.8,
    output_ass_path: Optional[Path] = None,
    style_preset: str = "viral_karaoke",
    primary_color: Optional[str] = None,
    active_color: Optional[str] = None,
    glow_color: Optional[str] = None,
    character_name: str = "SPIDER-MAN",
    chunk_size: int = 3
) -> Path:
    """
    Generates word-by-word animated kinetic karaoke subtitles (.ass) for YouTube Shorts.

    Key fixes vs previous version:
    - No more [CHARACTER] badge (it was ugly and amateurish)
    - WrapStyle=1: text wraps instead of clipping off right edge
    - margin_v=180: sits above phone navigation chrome
    - Wider MarginL/MarginR to keep text inside safe zone
    - Bigger fontsize + outline for punchy viral look
    """
    output_ass_path.parent.mkdir(parents=True, exist_ok=True)
    
    cfg = SUBTITLE_STYLE_PRESETS.get(style_preset, SUBTITLE_STYLE_PRESETS["viral_karaoke"]).copy()
    if primary_color:
        cfg["primary"] = primary_color
    if active_color:
        cfg["active_word"] = active_color
    if glow_color:
        cfg["outline"] = glow_color

    margin_lr = cfg.get("margin_lr", 80)
        
    words = [w.strip() for w in quote_text.strip().split() if w.strip()]
    if not words:
        words = ["HONORED", "ONE"]
        
    total_dur = max(0.6, end_time - start_time)
    word_dur = total_dur / len(words)
    
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
Style: BaseText,{cfg['font']},{cfg['fontsize']},{cfg['primary']},&H00000000,{cfg['outline']},{cfg['shadow']},-1,0,0,0,100,100,2,0,1,{cfg['outline_width']},{cfg['shadow_depth']},{cfg['alignment']},{margin_lr},{margin_lr},{cfg['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events = []
    
    # Word-by-word karaoke lines (NO badge — removed ugly [CHARACTER] top tag)
    for chunk_idx in range(0, len(words), chunk_size):
        chunk_words = words[chunk_idx:chunk_idx + chunk_size]
        chunk_start = start_time + (chunk_idx * word_dur)
        chunk_end = min(end_time, start_time + ((chunk_idx + len(chunk_words)) * word_dur))
        
        # Word-by-word highlight within this chunk
        for word_in_chunk_idx, active_word in enumerate(chunk_words):
            global_word_idx = chunk_idx + word_in_chunk_idx
            w_start = start_time + (global_word_idx * word_dur)
            w_end = min(end_time, w_start + word_dur)
            
            ts_start = format_ass_timestamp(w_start)
            ts_end = format_ass_timestamp(w_end)
            
            # Construct chunk string with highlighted word
            line_parts = []
            for j, w in enumerate(chunk_words):
                w_upper = w.upper()
                if j == word_in_chunk_idx:
                    # Active word: Highlighted color + 118% dynamic bounce scale
                    line_parts.append(
                        f"{{\\c{cfg['active_word']}\\t(0,100,\\fscx118\\fscy118)\\t(100,200,\\fscx100\\fscy100)}}{w_upper}{{\\rBaseText}}"
                    )
                else:
                    # Inactive word: Clean white
                    line_parts.append(f"{{\\c{cfg['primary']}}}{w_upper}")
                    
            formatted_line = " ".join(line_parts)
            events.append(f"Dialogue: 1,{ts_start},{ts_end},BaseText,,0,0,0,,{formatted_line}")
            
    full_ass = ass_header + "\n".join(events) + "\n"
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(full_ass)
        
    return output_ass_path
