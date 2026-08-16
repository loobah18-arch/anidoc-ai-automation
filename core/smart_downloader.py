"""
Smart Multi-Source Clip Downloader for AniDoc.
Implements intelligent fallback chain:
  1. yt-dlp  → YouTube/TikTok scenepacks (logless, character-specific)
  2. Archive.org API → public domain films and anime OVAs
  3. Pixabay API → cinematic stock action footage as last resort

Inspired by OpenCut's media import approach — brings in diverse, high-quality
clips from multiple sources so every edit is visually distinct.
"""
import os
import json
import random
import shutil
import urllib.request
import urllib.parse
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from config.settings import MARVEL_DIR, JJK_DIR, SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT

# ─────────────────────────────────────────────────────────────
# ARCHIVE.ORG SEARCH (Public Domain / CC — No API Key Required)
# ─────────────────────────────────────────────────────────────
ARCHIVE_CHARACTER_QUERIES = {
    "spiderman":   "spider-man animated classic cartoon",
    "ironman":     "iron man animated marvel",
    "thor":        "thor norse mythology film",
    "gojo":        "jujutsu kaisen anime",
    "sukuna":      "jujutsu kaisen sukuna",
    "wolverine":   "wolverine x-men animated",
    "thanos":      "thanos marvel animated",
    "loki":        "loki asgard myth film",
    "gojo":        "jujutsu kaisen gojo",
    "toji":        "jujutsu kaisen toji",
    "yuji":        "yuji itadori jujutsu kaisen",
    "megumi":      "megumi fushiguro jujutsu",
}


def search_archive_org(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Search Internet Archive for video items matching query."""
    encoded = urllib.parse.quote(query)
    url = (
        f"https://archive.org/advancedsearch.php"
        f"?q={encoded}+mediatype:movies"
        f"&fl[]=identifier,title,description,downloads,mediatype"
        f"&sort[]=downloads+desc"
        f"&rows={max_results}&output=json"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AniDoc/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data.get("response", {}).get("docs", [])
    except Exception as e:
        print(f"⚠️  [Archive.org] Search error: {e}")
        return []


def download_archive_clip(identifier: str, output_dir: Path, prefix: str) -> Optional[Path]:
    """Downloads the first MP4 file from an Archive.org item."""
    try:
        meta_url = f"https://archive.org/metadata/{identifier}"
        req = urllib.request.Request(meta_url, headers={"User-Agent": "AniDoc/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            meta = json.loads(resp.read().decode())

        for f in meta.get("files", []):
            fname = f.get("name", "")
            if fname.lower().endswith(".mp4") and int(f.get("size", 0)) < 200_000_000:
                dl_url = f"https://archive.org/download/{identifier}/{fname}"
                out_path = output_dir / f"{prefix}_archive_{identifier[:12]}.mp4"
                print(f"📥 [Archive.org] Downloading: {fname} → {out_path.name}")
                urllib.request.urlretrieve(dl_url, str(out_path))
                if out_path.exists() and out_path.stat().st_size > 100_000:
                    return out_path
    except Exception as e:
        print(f"⚠️  [Archive.org] Download error ({identifier}): {e}")
    return None


def fetch_from_archive_org(character_key: str, output_dir: Path, max_clips: int = 3) -> List[Path]:
    """Fetches character-specific clips from Internet Archive."""
    query = ARCHIVE_CHARACTER_QUERIES.get(character_key, f"{character_key} animation action")
    print(f"🏛️  [Archive.org] Searching: '{query}'...")
    results = search_archive_org(query, max_results=max_clips + 3)

    clips = []
    for item in results[:max_clips + 2]:
        ident = item.get("identifier", "")
        if not ident:
            continue
        clip = download_archive_clip(ident, output_dir, character_key)
        if clip:
            clips.append(clip)
        if len(clips) >= max_clips:
            break
    return clips


# ─────────────────────────────────────────────────────────────
# PIXABAY API (Free Stock Video — Requires Free API Key)
# ─────────────────────────────────────────────────────────────
PIXABAY_ACTION_QUERIES = [
    "martial arts fight action",
    "superhero power effect",
    "explosion fire cinematic",
    "energy beam particle",
    "dark fantasy warrior",
    "lightning thunder power",
    "anime sword fight"
]


def fetch_from_pixabay(query: str, output_dir: Path, max_clips: int = 3) -> List[Path]:
    """Downloads vertical action footage from Pixabay (free tier)."""
    api_key = os.environ.get("PIXABAY_API_KEY", "")
    if not api_key:
        print("⚠️  [Pixabay] PIXABAY_API_KEY not set in environment. Skipping Pixabay fetch.")
        return []

    encoded_q = urllib.parse.quote(query)
    url = (
        f"https://pixabay.com/api/videos/"
        f"?key={api_key}&q={encoded_q}&per_page=10&video_type=film&order=popular"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AniDoc/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"⚠️  [Pixabay] API error: {e}")
        return []

    clips = []
    hits = data.get("hits", [])
    random.shuffle(hits)
    for hit in hits[:max_clips]:
        videos = hit.get("videos", {})
        video_url = (
            videos.get("large", {}).get("url")
            or videos.get("medium", {}).get("url")
            or videos.get("small", {}).get("url")
        )
        if not video_url:
            continue
        out_path = output_dir / f"{output_dir.name}_pixabay_{hit['id']}.mp4"
        try:
            urllib.request.urlretrieve(video_url, str(out_path))
            if out_path.exists() and out_path.stat().st_size > 50_000:
                clips.append(out_path)
                print(f"🎨 [Pixabay] Downloaded: {out_path.name}")
        except Exception as e:
            print(f"⚠️  [Pixabay] Download error: {e}")
    return clips


# ─────────────────────────────────────────────────────────────
# PEXELS API (Free Stock Video — Requires Free API Key)
# ─────────────────────────────────────────────────────────────
def fetch_from_pexels(query: str, output_dir: Path, max_clips: int = 3) -> List[Path]:
    """Downloads vertical portrait action footage from Pexels."""
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        print("⚠️  [Pexels] PEXELS_API_KEY not set. Skipping Pexels fetch.")
        return []

    url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&orientation=portrait&per_page=15"
    try:
        req = urllib.request.Request(url, headers={
            "Authorization": api_key,
            "User-Agent": "AniDoc/1.0"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"⚠️  [Pexels] API error: {e}")
        return []

    clips = []
    videos = data.get("videos", [])
    random.shuffle(videos)
    for vid in videos[:max_clips]:
        # Pick best quality available
        vid_files = sorted(vid.get("video_files", []), key=lambda x: x.get("width", 0), reverse=True)
        for vf in vid_files:
            if vf.get("file_type", "").startswith("video"):
                dl_url = vf["link"]
                out_path = output_dir / f"{output_dir.name}_pexels_{vid['id']}.mp4"
                try:
                    urllib.request.urlretrieve(dl_url, str(out_path))
                    if out_path.exists() and out_path.stat().st_size > 50_000:
                        clips.append(out_path)
                        print(f"📹 [Pexels] Downloaded: {out_path.name}")
                    break
                except Exception as e:
                    print(f"⚠️  [Pexels] Download error: {e}")
    return clips


# ─────────────────────────────────────────────────────────────
# YT-DLP MULTI-QUERY DOWNLOADER (Primary Source)
# ─────────────────────────────────────────────────────────────
from core.public_api_fetcher import (
    MULTI_CLIP_CATALOG,
    slice_scenepack_into_clips,
    fetch_character_scenepack
)


def yt_dlp_download_clip(query: str, output_dir: Path, prefix: str) -> Optional[Path]:
    """Downloads a single video via yt-dlp search query."""
    if not shutil.which("yt-dlp"):
        return None

    temp = SCRATCH_DIR / f"raw_{prefix}_{random.randint(1000, 9999)}.mp4"
    cmd = [
        "yt-dlp",
        "--extractor-args", "youtube:player_client=android,web",
        "-f", "b[height<=1080][ext=mp4]/b[ext=mp4]/b",
        "-o", str(temp),
        f"ytsearch1:{query}",
        "--max-downloads", "1",
        "--no-playlist",
        "--quiet"
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=120)
        if temp.exists() and temp.stat().st_size > 100_000:
            return temp
    except Exception as e:
        print(f"⚠️  [yt-dlp] Download error: {e}")
    return None


# ─────────────────────────────────────────────────────────────
# SMART MULTI-SOURCE DOWNLOADER (Full Fallback Chain)
# ─────────────────────────────────────────────────────────────
def smart_fetch_clips(
    character_key: str,
    universe_dir: Path,
    max_clips: int = 10,
    use_archive: bool = True,
    use_pixabay: bool = True,
    use_pexels: bool = True
) -> List[Path]:
    """
    Fetches clips using intelligent multi-source fallback:
    1. yt-dlp YouTube scenepack (primary, character-specific)
    2. Archive.org (classic anime/movie footage, public domain)
    3. Pixabay stock footage (cinematic action B-roll)
    4. Pexels stock footage (portrait action clips)

    Each source uses random query rotation for maximum visual diversity.
    """
    clips: List[Path] = []

    # ── Source 1: yt-dlp YouTube (primary)
    catalog = MULTI_CLIP_CATALOG.get(character_key, [f"{character_key} 4K anime edit scenepack logless"])
    query = random.choice(catalog)
    print(f"🎬 [SmartFetch] yt-dlp → '{query}'")
    raw = yt_dlp_download_clip(query, universe_dir, character_key)
    if raw:
        sliced = slice_scenepack_into_clips(raw, universe_dir, character_key, seg_duration=2.4, max_clips=max_clips)
        clips.extend(sliced)
        raw.unlink(missing_ok=True)

    if len(clips) < max_clips // 2 and use_archive:
        # ── Source 2: Archive.org (secondary)
        print(f"🏛️  [SmartFetch] Archive.org fallback...")
        archive_clips = fetch_from_archive_org(character_key, universe_dir, max_clips=3)
        for ac in archive_clips:
            sliced = slice_scenepack_into_clips(ac, universe_dir, character_key + "_arch", seg_duration=2.4, max_clips=3)
            clips.extend(sliced)

    if len(clips) < max_clips // 3 and use_pixabay:
        # ── Source 3: Pixabay (tertiary, generic action)
        q = random.choice(PIXABAY_ACTION_QUERIES)
        print(f"🎨 [SmartFetch] Pixabay fallback → '{q}'")
        pix_clips = fetch_from_pixabay(q, universe_dir, max_clips=4)
        clips.extend(pix_clips)

    if len(clips) < 3 and use_pexels:
        # ── Source 4: Pexels (last resort)
        print(f"📹 [SmartFetch] Pexels fallback...")
        pex_clips = fetch_from_pexels("dark fantasy action fight warrior", universe_dir, max_clips=4)
        clips.extend(pex_clips)

    print(f"✅ [SmartFetch] Total clips fetched: {len(clips)}")
    return clips
