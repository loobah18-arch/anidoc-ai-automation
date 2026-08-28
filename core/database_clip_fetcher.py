"""
Database-Driven Scene Clip Fetcher
Fetches clips from exact timestamps in the JJK database.
"""
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from core.scene_database import SceneDatabaseQuery


def fetch_clips_from_database(
    title: str,
    character_key: str,
    n_clips: int,
    output_dir: Path,
    min_intensity: float = 4.0,
    preferred_type: str = "action"
) -> List[Path]:
    """
    Fetch clips using the timestamp database instead of random episodes.

    Args:
        title: Video title (used for keyword matching)
        character_key: Character name (for logging/context)
        n_clips: Number of clips needed
        output_dir: Where to save cut clips
        min_intensity: Minimum audio intensity (0-10)
        preferred_type: Preferred scene type

    Returns:
        List of paths to cut video clips
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎯 [DatabaseFetcher] Querying timestamp database for title-coherent scenes...")
    print(f"📌 Title: {title}")
    print(f"👤 Character: {character_key}")

    # Query database for matching scenes
    query_engine = SceneDatabaseQuery()

    try:
        scenes = query_engine.query_scenes(
            title=title,
            n_scenes=n_clips,
            preferred_type=preferred_type,
            min_intensity=min_intensity,
            diversity_factor=0.7  # Spread across different episodes
        )
    except Exception as e:
        print(f"❌ [DatabaseFetcher] Database query failed: {e}")
        raise RuntimeError(
            f"Could not find matching scenes in database. "
            f"Make sure 'Build JJK Timestamp Database' workflow has been run."
        )

    if not scenes:
        raise RuntimeError(
            f"No scenes found matching title '{title}' with min_intensity={min_intensity}"
        )

    # Cut clips from exact timestamps
    clip_paths = []
    print(f"\n✂️ [DatabaseFetcher] Cutting {len(scenes)} clips from verified timestamps...")

    for i, scene in enumerate(scenes):
        file_path = Path(scene["file_path"])
        timestamp = scene["timestamp"]
        duration = min(scene["duration"], 5.0)  # Cap at 5 seconds per clip

        # Check if source file exists
        if not file_path.exists():
            print(f"  ⚠️ Source file not found: {file_path.name}, skipping...")
            continue

        output_clip = output_dir / f"{character_key}_db_{i:02d}_{scene['id']}.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-t", str(duration),
            "-i", str(file_path),
            "-map", "0:v:0", "-map", "0:a:0?",
            "-vf", (
                f"crop=in_h:in_h:(in_w-in_h)/2:0,"  # Crop to square
                f"scale=1080:1080,"
                f"setsar=1,fps=60"
            ),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            str(output_clip)
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=60)

            if output_clip.exists() and output_clip.stat().st_size > 50_000:
                clip_paths.append(output_clip)

                scene_type_emoji = {
                    "intense_action": "💥",
                    "action": "⚔️",
                    "dialogue": "💬",
                    "ambient": "🌅"
                }
                emoji = scene_type_emoji.get(scene["scene_type"], "📹")

                print(
                    f"  {emoji} Clip {i+1:02d}/{len(scenes)}: "
                    f"{scene['file_name'][:30]}... @ {timestamp:.1f}s "
                    f"(score: {scene['match_score']:.1f}, "
                    f"type: {scene['scene_type']}, "
                    f"intensity: {scene['audio']['intensity']:.1f})"
                )
            else:
                print(f"  ⚠️ Clip {i+1} failed: output too small")

        except subprocess.TimeoutExpired:
            print(f"  ⚠️ Clip {i+1} timed out")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️ Clip {i+1} FFmpeg error: {e}")

    if not clip_paths:
        raise RuntimeError(
            "Failed to cut any clips from database timestamps. Check source files exist."
        )

    print(f"\n✅ [DatabaseFetcher] Successfully cut {len(clip_paths)} title-coherent clips")

    # Print episode diversity stats
    episodes_used = {}
    for scene in scenes[:len(clip_paths)]:
        ep_key = f"S{scene['season']:02d}E{scene['episode']:02d}"
        episodes_used[ep_key] = episodes_used.get(ep_key, 0) + 1

    print(f"📊 [DatabaseFetcher] Episode diversity: {len(episodes_used)} different episodes")
    for ep, count in sorted(episodes_used.items()):
        print(f"     {ep}: {count} clips")

    return clip_paths
