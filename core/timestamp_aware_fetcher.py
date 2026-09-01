"""
Timestamp-aware Google Drive clip fetcher.

Integrates episode timestamp metadata with gdrive_manager for precise clip selection.
"""
import re
from pathlib import Path
from typing import List, Dict, Optional, Any

from core.timestamp_loader import (
    load_episode_metadata,
    get_character_clips,
    find_best_episode_for_character
)
from core.gdrive_manager import (
    list_gdrive_folder_items,
    download_gdrive_file,
    slice_video_clips
)


def fetch_timestamp_aware_clips(
    gdrive_url_or_id: str,
    target_character: str,
    output_dir: Path,
    n_clips: int = 50
) -> List[Path]:
    """
    Fetch clips using timestamp metadata instead of random slicing.

    1. Find best episode for character from metadata
    2. Match episode file in Google Drive
    3. Download episode
    4. Extract clips using precise timestamps from metadata
    """
    print(f"\n🎯 [TimestampAware] Fetching clips for '{target_character}' with metadata...")

    # Step 1: Find best episode
    best_episode = find_best_episode_for_character(target_character)
    if not best_episode:
        print(f"⚠️  No timestamp metadata found for '{target_character}', falling back to random selection")
        return []

    print(f"📂 [TimestampAware] Best episode: {best_episode}")

    # Step 2: Get high-action clips from metadata
    clips_metadata = get_character_clips(
        best_episode,
        target_character,
        min_action_score=0.5,
        max_clips=n_clips
    )

    if not clips_metadata:
        print(f"⚠️  No high-action clips found in metadata for '{target_character}'")
        return []

    print(f"✅ [TimestampAware] Found {len(clips_metadata)} high-action clips in metadata")

    # Step 3: Find matching episode file in Google Drive
    gdrive_items = list_gdrive_folder_items(gdrive_url_or_id)
    episode_file = None

    for item in gdrive_items:
        name = item.get('name', '')
        # Parse episode code from filename
        match = re.search(r'(S\d+E\d+)', name, re.IGNORECASE)
        if match and match.group(1).upper() == best_episode:
            episode_file = item
            break

    if not episode_file:
        print(f"❌ [TimestampAware] Episode {best_episode} not found in Google Drive")
        return []

    print(f"📥 [TimestampAware] Downloading: {episode_file['name']}")

    # Step 4: Download episode
    output_dir.mkdir(parents=True, exist_ok=True)
    video_path = download_gdrive_file(
        episode_file['id'],
        output_dir / episode_file['name']
    )

    if not video_path or not video_path.exists():
        print(f"❌ [TimestampAware] Failed to download {episode_file['name']}")
        return []

    print(f"✅ [TimestampAware] Downloaded: {video_path.name} ({video_path.stat().st_size // (1024*1024)} MB)")

    # Step 5: Extract clips using precise timestamps
    output_clips = []
    for i, clip_meta in enumerate(clips_metadata[:n_clips], 1):
        start = clip_meta['start']
        duration = clip_meta['end'] - clip_meta['start']
        action_level = clip_meta.get('action_level', 'MODERATE')

        clip_path = output_dir / f"clip_{target_character}_{best_episode}_{i:03d}_{action_level}.mp4"

        # Extract clip using ffmpeg
        extract_clip_precise(video_path, clip_path, start, duration)

        if clip_path.exists() and clip_path.stat().st_size > 10_000:
            output_clips.append(clip_path)
            if i <= 3:  # Show first 3 for debugging
                print(f"  ✂️  Clip {i:02d}: {start:.1f}s - {clip_meta['end']:.1f}s [{action_level}]")

    print(f"✅ [TimestampAware] Extracted {len(output_clips)} clips with precise timestamps")
    return output_clips


def extract_clip_precise(
    source_video: Path,
    output_clip: Path,
    start_time: float,
    duration: float
) -> bool:
    """Extract a precise clip using ffmpeg."""
    import subprocess

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_time:.2f}",
        "-i", str(source_video),
        "-t", f"{duration:.2f}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:a", "aac",
        "-b:a", "128k",
        "-avoid_negative_ts", "make_zero",
        str(output_clip)
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"⚠️  Failed to extract clip: {e}")
        return False


if __name__ == "__main__":
    # Test timestamp-aware fetching
    from config.settings import SCRATCH_DIR

    test_dir = SCRATCH_DIR / "timestamp_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    print("🧪 Testing Timestamp-Aware Clip Fetching\n")

    clips = fetch_timestamp_aware_clips(
        "1e5_IF3GRHNr315hP5zK_qlyfsKXm3Ox4",
        "yuji",
        test_dir,
        n_clips=5
    )

    print(f"\n✅ Test complete: {len(clips)} clips extracted")
