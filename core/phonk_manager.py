"""
Phonk Music Library & Live Trending Fetcher for AniDoc.

Now includes a live trending phonk fetcher that searches YouTube for
actual August 2026 phonk tracks — not a static catalog but live search.

Priority order:
1. Live trending 2026 phonk search via yt-dlp (freshest possible)
2. Static catalog fallback (if live search fails)
3. Existing local files
"""
import json
import subprocess
import random
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import PHONK_DIR, SCRATCH_DIR


# --- Curated Top 10 Viral AURA Phonk Catalog ---
POPULAR_PHONK_CATALOG = [
    {
        "id": "lonown_avangard_phonk",
        "title": "LONOWN - AVANGARD (SLOWED)",
        "genre": "Aura Phonk",
        "bpm": 132.0,
        "default_drop": 6.4,
    },
    {
        "id": "mvsterious_slava_funk",
        "title": "MVSTERIOUS - SLAVA FUNK!",
        "genre": "Slava Phonk",
        "bpm": 136.0,
        "default_drop": 5.2,
    },
    {
        "id": "dygo_funk_infernal",
        "title": "DYGO - FUNK INFERNAL",
        "genre": "Infernal Phonk",
        "bpm": 138.0,
        "default_drop": 6.8,
    },
    {
        "id": "ashreveal_manasha_phonk",
        "title": "ASHREVEAL - MANASHA",
        "genre": "Aggressive Phonk",
        "bpm": 134.0,
        "default_drop": 7.0,
    },
    {
        "id": "andromeda_no_fear_phonk",
        "title": "ANDROMEDA - NO FEAR!",
        "genre": "Aura Phonk",
        "bpm": 135.0,
        "default_drop": 6.0,
    },
    {
        "id": "ogryzek_aura_phonk",
        "title": "OGRYZEK - AURA",
        "genre": "Aura Phonk",
        "bpm": 130.0,
        "default_drop": 5.8,
    },
    {
        "id": "ncts_next_phonk",
        "title": "NCTS - NEXT",
        "genre": "Next Phonk",
        "bpm": 132.0,
        "default_drop": 6.2,
    },
    {
        "id": "nxght_blue_horizon_funk",
        "title": "NXGHT - BLUE HORIZON FUNK",
        "genre": "Horizon Phonk",
        "bpm": 136.0,
        "default_drop": 5.5,
    },
    {
        "id": "trashxrl_deus_do_olimpo",
        "title": "TRASHXRL - DEUS DO OLIMPO",
        "genre": "Brazilian Phonk",
        "bpm": 140.0,
        "default_drop": 4.8,
    },
    {
        "id": "irokz_funk_universo_slowed",
        "title": "IROKZ - FUNK UNIVERSO (SLOWED)",
        "genre": "Slowed Phonk",
        "bpm": 128.0,
        "default_drop": 7.5,
    },
]

# Live trending search queries — these rotate per run for max freshness
TRENDING_PHONK_QUERIES_2026 = [
    "trending phonk 2026 no copyright",
    "best phonk music august 2026 no copyright shorts",
    "new phonk 2026 aggressive bass drop no copyright",
    "viral phonk song 2026 no copyright",
    "phonk remix 2026 trending youtube shorts no copyright",
    "slowed phonk 2026 best hits no copyright",
    "dark phonk 2026 no copyright free use",
    "brazilian funk phonk 2026 no copyright",
    "phonk beats 2026 no copyright aggressive",
    "new age phonk 2026 no copyright viral",
]


def _ytdlp_available() -> bool:
    return shutil.which("yt-dlp") is not None


def _download_track_from_query(query: str, out_path: Path, max_duration: int = 210) -> Optional[Path]:
    """Download a single track matching query using yt-dlp. Returns path if successful."""
    cmd = [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=android,web",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", str(out_path),
        f"ytsearch1:{query}",
        "--max-downloads", "1",
        "--no-playlist",
        "--match-filter", f"duration <= {max_duration}",
        "--quiet",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        # yt-dlp may add extension automatically
        actual = out_path if out_path.exists() else out_path.with_suffix(".mp3")
        if actual.exists() and actual.stat().st_size > 50_000:
            return actual
        # Search result may not match duration filter — try without filter
        if not actual.exists():
            cmd_no_filter = [c for c in cmd if "duration" not in c and "match-filter" not in c]
            subprocess.run(cmd_no_filter, capture_output=True, text=True, timeout=90)
            actual = out_path if out_path.exists() else out_path.with_suffix(".mp3")
            if actual.exists() and actual.stat().st_size > 50_000:
                return actual
    except Exception as e:
        print(f"⚠️  [Phonk] Download error: {e}")
    return None


def fetch_trending_phonk_2026(n: int = 1) -> List[Path]:
    """
    Fetches n trending phonk tracks from YouTube, searching for August 2026 phonk.
    Returns list of downloaded .mp3 paths.
    """
    if not _ytdlp_available():
        print("⚠️  [Phonk] yt-dlp not found. Skipping live phonk fetch.")
        return []

    PHONK_DIR.mkdir(parents=True, exist_ok=True)

    # Shuffle queries so each run gets a different track
    queries = TRENDING_PHONK_QUERIES_2026.copy()
    random.shuffle(queries)

    downloaded = []
    tried = 0

    for query in queries:
        if len(downloaded) >= n:
            break
        tried += 1
        track_id = f"live_phonk_{tried}_{random.randint(1000, 9999)}"
        out_path = PHONK_DIR / f"{track_id}.mp3"

        print(f"🎵 [Phonk] Searching trending 2026 phonk: '{query[:60]}'")
        result = _download_track_from_query(query, out_path)
        if result:
            downloaded.append(result)
            print(f"  ✅ Got: {result.name} ({result.stat().st_size // 1024} KB)")

    return downloaded


def list_available_phonk_tracks() -> List[Dict[str, Any]]:
    """Lists all phonk audio files currently downloaded and ready to use."""
    PHONK_DIR.mkdir(parents=True, exist_ok=True)
    audio_files = list(PHONK_DIR.glob("*.mp3")) + list(PHONK_DIR.glob("*.wav"))

    catalog_map = {item["id"]: item for item in POPULAR_PHONK_CATALOG}

    results = []
    for f in audio_files:
        stem = f.stem
        info = catalog_map.get(stem, {
            "id": stem,
            "title": stem.replace("_", " ").title(),
            "genre": "Phonk",
            "bpm": 132.0,
            "default_drop": 6.5
        })
        results.append({
            "id": info["id"],
            "title": info["title"],
            "genre": info.get("genre", "Phonk"),
            "bpm": info.get("bpm", 132.0),
            "default_drop": info.get("default_drop", 6.5),
            "path": str(f),
            "size_kb": f.stat().st_size // 1024
        })
    return results


def download_phonk_track(track_id: str, query_override: Optional[str] = None) -> Optional[Path]:
    """Downloads a specific phonk track from the static catalog."""
    PHONK_DIR.mkdir(parents=True, exist_ok=True)
    target_mp3 = PHONK_DIR / f"{track_id}.mp3"

    if target_mp3.exists() and target_mp3.stat().st_size > 50_000:
        return target_mp3

    query = query_override
    if not query:
        matching = [item for item in POPULAR_PHONK_CATALOG if item["id"] == track_id]
        query = matching[0]["query"] if matching else f"{track_id} phonk no copyright"

    if not _ytdlp_available():
        return None

    print(f"🎵 [Phonk] Downloading catalog track '{track_id}'...")
    result = _download_track_from_query(query, target_mp3)
    return result


PHONK_STATE_FILE = PHONK_DIR / "rotation_state.json"


def _load_phonk_state() -> Dict[str, Any]:
    """Loads current phonk rotation state."""
    if PHONK_STATE_FILE.exists():
        try:
            with open(PHONK_STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_index": -1, "used_tracks": []}


def _save_phonk_state(state: Dict[str, Any]):
    """Saves phonk rotation state."""
    try:
        PHONK_DIR.mkdir(parents=True, exist_ok=True)
        with open(PHONK_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"⚠️ [Phonk] Failed to save rotation state: {e}")


def get_random_or_specified_phonk(track_id: Optional[str] = None) -> Optional[Path]:
    """
    Returns a phonk audio Path. Priority:
    1. If specific track_id given → return that exact curated track
    2. If 'random' or None → rotates sequentially through all 10 Top Viral AURA Phonk songs
    3. Fallback: live trending fetch or procedural audio
    """
    PHONK_DIR.mkdir(parents=True, exist_ok=True)
    curated_tracks = sorted([f for f in PHONK_DIR.glob("*.mp3") if f.stat().st_size > 50_000], key=lambda x: x.name)

    # 1. Specific track requested
    if track_id and track_id not in ("random", ""):
        direct = PHONK_DIR / f"{track_id}.mp3"
        if direct.exists() and direct.stat().st_size > 50_000:
            return direct
        for f in curated_tracks:
            if track_id in f.stem:
                return f

    # 2. Sequential Non-Repeating Rotation across 10 Curated Tracks
    if curated_tracks:
        state = _load_phonk_state()
        last_idx = state.get("last_index", -1)
        next_idx = (last_idx + 1) % len(curated_tracks)
        
        chosen = curated_tracks[next_idx]
        state["last_index"] = next_idx
        state["last_track"] = chosen.stem
        _save_phonk_state(state)
        
        print(f"🎧 [Phonk] Selected rotated Aura track ({next_idx + 1}/{len(curated_tracks)}): {chosen.stem}")
        return chosen

    # 3. Live trending fallback
    live = fetch_trending_phonk_2026(n=1)
    if live:
        return live[0]

    return None

    return None


def ensure_popular_phonk_library(min_tracks: int = 2) -> List[Path]:
    """Ensures at least min_tracks phonk tracks are downloaded and ready."""
    PHONK_DIR.mkdir(parents=True, exist_ok=True)
    existing = [f for f in PHONK_DIR.glob("*.mp3") if f.stat().st_size > 50_000]
    if len(existing) >= min_tracks:
        return existing

    # Fetch trending 2026 tracks first
    live = fetch_trending_phonk_2026(n=min_tracks - len(existing))
    if live:
        existing += live

    # Supplement from catalog if still short
    if len(existing) < min_tracks:
        for item in random.sample(POPULAR_PHONK_CATALOG, min(min_tracks, len(POPULAR_PHONK_CATALOG))):
            t = download_phonk_track(item["id"], item["query"])
            if t:
                existing.append(t)
                if len(existing) >= min_tracks:
                    break

    return existing
