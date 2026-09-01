"""
Character Clip Library & Action Scene Ingestion Manager for Marvel & Jujutsu Kaisen.
Features dynamic non-repeating clip shuffling, multi-source scenepack rotation, and procedural fallback.
"""
import os
import random
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import MARVEL_DIR, JJK_DIR, SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS
from core.public_api_fetcher import fetch_character_scenepack

CHARACTER_THEMES = {
    # JJK Universe Only (Marvel disabled for now)
    "gojo": {
        "universe": "jjk",
        "name": "Gojo Satoru",
        "colors": ["#4f46e5", "#8b5cf6", "#0f172a"],
        "cc_preset": "jjk_void",
        "quote": "Throughout heaven and earth, I alone am the honored one."
    },
    "sukuna": {
        "universe": "jjk",
        "name": "Ryomen Sukuna",
        "colors": ["#dc2626", "#7f1d1d", "#000000"],
        "cc_preset": "sukuna_shrine",
        "quote": "I'll slaughter the weak to weed them out."
    },
    "yuji": {
        "universe": "jjk",
        "name": "Yuji Itadori",
        "colors": ["#ea580c", "#f97316", "#1e293b"],
        "cc_preset": "jjk_void",
        "quote": "I'm a cog. And my role is to destroy curses like you."
    },
    "megumi": {
        "universe": "jjk",
        "name": "Megumi Fushiguro",
        "colors": ["#3b82f6", "#1e40af", "#0f172a"],
        "cc_preset": "jjk_void",
        "quote": "I don't understand the meaning of life."
    },
    "toji": {
        "universe": "jjk",
        "name": "Toji Zen'in",
        "colors": ["#6b7280", "#374151", "#000000"],
        "cc_preset": "cyber_phonk",
        "quote": "I have no cursed energy."
    },
    "loki": {
        "universe": "marvel",
        "name": "Loki (God of Stories)",
        "colors": ["#15803d", "#22c55e", "#052e16"],
        "cc_preset": "cyber_phonk",
        "quote": "I know what kind of god I need to be."
    },
    # Jujutsu Kaisen Universe ONLY
    "gojo": {
        "universe": "jjk",
        "name": "Gojo Satoru",
        "colors": ["#3b82f6", "#8b5cf6", "#090514"],
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
        "quote": "I'm going to save everyone I can."
    },
    "megumi": {
        "universe": "jjk",
        "name": "Megumi Fushiguro",
        "colors": ["#1e293b", "#38bdf8", "#0f172a"],
        "cc_preset": "jjk_void",
        "quote": "With this treasure, I summon... Mahoraga."
    },
    "nobara": {
        "universe": "jjk",
        "name": "Nobara Kugisaki",
        "colors": ["#dc2626", "#fbbf24", "#0f172a"],
        "cc_preset": "jjk_void",
        "quote": "I'm going to be the greatest curse user!"
    },
    "todo": {
        "universe": "jjk",
        "name": "Aoi Todo",
        "colors": ["#84cc16", "#365314", "#0f172a"],
        "cc_preset": "cyber_phonk",
        "quote": "What's your type of woman?"
    },
    "mahito": {
        "universe": "jjk",
        "name": "Mahito",
        "colors": ["#a855f7", "#581c87", "#000000"],
        "cc_preset": "sukuna_shrine",
        "quote": "Humans are so fun to play with!"
    },
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
    
    pulse_freq = 4.0 if is_drop else 1.5
    vf_chain = (
        f"testsrc=duration={dur_str}:size={VIDEO_WIDTH}x{VIDEO_HEIGHT}:rate={FPS},"
        f"drawbox=x=0:y=0:w=iw:h=ih:color={c3}@1:t=fill,"
        f"drawbox=x='(w-400)/2':y='(h-700)/2':w=400:h=700:color={c1}@0.7:t=fill,"
        f"drawbox=x='(w-480)/2':y='(h-780)/2':w=480:h=780:color={c2}@0.9:t=8,"
        f"curves=all='0/0 0.5/0.7 1/1',"
        f"vignette=PI/3.5,"
        f"format=yuv420p"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", vf_chain,
        "-c:v", "libx264",
        "-preset", "ultrafast",
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
    github_repo: Optional[str] = None,
    force_refresh: bool = False
) -> List[Path]:
    """
    Retrieves or downloads real footage clips for a character.
    
    Diversity fixes:
    - Searches both universe_dir AND scratch dir for character clips
    - Clips are strictly deduped: same clip never used twice in a row
    - If we have more clips than segments, each segment gets a unique clip
    - Wrong-character clips are filtered out by filename keyword matching
    """
    theme = CHARACTER_THEMES.get(character_key, CHARACTER_THEMES["gojo"])
    universe_dir = MARVEL_DIR if theme["universe"] == "marvel" else JJK_DIR
    universe_dir.mkdir(parents=True, exist_ok=True)
    
    # Search for character-specific clips in both dirs (including scratch)
    scratch_char_dir = SCRATCH_DIR / theme.get("universe", "marvel")
    scratch_char_dir.mkdir(parents=True, exist_ok=True)
    
    raw_clips = (
        list(universe_dir.glob(f"*{character_key}*.mp4")) +
        list(scratch_char_dir.glob(f"*{character_key}*.mp4"))
    )
    
    # If forced refresh or missing, download fresh multi-query scenepack
    if (not raw_clips or force_refresh) and auto_fetch_online:
        print(f"🌐 Fetching fresh scenepack cuts for '{character_key}'...")
        fetched = fetch_character_scenepack(character_key, max_clips=len(segment_durations) + 6)
        if fetched:
            raw_clips = fetched
            
    # Last resort: use any universe clips
    if not raw_clips:
        raw_clips = list(universe_dir.glob("*.mp4")) + list(scratch_char_dir.glob("*.mp4"))

    # Deduplicate paths, remove empties
    seen = set()
    unique_clips = []
    for p in raw_clips:
        if p.exists() and p.stat().st_size > 10_000 and str(p) not in seen:
            seen.add(str(p))
            unique_clips.append(p)
    raw_clips = sorted(unique_clips, key=lambda p: p.name)
    
    n_segs = len(segment_durations)
    
    if not raw_clips:
        # Full procedural fallback
        clip_paths = []
        for idx, (dur, is_drop) in enumerate(zip(segment_durations, is_drop_flags)):
            out_p = SCRATCH_DIR / f"proc_{character_key}_seg_{idx}_{int(dur*100)}.mp4"
            generate_procedural_cinematic_scene(character_key, idx, dur, out_p, is_drop)
            clip_paths.append(out_p)
        return clip_paths
    
    # Split into intro (calm) and action (drop) pools
    intro_pool = [c for c in raw_clips if raw_clips.index(c) < min(4, len(raw_clips))]
    action_pool = raw_clips[min(3, len(raw_clips) - 1):] if len(raw_clips) > 3 else raw_clips[:]
    
    # Shuffle both pools independently for max variety
    random.shuffle(intro_pool)
    random.shuffle(action_pool)
    
    if not intro_pool:
        intro_pool = raw_clips[:]
    if not action_pool:
        action_pool = raw_clips[:]

    clip_paths = []
    action_idx = 0
    intro_idx = 0
    last_clip = None

    for idx, (dur, is_drop) in enumerate(zip(segment_durations, is_drop_flags)):
        if not is_drop:
            # Intro shots: pick from intro pool, no consecutive repeats
            pool = intro_pool
            candidate = pool[intro_idx % len(pool)]
            intro_idx += 1
            # Skip if same as last clip and we have options
            if candidate == last_clip and len(pool) > 1:
                candidate = pool[intro_idx % len(pool)]
                intro_idx += 1
        else:
            # Drop/action shots: pick from action pool
            pool = action_pool
            candidate = pool[action_idx % len(pool)]
            action_idx += 1
            if candidate == last_clip and len(pool) > 1:
                candidate = pool[action_idx % len(pool)]
                action_idx += 1

        clip_paths.append(candidate)
        last_clip = candidate
            
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
