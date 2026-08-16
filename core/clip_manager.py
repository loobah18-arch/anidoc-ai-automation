"""
Clip Asset & Procedural Scene Generator for Marvel & Jujutsu Kaisen.
Manages raw 1080p/4K clips and provides procedural motion scene generation.
"""
import subprocess
import random
from pathlib import Path
from typing import List, Dict, Any
from config.settings import MARVEL_DIR, JJK_DIR, SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT

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
    is_drop_flags: List[bool]
) -> List[Path]:
    """
    Returns a list of video clip paths for each segment.
    Uses real video files from assets directory if available,
    otherwise renders pristine animated procedural scenes.
    """
    theme = CHARACTER_THEMES.get(character_key, CHARACTER_THEMES["gojo"])
    universe_dir = MARVEL_DIR if theme["universe"] == "marvel" else JJK_DIR
    
    # Search for real clip files matching the character
    raw_clips = list(universe_dir.glob(f"*{character_key}*.mp4")) + list(universe_dir.glob("*.mp4"))
    
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
