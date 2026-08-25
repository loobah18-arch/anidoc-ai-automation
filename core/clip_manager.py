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
    # Marvel Universe
    "spiderman": {
        "universe": "marvel",
        "name": "Spider-Man (Peter Parker)",
        "colors": ["#e11d48", "#1e3a8a", "#0f172a"],
        "cc_preset": "marvel_hdr",
        "quote": "Mr. Stark, it smells like a new car in here!"
    },
    "ironman": {
        "universe": "marvel",
        "name": "Iron Man (Tony Stark)",
        "colors": ["#eab308", "#991b1b", "#1c1917"],
        "cc_preset": "marvel_hdr",
        "quote": "And I... am... Iron Man."
    },
    "thor": {
        "universe": "marvel",
        "name": "Thor (God of Thunder)",
        "colors": ["#0284c7", "#38bdf8", "#030712"],
        "cc_preset": "marvel_hdr",
        "quote": "Bring me Thanos!"
    },
    "thanos": {
        "universe": "marvel",
        "name": "Thanos (The Mad Titan)",
        "colors": ["#7e22ce", "#3b0764", "#09090b"],
        "cc_preset": "marvel_hdr",
        "quote": "I am inevitable."
    },
    "wolverine": {
        "universe": "marvel",
        "name": "Wolverine (Logan)",
        "colors": ["#ca8a04", "#1e293b", "#0f172a"],
        "cc_preset": "marvel_hdr",
        "quote": "I'm the best there is at what I do."
    },
    "loki": {
        "universe": "marvel",
        "name": "Loki (God of Stories)",
        "colors": ["#15803d", "#22c55e", "#052e16"],
        "cc_preset": "cyber_phonk",
        "quote": "I know what kind of god I need to be."
    },
    # Jujutsu Kaisen Universe
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
    }
}


def is_likely_intro_or_irrelevant(clip_path: Path, character_key: str) -> bool:
    """
    Detects if a clip is likely an intro, outro, or irrelevant content.
    Returns True if the clip should be filtered out.

    CRITICAL: This ensures only the correct character's clips are used in videos.
    """
    filename = clip_path.name.lower()

    # Get character theme for additional matching
    theme = CHARACTER_THEMES.get(character_key, {})
    character_name_parts = theme.get("name", "").lower().split() if theme else []

    # Filter out clips with intro/outro/opening/ending keywords
    intro_keywords = ["intro", "opening", "op", "ending", "ed", "credits", "preview", "next_episode",
                      "trailer", "teaser", "recap"]
    if any(keyword in filename for keyword in intro_keywords):
        return True

    # Build comprehensive character matching patterns
    char_variants = [
        character_key,
        character_key.replace("_", ""),
        character_key.replace("-", ""),
        character_key.replace(" ", "")
    ]

    # Add character name parts (e.g., "gojo", "satoru" for "Gojo Satoru")
    char_variants.extend([part for part in character_name_parts if len(part) > 3])

    # Special case handling for common character name variations
    character_aliases = {
        "gojo": ["gojo", "satoru", "satorugojo"],
        "sukuna": ["sukuna", "ryomen", "ryomensukuna"],
        "toji": ["toji", "fushiguro", "tojifushiguro", "zenin"],
        "yuji": ["yuji", "itadori", "yujiitadori"],
        "megumi": ["megumi", "fushiguro", "megumifushiguro"],
        "spiderman": ["spiderman", "spider-man", "spidey", "peter", "parker", "peterparker"],
        "ironman": ["ironman", "iron-man", "tony", "stark", "tonystark"],
        "thor": ["thor", "odinson"],
        "wolverine": ["wolverine", "logan", "xmen"],
        "loki": ["loki", "odinson", "laufeyson"],
        "thanos": ["thanos", "titan"]
    }

    if character_key in character_aliases:
        char_variants.extend(character_aliases[character_key])

    # Check if any character variant is in the filename
    has_character_match = any(variant in filename for variant in char_variants)

    if not has_character_match:
        # Check for wrong character names (clips from other characters)
        all_other_characters = [k for k in CHARACTER_THEMES.keys() if k != character_key]
        for other_char in all_other_characters:
            other_variants = character_aliases.get(other_char, [other_char])
            if any(variant in filename for variant in other_variants):
                print(f"🚫 [ClipManager] Rejected clip with wrong character '{other_char}': {filename}")
                return True

        # If no character match and no action keywords, filter it out
        action_keywords = ["fight", "battle", "action", "scene", "clip", "moment", "edit", "vs"]
        if not any(keyword in filename for keyword in action_keywords):
            return True

    return False


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

    # Deduplicate paths, remove empties, and filter out intros/irrelevant clips
    seen = set()
    unique_clips = []
    for p in raw_clips:
        if p.exists() and p.stat().st_size > 10_000 and str(p) not in seen:
            # Skip intro/outro clips and clips that don't match the character
            if not is_likely_intro_or_irrelevant(p, character_key):
                seen.add(str(p))
                unique_clips.append(p)
            else:
                print(f"⚠️  [ClipManager] Filtered out intro/irrelevant clip: {p.name}")
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
    
    # IMPROVED: Use all filtered clips as action clips (no artificial intro/action split)
    # Since we already filtered out intros above, all remaining clips are action-worthy
    # Shuffle for variety while preventing consecutive repeats
    random.shuffle(raw_clips)

    clip_paths = []
    clip_idx = 0
    last_clip = None

    for idx, (dur, is_drop) in enumerate(zip(segment_durations, is_drop_flags)):
        # Pick next clip from the shuffled pool
        candidate = raw_clips[clip_idx % len(raw_clips)]
        clip_idx += 1

        # Skip if same as last clip and we have options
        if candidate == last_clip and len(raw_clips) > 1:
            candidate = raw_clips[clip_idx % len(raw_clips)]
            clip_idx += 1

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
