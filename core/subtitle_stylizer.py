"""
Dynamic Glowing ASS Subtitle Generator for Marvel & JJK Edits.
Creates centered kinetic typography with neon strokes and word-by-word emphasis.
"""
from pathlib import Path
from typing import List, Dict, Any

def format_ass_timestamp(seconds: float) -> str:
    """Formats float seconds into ASS timestamp format: H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def generate_kinetic_subtitles(
    quote_text: str,
    start_time: float,
    end_time: float,
    output_ass_path: Path,
    primary_color: str = "&H00FFFFFF",
    glow_color: str = "&H00D2FF00",
    character_name: str = "SPIDER-MAN"
) -> Path:
    """
    Generates high-energy centered kinetic subtitles with neon outline and drop shadow.
    """
    output_ass_path.parent.mkdir(parents=True, exist_ok=True)
    
    words = quote_text.strip().split()
    total_dur = max(0.5, end_time - start_time)
    word_dur = total_dur / max(1, len(words))
    
    ass_header = f"""[Script Info]
Title: Cinematic 4K Edit Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,68,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,2,0,1,5,3,5,40,40,960,1
Style: Glow,Arial,74,{primary_color},&H00FFFFFF,{glow_color},&H90000000,-1,0,0,0,105,105,3,0,1,6,4,5,40,40,960,1
Style: Badge,Arial,36,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,2,0,1,3,2,8,40,40,160,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events = []
    
    # 1. Character badge on top
    badge_start = format_ass_timestamp(start_time)
    badge_end = format_ass_timestamp(end_time)
    events.append(f"Dialogue: 1,{badge_start},{badge_end},Badge,,0,0,0,,{{\\fad(200,200)}}[ {character_name.upper()} ]")
    
    # 2. Chunk words into short 2-3 word punchy lines
    chunk_size = 3
    for i in range(0, len(words), chunk_size):
        chunk = words[i:i+chunk_size]
        chunk_str = " ".join(chunk).upper()
        
        c_start = start_time + (i * word_dur)
        c_end = min(end_time, start_time + ((i + len(chunk)) * word_dur))
        
        t_start_fmt = format_ass_timestamp(c_start)
        t_end_fmt = format_ass_timestamp(c_end)
        
        # Word burst effect with subtle scale bounce
        line_text = f"{{\\fad(80,80)\\t(0,100,\\fscx110\\fscy110)\\t(100,200,\\fscx100\\fscy100)}}{chunk_str}"
        events.append(f"Dialogue: 0,{t_start_fmt},{t_end_fmt},Glow,,0,0,0,,{line_text}")
        
    full_content = ass_header + "\n".join(events) + "\n"
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(full_content)
        
    return output_ass_path
