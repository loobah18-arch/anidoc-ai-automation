"""
Free Stream Fetcher for AniDoc — $0, no subscriptions needed.

Fetches real anime episodes and movie clips using:
1. ANIME: Multiple free streaming sites via yt-dlp (gogoanime, aniwatchtv, etc.)
   These sites are NOT blocked on GitHub Actions (only YouTube is).
2. MOVIES: VidSrc.to + FlixHQ embed scrapers via yt-dlp for MCU/Marvel movies.
3. FALLBACK: Best public scenepack searches on non-YouTube video hosts.

After fetching, FFmpeg audio energy analysis (astats RMS) finds the best
high-energy moments automatically (fights, power-ups, explosions).

All sources are free. No Real-Debrid, no subscription, no API keys needed.
"""
import subprocess
import json
import random
import shutil
import time
from pathlib import Path
from typing import List, Optional, Dict

from config.settings import SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS


# ─── Character → Content Mappings ───────────────────────────────────────────

ANIME_SOURCES = {
    "gojo": {
        "show_slug": "jujutsu-kaisen",
        "show_title": "Jujutsu Kaisen",
        # Best episodes for Gojo (1-indexed, confirmed great moments)
        "key_episodes": [7, 13, 20, 24, 26, 28, 36, 48],
        "search_queries": [
            "jujutsu kaisen gojo satoru best fight moments",
            "jujutsu kaisen hollow purple gojo",
            "gojo vs sukuna jujutsu kaisen",
            "jujutsu kaisen season 2 gojo hidden inventory",
        ],
    },
    "sukuna": {
        "show_slug": "jujutsu-kaisen",
        "show_title": "Jujutsu Kaisen",
        "key_episodes": [20, 24, 40, 41, 42, 47, 48],
        "search_queries": [
            "ryomen sukuna malevolent shrine jujutsu kaisen",
            "sukuna vs gojo jujutsu kaisen best moments",
            "sukuna world cutting slash jujutsu kaisen",
        ],
    },
    "toji": {
        "show_slug": "jujutsu-kaisen",
        "show_title": "Jujutsu Kaisen",
        "key_episodes": [26, 27, 28],
        "search_queries": [
            "toji fushiguro vs gojo jujutsu kaisen hidden inventory",
            "toji fushiguro best moments jujutsu kaisen",
        ],
    },
    "yuji": {
        "show_slug": "jujutsu-kaisen",
        "show_title": "Jujutsu Kaisen",
        "key_episodes": [4, 12, 20, 39, 43],
        "search_queries": [
            "yuji itadori divergent fist jujutsu kaisen",
            "yuji best fight moments jujutsu kaisen",
        ],
    },
    "megumi": {
        "show_slug": "jujutsu-kaisen",
        "show_title": "Jujutsu Kaisen",
        "key_episodes": [13, 23, 36],
        "search_queries": [
            "megumi fushiguro mahoraga jujutsu kaisen",
            "megumi best fight moments jujutsu kaisen",
        ],
    },
}

MOVIE_SOURCES = {
    "spiderman": {
        # Spider-Man: No Way Home (2021) — best for action/dialogue
        "imdb_id": "tt10872600",
        "title": "Spider-Man No Way Home",
        "alt_imdb": ["tt0413300", "tt2250912"],  # Far From Home, Homecoming
        "search_queries": [
            "spider-man no way home best action scenes",
            "spider-man homecoming best moments",
        ],
    },
    "ironman": {
        "imdb_id": "tt0371746",
        "title": "Iron Man",
        "alt_imdb": ["tt1228705", "tt1300854"],  # Iron Man 2, 3
        "search_queries": [
            "iron man best suit up scenes avengers",
            "tony stark best moments avengers endgame",
        ],
    },
    "thor": {
        "imdb_id": "tt3501632",
        "title": "Thor Ragnarok",
        "alt_imdb": ["tt0800369", "tt1300854"],
        "search_queries": [
            "thor ragnarok best fight scenes",
            "thor avengers endgame best moments",
        ],
    },
    "thanos": {
        "imdb_id": "tt4154756",
        "title": "Avengers Infinity War",
        "alt_imdb": ["tt4154796"],  # Endgame
        "search_queries": [
            "thanos best moments avengers infinity war",
            "thanos i am inevitable avengers endgame",
        ],
    },
    "wolverine": {
        "imdb_id": "tt3385516",  # Days of Future Past
        "title": "X-Men Days of Future Past",
        "alt_imdb": ["tt0376994", "tt1430132"],
        "search_queries": [
            "wolverine berserker rage best scenes",
            "wolverine logan best fight moments",
        ],
    },
    "loki": {
        "imdb_id": "tt0800369",
        "title": "Thor",
        "alt_imdb": ["tt2395427", "tt1300854"],
        "search_queries": [
            "loki best moments thor avengers",
            "loki god of mischief best scenes marvel",
        ],
    },
}


# ─── Free Anime Streaming Site URL Templates ─────────────────────────────────
# These sites are NOT blocked on GitHub Actions (only YouTube is)
# yt-dlp has extractors for most of these

ANIME_SITE_TEMPLATES = [
    # gogoanime — most reliable, yt-dlp support
    "https://gogoanime3.co/watch/{slug}-episode-{ep}",
    # aniwatchtv (formerly animixplay)
    "https://aniwatchtv.to/{slug}-episode-{ep}",
    # animesuge
    "https://animesuge.to/anime/{slug}/ep-{ep}",
]

# VidSrc — free movie embed, yt-dlp can extract
VIDSRC_MOVIE_TEMPLATE = "https://vidsrc.to/embed/movie/{imdb_id}"
VIDSRC_TV_TEMPLATE = "https://vidsrc.to/embed/tv/{imdb_id}/{season}/{episode}"
FLIXHQ_TEMPLATE = "https://flixhq.to/movie/watch-{slug}-{id}"


def _ytdlp_available() -> bool:
    return shutil.which("yt-dlp") is not None


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _try_ytdlp_download(
    url: str,
    output_path: Path,
    max_duration: int = 300,
    timeout: int = 120
) -> Optional[Path]:
    """
    Attempt to download a video URL with yt-dlp.
    Returns output path if successful, None otherwise.
    """
    cmd = [
        "yt-dlp",
        "--extractor-args", "generic:impersonate",
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", str(output_path),
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        actual = output_path if output_path.exists() else output_path.with_suffix(".mp4")
        if actual.exists() and actual.stat().st_size > 500_000:
            return actual
        return None
    except (subprocess.TimeoutExpired, Exception) as e:
        print(f"    ⚠️  yt-dlp failed for {url[:60]}: {type(e).__name__}")
        return None


def _try_ytdlp_search(
    query: str,
    output_path: Path,
    site_filter: str = "",
    timeout: int = 90
) -> Optional[Path]:
    """
    Search for a video using yt-dlp's ytsearch on non-YouTube hosts.
    For anime/movie sites that yt-dlp supports natively.
    """
    # Try DailyMotion (anime content, no bot-block on datacenter IPs)
    # Try Bilibili (large anime library, no bot-block)
    # Try generic search on archive.org
    search_sources = [
        f"dailymotionsearch1:{query}",
        f"billibillisearch1:{query}",
    ]

    for search in search_sources:
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[height<=1080]+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", str(output_path),
            "--no-playlist",
            "--quiet",
            "--no-warnings",
            "--match-filter", f"duration <= {300}",
            search,
            "--max-downloads", "1",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            actual = output_path if output_path.exists() else output_path.with_suffix(".mp4")
            if actual.exists() and actual.stat().st_size > 200_000:
                return actual
        except (subprocess.TimeoutExpired, Exception):
            continue
    return None


def _extract_audio_energy_clips(
    video_path: Path,
    character_key: str,
    output_dir: Path,
    n_clips: int = 14,
    clip_duration: float = 2.2
) -> List[Path]:
    """
    Scan a downloaded video for the most energetic moments
    (loudest audio = fights, screams, power-ups, explosions).
    Extract them as portrait-cropped 9:16 clips with original audio.
    """
    # Get total duration
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(video_path)
    ]
    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=15)
        info = json.loads(result.stdout)
        total_dur = float(info["format"].get("duration", 60))
    except Exception:
        total_dur = 60.0

    print(f"  📊 Analyzing {total_dur:.0f}s of footage for best {n_clips} moments...")

    # Scan audio energy in sliding windows
    step = 1.0
    segments = []
    t = 0.0
    while t + clip_duration <= total_dur:
        cmd = [
            "ffmpeg", "-ss", str(t), "-t", str(clip_duration),
            "-i", str(video_path),
            "-af", "volumedetect",
            "-vn", "-f", "null", "-"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            mean_vol = -60.0
            for line in res.stderr.split("\n"):
                if "mean_volume" in line:
                    try:
                        mean_vol = float(line.split(":")[1].strip().split(" ")[0])
                    except Exception:
                        pass
            segments.append((t, mean_vol))
        except Exception:
            segments.append((t, -60.0))
        t += step

    # Pick top N non-overlapping segments
    segments.sort(key=lambda x: x[1], reverse=True)
    selected_starts = []
    for start, energy in segments:
        if not any(abs(start - s) < clip_duration for s in selected_starts):
            selected_starts.append(start)
        if len(selected_starts) >= n_clips:
            break

    # Sort chronologically for natural edit flow
    selected_starts.sort()

    # Extract clips
    output_dir.mkdir(parents=True, exist_ok=True)
    clips = []
    for i, start in enumerate(selected_starts):
        out_clip = output_dir / f"{character_key}_stream_{i:02d}_{int(start)}s.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-t", str(clip_duration),
            "-i", str(video_path),
            "-vf", (
                f"crop=in_h*9/16:in_h:(in_w-in_h*9/16)/2:0,"
                f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1,fps={FPS}"
            ),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            str(out_clip)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=45)
            if out_clip.exists() and out_clip.stat().st_size > 30_000:
                clips.append(out_clip)
                print(f"    ✂️  Clip {i+1}: {start:.1f}s (energy: {segments[i][1]:.1f} dB)")
        except Exception as e:
            print(f"    ⚠️  Clip {i+1} extraction failed: {e}")

    return clips


def _fetch_vidsrc_movie_clips(
    character_key: str,
    output_dir: Path,
    n_clips: int = 14
) -> List[Path]:
    """
    Fetch real MCU/Marvel movie clips via VidSrc embed (free, no auth).
    VidSrc serves movies via IMDB ID with no account required.
    """
    source = MOVIE_SOURCES.get(character_key)
    if not source:
        print(f"  ⚠️  No movie source mapped for '{character_key}'")
        return []

    raw_dir = SCRATCH_DIR / "movies_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Try primary IMDB ID first, then alternates
    all_imdb = [source["imdb_id"]] + source.get("alt_imdb", [])
    random.shuffle(all_imdb)  # Vary which movie per run

    for imdb_id in all_imdb[:2]:  # Try max 2 movies per run
        url = VIDSRC_MOVIE_TEMPLATE.format(imdb_id=imdb_id)
        print(f"  🎬 [Movies] Trying VidSrc: {source['title']} ({imdb_id})")
        out_path = raw_dir / f"{character_key}_{imdb_id}_raw.mp4"

        raw = _try_ytdlp_download(url, out_path, timeout=90)
        if raw:
            print(f"  ✅ [Movies] Got raw movie stream: {raw.stat().st_size // 1024} KB")
            clips = _extract_audio_energy_clips(raw, character_key, output_dir, n_clips)
            try:
                raw.unlink()
            except Exception:
                pass
            if clips:
                return clips
        else:
            print(f"  ⚠️  VidSrc failed for {imdb_id}, trying search fallback...")

    # Search fallback on DailyMotion/BiliBili
    query = random.choice(source["search_queries"])
    print(f"  🔍 [Movies] Search fallback: '{query}'")
    out_path = raw_dir / f"{character_key}_search_raw.mp4"
    raw = _try_ytdlp_search(query, out_path)
    if raw:
        clips = _extract_audio_energy_clips(raw, character_key, output_dir, n_clips)
        try:
            raw.unlink()
        except Exception:
            pass
        return clips

    return []


def _fetch_anime_episode_clips(
    character_key: str,
    output_dir: Path,
    n_clips: int = 14
) -> List[Path]:
    """
    Fetch real anime episode clips from free streaming sites via yt-dlp.
    Sites like gogoanime/aniwatchtv are NOT blocked on GitHub Actions.
    Tries multiple episode URLs and streaming sites until one works.
    """
    source = ANIME_SOURCES.get(character_key)
    if not source:
        print(f"  ⚠️  No anime source mapped for '{character_key}'")
        return []

    raw_dir = SCRATCH_DIR / "anime_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    slug = source["show_slug"]

    # Shuffle key episodes for variety
    episodes = source["key_episodes"].copy()
    random.shuffle(episodes)
    ep = episodes[0]  # Try best episode first

    # Try each streaming site template
    for template in ANIME_SITE_TEMPLATES:
        url = template.format(slug=slug, ep=ep)
        print(f"  📺 [Anime] Trying: {url[:70]}")
        out_path = raw_dir / f"{character_key}_ep{ep}_raw.mp4"

        raw = _try_ytdlp_download(url, out_path, timeout=120)
        if raw:
            print(f"  ✅ [Anime] Got episode stream: {raw.stat().st_size // (1024*1024):.1f} MB")
            clips = _extract_audio_energy_clips(raw, character_key, output_dir, n_clips)
            try:
                raw.unlink()
            except Exception:
                pass
            if clips:
                return clips

    # Search fallback on free video hosts (not blocked on GitHub Actions)
    query = random.choice(source["search_queries"])
    print(f"  🔍 [Anime] Search fallback: '{query}'")
    out_path = raw_dir / f"{character_key}_search_raw.mp4"
    raw = _try_ytdlp_search(query, out_path)
    if raw:
        clips = _extract_audio_energy_clips(raw, character_key, output_dir, n_clips)
        try:
            raw.unlink()
        except Exception:
            pass
        return clips

    return []


def fetch_free_stream_clips(
    character_key: str,
    output_dir: Path,
    n_clips: int = 14
) -> List[Path]:
    """
    TOP-LEVEL FUNCTION: Fetch real anime or movie clips for free.

    Automatically routes to the correct fetcher:
    - JJK characters → Free anime streaming site extractor
    - Marvel characters → VidSrc/FlixHQ movie embed extractor

    Returns a list of portrait-cropped clip paths with original audio,
    ready to use directly in the video assembler.
    """
    if not _ytdlp_available():
        print("⚠️  [FreeStream] yt-dlp not found.")
        return []
    if not _ffmpeg_available():
        print("⚠️  [FreeStream] FFmpeg not found.")
        return []

    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if we have enough fresh clips already
    existing = [p for p in output_dir.glob(f"{character_key}_stream_*.mp4")
                if p.stat().st_size > 30_000]
    if len(existing) >= n_clips:
        print(f"✅ [FreeStream] Using {len(existing)} cached stream clips for '{character_key}'")
        random.shuffle(existing)
        return existing[:n_clips]

    print(f"\n🌐 [FreeStream] Fetching real footage for '{character_key}'...")

    if character_key in ANIME_SOURCES:
        clips = _fetch_anime_episode_clips(character_key, output_dir, n_clips)
    elif character_key in MOVIE_SOURCES:
        clips = _fetch_vidsrc_movie_clips(character_key, output_dir, n_clips)
    else:
        # Try anime first, then movie
        clips = _fetch_anime_episode_clips(character_key, output_dir, n_clips)
        if not clips:
            clips = _fetch_vidsrc_movie_clips(character_key, output_dir, n_clips)

    if clips:
        print(f"✅ [FreeStream] Ready: {len(clips)} real clips with original audio.")
    else:
        print(f"⚠️  [FreeStream] All sources failed for '{character_key}'. Returning empty.")

    return clips
