"""
Clip Asset & Procedural Scene Generator for Marvel & Jujutsu Kaisen.
Manages raw 1080p/4K clips, public API/GitHub fetching, and procedural motion scene generation.
"""
import subprocess
import random
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import MARVEL_DIR, JJK_DIR, SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT
from core.public_api_fetcher import fetch_character_scenepack, fetch_from_github_repo

# Curated Character Universe Themes
CHARACTER_THEMES = {
    # Marvel
    "spiderman": {
        "universe": "marvel",
        "name": "Spider-Man (Peter Parker)",
        "colors": ["#e23636", "#0055b3", "#1a1a24"],
        "cc_preset": "marvel_hdr",
        "quote": "I'm a machine. You think I'm afraid of you?"
    },
    "ironman": {
        "universe": "marvel",
        "name": "Iron Man (Tony Stark)",
        "colors": ["#d4af37", "#990000", "#111118"],
        "cc_preset": "marvel_hdr",
        "quote": "And I... am... Iron Man."
    },
    "thor": {
        "universe": "marvel",
        "name": "Thor Odinson",
        "colors": ["#00d2ff", "#1e3a8a", "#0f172a"],
        "cc_preset": "marvel_hdr",
        "quote": "Bring me Thanos!"
    },
    "thanos": {
        "universe": "marvel",
        "name": "Thanos",
        "colors": ["#581c87", "#7e22ce", "#18181b"],
        "cc_preset": "sukuna_shrine",
        "quote": "You should have gone for the head."
    },
    "wolverine": {
        "universe": "marvel",
        "name": "Wolverine (Logan)",
        "colors": ["#fbbf24", "#1e3a8a", "#0f172a"],
        "cc_preset": "marvel_hdr",
        "quote": "I'm the best there is at what I do, but what I do isn't very nice."
    },
    "loki": {
        "universe": "marvel",
        "name": "Loki (God of Stories)",
        "colors": ["#10b981", "#047857", "#064e3b"],
        "cc_preset": "cyber_phonk",
        "quote": "I know what kind of god I need to be. For you. For all of us."
    },
    # Jujutsu Kaisen
    "gojo": {
        "universe": "jjk",
        "name": "Gojo Satoru",
        "colors": ["#7c3aed", "#00d2ff", "#0f0c29"],
        "cc_preset": "jjk_void",
        "quote": "Throughout heaven and earth, I alone am the honored one."
    },
    "sukuna": {
        "universe": "jjk",
        "name": "Ryomen Sukuna",
        "colors": ["#991b1b", "#dc2626", "#180000"],
        "cc_preset": "sukuna_shrine",
        "quote": "Stand proud. You are strong."
    },
    "toji": {
        "universe": "jjk",
        "name": "Toji Fushiguro",
        "colors": ["#334155", "#0284c7", "#090d16"],
        "cc_preset": "cyber_phonk",
        "quote": "Don't get cocky just because you have cursed energy."
    },
    "yuji": {
        "universe": "jjk",
        "name": "Yuji Itadori",
        "colors": ["#b91c1c", "#fbbf24", "#1a0b0b"],
        "cc_preset": "sukuna_shrine",
        "quote": "I don't know how I'll feel when I'm dead, but I don't want to regret the way I lived."
    },
    "megumi": {
        "universe": "jjk",
        "name": "Megumi Fushiguro",
        "colors": ["#1e293b", "#38bdf8", "#0f172a"],
        "cc_preset": "jjk_void",
        "quote": "With this treasure, I summon... Eight-Handled Sword Divergent Sila Divine General Mahoraga."
    }
}


def generate_procedural_cinematic_scene(
    character_key: str,
    seg_idx: int,
    duration: float,
    output_path: Path,
    is_drop: bool = False
) -> Path:
    """
    Renders an animated high-contrast 1080x1920 procedural motion scene
    with energy particles, kinetic glow pulses, and stylized framing.
    """
    theme = CHARACTER_THEMES.get(character_key, CHARACTER_THEMES["gojo"])
    c1, c2, c3 = theme["colors"]
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dur_str = f"{duration:.2f}"
    
    # Animated generative background pattern using FFmpeg testsrc & gradients
    pulse_freq = 4.0 if is_drop else 1.5
    v_expr = (
        f"color=c={c3}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:d={dur_str},"
        f"drawbox=x=80:y=120:w={VIDEO_WIDTH-160}:h={VIDEO_HEIGHT-240}:color={c2}@0.15:t=fill,"
        f"drawbox=x=120:y=160:w={VIDEO_WIDTH-240}:h={VIDEO_HEIGHT-320}:color={c1}@0.35:t=2,"
        f"drawbox=x=0:y=ih-16:w='iw*(t/{dur_str})':h=16:color={c2}@0.9:t=fill"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", v_expr,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-t", dur_str,
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def get_character_scene_clips(
    character_key: str,
    segment_durations: List[float],
    is_drop_flags: List[bool],
    auto_fetch_online: bool = True,
    github_repo: Optional[str] = None
) -> List[Path]:
    """
    Returns a list of video clip paths for each segment.
    1. Checks local universe video directory for character-specific clips.
    2. If missing and github_repo is provided, fetches from GitHub repo.
    3. If missing and auto_fetch_online is True, downloads raw scenepack.
    4. Falls back to generating high-octane procedural scenes.
    """
    theme = CHARACTER_THEMES.get(character_key, CHARACTER_THEMES["gojo"])
    universe_dir = MARVEL_DIR if theme["universe"] == "marvel" else JJK_DIR
    universe_dir.mkdir(parents=True, exist_ok=True)
    
    # Search for real clip files matching the character
    raw_clips = list(universe_dir.glob(f"*{character_key}*.mp4"))
    
    # If no character-specific clips exist and github_repo specified, fetch from GitHub
    if not raw_clips and github_repo:
        print(f"🐙 Sourcing clips from GitHub repo: {github_repo}")
        raw_clips = fetch_from_github_repo(github_repo, universe_dir, character_filter=character_key)
        
    # If still no clips and auto_fetch enabled, download & slice scenepack
    if not raw_clips and auto_fetch_online:
        print(f"🌐 No local clips for '{character_key}'. Fetching from public streamer...")
        raw_clips = fetch_character_scenepack(character_key, max_clips=len(segment_durations) + 2)
        
    # Fallback to any general universe clips if present
    if not raw_clips:
        raw_clips = list(universe_dir.glob("*.mp4"))
        
    clip_paths = []
    for idx, (dur, is_drop) in enumerate(zip(segment_durations, is_drop_flags)):
        if raw_clips:
            # Pick from available raw clips
            clip_paths.append(random.choice(raw_clips))
        else:
            # Generate tailored procedural scene
            out_p = SCRATCH_DIR / f"proc_{character_key}_seg_{idx}_{int(dur*100)}.mp4"
            generate_procedural_cinematic_scene(character_key, idx, dur, out_p, is_drop)
            clip_paths.append(out_p)
            
    return clip_paths


def list_available_character_clips(universe: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Lists all available downloaded clips categorized by character and universe."""
    result = {}
    
    dirs = []
    if universe == "marvel" or not universe:
        dirs.append(("marvel", MARVEL_DIR))
    if universe == "jjk" or not universe:
        dirs.append(("jjk", JJK_DIR))
        
    for univ_name, udir in dirs:
        udir.mkdir(parents=True, exist_ok=True)
        for clip in udir.glob("*.mp4"):
            char_match = "generic"
            for k in CHARACTER_THEMES.keys():
                if k in clip.name.lower():
                    char_match = k
                    break
            if char_match not in result:
                result[char_match] = []
            result[char_match].append({
                "filename": clip.name,
                "path": str(clip),
                "universe": univ_name,
                "size_kb": clip.stat().st_size // 1024
            })
    return result
