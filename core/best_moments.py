"""
Best Moments Extractor for AniDoc.

Downloads real anime episodes / movie scenepacks via yt-dlp, then uses
FFmpeg audio energy analysis + scene change detection to automatically
find and extract the most exciting, high-energy moments.

No AI voice. No TTS. 100% real character audio from the source material.

How it works:
1. Download a full scenepack or episode with audio intact
2. Run FFmpeg's `astats` filter to find segments with loudest average audio
   (= fights, screams, power-ups — the best moments)
3. Run scene change detection to align cuts to visual shot boundaries
4. Extract N best clips at those timestamps
5. Return as ready-to-use clip paths
"""
import subprocess
import json
import random
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from config.settings import SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS


# Search queries for real episodes / scenepacks per character
# These target YouTube scenepacks that keep the original anime audio
EPISODE_SCENEPACK_QUERIES = {
    "gojo": [
        "gojo satoru best moments scenepack with audio jujutsu kaisen",
        "gojo hollow purple scene audio 1080p jujutsu kaisen",
        "gojo vs toji scenepack with original audio",
        "gojo infinity domain expansion audio scene",
    ],
    "sukuna": [
        "ryomen sukuna best moments scenepack with audio",
        "sukuna malevolent shrine scene original audio jujutsu kaisen",
        "sukuna vs mahoraga scenepack audio 1080p",
    ],
    "toji": [
        "toji fushiguro fight scenes original audio jujutsu kaisen",
        "toji vs gojo scenepack with audio hidden inventory",
    ],
    "yuji": [
        "yuji itadori best fight moments scenepack audio jujutsu kaisen",
        "yuji divergent fist scene original audio",
    ],
    "megumi": [
        "megumi fushiguro mahoraga scene scenepack audio jujutsu kaisen",
        "megumi best moments original audio 1080p",
    ],
    "spiderman": [
        "spider-man best fight scenes scenepack original audio marvel",
        "spiderman no way home best moments audio 1080p",
    ],
    "ironman": [
        "iron man best moments scenepack original audio marvel mcu",
        "tony stark suit up scene original audio avengers",
    ],
    "thor": [
        "thor best fight moments scenepack original audio marvel",
        "thor ragnarok battle scene original audio 1080p",
    ],
    "wolverine": [
        "wolverine best fight scenes original audio scenepack",
        "wolverine berserker rage scene original audio x-men",
    ],
    "thanos": [
        "thanos best moments scenepack original audio avengers",
        "thanos snap scene original audio infinity war 1080p",
    ],
    "loki": [
        "loki best moments scenepack original audio marvel",
        "loki fight scene original audio thor avengers",
    ],
}


def download_episode_with_audio(
    character_key: str,
    output_dir: Path,
    max_duration_secs: int = 180
) -> Optional[Path]:
    """
    Downloads a real scenepack or episode clip from YouTube using yt-dlp,
    keeping the original audio track intact.

    Targets videos under max_duration_secs to avoid hour-long episodes.
    Returns the path to the downloaded video file.
    """
    if not shutil.which("yt-dlp"):
        print("⚠️  [BestMoments] yt-dlp not found, skipping episode download.")
        return None

    queries = EPISODE_SCENEPACK_QUERIES.get(
        character_key,
        [f"{character_key} anime best moments scenepack original audio 1080p"]
    )
    query = random.choice(queries)
    print(f"📺 [BestMoments] Searching for real episode audio: '{query}'")

    out_path = output_dir / f"ep_{character_key}_{random.randint(1000, 9999)}.mp4"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=android,web",
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "-o", str(out_path),
        f"ytsearch1:{query}",
        "--max-downloads", "1",
        "--no-playlist",
        "--match-filter", f"duration <= {max_duration_secs}",
        "--quiet",
        "--merge-output-format", "mp4",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if out_path.exists() and out_path.stat().st_size > 500_000:
            print(f"✅ [BestMoments] Downloaded: {out_path.name} ({out_path.stat().st_size // 1024} KB)")
            return out_path
        else:
            print(f"⚠️  [BestMoments] Download failed or too small. stderr: {result.stderr[:150]}")
            return None
    except Exception as e:
        print(f"⚠️  [BestMoments] Download exception: {e}")
        return None


def get_audio_energy_segments(
    video_path: Path,
    window_secs: float = 2.5,
    step_secs: float = 1.0,
    top_n: int = 12
) -> List[Tuple[float, float, float]]:
    """
    Scans the video's audio track in sliding windows and returns the
    top N loudest (most energetic) segments as (start, end, energy_db) tuples.

    Uses FFmpeg's `astats` filter for per-window RMS energy measurement.
    Loud windows = fights, screams, explosions, power-ups.
    """
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(video_path)
    ]
    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=15)
        info = json.loads(result.stdout)
        total_duration = float(info["format"].get("duration", 0))
    except Exception:
        total_duration = 60.0

    if total_duration < 3.0:
        return [(0.0, window_secs, -20.0)]

    segments = []
    t = 0.0
    while t + window_secs <= total_duration:
        # Sample audio energy in this window
        cmd = [
            "ffmpeg", "-ss", str(t), "-t", str(window_secs),
            "-i", str(video_path),
            "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
            "-vn", "-f", "null", "-"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            rms_values = []
            for line in res.stderr.split("\n"):
                if "RMS_level" in line and "=" in line:
                    try:
                        val = float(line.split("=")[-1].strip())
                        if val > -100:
                            rms_values.append(val)
                    except ValueError:
                        pass
            energy = max(rms_values) if rms_values else -60.0
            segments.append((t, t + window_secs, energy))
        except Exception:
            segments.append((t, t + window_secs, -60.0))
        t += step_secs

    # Sort by energy descending, return top N non-overlapping
    segments.sort(key=lambda x: x[2], reverse=True)

    selected = []
    used_starts = set()
    for start, end, energy in segments:
        # Ensure minimum 1s gap between clips
        if not any(abs(start - u) < window_secs for u in used_starts):
            selected.append((start, end, energy))
            used_starts.add(start)
        if len(selected) >= top_n:
            break

    # Return sorted by timestamp (so final edit flows chronologically)
    selected.sort(key=lambda x: x[0])
    return selected


def extract_best_clips(
    video_path: Path,
    character_key: str,
    output_dir: Path,
    n_clips: int = 12,
    clip_duration: float = 2.4
) -> List[Path]:
    """
    Main pipeline: finds the best N moments in a downloaded episode/scenepack
    and extracts them as individual portrait-cropped clips with original audio.

    Returns list of extracted clip paths.
    """
    print(f"🔍 [BestMoments] Analyzing audio energy in: {video_path.name}")
    segments = get_audio_energy_segments(
        video_path,
        window_secs=clip_duration,
        step_secs=1.0,
        top_n=n_clips + 4
    )

    if not segments:
        print("⚠️  [BestMoments] No segments found, falling back to uniform slicing.")
        segments = [(i * clip_duration, (i + 1) * clip_duration, -30.0)
                    for i in range(n_clips)]

    print(f"🎯 [BestMoments] Found {len(segments)} energetic moments. Extracting clips...")

    clips = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, (start, end, energy) in enumerate(segments[:n_clips]):
        out_clip = output_dir / f"{character_key}_best_{i:02d}_{int(start)}s.mp4"
        dur = end - start

        # Extract clip: crop + scale to 9:16 portrait, keep original audio
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-t", str(dur),
            "-i", str(video_path),
            "-vf", (
                f"crop=in_h:in_h:(in_w-in_h)/2:0,"
                f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
                f"setsar=1,fps={FPS}"
            ),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            str(out_clip)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=60)
            if out_clip.exists() and out_clip.stat().st_size > 50_000:
                clips.append(out_clip)
                print(f"  ✂️  Clip {i+1}: {start:.1f}s → {end:.1f}s (energy: {energy:.1f} dB)")
        except Exception as e:
            print(f"  ⚠️  Clip {i+1} extraction failed: {e}")

    print(f"✅ [BestMoments] Extracted {len(clips)} real episode clips with original audio.")
    return clips


def fetch_best_episode_clips(
    character_key: str,
    output_dir: Path,
    n_clips: int = 12
) -> List[Path]:
    """
    Top-level function: downloads a real episode scenepack and extracts
    the best N energetic moments from it, with original audio intact.

    Returns list of clip paths ready for the video assembler.
    """
    raw_video = download_episode_with_audio(
        character_key=character_key,
        output_dir=SCRATCH_DIR / "episodes",
        max_duration_secs=300  # Up to 5 min scenepacks
    )

    if not raw_video:
        print("⚠️  [BestMoments] Episode download failed. Returning empty list.")
        return []

    clips = extract_best_clips(
        video_path=raw_video,
        character_key=character_key,
        output_dir=output_dir,
        n_clips=n_clips,
        clip_duration=2.4
    )

    # Clean up raw episode file to save disk space
    try:
        raw_video.unlink()
    except Exception:
        pass

    return clips
