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
        "font": "Montserrat",
        "fontsize": 56,
        "primary": "&H00FFFFFF",         # Pure Crisp White
        "active_word": "&H001E27FF",     # Crimson Red / Theme Accent
        "outline": "&H00000000",         # Solid Crisp Black Outline
        "shadow": "&H80000000",          # Subtle Soft Drop Shadow
        "outline_width": 2.8,
        "shadow_depth": 1.5,
        "alignment": 8,                  # TOP CENTER (Upper Third Mobile Safe Zone)
        "margin_v": 200,                 # Safe below top mobile header (status bar, search & sound icons)
        "margin_lr": 100,                # Safe horizontal padding from mobile edges
    },
    "viral_karaoke": {
        "font": "Montserrat",
        "fontsize": 56,
        "primary": "&H00FFFFFF",
        "active_word": "&H001E27FF",
        "outline": "&H00000000",
        "shadow": "&H80000000",
        "outline_width": 2.8,
        "shadow_depth": 1.5,
        "alignment": 8,
        "margin_v": 200,
        "margin_lr": 100,
    },
    "cyber_glow": {
        "font": "Montserrat",
        "fontsize": 56,
        "primary": "&H00FFFFFF",
        "active_word": "&H0000FFFF",
        "outline": "&H00000000",
        "shadow": "&H80000000",
        "outline_width": 2.8,
        "shadow_depth": 1.5,
        "alignment": 8,
        "margin_v": 200,
        "margin_lr": 100,
    },
    "anime_shrine": {
        "font": "Montserrat",
        "fontsize": 56,
        "primary": "&H00FFFFFF",
        "active_word": "&H0000C8FF",
        "outline": "&H00000000",
        "shadow": "&H80000000",
        "outline_width": 2.8,
        "shadow_depth": 1.5,
        "alignment": 8,
        "margin_v": 200,
        "margin_lr": 100,
    },
    "cinematic_minimal": {
        "font": "Montserrat",
        "fontsize": 56,
        "primary": "&H00FFFFFF",
        "active_word": "&H00FFFFFF",
        "outline": "&H00000000",
        "shadow": "&H80000000",
        "outline_width": 2.8,
        "shadow_depth": 1.5,
        "alignment": 8,
        "margin_v": 200,
        "margin_lr": 100,
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


DEFAULT_CHARACTER_DIALOGUE = {
    "rengoku": [
        {"speaker": "Akaza", "text": "WHY DON'T YOU BECOME A DEMON TOO?", "start_rel": 0.6, "end_rel": 4.5, "glow_color": "&H001E27FF"},
        {"speaker": "Rengoku", "text": "I WILL NOT. GROWING OLD AND DYING IS THE BEAUTY OF FLEETING HUMAN LIFE.", "start_rel": 5.0, "end_rel": 12.5, "glow_color": "&H0000C8FF"},
        {"speaker": "Akaza", "text": "I CAN SENSE YOUR BATTLE SPIRIT... BECOME A DEMON, KYOJURO!", "start_rel": 13.0, "end_rel": 19.5, "glow_color": "&H001E27FF"},
        {"speaker": "Rengoku", "text": "NO MATTER WHAT HAPPENS, I WILL FULFILL MY DUTY!", "start_rel": 20.0, "end_rel": 25.5, "glow_color": "&H0000C8FF"},
        {"speaker": "Rengoku", "text": "SET YOUR HEART ABLAZE! NINTH FORM: RENGOKU!", "start_rel": 26.0, "end_rel": 29.8, "glow_color": "&H0000C8FF"}
    ],
    "akaza": [
        {"speaker": "Akaza", "text": "WHY DON'T YOU BECOME A DEMON TOO? WE CAN FIGHT FOR ETERNITY.", "start_rel": 0.6, "end_rel": 6.5, "glow_color": "&H001E27FF"},
        {"speaker": "Rengoku", "text": "I WILL NOT. MORTALITY IS WHAT MAKES HUMAN LIFE PRECIOUS.", "start_rel": 7.0, "end_rel": 13.5, "glow_color": "&H0000C8FF"},
        {"speaker": "Akaza", "text": "IF YOU WON'T BECOME A DEMON, THEN I'LL HAVE TO KILL YOU WHILE YOU'RE STRONG!", "start_rel": 14.0, "end_rel": 21.0, "glow_color": "&H001E27FF"},
        {"speaker": "Akaza", "text": "DESTRUCTIVE DEATH: COMPASS NEEDLE!", "start_rel": 21.5, "end_rel": 26.0, "glow_color": "&H001E27FF"},
        {"speaker": "Akaza", "text": "ANNIHILATION TYPE!", "start_rel": 26.5, "end_rel": 29.8, "glow_color": "&H001E27FF"}
    ],
    "gojo": [
        {"speaker": "Gojo", "text": "THE REASON YOU'RE GOING TO LOSE IS BECAUSE YOU DIDN'T CHOP MY HEAD OFF...", "start_rel": 0.6, "end_rel": 6.0},
        {"speaker": "Gojo", "text": "...AND BECAUSE YOU DIDN'T USE THAT CURSED TOOL WHEN YOU STABBED ME IN THE HEAD.", "start_rel": 6.5, "end_rel": 13.0},
        {"speaker": "Toji", "text": "I'M GOING TO LOSE? OUR FIGHT IS JUST GETTING STARTED!", "start_rel": 13.5, "end_rel": 18.5},
        {"speaker": "Gojo", "text": "THROUGHOUT HEAVEN AND EARTH... I ALONE AM THE HONORED ONE.", "start_rel": 19.0, "end_rel": 25.5},
        {"speaker": "Gojo", "text": "SECRET TECHNIQUE: HOLLOW PURPLE.", "start_rel": 26.0, "end_rel": 29.8}
    ],
    "sukuna": [
        {"speaker": "Sukuna", "text": "YOU CAN SEE MY CURSED TECHNIQUE? NOT BAD.", "start_rel": 0.5, "end_rel": 6.5},
        {"speaker": "Sukuna", "text": "LET US SEE IF YOU CAN ADAPT TO THIS.", "start_rel": 7.0, "end_rel": 13.0},
        {"speaker": "Sukuna", "text": "AN EIGHT-HANDLED SWORD... DIVINE GENERAL MAHORAGA.", "start_rel": 13.5, "end_rel": 20.0},
        {"speaker": "Sukuna", "text": "YOU HAVE ENTERTAINED ME WELL.", "start_rel": 20.5, "end_rel": 25.5},
        {"speaker": "Sukuna", "text": "DOMAIN EXPANSION: MALEVOLENT SHRINE!", "start_rel": 26.0, "end_rel": 29.8}
    ],
    "toji": [
        {"speaker": "Gojo", "text": "THE REASON YOU'RE GOING TO LOSE IS BECAUSE YOU DIDN'T CHOP MY HEAD OFF...", "start_rel": 0.6, "end_rel": 6.0},
        {"speaker": "Gojo", "text": "...AND BECAUSE YOU DIDN'T USE THAT CURSED TOOL WHEN YOU STABBED ME IN THE HEAD.", "start_rel": 6.5, "end_rel": 13.0},
        {"speaker": "Toji", "text": "A DEAD MAN TALKING? YOU'RE FLOATING IN THE AIR, KID.", "start_rel": 13.5, "end_rel": 19.5},
        {"speaker": "Gojo", "text": "THROUGHOUT HEAVEN AND EARTH, I ALONE AM THE HONORED ONE.", "start_rel": 20.0, "end_rel": 25.5},
        {"speaker": "Toji", "text": "SOMETHING IS WRONG... I HAVE TO FINISH HIM NOW!", "start_rel": 26.0, "end_rel": 29.8}
    ],
    "tanjiro": [
        {"speaker": "Tanjiro", "text": "NO MATTER HOW MANY TIMES I FALL, I WILL KEEP MOVING FORWARD!", "start_rel": 0.5, "end_rel": 6.5},
        {"speaker": "Tanjiro", "text": "NEZUKO AND I... OUR BOND CAN NEVER BE SEVERED BY ANYONE!", "start_rel": 7.0, "end_rel": 14.0},
        {"speaker": "Tanjiro", "text": "REMEMBER FATHER'S DANCE... MATCH YOUR BREATHING TO THE FLAME!", "start_rel": 14.5, "end_rel": 22.0},
        {"speaker": "Tanjiro", "text": "TOTAL CONCENTRATION... SUN BREATHING!", "start_rel": 22.5, "end_rel": 26.5},
        {"speaker": "Tanjiro", "text": "HINOKAMI KAGURA: DANCE OF THE FIRE GOD!", "start_rel": 27.0, "end_rel": 29.8}
    ],
    "zenitsu": [
        {"speaker": "Zenitsu", "text": "DON'T GIVE UP. EVEN IF IT'S PAINFUL, DON'T RUN AWAY.", "start_rel": 0.5, "end_rel": 6.5},
        {"speaker": "Zenitsu", "text": "GRANDPA TOLD ME... IT'S OKAY TO ONLY MASTER A SINGLE TECHNIQUE.", "start_rel": 7.0, "end_rel": 14.5},
        {"speaker": "Zenitsu", "text": "HONE THAT ONE MOVE UNTIL IT REACHES ABSOLUTE PERFECTION!", "start_rel": 15.0, "end_rel": 22.5},
        {"speaker": "Zenitsu", "text": "THUNDER BREATHING, FIRST FORM: THUNDERCLAP AND FLASH...", "start_rel": 23.0, "end_rel": 27.0},
        {"speaker": "Zenitsu", "text": "GODSPEED SIXFOLD!", "start_rel": 27.5, "end_rel": 29.8}
    ],
    "tengen": [
        {"speaker": "Tengen", "text": "I AM A GOD OF FESTIVALS. THE FLASHIEST GUY YOU'LL EVER MEET.", "start_rel": 0.5, "end_rel": 6.5, "glow_color": "&H00FFAA00"},
        {"speaker": "Gyutaro", "text": "YOU'RE DIFFERENT FROM THE OTHER HASHIRA... BORN WITH NATURAL LUCK.", "start_rel": 7.0, "end_rel": 13.5},
        {"speaker": "Tengen", "text": "TALENT? DO I LOOK LIKE SOMEONE WITH TALENT? MANY DIED BEFORE ME!", "start_rel": 14.0, "end_rel": 21.0, "glow_color": "&H00FFAA00"},
        {"speaker": "Tengen", "text": "I'VE COMPLETED MY MUSICAL SCORE! WE'RE WINNING THIS!", "start_rel": 21.5, "end_rel": 26.5, "glow_color": "&H0000C8FF"},
        {"speaker": "Tengen", "text": "SOUND BREATHING, FOURTH FORM: BLOOMING FLAME CALAMITY!", "start_rel": 27.0, "end_rel": 29.8, "glow_color": "&H0000C8FF"}
    ],
    "inosuke": [
        {"speaker": "Inosuke", "text": "COMING THROUGH! MAKE WAY FOR LORD INOSUKE!", "start_rel": 0.5, "end_rel": 6.5, "glow_color": "&H0000FFCC"},
        {"speaker": "Inosuke", "text": "DON'T UNDERESTIMATE MY BEASTLY INSTINCTS!", "start_rel": 7.0, "end_rel": 14.5, "glow_color": "&H0000FFCC"},
        {"speaker": "Inosuke", "text": "I CAN FEEL WHERE EVERY ENEMY IS SPREAD ACROSS THIS MOUNTAIN!", "start_rel": 15.0, "end_rel": 22.0, "glow_color": "&H0000FFFF"},
        {"speaker": "Inosuke", "text": "BEAST BREATHING, FIFTH FANG: CRAZY CUTTING!", "start_rel": 22.5, "end_rel": 29.8, "glow_color": "&H0000FFFF"}
    ],
    "giyu": [
        {"speaker": "Tanjiro", "text": "DON'T KILL HER! PLEASE, SHE'S MY SISTER!", "start_rel": 0.5, "end_rel": 5.5, "glow_color": "&H00FF8800"},
        {"speaker": "Giyu", "text": "DON'T GIVE OTHERS THE POWER OVER YOUR OWN LIFE!", "start_rel": 6.0, "end_rel": 12.0, "glow_color": "&H00FF8800"},
        {"speaker": "Giyu", "text": "WEAKLINGS HAVE NO RIGHTS OR CHOICES.", "start_rel": 12.5, "end_rel": 18.0, "glow_color": "&H00FF8800"},
        {"speaker": "Giyu", "text": "CRYING WON'T CHANGE REALITY... THE DEAD WILL NEVER RETURN.", "start_rel": 18.5, "end_rel": 24.5, "glow_color": "&H00FF8800"},
        {"speaker": "Giyu", "text": "WATER BREATHING, ELEVENTH FORM: DEAD CALM.", "start_rel": 25.0, "end_rel": 29.8, "glow_color": "&H00FFFF00"}
    ],
    "muichiro": [
        {"speaker": "Gyokko", "text": "MY BEAUTIFUL POTS ARE SUPERIOR TO ANY HUMAN ART!", "start_rel": 0.5, "end_rel": 6.0, "glow_color": "&H00CCFF00"},
        {"speaker": "Muichiro", "text": "WHICH FORM WAS IT AGAIN? YOUR POTS LOOK QUITE ASYMMETRIC.", "start_rel": 6.5, "end_rel": 13.0, "glow_color": "&H00CCFF00"},
        {"speaker": "Gyokko", "text": "HOW DARE YOU INSULT MY MASTERPIECES, YOU PEST!", "start_rel": 13.5, "end_rel": 19.5, "glow_color": "&H00CCFF00"},
        {"speaker": "Muichiro", "text": "YOU'RE TALKING A LOT FOR SOMEONE WHO CAN'T EVEN TOUCH ME.", "start_rel": 20.0, "end_rel": 25.5, "glow_color": "&H00FFFFFF"},
        {"speaker": "Muichiro", "text": "MIST BREATHING, SEVENTH FORM: OBSCURING CLOUDS.", "start_rel": 26.0, "end_rel": 29.8, "glow_color": "&H00FFFFFF"}
    ],
    "gyutaro": [
        {"speaker": "Gyutaro", "text": "YOU'RE A PRETTY BOY, AREN'T YOU? I HATE THAT...", "start_rel": 0.5, "end_rel": 6.0, "glow_color": "&H000000FF"},
        {"speaker": "Gyutaro", "text": "PEOPLE LIKE YOU WERE BORN BLESSED, WHILE WE SUFFERED IN DIRT.", "start_rel": 6.5, "end_rel": 13.5, "glow_color": "&H000000FF"},
        {"speaker": "Tengen", "text": "I'M NOT BLESSED. I WATCHED MY SIBLINGS DIE ONE BY ONE.", "start_rel": 14.0, "end_rel": 20.5, "glow_color": "&H00FFAA00"},
        {"speaker": "Gyutaro", "text": "ENVY, HATE, SPITE... THAT'S WHAT FEEDS MY BLADES!", "start_rel": 21.0, "end_rel": 26.0, "glow_color": "&H002200CC"},
        {"speaker": "Gyutaro", "text": "BLOOD DEMON ART: FLYING BLOOD SICKLES!", "start_rel": 26.5, "end_rel": 29.8, "glow_color": "&H002200CC"}
    ],
    "yuji": [
        {"speaker": "Yuji", "text": "I DON'T CARE IF THIS BODY BREAKS OR FALLS APART...", "start_rel": 0.5, "end_rel": 6.5, "glow_color": "&H000000FF"},
        {"speaker": "Mahito", "text": "YOU DON'T GET IT, ITADORI! I AM A CURSE, YOU ARE A SORCERER!", "start_rel": 7.0, "end_rel": 14.0, "glow_color": "&H00AA00FF"},
        {"speaker": "Yuji", "text": "I ADMIT IT, MAHITO. I AM YOU. I WILL KILL YOU.", "start_rel": 14.5, "end_rel": 21.5, "glow_color": "&H000000FF"},
        {"speaker": "Todo", "text": "THE BELL OF GION SHOJA ECHOES... WE ARE THE EXCEPTION!", "start_rel": 22.0, "end_rel": 26.5, "glow_color": "&H00FFAA00"},
        {"speaker": "Yuji", "text": "CONSECUTIVE BLACK FLASH!", "start_rel": 27.0, "end_rel": 29.8, "glow_color": "&H000000FF"}
    ],
    "megumi": [
        {"speaker": "Megumi", "text": "I RECOGNIZE THAT MY TECHNIQUE HAS BEEN LIMITING ME...", "start_rel": 0.5, "end_rel": 6.5, "glow_color": "&H00333333"},
        {"speaker": "Megumi", "text": "IMAGINE IT... IMAGINE THE FUTURE WHERE I SURPASS MY LIMITS!", "start_rel": 7.0, "end_rel": 14.0, "glow_color": "&H00333333"},
        {"speaker": "Megumi", "text": "EVEN IF I DIE HERE, I'LL DRAG YOU TO HELL WITH ME!", "start_rel": 14.5, "end_rel": 21.0, "glow_color": "&H00333333"},
        {"speaker": "Megumi", "text": "WITH THIS TREASURE I SUMMON...", "start_rel": 21.5, "end_rel": 25.5, "glow_color": "&H00333333"},
        {"speaker": "Megumi", "text": "EIGHT-HANDLED SWORD DIVERGENT SILA DIVINE GENERAL MAHORAGA!", "start_rel": 26.0, "end_rel": 29.8, "glow_color": "&H00FFFFFF"}
    ],
    "nobara": [
        {"speaker": "Nobara", "text": "DON'T LOOK DOWN ON ME!", "start_rel": 0.5, "end_rel": 6.5, "glow_color": "&H000055FF"},
        {"speaker": "Nobara", "text": "I BET MY LIFE ON LIVING AS MY TRUE SELF!", "start_rel": 7.0, "end_rel": 15.0, "glow_color": "&H000055FF"},
        {"speaker": "Nobara", "text": "HAIRPIN... RESONANCE!", "start_rel": 15.5, "end_rel": 22.5, "glow_color": "&H000088FF"},
        {"speaker": "Nobara", "text": "BLACK FLASH STRIKE!", "start_rel": 23.0, "end_rel": 29.8, "glow_color": "&H000088FF"}
    ],
    "todo": [
        {"speaker": "Todo", "text": "WHAT KIND OF WOMAN IS YOUR TYPE?", "start_rel": 0.5, "end_rel": 6.5, "glow_color": "&H00FF00AA"},
        {"speaker": "Todo", "text": "A BORING ANSWER MERITS A COMPLETE BEATDOWN!", "start_rel": 7.0, "end_rel": 14.5, "glow_color": "&H00FF00AA"},
        {"speaker": "Todo", "text": "CLAP OF MY HANDS SWITCHES POSITIONS IN AN INSTANT!", "start_rel": 15.0, "end_rel": 22.0, "glow_color": "&H00FFAA00"},
        {"speaker": "Todo", "text": "WE ARE THE EXCEPTION... BOOGIE WOOGIE!", "start_rel": 22.5, "end_rel": 29.8, "glow_color": "&H00FFAA00"}
    ],
    "mahito": [
        {"speaker": "Mahito", "text": "THE SOUL COMES BEFORE THE BODY.", "start_rel": 0.5, "end_rel": 6.5, "glow_color": "&H00AA00FF"},
        {"speaker": "Mahito", "text": "WHEN THE SOUL CHANGES SHAPE, THE FLESH FOLLOWS!", "start_rel": 7.0, "end_rel": 14.5, "glow_color": "&H00AA00FF"},
        {"speaker": "Mahito", "text": "YOU AND I ARE INHERENTLY THE SAME, ITADORI!", "start_rel": 15.0, "end_rel": 22.0, "glow_color": "&H00AA00FF"},
        {"speaker": "Mahito", "text": "IDLE TRANSFIGURATION: INSTANT SPIRIT BODY OF DISTORTED KILLING!", "start_rel": 22.5, "end_rel": 29.8, "glow_color": "&H00FF00FF"}
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

    if len(words) >= 3:
        mid = len(words) // 2
        return " ".join(formatted[:mid]) + r"\N" + " ".join(formatted[mid:])
    return " ".join(formatted)


def _format_dialogue_text(raw_text: str) -> str:
    """
    Cleans and formats dialogue subtitles:
    - Strips surrounding quotes, double quotes, speaker tags, and accidental backslashes.
    - Preserves or inserts clean ASS linebreaks (\\N) at natural punctuation pauses
      so lines fit comfortably and never get cut off at canvas margins.
    - Converts text to clean ALL CAPS matching modern AMV reference style.
    """
    cleaned = raw_text.strip().strip('"\'').replace('\\"', '"').replace('\\', '')
    cleaned = cleaned.strip('"\'')

    # Strip any speaker tags like "Akaza: " or "[Akaza]"
    for char in ["akaza", "rengoku", "gojo", "sukuna", "toji", "tanjiro", "zenitsu", "reze", "yuji", "megumi", "demon", "villain"]:
        if cleaned.lower().startswith(char + ":"):
            cleaned = cleaned[len(char) + 1:].strip()
        elif cleaned.lower().startswith("[" + char + "]"):
            cleaned = cleaned[len(char) + 2:].strip()

    if r"\N" in cleaned:
        return cleaned.upper()
    if "\n" in cleaned:
        return cleaned.replace("\n", r"\N").upper()

    if len(cleaned) > 28:
        for delim in [": ", ", ", " - ", "; ", "! ", "? "]:
            if delim in cleaned:
                idx = cleaned.find(delim) + len(delim.strip())
                if 8 <= idx <= len(cleaned) - 8:
                    return (cleaned[:idx].strip() + r"\N" + cleaned[idx:].strip()).upper()
        words = cleaned.split()
        if len(words) > 3:
            mid = len(words) // 2
            return (" ".join(words[:mid]) + r"\N" + " ".join(words[mid:])).upper()
    return cleaned.upper()


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
    dialogue_lines: Optional[List[Dict[str, Any]]] = None
) -> Path:
    """
    Generates high-retention ASS subtitles for YouTube Shorts.
    Supports:
    1. Clean Reference Dialogue Subtitles (ALL CAPS, bold sans-serif, solid white with black outline,
       centered lower third, zero speaker tags or clutter, exactly matching reference style).
    2. Upper-Third Viral Hook Statement Mode (spur_hook) and Kinetic Word Karaoke when no dialogue is present.
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
    
    scale_y = VIDEO_HEIGHT / 1920.0
    scale_x = VIDEO_WIDTH / 1080.0
    
    # ── Upper-Third Hook Question (BaseText) ──
    # Placed at TOP CENTER (alignment 8) in the upper third mobile safe zone
    q_fontsize = int(round(cfg.get('fontsize', 56) * scale_y))
    q_outline = round(cfg.get('outline_width', 4.5) * scale_y, 1)
    q_shadow = round(cfg.get('shadow_depth', 2.0) * scale_y, 1)
    q_margin_v = int(round(cfg.get('margin_v', 200) * scale_y))  # Safe below top mobile chrome
    q_margin_lr = int(round(cfg.get('margin_lr', 100) * scale_x))
    q_alignment = cfg.get('alignment', 8)

    # ── Lower-Third Dialogue Subtitles (DialogueSub) ──
    # Placed at BOTTOM CENTER (alignment 2) in the lower third mobile safe zone
    # MarginV is calibrated to sit safely ABOVE the YouTube Shorts bottom chrome (channel, title, subscribe button)
    d_fontsize = int(round(48 * scale_y))
    d_outline = round(3.8 * scale_y, 1)
    d_shadow = round(1.8 * scale_y, 1)
    d_margin_v = int(round(440 * scale_y))  # Safe above YouTube Shorts channel & title overlay
    d_margin_lr = int(round(120 * scale_x)) # Safe inside YouTube right-side like/comment buttons

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
Style: BaseText,{cfg['font']},{q_fontsize},{cfg['primary']},&H00000000,{cfg['outline']},{cfg['shadow']},-1,0,0,0,100,100,0,0,1,{q_outline},{q_shadow},{q_alignment},{q_margin_lr},{q_margin_lr},{q_margin_v},1
Style: DialogueSub,Montserrat,{d_fontsize},&H00FFFFFF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{d_outline},{d_shadow},2,{d_margin_lr},{d_margin_lr},{d_margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events = []

    # 1. Upper-Third Engaging Hook Question Mode (spur_hook)
    # Plays setup premise before drop, and punch question from drop to end in the upper third
    if style_preset == "spur_hook":
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

        # Setup statement line (plays cleanly until the beat drop)
        setup_line = _format_spur_line(setup_words, cfg['active_word'], cfg['primary'])
        ts_0 = format_ass_timestamp(start_time)
        ts_drop = format_ass_timestamp(t_drop)
        events.append(f"Dialogue: 1,{ts_0},{ts_drop},BaseText,,0,0,0,,{{\\fscx106\\fscy106\\t(0,100,\\fscx100\\fscy100)}}{setup_line}")

        # Punchline statement line (with crimson red emphasis keywords, from drop to end)
        punch_line = _format_spur_line(punch_words, cfg['active_word'], cfg['primary'])
        ts_end = format_ass_timestamp(end_time)
        events.append(f"Dialogue: 1,{ts_drop},{ts_end},BaseText,,0,0,0,,{{\\fscx110\\fscy110\\t(0,100,\\fscx100\\fscy100)}}{punch_line}")
    elif not dialogue_lines:
        # Word-by-word karaoke lines (when not spur_hook and no dialogue)
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
                        line_parts.append(
                            f"{{\\c{cfg['active_word']}\\t(0,100,\\fscx118\\fscy118)\\t(100,200,\\fscx100\\fscy100)}}{w_upper}{{\\rBaseText}}"
                        )
                    else:
                        line_parts.append(f"{{\\c{cfg['primary']}}}{w_upper}")

                formatted_line = " ".join(line_parts)
                events.append(f"Dialogue: 1,{ts_start},{ts_end},BaseText,,0,0,0,,{formatted_line}")

    # ── Dialogue Subtitles during pre-fight conversation ──
    # Dynamic word-by-word accumulation matching reference XeqGgslY3h0:
    # Strictly what the characters say, ALL CAPS, bold sans-serif, solid white with heavy black outline.
    # Each word pops in dynamically as spoken, zero speaker name tags, zero quote clutter, finishes strictly before beat drop.
    if dialogue_lines:
        for dl in dialogue_lines:
            st_val = float(dl.get("start") if "start" in dl else dl.get("start_rel", 0.0))
            en_val = float(dl.get("end") if "end" in dl else dl.get("end_rel", st_val + 3.0))
            raw_txt = dl.get("text", "")
            cleaned = _format_dialogue_text(raw_txt)

            # Split by line breaks to maintain visual lines
            raw_lines = [l.strip() for l in cleaned.replace(r"\N", "\n").split("\n") if l.strip()]
            all_words = []
            for l_idx, line in enumerate(raw_lines):
                for w in line.split():
                    all_words.append((w.upper(), l_idx))

            if not all_words:
                continue

            total_dur = max(0.5, en_val - st_val)
            # Natural speech pacing: reserve 0.8s - 1.2s at the end so the viewer comfortably absorbs the completed sentence
            hold_dur = min(1.2, max(0.6, total_dur * 0.25))
            speech_dur = max(0.3, total_dur - hold_dur)

            # Weight each word by character length and natural punctuation pauses (colons, commas, ellipses)
            weights = []
            for w, _ in all_words:
                wt = max(1.0, len(w) * 0.2)
                if w.endswith(":") or w.endswith(","):
                    wt += 1.8
                elif w.endswith("...") or w.endswith("…"):
                    wt += 2.2
                elif w.endswith("!") or w.endswith("?"):
                    wt += 1.5
                weights.append(wt)

            total_wt = sum(weights)
            word_durs = [(wt / total_wt) * speech_dur for wt in weights]

            curr_t = st_val
            for w_idx in range(len(all_words)):
                w_start = curr_t
                dur = word_durs[w_idx]
                if w_idx == len(all_words) - 1:
                    w_end = en_val  # Final completed line holds through the sentence duration
                else:
                    w_end = curr_t + dur
                curr_t += dur

                d_start = format_ass_timestamp(w_start)
                d_end = format_ass_timestamp(w_end)

                current_words = all_words[:w_idx + 1]
                # Simple, rock-solid font styling without jumpy scale pops or artificial glow
                lines_formatted = [[], []]
                for idx_w, (w, l_idx) in enumerate(current_words):
                    lines_formatted[l_idx].append(w)

                line0 = " ".join(lines_formatted[0])
                line1 = " ".join(lines_formatted[1]) if lines_formatted[1] else ""

                full_text = line0
                if line1:
                    full_text += r"\N" + line1

                # Clean subtle fade at phrase boundaries
                fade_tag = r"{\fad(60,0)}" if w_idx == 0 else (r"{\fad(0,60)}" if w_idx == len(all_words) - 1 else "")
                events.append(f"Dialogue: 2,{d_start},{d_end},DialogueSub,,0,0,0,,{fade_tag}{full_text}")
            
    full_ass = ass_header + "\n".join(events) + "\n"
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(full_ass)
        
    return output_ass_path
