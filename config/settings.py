"""
Configuration and Environment Settings for AniDoc AI Automation Engine
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "output"
WEB_DIR = BASE_DIR / "web"
EXAMPLES_DIR = BASE_DIR / "examples"

OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Load environment variables from .env if present
def load_env():
    env_paths = [
        BASE_DIR / ".env",
        Path.home() / ".env",
        Path.home() / "antigravity" / "auto-clipper-shorts" / ".env"
    ]
    for p in env_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("\"'")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

load_env()

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY", "")

# Default Models
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "openrouter" if OPENROUTER_API_KEY else "nvidia" if NVIDIA_API_KEY else "free")
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "anthropic/claude-3.5-sonnet" if OPENROUTER_API_KEY else "nvidia/nemotron-3-nano" if NVIDIA_API_KEY else "deepseek/deepseek-chat")

# TTS Defaults
DEFAULT_TTS_PROVIDER = os.getenv("DEFAULT_TTS_PROVIDER", "edge") # "edge" (free) or "elevenlabs"
DEFAULT_HINDI_VOICE_EDGE = "hi-IN-MadhurNeural" # Authoritative deep Hindi male voice
DEFAULT_ENGLISH_VOICE_EDGE = "en-US-ChristopherNeural" # Deep documentary male voice

# Video Defaults
DEFAULT_VIDEO_WIDTH = 1920
DEFAULT_VIDEO_HEIGHT = 1080
DEFAULT_FPS = 30
DEFAULT_IMAGE_DURATION_SEC = 5.0

# Subtitle Styling (Devanagari / English Documentary)
SUBTITLE_FONT = "Arial"
SUBTITLE_FONT_SIZE = 24
SUBTITLE_PRIMARY_COLOR = "&H00FFFFFF" # White
SUBTITLE_HIGHLIGHT_COLOR = "&H0000FFFF" # Yellow
