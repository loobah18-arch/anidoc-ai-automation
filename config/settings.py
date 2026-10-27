"""
Configuration settings for Cinematic 4K Phonk / Scene Edit Engine (Marvel & Jujutsu Kaisen).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
AUDIO_DIR = ASSETS_DIR / "audio"
PHONK_DIR = AUDIO_DIR / "phonk"
DIALOGUE_DIR = AUDIO_DIR / "dialogue"
VIDEO_DIR = ASSETS_DIR / "video"
MARVEL_DIR = VIDEO_DIR / "marvel"
JJK_DIR = VIDEO_DIR / "jjk"
DEMONSLAYER_DIR = VIDEO_DIR / "demonslayer"
FONTS_DIR = ASSETS_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"
SCRATCH_DIR = BASE_DIR / "scratch"
AGENTS_DATA_DIR = BASE_DIR / ".agents" / "data"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
DEMONSLAYER_DIR.mkdir(parents=True, exist_ok=True)
AGENTS_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Channel metadata
CHANNEL_NAME = "@Jazzcreatesclips"
CHANNEL_ID = "UCW-tzdlwTcHHCwNWlyLQ1hQ"
TITLE_HISTORY_FILE = AGENTS_DATA_DIR / "title_history.json"

# Video Rendering Config (9:16 Portrait, matching viral anime short sweet spot)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FOREGROUND_WIDTH = 1080
FOREGROUND_HEIGHT = 1350  # 4:5 tall centered foreground
FOREGROUND_Y_OFFSET = 285   # (1920 - 1350) / 2 = 285
FPS = 60  # High-bitrate 60fps export
DEFAULT_DURATION = 28.0  # Perfect 28.0s duration: 5s buildup + 23s drop combat rush & finisher

# Clean Cinematic Widescreen Framing (Preserves 100% anime choreography with letterbox bars)
FRAMING_MODE = "cinematic_widescreen"
LETTERBOX_TOP_BAR = 285
LETTERBOX_BOT_BAR = 285
ACTIVE_FRAME_HEIGHT = 1350
LETTERBOX_BAR_HEIGHT = 285

# Color Grading (CC) Presets — Vibrant Anime Glow (HDR-style highlights, no crushed-black mud)
CC_PRESETS = {
    # ── Vibrant Anime Glow (2026 AMV Standard) ──
    "vibrant_anime_glow": {
        "contrast": 1.15,
        "brightness": 0.02,
        "saturation": 1.25,
        "gamma": 1.15,
        "colorbalance": "rs=0.03:gs=0.01:bs=0.04",
        "unsharp": "5:5:1.0:5:5:0.0",
        "vignette": "0",  # Clean edges, no dark crushing
        "primary_color": "&H00FFFFFF",
        "accent_color": "#FFD700"
    },
    # ── Modern 2025/2026 TikTok & Shorts AMV Preset ──
    "anime_hdr_vibrant": {
        "contrast": 1.18,
        "brightness": 0.01,
        "saturation": 1.25,
        "gamma": 1.12,
        "colorbalance": "rs=0.03:gs=0.01:bs=0.04",
        "unsharp": "5:5:1.0:5:5:0.0",
        "vignette": "0",
        "primary_color": "&H00FFFFFF",
        "accent_color": "#FFD700"
    },
    # ── Reference-Matched Unified Cinematic Presets ──
    "jjk_cinematic_dark": {
        "contrast": 1.35,
        "brightness": -0.06,
        "saturation": 0.70,
        "gamma": 0.85,
        "colorbalance": "rs=-0.12:gs=0.04:bs=0.18:rm=-0.06:gm=0.02:bm=0.12",
        "unsharp": "5:5:1.2:5:5:0.0",
        "vignette": "PI/3.8",
        "primary_color": "&H00D2FF00",  # Cyan
        "accent_color": "#00D2FF"
    },
    "daylight_glow": {
        "contrast": 1.32,
        "brightness": -0.03,
        "saturation": 0.80,
        "gamma": 0.90,
        "colorbalance": "rs=0.05:gs=-0.02:bs=0.10:rm=0.03:gm=-0.01:bm=0.08",
        "unsharp": "5:5:1.1:5:5:0.0",
        "vignette": "PI/4.2",
        "primary_color": "&H00FFFFFF",
        "accent_color": "#FFFFFF"
    },
    "sukuna_crimson": {
        "contrast": 1.15,
        "brightness": 0.01,
        "saturation": 1.25,
        "gamma": 1.12,
        "colorbalance": "rs=0.10:gs=-0.02:bs=-0.06:rm=0.08:gm=-0.02:bm=-0.04",
        "unsharp": "3:3:0.6:3:3:0.0",
        "vignette": "0",
        "primary_color": "&H003333FF",
        "accent_color": "#FF2233"
    },
    # ── Primary dual-tone presets (cool blue ↔ warm red alternation) ──
    "cool_blue": {
        "contrast": 1.15,
        "brightness": 0.01,
        "saturation": 1.25,
        "gamma": 1.12,
        "colorbalance": "rs=-0.06:gs=0.02:bs=0.08:rm=-0.04:gm=0.01:bm=0.06",
        "unsharp": "3:3:0.6:3:3:0.0",
        "vignette": "0",
        "primary_color": "&H00D2FF00",  # Cyan
        "accent_color": "#00D2FF"
    },
    "warm_red": {
        "contrast": 1.15,
        "brightness": 0.01,
        "saturation": 1.25,
        "gamma": 1.15,
        "colorbalance": "rs=0.10:gs=-0.02:bs=-0.05",
        "unsharp": "5:5:1.0:5:5:0.0",
        "vignette": "0",  # Eliminated dark-red crushed vignette
        "primary_color": "&H003333FF",  # Crimson
        "accent_color": "#FF2233"
    },
    # ── Monochromatic modes (3 types matching reference) ──
    "mono_blue": {
        "contrast": 1.50,
        "brightness": -0.06,
        "saturation": 0.08,
        "gamma": 0.80,
        "colorbalance": "rs=-0.20:gs=0.0:bs=0.30:rm=-0.15:gm=0.0:bm=0.25",
        "unsharp": "5:5:1.4:5:5:0.0",
        "vignette": "PI/3.5",
        "primary_color": "&H00D2FF00",
        "accent_color": "#00D2FF"
    },
    "mono_white": {
        "contrast": 1.55,
        "brightness": +0.05,
        "saturation": 0.05,
        "gamma": 1.10,
        "colorbalance": "",
        "unsharp": "5:5:1.2:5:5:0.0",
        "vignette": "PI/4.5",
        "primary_color": "&H00FFFFFF",
        "accent_color": "#FFFFFF"
    },
    "mono_bw": {
        "contrast": 1.65,
        "brightness": -0.04,
        "saturation": 0.0,
        "gamma": 0.78,
        "colorbalance": "",
        "unsharp": "5:5:1.5:5:5:0.0",
        "vignette": "PI/3.2",
        "primary_color": "&H00FFFFFF",
        "accent_color": "#FFFFFF"
    },
    # ── Character-specific presets (for title cards and character scenes) ──
    "yuji_cyan": {
        "contrast": 1.35,
        "brightness": -0.07,
        "saturation": 0.60,
        "gamma": 0.83,
        "colorbalance": "rs=-0.10:gs=0.10:bs=0.25:rm=-0.05:gm=0.08:bm=0.18",
        "unsharp": "5:5:1.3:5:5:0.0",
        "vignette": "PI/4.0",
        "primary_color": "&H00FFFF00",  # Cyan for Yuji
        "accent_color": "#00FFFF"
    },
    "mahito_purple": {
        "contrast": 1.38,
        "brightness": -0.08,
        "saturation": 0.55,
        "gamma": 0.82,
        "colorbalance": "rs=0.12:gs=-0.08:bs=0.15:rm=0.10:gm=-0.06:bm=0.12",
        "unsharp": "5:5:1.3:5:5:0.0",
        "vignette": "PI/3.8",
        "primary_color": "&H00D200FF",  # Purple for Mahito
        "accent_color": "#D200FF"
    },
    # ── Legacy presets (mapped to new system for backward compat) ──
    "marvel_hdr": {
        "contrast": 1.40,
        "brightness": -0.08,
        "saturation": 0.65,
        "gamma": 0.82,
        "colorbalance": "rs=-0.12:gs=0.02:bs=0.15:rm=-0.06:gm=0.01:bm=0.10",
        "unsharp": "5:5:1.3:5:5:0.0",
        "vignette": "PI/3.8",
        "primary_color": "&H00D2FF00",
        "accent_color": "#00D2FF"
    },
    "jjk_void": {
        "contrast": 1.15,
        "brightness": 0.01,
        "saturation": 1.25,
        "gamma": 1.12,
        "colorbalance": "rs=0.05:gs=-0.02:bs=0.08:rm=0.04:gm=-0.01:bm=0.06",
        "unsharp": "3:3:0.6:3:3:0.0",
        "vignette": "0",
        "primary_color": "&H00FF55D2",
        "accent_color": "#D200FF"
    },
    "sukuna_shrine": {
        "contrast": 1.15,
        "brightness": 0.01,
        "saturation": 1.25,
        "gamma": 1.12,
        "colorbalance": "rs=0.08:gs=-0.02:bs=-0.05:rm=0.06:gm=-0.02:bm=-0.03",
        "unsharp": "3:3:0.6:3:3:0.0",
        "vignette": "0",
        "primary_color": "&H003333FF",
        "accent_color": "#FF2233"
    },
    "cyber_phonk": {
        "contrast": 1.38,
        "brightness": -0.07,
        "saturation": 0.60,
        "gamma": 0.84,
        "colorbalance": "rs=-0.08:gs=0.08:bs=0.20:rm=-0.04:gm=0.06:bm=0.15",
        "unsharp": "5:5:1.2:5:5:0.0",
        "vignette": "PI/4.0",
        "primary_color": "&H00FFFF00",
        "accent_color": "#00FFFF"
    },
    # ── Demon Slayer (Kimetsu no Yaiba) Presets ──
    "hinokami_flame": {
        "contrast": 1.15,
        "brightness": 0.01,
        "saturation": 1.25,
        "gamma": 1.12,
        "colorbalance": "rs=0.10:gs=0.01:bs=-0.08:rm=0.08:gm=0.01:bm=-0.05",
        "unsharp": "3:3:0.6:3:3:0.0",
        "vignette": "0",
        "primary_color": "&H001166FF",  # Sun Breathing Orange-Flame
        "accent_color": "#FF6611"
    },
    "thunder_gold": {
        "contrast": 1.15,
        "brightness": 0.01,
        "saturation": 1.25,
        "gamma": 1.12,
        "colorbalance": "rs=0.08:gs=0.06:bs=-0.10:rm=0.06:gm=0.04:bm=-0.06",
        "unsharp": "3:3:0.6:3:3:0.0",
        "vignette": "0",
        "primary_color": "&H0000D7FF",  # Electric Golden Amber
        "accent_color": "#FFD700"
    },
    "water_breathing": {
        "contrast": 1.15,
        "brightness": 0.01,
        "saturation": 1.25,
        "gamma": 1.12,
        "colorbalance": "rs=-0.08:gs=0.03:bs=0.10:rm=-0.05:gm=0.02:bm=0.08",
        "unsharp": "3:3:0.6:3:3:0.0",
        "vignette": "0",
        "primary_color": "&H00FFFF00",  # Oceanic Cyan / Aqua
        "accent_color": "#00FFFF"
    },
    "flame_hashira": {
        "contrast": 1.15,
        "brightness": 0.01,
        "saturation": 1.25,
        "gamma": 1.12,
        "colorbalance": "rs=0.12:gs=-0.02:bs=-0.08:rm=0.10:gm=-0.01:bm=-0.05",
        "unsharp": "3:3:0.6:3:3:0.0",
        "vignette": "0",
        "primary_color": "&H001133FF",  # Fiery Crimson Flame
        "accent_color": "#FF3311"
    },
    "akaza_compass": {
        "contrast": 1.15,
        "brightness": 0.01,
        "saturation": 1.25,
        "gamma": 1.12,
        "colorbalance": "rs=0.04:gs=-0.03:bs=0.10:rm=0.03:gm=-0.02:bm=0.08",
        "unsharp": "3:3:0.6:3:3:0.0",
        "vignette": "0",
        "primary_color": "&H00E020D0",  # Snowflake Cyan / Magenta
        "accent_color": "#D020E0"
    },
    "beast_breathing": {
        "contrast": 1.15,
        "brightness": 0.01,
        "saturation": 1.25,
        "gamma": 1.12,
        "colorbalance": "rs=-0.06:gs=0.02:bs=0.08:rm=-0.04:gm=0.01:bm=0.06",
        "unsharp": "3:3:0.6:3:3:0.0",
        "vignette": "0",
        "primary_color": "&H00D2FF00",  # Wild Beast Indigo/Cyan
        "accent_color": "#00FFD2"
    }
}

# Character-specific color mapping (used by dual-tone grading system)
CHARACTER_COLOR_MAP = {
    # JJK Characters
    "yuji":      {"primary": "cool_blue",  "energy": "yuji_cyan",     "text_color": "&H00FFFF00", "energy_hex": "#00FFFF"},
    "gojo":      {"primary": "cool_blue",  "energy": "cool_blue",     "text_color": "&H00D2FF00", "energy_hex": "#00D2FF"},
    "sukuna":    {"primary": "warm_red",   "energy": "sukuna_shrine", "text_color": "&H003333FF", "energy_hex": "#FF2233"},
    "toji":      {"primary": "warm_red",   "energy": "warm_red",      "text_color": "&H003333FF", "energy_hex": "#FF2233"},
    "megumi":    {"primary": "cool_blue",  "energy": "cool_blue",     "text_color": "&H00D2FF00", "energy_hex": "#00D2FF"},
    "mahito":    {"primary": "mahito_purple", "energy": "mahito_purple", "text_color": "&H00D200FF", "energy_hex": "#D200FF"},
    "todo":      {"primary": "cool_blue",  "energy": "yuji_cyan",     "text_color": "&H00FFFF00", "energy_hex": "#00FFFF"},
    "nobara":    {"primary": "warm_red",   "energy": "warm_red",      "text_color": "&H003333FF", "energy_hex": "#FF2233"},
    # Demon Slayer Characters
    "tanjiro":   {"primary": "warm_red",   "energy": "hinokami_flame", "text_color": "&H001166FF", "energy_hex": "#FF6611"},
    "rengoku":   {"primary": "warm_red",   "energy": "flame_hashira",  "text_color": "&H001133FF", "energy_hex": "#FF3311"},
    "zenitsu":   {"primary": "cool_blue",  "energy": "thunder_gold",   "text_color": "&H0000D7FF", "energy_hex": "#FFD700"},
    "akaza":     {"primary": "cool_blue",  "energy": "akaza_compass",  "text_color": "&H00E020D0", "energy_hex": "#D020E0"},
    "giyu":      {"primary": "cool_blue",  "energy": "water_breathing","text_color": "&H00FFFF00", "energy_hex": "#00FFFF"},
    "tengen":    {"primary": "warm_red",   "energy": "thunder_gold",   "text_color": "&H0000D7FF", "energy_hex": "#FFD700"},
    "inosuke":   {"primary": "cool_blue",  "energy": "beast_breathing","text_color": "&H00D2FF00", "energy_hex": "#00FFD2"},
    "muzan":     {"primary": "warm_red",   "energy": "sukuna_crimson", "text_color": "&H003333FF", "energy_hex": "#FF2233"},
    "nezuko":    {"primary": "warm_red",   "energy": "hinokami_flame", "text_color": "&H008833FF", "energy_hex": "#FF3388"},
    "muichiro":  {"primary": "cool_blue",  "energy": "cool_blue",      "text_color": "&H00D2FF00", "energy_hex": "#00D2FF"},
    "gyutaro":   {"primary": "warm_red",   "energy": "sukuna_crimson", "text_color": "&H0033FF33", "energy_hex": "#33FF33"},
    # Marvel Characters (legacy)
    "loki":      {"primary": "cool_blue",  "energy": "mahito_purple", "text_color": "&H00D200FF", "energy_hex": "#D200FF"},
    "spiderman": {"primary": "warm_red",   "energy": "warm_red",      "text_color": "&H003333FF", "energy_hex": "#FF2233"},
    "ironman":   {"primary": "warm_red",   "energy": "warm_red",      "text_color": "&H003333FF", "energy_hex": "#FF2233"},
    "thor":      {"primary": "cool_blue",  "energy": "cool_blue",     "text_color": "&H00D2FF00", "energy_hex": "#00D2FF"},
    "thanos":    {"primary": "mahito_purple", "energy": "mahito_purple", "text_color": "&H00D200FF", "energy_hex": "#D200FF"},
    "wolverine": {"primary": "warm_red",   "energy": "warm_red",      "text_color": "&H003333FF", "energy_hex": "#FF2233"},
}


# API Keys & Secrets
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
YOUTUBE_ACCESS_TOKEN = os.environ.get("YOUTUBE_ACCESS_TOKEN", "")

# Channel Branding & SEO
CHANNEL_TAGS = [
    "jjk", "gojo", "sukuna", "jujutsukaisen", "animeedit", "phonk", "velocity",
    "demonslayer", "kimetsunoyaiba", "tanjiro", "rengoku", "zenitsu", "akaza", "giyu", "tengen",
    "marvel", "spiderman", "avengers", "ironman", "infinitywar", "4kedit", "shorts"
]
