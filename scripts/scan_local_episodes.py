#!/usr/bin/env python3
"""
Lightweight JJK Episode Scanner for Phone
Scans episodes with minimal processing, samples key timestamps only.
"""
import os
import sys
import json
import hashlib
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Phone-optimized settings
DEFAULT_FOOTAGE_DIR = Path("/storage/emulated/0/Download/AniDoc-Footage")
DEFAULT_OUTPUT_DB = Path(__file__).parent.parent / "data" / "jjk_timestamp_database.json"
MIN_SCENE_DURATION = 3.0
SAMPLE_INTERVAL = 30  # Sample every 30 seconds instead of full scene detection


def get_video_info(video_path: Path) -> Optional[Dict[str, Any]]:
    """Get basic video info using FFprobe (fast, no decoding)."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size:stream=codec_type,width,height",
        "-of", "json",
        str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        data = json.loads(result.stdout)

        duration = float(data.get("format", {}).get("duration", 0))
        file_size = int(data.get("format", {}).get("size", 0))

        video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        width = video_stream.get("width", 0)
        height = video_stream.get("height", 0)

        return {
            "duration": duration,
            "file_size": file_size,
            "width": width,
            "height": height
        }
    except Exception as e:
        print(f"  ❌ FFprobe failed: {e}")
        return None


def parse_episode_info(filename: str) -> Dict[str, Any]:
    """Parse season/episode from filename (defensive)."""
    # Try patterns like: S01E05, s1e5, Episode 05, etc.
    patterns = [
        r'[Ss](\d+)[Ee](\d+)',
        r'[Ee]pisode[_ ](\d+)',
        r'[_ -](\d+)[_ -]',
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            groups = match.groups()
            if len(groups) == 2:
                return {"season": int(groups[0]), "episode": int(groups[1])}
            elif len(groups) == 1:
                return {"season": 1, "episode": int(groups[0])}

    return {"season": None, "episode": None}


def generate_source_id(filename: str, file_size: int) -> str:
    """Generate deterministic source_id from filename+size."""
    content = f"{filename}:{file_size}".encode()
    digest = hashlib.sha256(content).hexdigest()[:16]
    return f"local_{digest}"


def sample_timestamps(duration: float, interval: int = SAMPLE_INTERVAL) -> List[float]:
    """
    Generate sample timestamps at regular intervals.
    Skip first/last 60s to avoid intros/credits.
    """
    start_offset = 60.0
    end_offset = 60.0

    if duration < start_offset + end_offset + interval:
        # Video too short, just use midpoint
        return [duration / 2.0]

    timestamps = []
    current = start_offset
    end_point = duration - end_offset

    while current < end_point:
        timestamps.append(round(current, 2))
        current += interval

    return timestamps


def scan_episode_lightweight(video_path: Path) -> Optional[Dict[str, Any]]:
    """
    Lightweight scan: probe duration, sample timestamps, skip heavy processing.
    """
    print(f"\n📹 {video_path.name}")

    # Get video info
    info = get_video_info(video_path)
    if not info or info["duration"] == 0:
        print(f"  ❌ Failed to probe video")
        return None

    duration = info["duration"]
    file_size = info["file_size"]

    print(f"  ⏱️  {duration/60:.1f}min, {file_size/(1024*1024):.0f}MB, {info['width']}x{info['height']}")

    # Parse episode info
    ep_info = parse_episode_info(video_path.name)

    # Generate source ID
    source_id = generate_source_id(video_path.name, file_size)

    # Sample timestamps
    timestamps = sample_timestamps(duration, SAMPLE_INTERVAL)
    print(f"  📍 Sampled {len(timestamps)} timestamps (every {SAMPLE_INTERVAL}s)")

    # Build scene windows from samples
    scenes = []
    for i, start in enumerate(timestamps):
        end = timestamps[i + 1] if i + 1 < len(timestamps) else duration - 60.0
        scene_duration = end - start

        if scene_duration < MIN_SCENE_DURATION:
            continue

        scenes.append({
            "id": f"{source_id}_{i:04d}",
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(scene_duration, 2),
            "audio_energy_band": "unknown",  # Skip audio analysis for speed
            "scene_boundary_method": "interval_sampling",
            "semantic": {
                "status": "unverified",
                "characters": [],
                "action": None,
                "tags": []
            }
        })

    return {
        "source_id": source_id,
        "drive_file_id": None,
        "canonical_filename": video_path.name,
        "original_filename": video_path.name,
        "season": ep_info["season"],
        "episode": ep_info["episode"],
        "duration": round(duration, 2),
        "file_size": file_size,
        "resolution": f"{info['width']}x{info['height']}",
        "scan_status": "success",
        "scan_method": "lightweight_sampling",
        "scanned_at": datetime.utcnow().isoformat() + "Z",
        "total_scenes": len(scenes),
        "scenes": scenes
    }


def scan_directory(footage_dir: Path, output_db: Path, limit: Optional[int] = None):
    """Scan all episodes in directory."""
    print("=" * 80)
    print("🔍 JJK Episode Scanner (Lightweight)")
    print("=" * 80)
    print(f"📂 Source: {footage_dir}")
    print(f"💾 Output: {output_db}")

    if not footage_dir.exists():
        print(f"\n❌ Directory not found: {footage_dir}")
        sys.exit(1)

    # Find video files
    video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.webm'}
    video_files = [
        f for f in sorted(footage_dir.iterdir())
        if f.is_file() and f.suffix.lower() in video_extensions
    ]

    if not video_files:
        print(f"\n❌ No video files found in {footage_dir}")
        sys.exit(1)

    if limit:
        video_files = video_files[:limit]

    print(f"\n📊 Found {len(video_files)} episodes to scan")

    # Load existing database if present
    existing_db = {}
    if output_db.exists():
        try:
            with open(output_db) as f:
                existing_db = json.load(f)
            print(f"✓ Loaded existing database with {len(existing_db.get('episodes', {}))} episodes")
        except Exception as e:
            print(f"⚠️  Could not load existing database: {e}")

    # Scan episodes
    episodes = existing_db.get("episodes", {})
    total_scenes = 0
    success_count = 0

    for i, video_file in enumerate(video_files, 1):
        print(f"\n[{i}/{len(video_files)}]", end=" ")

        result = scan_episode_lightweight(video_file)

        if result:
            episodes[result["source_id"]] = result
            total_scenes += result["total_scenes"]
            success_count += 1
        else:
            print(f"  ⚠️  Skipped")

    # Build database
    database = {
        "version": "1.0.0",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source_directory": str(footage_dir),
        "scan_method": "lightweight_sampling",
        "total_episodes": len(episodes),
        "total_scenes": total_scenes,
        "episodes": episodes,
        "events": []  # Populated by manual tagging or semantic verification
    }

    # Save
    output_db.parent.mkdir(parents=True, exist_ok=True)
    with open(output_db, 'w') as f:
        json.dump(database, f, indent=2)

    print("\n" + "=" * 80)
    print(f"✅ Scan complete!")
    print(f"📊 Episodes: {success_count}/{len(video_files)} successful")
    print(f"📊 Total scenes: {total_scenes}")
    print(f"💾 Database: {output_db}")
    print("=" * 80)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Lightweight JJK Episode Scanner")
    parser.add_argument("--footage-dir", type=str, default=str(DEFAULT_FOOTAGE_DIR),
                        help="Directory containing episode files")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT_DB),
                        help="Output database JSON path")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of episodes to scan (for testing)")

    args = parser.parse_args()

    scan_directory(
        footage_dir=Path(args.footage_dir),
        output_db=Path(args.output),
        limit=args.limit
    )


if __name__ == "__main__":
    main()
