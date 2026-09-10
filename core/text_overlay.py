"""
Multi-Style Text Overlay System for Dramatic AMV Edits.
Replicates the 9 distinct text overlay styles from the reference video:

1. Character Title Cards — Large stylized text dominating the frame
2. Small White Dialogue — Clean lower-third subtitles
3. Red Glowing Dialogue — Larger text with red glow for emotional lines
4. Mixed-Color Emphasis (Red) — Key word highlighted in red, rest white
5. Mixed-Color Emphasis (Cyan) — Key word highlighted in cyan, rest white
6. Roman Numeral Section Markers — Large transparent structural dividers
7. Large Transparent Background Text — Fills frame behind subject
8. Two-Layer Simultaneous — Background text + foreground subtitle
9. Decorative Initial — Large white block first letter + colored rest

All text is generated as FFmpeg drawtext filter chains for injection
into the video filtergraph. No separate files needed.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from config.settings import VIDEO_WIDTH, VIDEO_HEIGHT


def _escape_drawtext(text: str) -> str:
    """Escapes text for FFmpeg drawtext filter (special chars)."""
    return (text
        .replace("\\", "\\\\\\\\")
        .replace("'", "'\\\\\\''")
        .replace(":", "\\\\:")
        .replace("%", "%%")
        .replace("[", "\\\\[")
        .replace("]", "\\\\]")
    )


def _find_font() -> str:
    """Finds a bold sans font for title cards and overlays."""
    import os
    prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
    candidates = [
        f"{prefix}/share/fonts/TTF/DejaVuSans-Bold.ttf",
        f"{prefix}/share/fonts/TTF/DejaVuSansCondensed-Bold.ttf",
        f"{prefix}/share/fonts/TTF/DejaVuSerif-Bold.ttf",  # Serif for title cards
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for f in candidates:
        if os.path.exists(f):
            return f
    return ""


FONT_PATH = _find_font()


def _fade_alpha_expr(start: float, end: float, fade_in: float = 0.25, fade_out: float = 0.25) -> str:
    """Generates an alpha fade-in/fade-out expression for drawtext."""
    return (
        f"if(lt(t\\,{start:.2f})\\,0\\,"
        f"if(lt(t\\,{start + fade_in:.2f})\\,(t-{start:.2f})/{fade_in:.2f}\\,"
        f"if(lt(t\\,{end - fade_out:.2f})\\,1\\,"
        f"if(lt(t\\,{end:.2f})\\,({end:.2f}-t)/{fade_out:.2f}\\,0))))"
    )


# ═══════════════════════════════════════════════════════════════════
# STYLE 1: Character Title Cards
# Large stylized text (e.g., "MAHITO", "YUJI") dominating the frame.
# Multiple compositions: solid dark bg + text, or text over character face.
# ═══════════════════════════════════════════════════════════════════
def build_title_card_filter(
    character_name: str,
    start_time: float,
    end_time: float,
    color: str = "white",
    fontsize: int = 120,
    bg_opacity: float = 0.6,
    font_path: str = FONT_PATH
) -> str:
    """
    Character title card: large name text centered on semi-transparent dark background.
    Reference: "MAHITO" in large RED text on dark blue, or "REBORN" in PURPLE on dark.
    """
    name = _escape_drawtext(character_name.upper())
    alpha = _fade_alpha_expr(start_time, end_time, fade_in=0.15, fade_out=0.15)

    # Dark background box behind text
    bg_filter = (
        f"drawbox=x=0:y=ih/2-120:w=iw:h=240:color=black@{bg_opacity}:t=fill:"
        f"enable='between(t\\,{start_time:.2f}\\,{end_time:.2f})'"
    )
    # Large centered text
    text_filter = (
        f"drawtext=text='{name}'"
        f":fontfile={font_path}"
        f":fontsize={fontsize}"
        f":fontcolor={color}"
        f":x=(w-text_w)/2"
        f":y=(h-text_h)/2"
        f":alpha='{alpha}'"
    )
    return f"{bg_filter},{text_filter}"


def build_title_card_over_face_filter(
    character_name: str,
    start_time: float,
    end_time: float,
    color: str = "red",
    fontsize: int = 100,
    font_path: str = FONT_PATH
) -> str:
    """
    Title card OVER character face: semi-transparent text integrated with portrait.
    Reference: "MAHITO" text visible THROUGH the letterforms over character's face.
    """
    name = _escape_drawtext(character_name.upper())
    alpha = _fade_alpha_expr(start_time, end_time, fade_in=0.1, fade_out=0.1)

    return (
        f"drawtext=text='{name}'"
        f":fontfile={font_path}"
        f":fontsize={fontsize}"
        f":fontcolor={color}@0.55"
        f":x=(w-text_w)/2"
        f":y=(h-text_h)/2"
        f":alpha='{alpha}'"
    )


# ═══════════════════════════════════════════════════════════════════
# STYLE 2: Small White Dialogue Subtitles
# Clean white text, small size, centered lower-third.
# ═══════════════════════════════════════════════════════════════════
def build_dialogue_subtitle_filter(
    text: str,
    start_time: float,
    end_time: float,
    fontsize: int = 42,
    font_path: str = FONT_PATH,
    y_offset: int = 280,
    outline_width: int = 3
) -> str:
    """Small white dialogue text, centered in lower portion of frame."""
    safe = _escape_drawtext(text)
    alpha = _fade_alpha_expr(start_time, end_time, fade_in=0.12, fade_out=0.12)

    return (
        f"drawtext=text='{safe}'"
        f":fontfile={font_path}"
        f":fontsize={fontsize}"
        f":fontcolor=white"
        f":bordercolor=black"
        f":borderw={outline_width}"
        f":x=(w-text_w)/2"
        f":y=h-{y_offset}"
        f":alpha='{alpha}'"
    )


# ═══════════════════════════════════════════════════════════════════
# STYLE 3: Red Glowing Dialogue
# Larger text with red glow for villain/emotionally charged lines.
# ═══════════════════════════════════════════════════════════════════
def build_red_glow_dialogue_filter(
    text: str,
    start_time: float,
    end_time: float,
    fontsize: int = 56,
    glow_color: str = "red",
    font_path: str = FONT_PATH,
    y_offset: int = 300
) -> str:
    """
    Red glowing dialogue text — used for villain lines or emotionally charged moments.
    Reference: "I am you" in large red text that acts as environmental light source.
    """
    safe = _escape_drawtext(text)
    alpha = _fade_alpha_expr(start_time, end_time, fade_in=0.15, fade_out=0.15)

    # Glow layer (slightly larger, lower opacity red)
    glow_filter = (
        f"drawtext=text='{safe}'"
        f":fontfile={font_path}"
        f":fontsize={fontsize + 4}"
        f":fontcolor={glow_color}@0.4"
        f":x=(w-text_w)/2+1"
        f":y=h-{y_offset}+1"
        f":alpha='{alpha}'"
    )
    # Main text layer (white with red outline)
    main_filter = (
        f"drawtext=text='{safe}'"
        f":fontfile={font_path}"
        f":fontsize={fontsize}"
        f":fontcolor=white"
        f":bordercolor={glow_color}"
        f":borderw=4"
        f":x=(w-text_w)/2"
        f":y=h-{y_offset}"
        f":alpha='{alpha}'"
    )
    return f"{glow_filter},{main_filter}"


# ═══════════════════════════════════════════════════════════════════
# STYLE 4 & 5: Mixed-Color Emphasis Text
# Sentence in white with KEY VERB/NOUN highlighted in a color.
# Red variant for anger/pain, Cyan variant for hope/energy.
# ═══════════════════════════════════════════════════════════════════
def build_emphasis_text_filters(
    full_text: str,
    emphasized_word: str,
    start_time: float,
    end_time: float,
    emphasis_color: str = "red",
    fontsize: int = 52,
    font_path: str = FONT_PATH,
    y_offset: int = 300,
    x_pos: str = "(w-text_w)/2"
) -> str:
    """
    Builds a two-layer emphasis text: the full sentence in white, with the
    emphasized word rendered separately in the emphasis color, positioned to overlap.

    Reference examples:
    - "I WANTED TO" (WANTED in red)
    - "as a new" (new in cyan)
    """
    words = full_text.split()
    safe_full = _escape_drawtext(full_text)
    alpha = _fade_alpha_expr(start_time, end_time, fade_in=0.15, fade_out=0.15)

    # Base layer: full text in white
    base = (
        f"drawtext=text='{safe_full}'"
        f":fontfile={font_path}"
        f":fontsize={fontsize}"
        f":fontcolor=white"
        f":bordercolor=black"
        f":borderw=3"
        f":x={x_pos}"
        f":y=h-{y_offset}"
        f":alpha='{alpha}'"
    )

    # Emphasis layer: colored word positioned over its location
    # Calculate x offset of the emphasized word within the full text
    words_before = full_text.split(emphasized_word)[0].split()
    char_width_approx = fontsize * 0.55
    word_gap = fontsize * 0.3
    x_offset = int(len(words_before) * (char_width_approx * 6 + word_gap) / max(1, len(words_before) + 1))

    safe_emph = _escape_drawtext(emphasized_word.upper())
    emphasis = (
        f"drawtext=text='{safe_emph}'"
        f":fontfile={font_path}"
        f":fontsize={fontsize}"
        f":fontcolor={emphasis_color}"
        f":bordercolor=black"
        f":borderw=3"
        f":x={x_pos}+{x_offset}"
        f":y=h-{y_offset}"
        f":alpha='{alpha}'"
    )
    return f"{base},{emphasis}"


# ═══════════════════════════════════════════════════════════════════
# STYLE 6: Roman Numeral Section Markers
# Large transparent structural dividers: "VIII", "IX".
# ═══════════════════════════════════════════════════════════════════
def build_roman_numeral_filter(
    numeral: str,
    start_time: float,
    end_time: float,
    fontsize: int = 200,
    color: str = "white",
    opacity: float = 0.35,
    font_path: str = FONT_PATH
) -> str:
    """
    Large semi-transparent Roman numeral section marker.
    Reference: "VIII" and "IX" overlaid as structural chapter dividers.
    """
    safe = _escape_drawtext(numeral.upper())
    alpha = _fade_alpha_expr(start_time, end_time, fade_in=0.4, fade_out=0.4)

    return (
        f"drawtext=text='{safe}'"
        f":fontfile={font_path}"
        f":fontsize={fontsize}"
        f":fontcolor={color}@{opacity}"
        f":x=(w-text_w)/2"
        f":y=(h-text_h)/2"
        f":alpha='{alpha}'"
    )


# ═══════════════════════════════════════════════════════════════════
# STYLE 7: Large Transparent Background Text
# Semi-transparent words filling the frame behind the main subject.
# ═══════════════════════════════════════════════════════════════════
def build_bg_text_filter(
    text: str,
    start_time: float,
    end_time: float,
    fontsize: int = 180,
    color: str = "white",
    opacity: float = 0.15,
    font_path: str = FONT_PATH,
    y_pos: str = "(h-text_h)/2"
) -> str:
    """
    Large semi-transparent text filling the frame — creates depth by becoming
    part of the environment behind the character.
    Reference: "accept", "NOW" rendered as environmental text.
    """
    safe = _escape_drawtext(text.upper())
    alpha = _fade_alpha_expr(start_time, end_time, fade_in=0.3, fade_out=0.3)

    return (
        f"drawtext=text='{safe}'"
        f":fontfile={font_path}"
        f":fontsize={fontsize}"
        f":fontcolor={color}@{opacity}"
        f":x=(w-text_w)/2"
        f":y={y_pos}"
        f":alpha='{alpha}'"
    )


# ═══════════════════════════════════════════════════════════════════
# STYLE 8: Two-Layer Simultaneous Text
# Large transparent background text + small foreground subtitle.
# ═══════════════════════════════════════════════════════════════════
def build_two_layer_text_filters(
    bg_text: str,
    fg_text: str,
    start_time: float,
    end_time: float,
    bg_fontsize: int = 160,
    fg_fontsize: int = 40,
    bg_color: str = "white",
    fg_color: str = "white",
    bg_opacity: float = 0.18,
    font_path: str = FONT_PATH
) -> str:
    """
    Two-layer text: large transparent bg text + small foreground subtitle.
    Reference: "accept" (large bg) + "i really wanted to" (small fg) simultaneously.
    """
    bg_filter = build_bg_text_filter(bg_text, start_time, end_time, bg_fontsize, bg_color, bg_opacity, font_path)
    fg_filter = build_dialogue_subtitle_filter(fg_text, start_time, end_time, fg_fontsize, font_path)
    return f"{bg_filter},{fg_filter}"


# ═══════════════════════════════════════════════════════════════════
# STYLE 9: Decorative Initial Letter
# First letter in large white block font, rest in accent color.
# ═══════════════════════════════════════════════════════════════════
def build_decorative_initial_filter(
    text: str,
    start_time: float,
    end_time: float,
    accent_color: str = "red",
    fontsize: int = 60,
    font_path: str = FONT_PATH,
    y_offset: int = 300
) -> str:
    """
    Decorative initial: first letter in large white block, rest in accent color.
    Reference: "WANTED" with large white "W" + red "ANTED".
    """
    if not text:
        return ""
    initial = text[0].upper()
    rest = text[1:].upper()
    safe_initial = _escape_drawtext(initial)
    safe_rest = _escape_drawtext(rest)
    alpha = _fade_alpha_expr(start_time, end_time, fade_in=0.15, fade_out=0.15)

    # Large white initial
    initial_filter = (
        f"drawtext=text='{safe_initial}'"
        f":fontfile={font_path}"
        f":fontsize={int(fontsize * 1.8)}"
        f":fontcolor=white"
        f":bordercolor=black"
        f":borderw=4"
        f":x=(w-text_w)/2-{fontsize * 3}"
        f":y=h-{y_offset}"
        f":alpha='{alpha}'"
    )
    # Colored rest
    rest_filter = (
        f"drawtext=text='{safe_rest}'"
        f":fontfile={font_path}"
        f":fontsize={fontsize}"
        f":fontcolor={accent_color}"
        f":bordercolor=black"
        f":borderw=3"
        f":x=(w-text_w)/2+{fontsize}"
        f":y=h-{y_offset}+{int(fontsize * 0.3)}"
        f":alpha='{alpha}'"
    )
    return f"{initial_filter},{rest_filter}"


# ═══════════════════════════════════════════════════════════════════
# HIGH-LEVEL: Generate complete text overlay filter chain for an edit
# ═══════════════════════════════════════════════════════════════════
def generate_edit_text_overlays(
    character_key: str,
    quote_text: str,
    beat_times: List[float],
    drop_time: float,
    total_duration: float,
    character_colors: Optional[Dict[str, str]] = None
) -> str:
    """
    Generates clean, cinematic text overlays for an edit matching reference AMV style:
    1. Elegant dialogue subtitle during the intro, positioned in the lower letterbox bar
       so it never obstructs the anime animation.
    2. Optional subtle anime branding watermark in the upper letterbox bar.
    3. NO intrusive full-screen blocking boxes or random Roman numeral markers.

    Returns comma-separated drawtext filters for injection into filtergraph.
    """
    if not character_colors:
        from config.settings import CHARACTER_COLOR_MAP
        character_colors = CHARACTER_COLOR_MAP.get(character_key, CHARACTER_COLOR_MAP.get("gojo", {}))

    filters = []

    # ── 1. Clean Dialogue Subtitle during Intro (0.4s to drop) ──
    # Placed in the lower letterbox area (y=1360), crisp white with outline
    words = quote_text.strip().split() if quote_text else []
    if words and drop_time > 1.5:
        # Split into readable chunks of max 5 words each for mobile viewports
        chunk_size = 5 if len(words) >= 6 else len(words)
        chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
        t_avail = max(1.0, drop_time - 0.6)
        dt_chunk = t_avail / len(chunks)
        for i, chunk in enumerate(chunks):
            t_start = 0.4 + i * dt_chunk
            t_end = min(drop_time - 0.2, t_start + dt_chunk - 0.1)
            filters.append(build_dialogue_subtitle_filter(chunk, t_start, t_end, fontsize=38, y_offset=560))

    # Clean, pristine letterbox bars matching lX7bIlY_KEE (no distracting top bar clutter)
    return ",".join(filters) if filters else "null"

