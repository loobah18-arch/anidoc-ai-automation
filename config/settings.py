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
FONTS_DIR = ASSETS_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"
SCRATCH_DIR = BASE_DIR / "scratch"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

# Video Rendering Config (9:16 1080x1920 60FPS Portrait YouTube Shorts / TikTok Format)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 60
DEFAULT_DURATION = 38.0  # Optimal high-retention 35-40s range matching reference edits

# Color Grading (CC) Presets for 4K 60FPS HDR Look
CC_PRESETS = {
    "marvel_hdr": {
        "contrast": 1.28,
        "brightness": -0.02,
        "saturation": 1.40,
        "gamma": 0.95,
        "unsharp": "5:5:1.3:5:5:0.0",
        "vignette": "PI/4.2",
        "primary_color": "&H00D2FF00",  # Cyan / Gold glow
        "accent_color": "#00D2FF"
    },
    "jjk_void": {
        "contrast": 1.34,
        "brightness": -0.03,
        "saturation": 1.45,
        "gamma": 0.92,
        "unsharp": "5:5:1.4:5:5:0.0",
        "vignette": "PI/4.0",
        "primary_color": "&H00FF55D2",  # Electric Violet / Hollow Purple
        "accent_color": "#D200FF"
    },
    "sukuna_shrine": {
        "contrast": 1.30,
        "brightness": -0.03,
        "saturation": 1.45,
        "gamma": 0.92,
        "unsharp": "5:5:1.3:5:5:0.0",
        "vignette": "PI/3.8",
        "primary_color": "&H003333FF",  # Crimson / Blood Red
        "accent_color": "#FF2233"
    },
    "cyber_phonk": {
        "contrast": 1.25,
        "brightness": -0.02,
        "saturation": 1.38,
        "gamma": 0.95,
        "unsharp": "5:5:1.2:5:5:0.0",
        "vignette": "PI/4.2",
        "primary_color": "&H00FFFF00",  # Neon Cyan
        "accent_color": "#00FFFF"
    }
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
    "marvel", "spiderman", "avengers", "ironman", "infinitywar", "4kedit", "shorts",
    "jjk", "gojo", "sukuna", "jujutsukaisen", "animeedit", "phonk", "velocity"
]
