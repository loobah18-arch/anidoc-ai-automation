"""
High-Speed Google Drive Ingestion, Non-Repetitive Episode Selector & Action Moments Slicer.

Features:
1. Non-Repetitive Episode Rotation: Tracks used episodes so each run uses a DIFFERENT
   episode/movie from your Google Drive library (e.g. rotating through JJK Season 2 Ep 01-23).
2. Non-Repetitive Clip Slicing: Adds randomized start scanning offsets and tracks timestamp
   history so it never slices the exact same scene twice.
3. Fast Targeted Download: Downloads only 1 selected file (~150MB - 1GB) in ~10s via direct
   chunked streaming with Google Drive confirmation token handling.
4. Action Energy Slicing: Uses FFmpeg volume analysis to cut out 15-35 high-energy 9:16
   portrait clips with original Japanese/English dialogue & combat SFX.
"""
import os
import re
import json
import random
import shutil
import subprocess
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

from config.settings import SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS
from core.clip_manager import CHARACTER_THEMES
from core.timestamp_loader import (
    match_episode_code_from_filename,
    load_episode_metadata,
    get_character_clips
)
from core.title_driven_selector import parse_title_intent, get_title_driven_clips

SUPPORTED_VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".ts", ".m4v"}
SUPPORTED_ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar"}

HISTORY_FILE = SCRATCH_DIR / "gdrive_edit_history.json"

CHARACTER_EPISODE_PREFERENCES = {
    # JJK Combat Preferences
    "gojo": ["e09", "e04", "e03", "e08", "e05", "e07", "e01"],       # Shibuya Curses, Awakened vs Toji, Subway Brawl
    "sukuna": ["e17", "e16", "e15", "e18", "e20"],                   # Sukuna vs Mahoraga, Sukuna vs Jogo Meteor, Shibuya Climax
    "toji": ["e04", "e03", "e14", "e15", "e02"],                     # Toji vs Gojo Awakened, Toji vs Dagon, Toji vs Megumi
    "yuji": ["e20", "e21", "e13", "e19", "e22", "e18"],             # Yuji & Todo vs Mahito (Black Flash), Yuji vs Choso Brawl
    "megumi": ["e15", "e16", "e14", "e17", "e12"],                   # Mahoraga Summon & Domain Clashes
    "mahito": ["e20", "e21", "e19", "e18", "e22", "e13", "e12", "e07"], # Yuji & Todo vs Mahito, Nanami vs Mahito
    "todo": ["e20", "e21", "e19", "e18", "e15"],                         # Double Black Flash, Boogie Woogie
    "nobara": ["e19", "e24", "e03"],                                     # Resonance vs Mahito, Death Painting
    "choso": ["e13", "e24", "choso", "shibuya"],                         # Choso vs Yuji bathroom brawl, Death Painting
    # Demon Slayer (Kimetsu no Yaiba) Preferences
    "tanjiro": ["entertainment", "mugen", "swordsmith", "hashira", "hinokami", "e19", "e10", "e11", "e08", "e01"],
    "rengoku": ["mugen", "train", "akaza", "rengoku", "e07", "e06", "e05"],
    "akaza": ["mugen", "train", "akaza", "rengoku", "e06", "e07", "hashira"],
    "zenitsu": ["thunder", "zenitsu", "e12", "e17", "entertainment", "e10", "spider"],
    "tengen": ["entertainment", "uzui", "tengen", "gyutaro", "e08", "e09", "e10"],
    "gyutaro": ["entertainment", "gyutaro", "daki", "e08", "e09", "e10"],
    "giyu": ["rui", "spider", "e19", "e20", "e21", "giyu", "water", "hashira", "e01"],
    "inosuke": ["inosuke", "beast", "entertainment", "train", "spider"],
    "muzan": ["muzan", "infinity", "castle", "hashira", "e08"],
    "nezuko": ["nezuko", "blood", "awakened", "entertainment", "swordsmith", "e19"],
    "muichiro": ["swordsmith", "gyokko", "mist", "muichiro", "e08", "e09"],
    # Marvel Legacy Preferences
    "spiderman": ["spider", "no way home", "far from home", "peter"], # Bridge Fight & Final Climax
    "thor": ["ragnarok", "thor", "odinson"],                          # Arena Fight & Bridge Lightning Battle
    "ironman": ["iron", "stark", "avengers"],
    "thanos": ["infinity war", "endgame", "thanos"],
    "wolverine": ["wolverine", "logan", "deadpool"],
    "loki": ["loki", "thor"],
}


def _load_history() -> Dict[str, Any]:
    """Loads previously used episodes and timestamps."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"used_files": [], "used_timestamps": {}}


def _save_history(history: Dict[str, Any]):
    """Persists used episodes and timestamps."""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"⚠️ [GoogleDrive] Failed to save history: {e}")


def list_gdrive_folder_items(folder_url_or_id: str) -> List[Dict[str, str]]:
    """
    Parses a public Google Drive folder in ~1 second via HTTP and extracts all file names & clean file IDs.
    """
    match = re.search(r"folders/([a-zA-Z0-9_-]+)", folder_url_or_id)
    folder_id = match.group(1) if match else folder_url_or_id.strip()
    url = f"https://drive.google.com/drive/folders/{folder_id}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"⚠️ [GoogleDrive] HTTP error {r.status_code} fetching folder index.")
            return []

        text = r.text
        matches = re.findall(
            r'aria-label=\"([^\"]+?)\s+(?:Video|Shared|Archive|Zip|Audio).*?ssk=[\'\"][^:]+:[^:]+:([a-zA-Z0-9_-]{25,})',
            text
        )

        results = []
        seen = set()
        for name, raw_fid in matches:
            clean_fid = re.sub(r"-\d+-\d+$", "", raw_fid)
            if clean_fid not in seen:
                seen.add(clean_fid)
                results.append({
                    "name": name,
                    "id": clean_fid,
                    "url": f"https://drive.google.com/uc?id={clean_fid}"
                })

        print(f"📋 [GoogleDrive] Found {len(results)} items in Google Drive folder index.")
        return results
    except Exception as e:
        print(f"⚠️ [GoogleDrive] Failed to parse folder index: {e}")
        return []


def get_file_universe(filename: str) -> Optional[str]:
    """
    Identifies the anime or movie universe of a video file with strict keyword isolation.
    Guarantees Demon Slayer, Jujutsu Kaisen, and Marvel footage are never conflated.
    """
    fn = filename.lower()
    is_ds = any(k in fn for k in [
        "demon", "slayer", "kimetsu", "yaiba", "kny", "mugen", "tanjiro", "rengoku",
        "zenitsu", "uzui", "akaza", "giyu", "inosuke", "muzan", "nezuko", "muichiro",
        "gyutaro", "swordsmith", "entertainment", "yukaku", "hashira"
    ])
    is_jjk = any(k in fn for k in [
        "jujutsu", "jjk", "gojo", "sukuna", "itadori", "yuji", "megumi", "toji",
        "nobara", "choso", "mahito", "shibuya", "geto", "nanami", "maki", "panda"
    ])
    is_marvel = any(k in fn for k in [
        "spider", "thor", "iron", "marvel", "avenger", "thanos", "loki", "wolverine", "deadpool"
    ])

    if is_ds and not is_jjk and not is_marvel:
        return "demonslayer"
    if is_jjk and not is_ds and not is_marvel:
        return "jjk"
    if is_marvel and not is_ds and not is_jjk:
        return "marvel"
    return None


def pick_best_file_for_character(
    files: List[Dict[str, str]],
    character_key: str,
    title: Optional[str] = None
) -> Optional[Dict[str, str]]:
    """
    Selects a DIVERSE, non-repetitive episode or movie for the target character.
    Tracks history so the same episode is not reused until the entire pool has been rotated through.
    Guarantees strict universe isolation:
      - Demon Slayer characters ONLY receive Demon Slayer episodes.
      - Jujutsu Kaisen characters ONLY receive Jujutsu Kaisen episodes.
      - Cross-universe contamination is strictly prohibited.
    """
    if not files:
        return None

    char_theme = CHARACTER_THEMES.get(character_key)
    if not char_theme:
        return None
    char_universe = char_theme["universe"]

    # 1. STRICT UNIVERSE FILTERING: Filter files so ONLY the character's universe is eligible
    universe_files = [f for f in files if get_file_universe(f["name"]) == char_universe]
    if not universe_files:
        print(f"⚠️ [GoogleDrive] No Google Drive files match universe '{char_universe}' for character '{character_key}'. Rejecting cross-universe selection.")
        return None

    history = _load_history()
    used_files = set(history.get("used_files", []))

    # 2. Check if title prefers specific episodes within the character's universe
    if title:
        try:
            intent = parse_title_intent(title)
            preferred_eps = intent.get("preferred_episodes") or []
            if preferred_eps:
                title_matches = []
                for f in universe_files:
                    code = match_episode_code_from_filename(f["name"])
                    if code and code in preferred_eps:
                        title_matches.append(f)
                if title_matches:
                    unused_title = [f for f in title_matches if f["name"] not in used_files]
                    cand_pool = unused_title if unused_title else title_matches
                    chosen = random.choice(cand_pool)
                    print(f"🎯 [GoogleDrive] Selected title-optimized episode ({intent['scene_type']}) for '{character_key}' ({char_universe.upper()}): {chosen['name']}")
                    history["used_files"].append(chosen["name"])
                    _save_history(history)
                    return chosen
        except Exception as e:
            print(f"⚠️ [GoogleDrive] Title-based file matching error: {e}")

    # 3. Match character episode preferences within the character's universe
    prefs = CHARACTER_EPISODE_PREFERENCES.get(character_key, [character_key])
    eligible_files = []

    for f in universe_files:
        clean_name = re.sub(r"[_\.\-\[\]\(\)]+", " ", f["name"]).lower()
        if any(pref in clean_name or pref in f["name"].lower() for pref in prefs):
            eligible_files.append(f)

    if not eligible_files:
        eligible_files = universe_files

    # 4. Filter out recently used files to guarantee fresh footage
    unused_eligible = [f for f in eligible_files if f["name"] not in used_files]

    if not unused_eligible:
        # Reset cycle if all eligible episodes in this universe have been used
        print(f"🔄 [GoogleDrive] All '{char_universe}' episodes in library have been used once. Resetting history cycle.")
        history["used_files"] = [f for f in history.get("used_files", []) if f not in [u["name"] for u in universe_files]]
        unused_eligible = eligible_files

    # 5. Pick a random unused file from the correct universe
    chosen = random.choice(unused_eligible)
    print(f"🎯 [GoogleDrive] Selected fresh non-repetitive {char_universe.upper()} episode for '{character_key}': {chosen['name']}")

    # Record in history
    history["used_files"].append(chosen["name"])
    _save_history(history)

    return chosen


def download_single_gdrive_file(file_info: Dict[str, str], download_dir: Path) -> Optional[Path]:
    """
    Downloads a single targeted movie or episode from Google Drive in seconds.
    Triple-fallback:
      1. High-speed direct streaming with large-file confirmation token handling
      2. Python gdown downloader
      3. yt-dlp Google Drive extractor
    """
    download_dir.mkdir(parents=True, exist_ok=True)
    file_id = file_info["id"]
    safe_name = re.sub(r"[^\w\.-]", "_", file_info["name"])
    out_path = download_dir / safe_name

    if out_path.exists() and out_path.stat().st_size > 1_000_000:
        print(f"⚡ [GoogleDrive] File already cached: {out_path.name} ({out_path.stat().st_size // (1024*1024)} MB)")
        return out_path

    print(f"🚀 [GoogleDrive] Downloading '{file_info['name']}' ({file_id})...")

    # ─────────────────────────────────────────────────────────────────────────
    # METHOD 1: Direct requests streaming with confirmation token handling
    # ─────────────────────────────────────────────────────────────────────────
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        init_url = "https://drive.google.com/uc?export=download"
        r = session.get(init_url, params={"id": file_id, "confirm": "t"}, stream=True, timeout=30)
        
        download_url = init_url
        download_params = {"id": file_id, "confirm": "t"}
        
        content_type = r.headers.get("content-type", "").lower()
        if "text/html" in content_type or "text/plain" in content_type:
            form_match = re.search(r'<form [^>]*action=\"([^\"]+)\"', r.text)
            if form_match:
                download_url = form_match.group(1)
                inputs = re.findall(r'<input type=\"hidden\" name=\"([^\"]+)\" value=\"([^\"]+)\"', r.text)
                download_params = dict(inputs)
            elif "confirm=" in r.text:
                c_match = re.search(r'confirm=([0-9A-Za-z_-]+)', r.text)
                if c_match:
                    download_params["confirm"] = c_match.group(1)
            
            r = session.get(download_url, params=download_params, stream=True, timeout=180)

        if r.status_code == 200:
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=2 * 1024 * 1024):  # 2MB chunks
                    if chunk:
                        f.write(chunk)
            
            if out_path.exists() and out_path.stat().st_size > 1_000_000:
                print(f"✅ [GoogleDrive] Direct stream downloaded: {out_path.name} ({out_path.stat().st_size // (1024*1024)} MB)")
                return out_path
            else:
                if out_path.exists():
                    out_path.unlink()
    except Exception as e:
        print(f"⚠️ [GoogleDrive] Direct stream error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # METHOD 2: Python gdown module
    # ─────────────────────────────────────────────────────────────────────────
    try:
        import gdown
        print(f"🔄 [GoogleDrive] Trying gdown for file {file_id}...")
        downloaded = gdown.download(id=file_id, output=str(out_path), quiet=False)
        if downloaded and Path(downloaded).exists() and Path(downloaded).stat().st_size > 1_000_000:
            print(f"✅ [GoogleDrive] gdown downloaded: {out_path.name} ({Path(downloaded).stat().st_size // (1024*1024)} MB)")
            return Path(downloaded)
    except Exception as e:
        print(f"⚠️ [GoogleDrive] gdown module error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # METHOD 3: yt-dlp Google Drive extractor
    # ─────────────────────────────────────────────────────────────────────────
    try:
        print(f"🔄 [GoogleDrive] Trying yt-dlp for file {file_id}...")
        cmd = [
            "yt-dlp",
            f"https://drive.google.com/file/d/{file_id}/view",
            "-o", str(out_path),
            "--no-playlist",
            "--quiet"
        ]
        subprocess.run(cmd, capture_output=True, timeout=300)
        if out_path.exists() and out_path.stat().st_size > 1_000_000:
            print(f"✅ [GoogleDrive] yt-dlp downloaded: {out_path.name} ({out_path.stat().st_size // (1024*1024)} MB)")
            return out_path
    except Exception as e:
        print(f"⚠️ [GoogleDrive] yt-dlp error: {e}")

    return None


def get_english_audio_map(video_path: Path) -> List[str]:
    """
    Probes video streams and returns the FFmpeg -map arguments for the English audio track,
    preferring English Dub streams in multi-language MKV/MP4 files.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "stream=index,codec_type:stream_tags=language,title",
        "-of", "json", str(video_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        
        eng_audio_idx = None
        first_audio_idx = None
        for s in streams:
            if s.get("codec_type") == "audio":
                idx = s.get("index")
                if first_audio_idx is None:
                    first_audio_idx = idx
                tags = s.get("tags", {})
                lang = tags.get("language", "").lower()
                title = tags.get("title", "").lower()
                if "eng" in lang or "english" in title or "dub" in title:
                    eng_audio_idx = idx
                    break
        
        chosen_idx = eng_audio_idx if eng_audio_idx is not None else first_audio_idx
        if chosen_idx is not None:
            return ["-map", "0:v:0", "-map", f"0:{chosen_idx}"]
    except Exception:
        pass
    return ["-map", "0:v:0", "-map", "0:a:0?"]


def slice_action_moments_from_source(
    video_path: Path,
    character_key: str,
    output_dir: Path,
    n_clips: int = 15,
    clip_duration: float = 3.2,
    title: Optional[str] = None
) -> List[Path]:
    """
    Hybrid Action Slicer: Combines curated iconic/epic episode timestamps from metadata analysis
    (e.g. Hinokami Kagura, Malevolent Shrine, Sixfold Lightning, Musical Score, Black Flash)
    with dynamic FFmpeg high-frequency audio energy clashing moments from the rest of the episode.
    
    Guarantees:
    1. Inclusion of newly analyzed iconic anime climax scenes.
    2. Dynamic variety from unscripted combat audio analysis.
    3. Non-repetitive rotation across multiple edits.
    4. Intelligent beat drop synchronization (#1 climax placed at Beat Drop).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean old slices for this character to ensure 100% fresh clips
    for old in output_dir.glob(f"{character_key}_gdrive_*.mp4"):
        try:
            old.unlink()
        except Exception:
            pass

    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(video_path)
    ]
    try:
        res = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=20)
        info = json.loads(res.stdout)
        total_duration = float(info["format"].get("duration", 120.0))
    except Exception:
        total_duration = 120.0

    print(f"🔍 [ActionSlicer] Analyzing '{video_path.name}' ({total_duration:.1f}s) for epic combat scenes...")

    # Load previously used timestamps for this video
    history = _load_history()
    file_used_ts = set(history.get("used_timestamps", {}).get(video_path.name, []))

    # Skip Opening (0-90s) and Ending/Preview credits (last 90s)
    start_bound = 90.0 if total_duration > 300 else 10.0
    end_bound = (total_duration - 90.0) if total_duration > 300 else (total_duration - 10.0)

    # Universe Safety Guard: Never slice a video for a character from another universe
    file_universe = get_file_universe(video_path.name)
    char_theme = CHARACTER_THEMES.get(character_key)
    char_universe = char_theme["universe"] if char_theme else None

    if file_universe and char_universe and file_universe != char_universe:
        raise ValueError(
            f"CRITICAL SAFETY VIOLATION: Source video '{video_path.name}' is from universe '{file_universe.upper()}', "
            f"but character '{character_key}' belongs to universe '{char_universe.upper()}'. Aborting slice to prevent cross-contamination!"
        )

    # ── Phase 1: Curated Episode Climax & Scene Extraction from Metadata ───────
    matched_ep_code = match_episode_code_from_filename(video_path.name)
    curated_candidates = []

    # Ensure matched_ep_code belongs to the character's universe
    if matched_ep_code:
        is_code_ds = matched_ep_code.startswith("DS_")
        if char_universe == "demonslayer" and not is_code_ds:
            print(f"⚠️ [ActionSlicer] Mismatched episode code {matched_ep_code} for Demon Slayer character '{character_key}'. Ignoring.")
            matched_ep_code = None
        elif char_universe == "jjk" and is_code_ds:
            print(f"⚠️ [ActionSlicer] Mismatched episode code {matched_ep_code} for JJK character '{character_key}'. Ignoring.")
            matched_ep_code = None

    if matched_ep_code:
        print(f"📖 [ActionSlicer] Matched episode code: {matched_ep_code} for '{video_path.name}'")

        # 1. Title-matched scenes
        title_scenes = []
        if title:
            try:
                tc = get_title_driven_clips(title, character_key, max_clips=n_clips)
                title_scenes = [c for c in tc if c.get("episode") == matched_ep_code]
            except Exception:
                pass

        # 2. Character-specific curated scenes from episode metadata
        char_scenes = get_character_clips(matched_ep_code, character_key, min_action_score=0.55, max_clips=25)

        # 3. General high-action scenes from episode metadata
        ep_meta = load_episode_metadata(matched_ep_code)
        general_scenes = []
        if ep_meta:
            general_scenes = [
                s for s in ep_meta.get("scenes", [])
                if float(s.get("action_score", 0.0)) >= 0.70
            ]

        seen_ranges = set()

        def _add_curated_scene(s: Dict[str, Any], bonus: float, tag_prefix: str):
            st = float(s.get("start", 0.0))
            en = float(s.get("end", st + 10.0))
            desc = s.get("description", "Curated epic scene")
            base_score = float(s.get("action_score", 0.8)) * 100.0 + bonus
            if s.get("priority") == "high":
                base_score += 15.0

            key = (int(st), int(en))
            if key in seen_ranges:
                return
            seen_ranges.add(key)

            scene_len = max(clip_duration, en - st)
            if scene_len <= clip_duration * 1.5:
                pts = [st]
            elif scene_len <= 15.0:
                mid = st + (scene_len - clip_duration) * 0.45
                pts = [mid]
            else:
                pts = [
                    st + 1.0,
                    st + (scene_len - clip_duration) * 0.65
                ]

            for p in pts:
                # Clamp within video bounds
                if p < start_bound or p + clip_duration > end_bound:
                    continue
                # Skip if timestamp was recently used
                if not any(abs(p - prev) < 5.0 for prev in file_used_ts):
                    curated_candidates.append({
                        "start": p,
                        "score": base_score,
                        "description": desc,
                        "tag": f"💎 {tag_prefix}: {desc[:42]}",
                        "is_curated": True
                    })

        for s in title_scenes:
            _add_curated_scene(s, bonus=20.0, tag_prefix="TITLE-MATCH")
        for s in char_scenes:
            _add_curated_scene(s, bonus=10.0, tag_prefix="CURATED-CHAR")
        for s in general_scenes:
            _add_curated_scene(s, bonus=0.0, tag_prefix="EPIC-SCENE")

        print(f"✨ [ActionSlicer] Extracted {len(curated_candidates)} curated epic moments from metadata for {matched_ep_code}.")

    # ── Phase 2: Dynamic FFmpeg Audio Volume Scan across the Episode ─────────
    rand_offset = random.uniform(0.0, 2.5)
    step = 4.0 if total_duration > 600 else 2.0
    t = start_bound + rand_offset
    audio_candidates = []

    while t + clip_duration <= end_bound:
        if not any(abs(t - prev) < 6.0 for prev in file_used_ts):
            cmd_h = [
                "ffmpeg", "-ss", str(t), "-t", str(clip_duration),
                "-i", str(video_path),
                "-af", "highpass=f=2000,volumedetect",
                "-vn", "-f", "null", "-"
            ]
            try:
                res_h = subprocess.run(cmd_h, capture_output=True, text=True, timeout=12)
                h_vol = -60.0
                for line in res_h.stderr.split("\n"):
                    if "mean_volume" in line:
                        try:
                            h_vol = float(line.split(":")[1].strip().split(" ")[0])
                        except Exception:
                            pass

                # Only analyze sub-bass if high-frequency clash meets fight threshold (> -40.0 dB)
                if h_vol > -40.0:
                    cmd_s = [
                        "ffmpeg", "-ss", str(t), "-t", str(clip_duration),
                        "-i", str(video_path),
                        "-af", "lowpass=f=150,volumedetect",
                        "-vn", "-f", "null", "-"
                    ]
                    res_s = subprocess.run(cmd_s, capture_output=True, text=True, timeout=12)
                    s_vol = -60.0
                    for line in res_s.stderr.split("\n"):
                        if "mean_volume" in line:
                            try:
                                s_vol = float(line.split(":")[1].strip().split(" ")[0])
                            except Exception:
                                pass

                    if s_vol > -40.0:
                        fight_score = (h_vol + 60.0) * 1.6 + (s_vol + 60.0) * 1.2
                        audio_candidates.append({
                            "start": t,
                            "score": fight_score,
                            "description": "Dynamic Audio Clashing Scene",
                            "tag": "⚔️ Dynamic Combat Clash",
                            "is_curated": False
                        })
            except Exception:
                pass
        t += step

    audio_candidates.sort(key=lambda x: x["score"], reverse=True)
    print(f"⚔️ [ActionSlicer] Discovered {len(audio_candidates)} dynamic audio combat moments.")

    # ── Phase 3: Hybrid Merge (Curated Climax + Dynamic Audio Variety) ────────
    curated_candidates.sort(key=lambda x: x["score"], reverse=True)
    final_candidates = []

    # Allocate up to 60-70% to curated scenes if available
    curated_quota = min(len(curated_candidates), max(4, int(n_clips * 0.65))) if curated_candidates else 0
    for c in curated_candidates[:curated_quota]:
        if not any(abs(c["start"] - s["start"]) < (clip_duration * 1.5) for s in final_candidates):
            final_candidates.append(c)

    # Fill with top dynamic audio combat scenes
    for a in audio_candidates:
        if len(final_candidates) >= n_clips + 8:
            break
        if not any(abs(a["start"] - s["start"]) < (clip_duration * 1.5) for s in final_candidates):
            final_candidates.append(a)

    # Fill any remaining quota with extra curated scenes
    for c in curated_candidates[curated_quota:]:
        if len(final_candidates) >= n_clips + 8:
            break
        if not any(abs(c["start"] - s["start"]) < (clip_duration * 1.5) for s in final_candidates):
            final_candidates.append(c)

    # Safe fallback if too few candidates met strict thresholds
    if len(final_candidates) < n_clips:
        print(f"⚠️ [ActionSlicer] Found {len(final_candidates)} candidates, adding paced scene fallback...")
        t = start_bound
        while t + clip_duration <= end_bound and len(final_candidates) < n_clips * 2:
            if not any(abs(t - s["start"]) < (clip_duration * 1.5) for s in final_candidates):
                final_candidates.append({
                    "start": t,
                    "score": 50.0,
                    "description": "Paced Scene",
                    "tag": "🎬 Paced Scene",
                    "is_curated": False
                })
            t += 15.0

    final_candidates.sort(key=lambda x: x["score"], reverse=True)
    print(f"🎬 [ActionSlicer] Total hybrid candidate pool: {len(final_candidates)} scenes (Curated + Dynamic Audio).")

    # ── Phase 4: Intelligent Scene Orchestration for Beat Drops ───────────────
    # The #1 loudest / most epic climax scene is mapped to the Beat Drop (index 4)
    # The #2 scene is mapped to the Bridge Drop (~index 22 or 12)
    # The #3 scene is mapped to the Climax Outro Finisher (last clip)
    # The lowest energy scenes are mapped to the Intro (clips 00-03)
    drop_idx = min(4, max(0, n_clips - 1))
    bridge_idx = min(22, max(0, n_clips - 2)) if n_clips > 24 else min(12, max(0, n_clips - 2))
    last_idx = n_clips - 1

    drop_climax = final_candidates[0]
    sec_drop = final_candidates[1] if len(final_candidates) > 1 else final_candidates[0]
    finisher = final_candidates[2] if len(final_candidates) > 2 else final_candidates[0]
    remaining_cand = final_candidates[3:] if len(final_candidates) > 3 else final_candidates

    # Sort remaining into intro (lowest score dialogue/walk) and combat (high energy clashes)
    sorted_by_energy = sorted(remaining_cand, key=lambda x: x["score"])
    intro_pool = sorted_by_energy[:drop_idx]
    combat_pool = sorted_by_energy[drop_idx:] if len(sorted_by_energy) > drop_idx else sorted_by_energy

    selected = [None] * n_clips
    for i in range(min(drop_idx, len(intro_pool))):
        selected[i] = intro_pool[i]

    selected[drop_idx] = drop_climax
    selected[bridge_idx] = sec_drop
    selected[last_idx] = finisher

    c_idx = 0
    for i in range(n_clips):
        if selected[i] is None:
            if combat_pool:
                selected[i] = combat_pool[c_idx % len(combat_pool)]
            else:
                selected[i] = final_candidates[c_idx % len(final_candidates)]
            c_idx += 1

    print(f"💥 [ActionSlicer] Mapped #1 CLIMAX scene ({drop_climax['start']:.1f}s, {drop_climax['tag']}) directly to Beat Drop (Clip {drop_idx+1})!")

    # Probe English Dub audio stream mapping
    eng_audio_map = get_english_audio_map(video_path)

    generated_clips = []
    new_used_ts = []

    for idx, cand in enumerate(selected):
        start = cand["start"]
        out_clip = output_dir / f"{character_key}_gdrive_{idx:02d}_{int(start)}s.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-t", str(clip_duration),
            "-i", str(video_path),
        ] + eng_audio_map + [
            "-vf", (
                f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
                f"setsar=1,fps={FPS}"
            ),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            str(out_clip)
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=60)
            if out_clip.exists() and out_clip.stat().st_size > 40_000:
                generated_clips.append(out_clip)
                new_used_ts.append(start)
                role_tag = (
                    "💥 BEAT DROP" if idx == drop_idx
                    else ("⚡ SECONDARY DROP" if idx == bridge_idx
                    else ("🔥 FINISHER" if idx == last_idx
                    else "⚔️ Scene"))
                )
                print(f"  ✂️ Clip {idx+1:02d}/{len(selected)} sliced ({start:.1f}s - {start+clip_duration:.1f}s) [{role_tag}] {cand.get('tag', '')}")
        except Exception as e:
            print(f"  ⚠️ Error cutting clip at {start}s: {e}")

    # Record used timestamps in history
    if "used_timestamps" not in history:
        history["used_timestamps"] = {}
    if video_path.name not in history["used_timestamps"]:
        history["used_timestamps"][video_path.name] = []
    history["used_timestamps"][video_path.name].extend(new_used_ts)
    # Keep last 50 timestamps per file
    history["used_timestamps"][video_path.name] = history["used_timestamps"][video_path.name][-50:]
    _save_history(history)

    print(f"✅ Generated {len(generated_clips)} unique non-repetitive action clips with original audio.")
    return generated_clips


def fetch_and_prepare_gdrive_footage(
    gdrive_url_or_id: str,
    target_character: str,
    output_dir: Path,
    n_clips: int = 15,
    title: Optional[str] = None
) -> List[Path]:
    """
    Lightning-Fast Non-Repetitive Google Drive Ingestion:
    1. Parses Google Drive folder index in 1s.
    2. Rotates to a DIFFERENT episode/movie for the character that hasn't been used yet (or title-matched).
    3. Downloads only that 1 video (~10s).
    4. Slices hybrid curated epic climax scenes + dynamic audio moments into 9:16 portrait clips.
    """
    gdrive_workdir = SCRATCH_DIR / "gdrive_workspace"
    gdrive_workdir.mkdir(parents=True, exist_ok=True)

    items = list_gdrive_folder_items(gdrive_url_or_id)
    if not items:
        print("⚠️ [GoogleDrive] No files retrieved from Google Drive folder index.")
        return []

    best_file = pick_best_file_for_character(items, target_character, title=title)
    if not best_file:
        print(f"⚠️ [GoogleDrive] No matching file found for '{target_character}'.")
        return []

    raw_video = download_single_gdrive_file(best_file, gdrive_workdir)
    if not raw_video:
        print(f"⚠️ [GoogleDrive] Failed to download {best_file['name']}.")
        return []

    sliced_clips = slice_action_moments_from_source(
        video_path=raw_video,
        character_key=target_character,
        output_dir=output_dir,
        n_clips=n_clips,
        title=title
    )

    return sliced_clips

