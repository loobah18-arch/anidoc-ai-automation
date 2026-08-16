"""
Phonk Music Library & Beat Profile Manager for AniDoc.
Manages popular phonk tracks, automatic internet downloaders, and audio analysis.
"""
import subprocess
import random
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import PHONK_DIR, SCRATCH_DIR

# Curated Popular Phonk Catalog with search queries and default drop timings
POPULAR_PHONK_CATALOG = [
    {
        "id": "brazilian_phonk_montagem",
        "title": "Brazilian Phonk (Montagem Slowed & Reverb)",
        "genre": "Brazilian Phonk",
        "bpm": 134.0,
        "default_drop": 6.4,
        "query": "brazilian phonk montagem slowed reverb no copyright 30 seconds"
    },
    {
        "id": "tokyo_drift_phonk",
        "title": "Tokyo Drift Phonk (Cowbell Aggressive)",
        "genre": "Drift Phonk",
        "bpm": 130.0,
        "default_drop": 5.8,
        "query": "tokyo drift phonk cowbell no copyright 30 seconds"
    },
    {
        "id": "dark_shadow_phonk",
        "title": "Dark Shadow Phonk (Aggressive Bass Drop)",
        "genre": "Dark Phonk",
        "bpm": 138.0,
        "default_drop": 7.2,
        "query": "dark aggressive shadow phonk no copyright 30 seconds"
    },
    {
        "id": "cyber_phonk_beat",
        "title": "Cyberpunk Neon Phonk (Synthesizer Wave)",
        "genre": "Cyber Phonk",
        "bpm": 128.0,
        "default_drop": 6.0,
        "query": "cyberpunk neon phonk beat no copyright 30 seconds"
    },
    {
        "id": "murder_mind_phonk",
        "title": "Kordhell Style Murder Phonk (Heavy Bass)",
        "genre": "Murder Phonk",
        "bpm": 136.0,
        "default_drop": 6.8,
        "query": "aggressive murder phonk bass boosted no copyright 30 seconds"
    },
    {
        "id": "gigachad_phonk",
        "title": "Gigachad Phonk (Sigma Slowed Edit Beat)",
        "genre": "Sigma Phonk",
        "bpm": 132.0,
        "default_drop": 6.5,
        "query": "gigachad phonk theme slowed reverb no copyright 30 seconds"
    }
]


def list_available_phonk_tracks() -> List[Dict[str, Any]]:
    """Lists all phonk audio files currently downloaded and ready to use."""
    PHONK_DIR.mkdir(parents=True, exist_ok=True)
    audio_files = list(PHONK_DIR.glob("*.mp3")) + list(PHONK_DIR.glob("*.wav")) + list(PHONK_DIR.glob("*.aac"))
    
    catalog_map = {item["id"]: item for item in POPULAR_PHONK_CATALOG}
    
    results = []
    for f in audio_files:
        stem = f.stem
        info = catalog_map.get(stem, {
            "id": stem,
            "title": stem.replace("_", " ").title(),
            "genre": "Phonk",
            "bpm": 130.0,
            "default_drop": 6.5
        })
        results.append({
            "id": info["id"],
            "title": info["title"],
            "genre": info.get("genre", "Phonk"),
            "bpm": info.get("bpm", 130.0),
            "default_drop": info.get("default_drop", 6.5),
            "path": str(f),
            "size_kb": f.stat().st_size // 1024
        })
    return results


def download_phonk_track(track_id: str, query_override: Optional[str] = None) -> Optional[Path]:
    """Downloads a specific phonk track from the internet using yt-dlp."""
    PHONK_DIR.mkdir(parents=True, exist_ok=True)
    target_mp3 = PHONK_DIR / f"{track_id}.mp3"
    
    if target_mp3.exists() and target_mp3.stat().st_size > 10000:
        return target_mp3
        
    query = query_override
    if not query:
        matching = [item for item in POPULAR_PHONK_CATALOG if item["id"] == track_id]
        if matching:
            query = matching[0]["query"]
        else:
            query = f"{track_id} phonk no copyright 30 seconds"
            
    print(f"🎵 Downloading Phonk BGM '{track_id}' from internet...")
    cmd = [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=android,web",
        "-x", "--audio-format", "mp3",
        "-o", str(target_mp3),
        f"ytsearch1:{query}",
        "--max-downloads", "1"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if target_mp3.exists() and target_mp3.stat().st_size > 10000:
        print(f"✅ Downloaded: {target_mp3.name} ({target_mp3.stat().st_size // 1024} KB)")
        return target_mp3
    else:
        print(f"⚠️ Failed to download '{track_id}': {res.stderr[:200] if res.stderr else 'Unknown error'}")
        return None


def ensure_popular_phonk_library(min_tracks: int = 3) -> List[Path]:
    """Ensures at least min_tracks popular phonk tracks are downloaded and ready."""
    PHONK_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(PHONK_DIR.glob("*.mp3"))
    if len(existing) >= min_tracks:
        return existing
        
    for item in POPULAR_PHONK_CATALOG:
        download_phonk_track(item["id"], item["query"])
        
    return list(PHONK_DIR.glob("*.mp3"))


def get_random_or_specified_phonk(track_id: Optional[str] = None) -> Optional[Path]:
    """Returns a phonk audio Path matching track_id, or a random downloaded phonk."""
    PHONK_DIR.mkdir(parents=True, exist_ok=True)
    if track_id:
        direct = PHONK_DIR / f"{track_id}.mp3"
        if direct.exists():
            return direct
        direct_alt = PHONK_DIR / track_id
        if direct_alt.exists():
            return direct_alt
        # Try downloading it
        downloaded = download_phonk_track(track_id)
        if downloaded:
            return downloaded
            
    tracks = list(PHONK_DIR.glob("*.mp3")) + list(PHONK_DIR.glob("*.wav"))
    if tracks:
        return random.choice(tracks)
    return None
