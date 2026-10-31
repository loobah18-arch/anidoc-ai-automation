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


CHARACTER_HYPE_PHRASES = {
    "gojo": [
        "UNTOUCHABLE",
        "INFINITY UNLEASHED",
        "DOMAIN EXPANSION",
        "INFINITE VOID",
        "HOLLOW PURPLE",
        "THROUGHOUT HEAVEN AND EARTH",
        "THE HONORED ONE 👑"
    ],
    "sukuna": [
        "KING OF CURSES",
        "MALEVOLENT SHRINE",
        "CLEAVE & DISMANTLE",
        "DIVINE FLAME",
        "STAND PROUD 💀",
        "ABSOLUTE POWER"
    ],
    "tanjiro": [
        "HINOKAMI KAGURA",
        "SUN BREATHING",
        "SET YOUR HEART ABLAZE",
        "TOTAL CONCENTRATION",
        "DRAGON SUN HALO 🔥",
        "NEVER GIVE UP"
    ],
    "rengoku": [
        "FLAME BREATHING",
        "NINTH FORM: RENGOKU",
        "SET YOUR HEART ABLAZE",
        "I WILL FULFILL MY DUTY ❤️‍🔥",
        "HERO OF THE CORPS"
    ],
    "yuji": [
        "BLACK FLASH ⚡",
        "DIVERGENT FIST",
        "HEAVY IMPACT",
        "UNYIELDING WILL",
        "LEFT RIGHT GOODNIGHT 🥊"
    ],
    "megumi": [
        "CHIMERA SHADOW GARDEN",
        "EIGHT-HANDLED SWORD",
        "SACRED TREASURE SWING",
        "WITH THIS TREASURE I SUMMON ⚡"
    ],
    "toji": [
        "HEAVENLY RESTRICTION",
        "ZERO CURSED ENERGY",
        "SORCERER KILLER 🗡️",
        "PURE SPEED",
        "APEX PREDATOR"
    ]
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
    drop_time: Optional[float] = None
) -> Path:
    """
    Generates high-retention ASS subtitles for YouTube Shorts.
    Supports both Upper-Third Viral Hook Statement Mode (spur_hook) and Kinetic Word Karaoke.
    """
    output_ass_path.parent.mkdir(parents=True, exist_ok=True)
    
    cfg = SUBTITLE_STYLE_PRESETS.get(style_preset, SUBTITLE_STYLE_PRESETS["spur_hook"]).copy()
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
Style: LowerHype,Bebas Neue,62,&H00FFFFFF,&H00000000,&H00000000,&HA0000000,-1,0,0,0,100,100,2,0,1,6.5,3.5,2,80,80,140,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events = []

    if style_preset == "spur_hook":
        # ── Viral Upper-Third Hook Statement Mode + Kinetic Combat Hype Progression ──
        # Phase 1: Setup statement (plays cleanly until the beat drop)
        # Phase 2: Climax punchline with Crimson Red keyword emphasis (drop to drop+2.8s, then dissolves)
        # Phase 3: Dynamic lower-third kinetic combat hype phrases (drop+3.0s to end, synced with action)
        t_drop = drop_time if drop_time and (start_time < drop_time < end_time) else (start_time + total_dur * 0.45)

        if " | " in quote_text:
            setup_raw, punch_raw = quote_text.split(" | ", 1)
            setup_words = [w.strip() for w in setup_raw.split() if w.strip()]
            punch_words = [w.strip() for w in punch_raw.split() if w.strip()]
            if punch_words and punch_words[0].upper() in ("OR", "BUT"):
                punch_words = punch_words[1:]
        elif len(words) >= 6:
            mid = len(words) // 2
            setup_words = words[:mid]
            punch_words = words[mid:]
        else:
            setup_words = words
            punch_words = words

        # Phase 1: Setup statement line (plays cleanly until beat drop)
        setup_line = _format_spur_line(setup_words, cfg['active_word'], cfg['primary'])
        ts_0 = format_ass_timestamp(start_time)
        ts_drop = format_ass_timestamp(t_drop)
        events.append(f"Dialogue: 1,{ts_0},{ts_drop},BaseText,,0,0,0,,{{\\fscx106\\fscy106\\t(0,100,\\fscx100\\fscy100)}}{setup_line}")

        # Phase 2: Punchline statement (impact pop bounce at drop, fades out cleanly after 2.8s)
        punch_line = _format_spur_line(punch_words, cfg['active_word'], cfg['primary'])
        t_punch_end = min(end_time, t_drop + 2.8)
        ts_punch_end = format_ass_timestamp(t_punch_end)
        events.append(f"Dialogue: 1,{ts_drop},{ts_punch_end},BaseText,,0,0,0,,{{\\fscx112\\fscy112\\t(0,120,\\fscx100\\fscy100)\\fad(0,350)}}{punch_line}")

        # Phase 3: Kinetic Combat Hype Phrases in Lower Ambient Safe Area (drop + 3.0s to end)
        char_key = (character_name or "").lower().strip()
        matched_hype = None
        for k, v in CHARACTER_HYPE_PHRASES.items():
            if k in char_key:
                matched_hype = v
                break
        if not matched_hype:
            matched_hype = ["LIMITLESS POWER", "UNSTOPPABLE", "DOMAIN EXPANSION", "PEAK BATTLE", "THE STRONGEST 👑"]

        t_curr = t_punch_end + 0.25
        h_idx = 0
        while t_curr < end_time - 0.4 and h_idx < len(matched_hype):
            phrase_dur = min(1.6, end_time - t_curr)
            p_end = t_curr + phrase_dur
            ts_s = format_ass_timestamp(t_curr)
            ts_e = format_ass_timestamp(p_end)
            phrase = matched_hype[h_idx]
            fmt_p = _format_spur_line(phrase.split(), cfg['active_word'], cfg['primary'])
            events.append(f"Dialogue: 1,{ts_s},{ts_e},LowerHype,,0,0,0,,{{\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)\\fad(80,120)}}{fmt_p}")
            t_curr = p_end + 0.15
            h_idx += 1
    else:
        # Word-by-word karaoke lines
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
