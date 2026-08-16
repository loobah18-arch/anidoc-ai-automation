"""
Dynamic High-Retention ASS Subtitle Stylizer for Anime & Marvel Shorts.
Features Word-by-Word Karaoke Highlighting, Kinetic Pops, and Safe-Zone Framing.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional

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
        "fontsize": 74,
        "primary": "&H00FFFFFF",      # Crisp White inactive
        "active_word": "&H002BF5FF",  # Bright Gold Active (BGR)
        "outline": "&H00000000",      # Deep Black Outline
        "shadow": "&H90000000",
        "outline_width": 5.5,
        "shadow_depth": 3.5,
        "alignment": 2,               # Mid-Lower Third (Safe Zone)
        "margin_v": 380,
        "badge_color": "&H002BF5FF"
    },
    "cyber_glow": {
        "font": "Arial",
        "fontsize": 74,
        "primary": "&H00FFFFFF",
        "active_word": "&H00FFFF00",  # Neon Cyan Active
        "outline": "&H00FF55D2",      # Neon Purple Glow Outline
        "shadow": "&H99000000",
        "outline_width": 6.0,
        "shadow_depth": 4.0,
        "alignment": 2,
        "margin_v": 380,
        "badge_color": "&H00FFFF00"
    },
    "anime_shrine": {
        "font": "Arial",
        "fontsize": 76,
        "primary": "&H00FFFFFF",
        "active_word": "&H003333FF",  # Blood Crimson Active
        "outline": "&H00000000",      # Pure Black
        "shadow": "&H99000088",       # Crimson Drop Shadow
        "outline_width": 5.5,
        "shadow_depth": 4.0,
        "alignment": 2,
        "margin_v": 380,
        "badge_color": "&H003333FF"
    },
    "cinematic_minimal": {
        "font": "Arial",
        "fontsize": 68,
        "primary": "&H00FFFFFF",
        "active_word": "&H00E0E0E0",
        "outline": "&H00000000",
        "shadow": "&H60000000",
        "outline_width": 4.5,
        "shadow_depth": 2.5,
        "alignment": 2,
        "margin_v": 380,
        "badge_color": "&H00FFFFFF"
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
    """
    output_ass_path.parent.mkdir(parents=True, exist_ok=True)
    
    cfg = SUBTITLE_STYLE_PRESETS.get(style_preset, SUBTITLE_STYLE_PRESETS["viral_karaoke"]).copy()
    if primary_color:
        cfg["primary"] = primary_color
    if active_color:
        cfg["active_word"] = active_color
    if glow_color:
        cfg["outline"] = glow_color
        
    words = [w.strip() for w in quote_text.strip().split() if w.strip()]
    if not words:
        words = ["HONORED", "ONE"]
        
    total_dur = max(0.6, end_time - start_time)
    word_dur = total_dur / len(words)
    
    ass_header = f"""[Script Info]
Title: AniDoc High-Retention Kinetic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: BaseText,{cfg['font']},{cfg['fontsize']},{cfg['primary']},&H00000000,{cfg['outline']},{cfg['shadow']},-1,0,0,0,100,100,2,0,1,{cfg['outline_width']},{cfg['shadow_depth']},{cfg['alignment']},40,40,{cfg['margin_v']},1
Style: Badge,{cfg['font']},40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,3,0,1,4.0,2.5,8,40,40,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events = []
    
    # 1. Top Character Universe Badge
    b_start = format_ass_timestamp(start_time)
    b_end = format_ass_timestamp(end_time)
    badge_tag = f"{{\\fad(150,150)\\c{cfg['badge_color']}}}[ {character_name.upper()} ]"
    events.append(f"Dialogue: 2,{b_start},{b_end},Badge,,0,0,0,,{badge_tag}")
    
    # 2. Chunk words into short 2-3 word sequences with active word karaoke
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
                    # Active word: Highlighted color + 118% dynamic bounce
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
