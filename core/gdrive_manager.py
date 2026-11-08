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
import collections
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
from core.scene_scorer import SceneScorer

SUPPORTED_VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".ts", ".m4v"}
SUPPORTED_ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar"}

HISTORY_FILE = Path(".agents/data/gdrive_history.json")
FALLBACK_HISTORY_FILE = SCRATCH_DIR / "gdrive_edit_history.json"

CHARACTER_EPISODE_PREFERENCES = {
    # JJK Combat Preferences
    "gojo": ["s02e09", "s02e04", "s01e07", "s02e03", "s02e08", "s02e05", "gojo"],       # Shibuya Curses, Awakened vs Toji, Subway Brawl (S1 & S2 ONLY)
    "sukuna": ["s02e17", "s02e16", "s02e15", "s01e04", "s01e05", "sukuna"],             # Sukuna vs Mahoraga, Sukuna vs Jogo Meteor, Shibuya Climax (S2)
    "toji": ["s02e04", "s02e03", "s02e14", "s02e15", "toji"],                           # Toji vs Gojo Awakened, Toji vs Dagon, Toji vs Megumi (S2 ONLY)
    "yuta": ["s03e01", "s03e02", "yuta", "okkotsu"],                                     # Yuta Execution of Yuji, Sendai Colony (S3 ONLY)
    "yuji": ["s02e21", "s02e20", "s03e01", "s03e02", "s02e13", "s01e24", "s01e19"],     # Black Flash Climax, Yuta vs Yuji, Choso Brawl (S1-S3)
    "choso": ["s03e01", "s03e02", "s02e13", "s01e24", "choso"],                          # Choso vs Naoya speed battle (S3), Choso vs Yuji (S2)
    "maki": ["s03e05", "s03e06", "s02e14", "s01e17", "maki"],                           # Zen'in Clan massacre (S3), Dagon clash (S2)
    "megumi": ["s02e15", "s02e16", "s02e14", "s01e05", "megumi"],                       # Mahoraga Summon & Domain Clashes
    "mahito": ["s02e21", "s02e20", "s02e19", "s02e18", "s02e13", "s01e13", "mahito"],   # Yuji & Todo vs Mahito, Nanami vs Mahito
    "todo": ["s02e21", "s02e20", "s02e19", "s02e18", "s01e20", "todo"],                 # Double Black Flash, Boogie Woogie
    "nobara": ["s02e19", "s01e24", "s01e03", "nobara"],                                 # Resonance vs Mahito, Death Painting
    # Demon Slayer (Kimetsu no Yaiba) Preferences - Prioritizes top combat episodes (Hinokami Kagura, Entertainment District, Mugen Train)
    "tanjiro": ["hinokami", "e19", "entertainment", "mugen", "swordsmith", "hashira", "e10", "e11", "e08"],
    "rengoku": ["s02e06", "s02e07", "s02_e06", "s02_e07", "mugen", "train", "akaza", "rengoku"],
    "akaza": ["s02e06", "s02e07", "s02_e06", "s02_e07", "mugen", "train", "akaza", "rengoku"],
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
    for p in [HISTORY_FILE, FALLBACK_HISTORY_FILE]:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {"used_files": [], "used_timestamps": {}}


def _save_history(history: Dict[str, Any]):
    """Persists used episodes and timestamps."""
    for p in [HISTORY_FILE, FALLBACK_HISTORY_FILE]:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
            break
        except Exception as e:
            print(f"⚠️ [GoogleDrive] Notice saving history to {p}: {e}")


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
            if clean_fid not in seen and not name.lower().startswith(("[delete", "_deleted")):
                seen.add(clean_fid)
                results.append({
                    "name": name,
                    "id": clean_fid,
                    "url": f"https://drive.google.com/uc?id={clean_fid}"
                })

        # Multi-page fallback: Google Drive web SSR caps at 50 items. Use gdown to fetch full folder index.
        if len(results) < 60:
            try:
                import gdown
                gdown_files = gdown.download_folder(id=folder_id, skip_download=True, quiet=True)
                for gf in gdown_files:
                    path_str = getattr(gf, "path", str(gf))
                    fid = getattr(gf, "id", "")
                    fname = Path(path_str).name
                    if fid and fname not in seen and not fname.lower().startswith(("[delete", "_deleted")):
                        seen.add(fname)
                        results.append({
                            "name": fname,
                            "id": fid,
                            "url": f"https://drive.google.com/uc?id={fid}"
                        })
            except Exception:
                pass

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

    # Dynamic Multi-Anime Universe Identification
    try:
        from core.auto_cataloger import parse_anime_identity
        parsed = parse_anime_identity(filename)
        return parsed.get("universe")
    except Exception:
        return None


def pick_character_episodes(
    files: List[Dict[str, str]],
    character_key: str,
    max_episodes: int = 1,
    title: Optional[str] = None,
    target_episode: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Selects up to max_episodes diverse, non-repetitive episodes/movies for the character.
    Guarantees single cohesive battle per Short (max_episodes=1 default) to avoid
    jarring era/visual clashes, unless explicitly Rengoku Mugen Train continuous arc (S02E06+S02E07).
    Supports:
      - Explicit target_episode selection (CLI/workflow parameter)
      - Title-driven episode routing
      - Autonomous rotation across all episodes in the Google Drive library
    """
    if not files:
        return []

    char_theme = CHARACTER_THEMES.get(character_key)
    if not char_theme:
        from core.clip_manager import ensure_character_theme
        char_theme = ensure_character_theme(character_key)
    char_universe = char_theme["universe"]

    universe_files = [
        f for f in files
        if get_file_universe(f["name"]) == char_universe
        and any(f["name"].lower().endswith(ext) for ext in SUPPORTED_VIDEO_EXTS)
    ]
    if not universe_files:
        print(f"⚠️ [GoogleDrive] No Google Drive video files match universe '{char_universe}' for character '{character_key}'.")
        return []

    # Clean pool of spam / piracy / corrupt files (keeps English-tagged library releases)
    clean_pool = [
        f for f in universe_files
        if not any(b in f["name"].lower() for b in ["hindi", "pikahd"])
    ]
    if clean_pool:
        universe_files = clean_pool

    # 1. Direct explicit episode targeting (CLI --episode or config)
    if target_episode:
        ep_norm = target_episode.lower().strip()
        matched = []
        for f in universe_files:
            fn = f["name"].lower()
            code = (match_episode_code_from_filename(f["name"]) or "").lower()
            if ep_norm in fn or ep_norm in code or ep_norm.replace("_", "") in fn.replace("_", ""):
                matched.append(f)
        if matched:
            print(f"🎯 [GoogleDrive] Explicit Episode Matched: {[m['name'] for m in matched[:max_episodes]]}")
            return matched[:max_episodes]
        else:
            print(f"⚠️ [GoogleDrive] Target episode '{target_episode}' not found in clean pool for {char_universe}. Falling back to smart selector.")

    # 2. Check title-driven preferred episodes
    history = _load_history()
    used_files = set(history.get("used_files", []))

    if title:
        try:
            intent = parse_title_intent(title)
            preferred_eps = intent.get("preferred_episodes") or []
            if preferred_eps:
                title_matches = []
                for ep_pref in preferred_eps:
                    for f in universe_files:
                        code = match_episode_code_from_filename(f["name"])
                        if code == ep_pref and f not in title_matches:
                            title_matches.append(f)
                if title_matches:
                    unused_title = [f for f in title_matches if f["name"] not in used_files]
                    chosen_title = unused_title if unused_title else title_matches
                    print(f"🎯 [GoogleDrive] Title-matched episode selection for '{intent['scene_type']}': {[c['name'] for c in chosen_title[:max_episodes]]}")
                    return chosen_title[:max_episodes]
        except Exception as e:
            print(f"⚠️ [GoogleDrive] Title episode intent resolution notice: {e}")

    # 3. Special multi-episode pairs for continuous anime battles:
    # Rengoku: S02E06 + S02E07 (the only legitimate continuous 2-part battle in library)
    if character_key == "rengoku" and max_episodes >= 2:
        e6 = next((f for f in universe_files if "s02_e06" in f["name"].lower() or "s02e06" in f["name"].lower()), None)
        e7 = next((f for f in universe_files if "s02_e07" in f["name"].lower() or "s02e07" in f["name"].lower()), None)
        chosen = []
        if e6:
            chosen.append(e6)
        if e7 and len(chosen) < max_episodes:
            chosen.append(e7)
        if chosen:
            print(f"🎯 [GoogleDrive] Multi-Episode Selection for Rengoku: {[c['name'] for c in chosen]}")
            return chosen

    # 4. Universal multi-episode rotation across ALL available episodes for the character / universe
    best = pick_best_file_for_character(universe_files, character_key, title=title, target_episode=target_episode)
    if not best:
        return []

    chosen_list = [best]
    if max_episodes > 1:
        other_candidates = [
            f for f in universe_files
            if f["name"] != best["name"] and (
                any(p in f["name"].lower() for p in CHARACTER_EPISODE_PREFERENCES.get(character_key, [])) or
                character_key in f["name"].lower()
            )
        ]
        if not other_candidates:
            other_candidates = [f for f in universe_files if f["name"] != best["name"]]
        unused_others = [f for f in other_candidates if f["name"] not in used_files]
        cand_pool = unused_others if unused_others else other_candidates
        if cand_pool:
            chosen_list.append(random.choice(cand_pool))

    return chosen_list


def pick_best_file_for_character(
    files: List[Dict[str, str]],
    character_key: str,
    title: Optional[str] = None,
    target_episode: Optional[str] = None
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

    # 1. STRICT UNIVERSE FILTERING: Filter files so ONLY valid video files from the character's universe are eligible
    universe_files = [
        f for f in files
        if get_file_universe(f["name"]) == char_universe
        and any(f["name"].lower().endswith(ext) for ext in SUPPORTED_VIDEO_EXTS)
    ]
    if not universe_files:
        print(f"⚠️ [GoogleDrive] No Google Drive video files match universe '{char_universe}' for character '{character_key}'. Rejecting cross-universe selection.")
        return None

    # Quality Gate: Filter out spam / piracy files, and filter 480p low-res only when higher res (720p/1080p) exists
    has_high_res = any(any(q in f["name"].lower() for q in ["1080p", "720p", "hdr", "bluray", "mkv"]) for f in universe_files)
    clean_pool = [
        f for f in universe_files
        if not any(b in f["name"].lower() for b in ["hindi", "pikahd"])
        and (not has_high_res or "480p" not in f["name"].lower())
    ]
    if clean_pool:
        universe_files = clean_pool

    # 1.1 Direct explicit episode targeting (CLI --episode or config)
    if target_episode:
        ep_norm = target_episode.lower().strip()
        for f in universe_files:
            fn = f["name"].lower()
            code = (match_episode_code_from_filename(f["name"]) or "").lower()
            if ep_norm in fn or ep_norm in code or ep_norm.replace("_", "") in fn.replace("_", ""):
                print(f"🎯 [GoogleDrive] Explicit Episode Selection: {f['name']}")
                return f

    # Character Presence Verification: If episode metadata exists, guarantee character appears
    verified_files = []
    for f in universe_files:
        code = match_episode_code_from_filename(f["name"])
        if code:
            meta = load_episode_metadata(code)
            if meta:
                chars = [c.get("name", "").lower() for c in meta.get("characters", [])]
                scenes = meta.get("scenes", [])
                in_scenes = any(character_key.lower() in [c.lower() for c in s.get("characters_present", [])] for s in scenes)
                if character_key.lower() in chars or in_scenes:
                    verified_files.append(f)
    if verified_files:
        universe_files = verified_files

    history = _load_history()
    used_files = set(history.get("used_files", []))

    # 1.5 Rengoku pre-fight preference (only if unused in current rotation)
    if character_key == "rengoku":
        s02e06_match = next((f for f in universe_files if ("s02_e06" in f["name"].lower() or "s02e06" in f["name"].lower()) and f["name"] not in used_files), None)
        if s02e06_match:
            print(f"🎯 [GoogleDrive] Selected Mugen Train S02E06 for Rengoku pre-fight confrontation: {s02e06_match['name']}")
            history["used_files"].append(s02e06_match["name"])
            _save_history(history)
            return s02e06_match

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
                    if unused_title:
                        chosen = random.choice(unused_title)
                        print(f"🎯 [GoogleDrive] Selected fresh title-optimized episode ({intent['scene_type']}) for '{character_key}' ({char_universe.upper()}): {chosen['name']}")
                        history["used_files"].append(chosen["name"])
                        _save_history(history)
                        return chosen
                    else:
                        print(f"ℹ️ [GoogleDrive] All title-matched episodes for '{intent['scene_type']}' already used in current cycle. Falling back to diverse episode rotation.")
        except Exception as e:
            print(f"⚠️ [GoogleDrive] Title-based file matching error: {e}")

    # 3. Match character episode preferences in strict priority order
    prefs = CHARACTER_EPISODE_PREFERENCES.get(character_key, [character_key])
    eligible_files = []

    for pref in prefs:
        pref_compact = re.sub(r"[^a-z0-9]", "", pref.lower())
        for f in universe_files:
            clean_name = re.sub(r"[_\.\-\[\]\(\)]+", " ", f["name"]).lower()
            compact_name = re.sub(r"[^a-z0-9]", "", f["name"].lower())
            if (pref in clean_name or pref_compact in compact_name or pref in f["name"].lower()) and f not in eligible_files:
                eligible_files.append(f)
        if len(eligible_files) >= 3:
            # Top-tier preference matches found (e.g. Hinokami Kagura or Shibuya Climax)
            break

    if not eligible_files:
        eligible_files = universe_files

    # 4. Filter out recently used files to guarantee fresh footage
    unused_eligible = [f for f in eligible_files if f["name"] not in used_files]

    if not unused_eligible:
        # Reset cycle if all eligible episodes in this universe have been used
        print(f"🔄 [GoogleDrive] All '{character_key}' episodes in library have been used once. Resetting history cycle.")
        history["used_files"] = [f for f in history.get("used_files", []) if f not in [u["name"] for u in eligible_files]]
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

    min_valid_bytes = 15_000_000  # Minimum 15MB to ensure full episode footage, not truncated preview uploads

    if out_path.exists() and out_path.stat().st_size > min_valid_bytes:
        print(f"⚡ [GoogleDrive] File already cached: {out_path.name} ({out_path.stat().st_size // (1024*1024)} MB)")
        return out_path
    elif out_path.exists():
        out_path.unlink(missing_ok=True)

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
            
            if out_path.exists() and out_path.stat().st_size > min_valid_bytes:
                print(f"✅ [GoogleDrive] Direct stream downloaded: {out_path.name} ({out_path.stat().st_size // (1024*1024)} MB)")
                return out_path
            else:
                if out_path.exists():
                    print(f"⚠️ [GoogleDrive] File '{out_path.name}' is only {out_path.stat().st_size // (1024*1024)} MB (incomplete/truncated upload < 15MB). Discarding.")
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
        if downloaded and Path(downloaded).exists() and Path(downloaded).stat().st_size > min_valid_bytes:
            print(f"✅ [GoogleDrive] gdown downloaded: {out_path.name} ({Path(downloaded).stat().st_size // (1024*1024)} MB)")
            return Path(downloaded)
        elif downloaded and Path(downloaded).exists():
            print(f"⚠️ [GoogleDrive] File '{out_path.name}' via gdown is only {Path(downloaded).stat().st_size // (1024*1024)} MB (< 15MB). Discarding.")
            Path(downloaded).unlink(missing_ok=True)
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
        if out_path.exists() and out_path.stat().st_size > min_valid_bytes:
            print(f"✅ [GoogleDrive] yt-dlp downloaded: {out_path.name} ({out_path.stat().st_size // (1024*1024)} MB)")
            return out_path
        elif out_path.exists():
            print(f"⚠️ [GoogleDrive] File '{out_path.name}' via yt-dlp is only {out_path.stat().st_size // (1024*1024)} MB (< 15MB). Discarding.")
            out_path.unlink(missing_ok=True)
    except Exception as e:
        print(f"⚠️ [GoogleDrive] yt-dlp error: {e}")

    return None


def get_japanese_audio_map(video_path: Path) -> List[str]:
    """
    Probes video streams and returns the FFmpeg -map arguments for the original Japanese audio track,
    preferring Japanese (jpn/japanese/jap/nihongo) streams in multi-language MKV/MP4 files.
    Avoids English/dubbed audio tracks to guarantee authentic anime voice acting.
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
        
        jpn_audio_a_idx = None
        first_audio_a_idx = None
        audio_count = 0
        for s in streams:
            if s.get("codec_type") == "audio":
                if first_audio_a_idx is None:
                    first_audio_a_idx = audio_count
                tags = s.get("tags", {})
                lang = tags.get("language", "").lower()
                title = tags.get("title", "").lower()
                if any(k in lang or k in title for k in ["jpn", "japanese", "jap", "nihongo"]):
                    jpn_audio_a_idx = audio_count
                    break
                audio_count += 1
        
        chosen_a_idx = jpn_audio_a_idx if jpn_audio_a_idx is not None else first_audio_a_idx
        if chosen_a_idx is not None:
            return ["-map", "0:v:0", "-map", f"0:a:{chosen_a_idx}?"]
    except Exception:
        pass
    return ["-map", "0:v:0", "-map", "0:a:0?"]


# Backward-compatible alias
get_english_audio_map = get_japanese_audio_map


def is_black_or_credit_frame(video_path: Path, start_time: float, duration: float = 2.0) -> bool:
    """
    Checks if a segment consists predominantly of black void or credits text.
    Uses FFmpeg blackdetect to filter out closing credits rolls.
    """
    cmd = [
        "ffmpeg", "-ss", str(start_time), "-t", str(duration),
        "-i", str(video_path),
        "-vf", "blackdetect=d=0.4:pix_th=0.15",
        "-f", "null", "-"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if "black_start:" in res.stderr:
            return True
    except Exception:
        pass
    return False


def get_episode_phase_boundaries(
    matched_ep_code: Optional[str],
    character_key: str,
    total_duration: float,
    video_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Computes canonical, production-grade semantic phase boundaries for any episode.
    
    Guarantees:
    1. Zero bystander / spectator / crying scene leakage (e.g. Inosuke tear at 273s, Yuji crying at 1080s).
    2. Zero post-battle aftermath / sunrise / mourning / credits leakage (e.g. 1000s sunrise, 1234s credits).
    3. Strict character co-presence (target character or primary combatant).
    4. Clean separation of Pre-Fight Dialogue/Conversation vs Pure Sakuga Combat.
    """
    # 1. Universal safe baseline bounds (skipping OP theme, cold open, and ED credits)
    start_bound = 180.0 if total_duration > 600 else (10.0 if total_duration > 60 else 1.0)
    if total_duration > 3600:
        end_bound = total_duration - 360.0
    elif total_duration > 600:
        end_bound = total_duration - 240.0  # Strictly exclude ED theme song, ending credits, and next episode preview
    elif total_duration > 300:
        end_bound = total_duration - 45.0
    elif total_duration > 60:
        end_bound = total_duration - 20.0
    else:
        end_bound = total_duration - 2.0

    conv_window = None
    combat_window = None
    curated_combat_scenes = []
    curated_conv_scenes = []

    pure_conv_keywords = [
        "dialogue", "conversation", "talk", "speak", "recruit", "demonhood",
        "refusal", "standoff", "pre-fight", "monologue", "confront"
    ]
    end_credit_keywords = [
        "credits", "ending theme", "ending song", "preview", "next episode",
        "taisho secret", "recap", "bumper", "staff roll", "cast roll",
        "crow", "aftermath", "mother", "weep", "crying", "dying", "mourning",
        "funeral", "sunrise", "dawn", "carriage", "passenger", "fleeing",
        "corpse", "tears", "flashback", "bystander", "reaction", "spectator",
        "injured", "kneeling", "impal", "prison realm", "kenjaku", "sealed",
        "sealing", "star religious", "riko", "headquarters", "crying in despair",
        "white void", "feeds sukuna", "church", "cult",
        # Strict Episode Intro Rejection
        "opening theme", "opening song", "title card", "episode title",
        "sponsor", "production", "cold open", "studio logo", "toho", "mappa",
        "ufotable", "aniplex", "opening", "intro theme", "op theme"
    ]

    ep_meta = load_episode_metadata(matched_ep_code) if matched_ep_code else None
    if not ep_meta and video_path and Path(video_path).exists():
        try:
            from core.auto_cataloger import auto_catalog_episode
            ep_meta = auto_catalog_episode(Path(video_path), forced_code=matched_ep_code, lead_character=character_key)
        except Exception as e:
            print(f"⚠️ [AutoCatalog] Phase boundaries notice: {e}")
    if ep_meta and "scenes" in ep_meta:
        char_k_lower = character_key.lower()
        # Does the episode have scenes explicitly featuring the target character?
        has_character_scenes = any(
            char_k_lower in [c.lower() for c in s.get("characters_present", [])]
            for s in ep_meta.get("scenes", [])
        )
        valid_fighters = {char_k_lower}
        for c in ep_meta.get("characters", []):
            role = c.get("role", "").lower()
            if any(r in role for r in ["hashira", "moon", "antagonist", "protagonist", "fighter", "curse", "demon", "sorcerer"]):
                valid_fighters.add(c.get("name", "").lower())

        for s in ep_meta["scenes"]:
            st = float(s.get("start", 0.0))
            en = float(s.get("end", st + 10.0))
            desc = s.get("description", "").lower()
            score = float(s.get("action_score") if s.get("action_score") is not None else (1.0 if s.get("action_level") == "EXPLOSIVE" else 0.85 if s.get("action_level") == "INTENSE" else 0.70 if s.get("action_level") == "MODERATE" else 0.50 if s.get("action_level") == "CALM" else 0.0))
            chars = [c.lower() for c in s.get("characters_present", [])]

            # Rejection 1: Episode intro/theme or aftermath/credits
            if total_duration > 600 and st < 120.0:
                continue
            if any(kw in desc for kw in end_credit_keywords) or bool(re.search(r"\b(ed|ending|op|opening)\b", desc)):
                continue

            # Check if this scene is pre-fight dialogue/conversation
            is_conv = (
                any(kw in desc for kw in pure_conv_keywords)
                or s.get("is_conversation", False)
                or s.get("action_level") == "CALM"
                or (score < 0.70 and ("intro" in desc or "dialogue" in desc))
            )

            has_target = char_k_lower in chars
            has_fighter = any(f in chars for f in valid_fighters)
            is_solo_bystander = (not has_target) and all(
                c in ["inosuke", "tanjiro", "zenitsu", "crow", "obanai", "yuji", "megumi", "spectator"]
                for c in chars
            )

            # Strict isolation: if episode has scenes for target character, ONLY select target's scenes
            fighter_ok = has_target if has_character_scenes else (has_fighter and not is_solo_bystander)

            if is_conv:
                if fighter_ok:
                    curated_conv_scenes.append(s)
            else:
                if score >= 0.70 and fighter_ok:
                    curated_combat_scenes.append(s)

        if curated_conv_scenes:
            conv_start = min(float(s["start"]) for s in curated_conv_scenes)
            conv_end = max(float(s["end"]) for s in curated_conv_scenes)
            conv_window = (conv_start, conv_end)

        if curated_combat_scenes:
            fight_start = min(float(s["start"]) for s in curated_combat_scenes)
            fight_end = max(float(s["end"]) for s in curated_combat_scenes)
            combat_window = (fight_start, fight_end)
            end_bound = fight_end

    return {
        "start_bound": start_bound,
        "end_bound": end_bound,
        "conv_window": conv_window,
        "combat_window": combat_window,
        "curated_combat_scenes": curated_combat_scenes,
        "curated_conv_scenes": curated_conv_scenes,
    }


def slice_action_moments_from_source(
    video_path: Path,
    character_key: str,
    output_dir: Path,
    n_clips: int = 15,
    clip_duration: float = 5.5,
    title: Optional[str] = None,
    drop_index: Optional[int] = None,
    clip_prefix: Optional[str] = None,
    clean_old: bool = True
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
    prefix = clip_prefix or f"{character_key}_gdrive"

    # Clean old slices for this character to ensure 100% fresh clips
    if clean_old:
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

    # Universal semantic phase boundaries from episode metadata:
    # Derives exact combat bounds, conversation windows, and excludes all bystander/aftermath/credit leakage.
    matched_ep_code = match_episode_code_from_filename(video_path.name)
    prefix = clip_prefix or (f"{character_key}_gdrive_{matched_ep_code}" if matched_ep_code else f"{character_key}_gdrive")
    phase_info = get_episode_phase_boundaries(
        matched_ep_code=matched_ep_code,
        character_key=character_key,
        total_duration=total_duration,
        video_path=video_path
    )
    start_bound = phase_info["start_bound"]
    end_bound = phase_info["end_bound"]
    combat_window = phase_info["combat_window"]
    conv_window = phase_info["conv_window"]

    # Bounds for combat clips:
    if combat_window:
        combat_start_bound = max(start_bound, combat_window[0] - 1.0)
        combat_end_bound = min(end_bound, combat_window[1] + 1.0)
    else:
        combat_start_bound = start_bound
        combat_end_bound = end_bound

    # Universe Safety Guard: Never slice a video for a character from another universe
    file_universe = get_file_universe(video_path.name)
    char_theme = CHARACTER_THEMES.get(character_key)
    if not char_theme:
        from core.clip_manager import ensure_character_theme
        char_theme = ensure_character_theme(character_key, universe=file_universe)
    char_universe = char_theme["universe"] if char_theme else None

    if file_universe and char_universe and file_universe != char_universe:
        raise ValueError(
            f"CRITICAL SAFETY VIOLATION: Source video '{video_path.name}' is from universe '{file_universe.upper()}', "
            f"but character '{character_key}' belongs to universe '{char_universe.upper()}'. Aborting slice to prevent cross-contamination!"
        )

    # ── Phase 1: Curated Episode Climax & Scene Extraction from Metadata ───────
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

    pure_conv_keywords = [
        "dialogue", "conversation", "talk", "speak", "recruit", "demonhood",
        "refusal", "standoff", "pre-fight", "monologue", "confront"
    ]
    end_credit_keywords = [
        "credits", "ending theme", "ending song", "preview", "next episode",
        "taisho secret", "recap", "bumper", "staff roll", "cast roll",
        "crow", "aftermath", "mother", "weep", "crying", "dying", "mourning",
        "funeral", "sunrise", "dawn", "carriage", "passenger", "fleeing",
        "corpse", "tears", "flashback", "bystander", "reaction", "spectator",
        "injured", "kneeling", "impal", "prison realm", "kenjaku", "sealed",
        "sealing", "star religious", "riko", "headquarters", "crying in despair",
        "white void", "feeds sukuna", "church", "cult",
        # Strict Episode Intro Rejection
        "opening theme", "opening song", "title card", "episode title",
        "sponsor", "production", "cold open", "studio logo", "toho", "mappa",
        "ufotable", "aniplex", "opening", "intro theme", "op theme"
    ]
    def _is_credit(desc_text: str) -> bool:
        low = desc_text.lower()
        return any(kw in low for kw in end_credit_keywords) or bool(re.search(r"\b(ed|ending|op|opening)\b", low))

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

        seen_ranges = set()

        def _add_curated_scene(s: Dict[str, Any], bonus: float, tag_prefix: str):
            st = float(s.get("start", 0.0))
            en = float(s.get("end", st + 10.0))
            desc = s.get("description", "Curated epic scene")

            # Hard Rule: For full episodes (>600s), reject any scene starting before 120s (intro theme, OP, logos)
            if total_duration > 600 and st < 120.0:
                return

            # Strictly reject episode intros, end credits, ending theme songs, next-episode previews, and bumpers
            if _is_credit(desc):
                return

            raw_action = s.get("action_score") if s.get("action_score") is not None else (1.0 if s.get("action_level") == "EXPLOSIVE" else 0.85 if s.get("action_level") == "INTENSE" else 0.70 if s.get("action_level") == "MODERATE" else 0.50 if s.get("action_level") == "CALM" else 0.80)
            base_score = float(raw_action) * 100.0 + bonus
            if s.get("priority") == "high":
                base_score += 15.0

            key = (int(st), int(en))
            if key in seen_ranges:
                return
            seen_ranges.add(key)

            scene_len = max(clip_duration, en - st)
            is_conv = (s in phase_info["curated_conv_scenes"]) or any(kw in desc.lower() for kw in pure_conv_keywords)

            if is_conv:
                if scene_len <= clip_duration * 1.5:
                    pts = [st]
                else:
                    pts = [st, round(st + (scene_len - clip_duration) * 0.5, 2)]
            else:
                dense_step = 2.6
                min_safe_dur = min(clip_duration, 3.5)
                pts = []
                curr = st
                while curr + min_safe_dur <= en:
                    pts.append(round(curr, 2))
                    curr += dense_step
                if en - min_safe_dur >= st and not any(abs(p - (en - min_safe_dur)) < 1.5 for p in pts):
                    pts.append(round(en - min_safe_dur, 2))

            for p in pts:
                if is_conv:
                    if conv_window and not (conv_window[0] - 1.0 <= p <= conv_window[1] + 1.0):
                        continue
                else:
                    if combat_window and not (combat_start_bound <= p and p + min(clip_duration, 3.5) <= combat_end_bound):
                        continue
                if p < start_bound or p + min(clip_duration, 3.5) > end_bound:
                    continue

                curated_candidates.append({
                    "start": p,
                    "scene_end": en,
                    "score": base_score + (30.0 if is_conv else 0.0),
                    "description": desc,
                    "tag": f"💎 {tag_prefix}: {desc[:42]}",
                    "is_curated": True,
                    "is_conversation": is_conv,
                    "dialogue": s.get("dialogue")
                })

        for s in title_scenes:
            _add_curated_scene(s, bonus=20.0, tag_prefix="TITLE-MATCH")
        for s in phase_info["curated_combat_scenes"]:
            _add_curated_scene(s, bonus=15.0, tag_prefix="SAKUGA-COMBAT")
        for s in phase_info["curated_conv_scenes"]:
            _add_curated_scene(s, bonus=10.0, tag_prefix="INTRO-DIALOGUE")

        print(f"✨ [ActionSlicer] Extracted {len(curated_candidates)} curated moments (dense sub-sliced) from metadata for {matched_ep_code}.")

    # ── Phase 2: OpenCV Motion, Climax & Highlight Energy Analysis ───────────
    cv_candidates = []
    intro_hook_cand = None
    try:
        scorer = SceneScorer(video_path)
        # Tight 1.5s window duration to evaluate combat sakuga with high temporal acuity
        scorer.analyze(step_frames=4, window_duration=1.5)
        ranked_cv = scorer.get_ranked_scenes(
            n_clips=n_clips * 2,
            clip_duration=1.5,
            min_gap=2.5,
            start_bound=combat_start_bound,
            end_bound=combat_end_bound
        )
        for w in ranked_cv:
            if not any(abs(w["start"] - prev) < 5.0 for prev in file_used_ts):
                cv_candidates.append({
                    "start": w["start"],
                    "score": float(w["score"]) + (25.0 if w.get("climax_boost") else 0.0),
                    "description": "OpenCV Climax Motion & Neon Energy",
                    "tag": f"🔥 CV Motion ({w.get('avg_diff', 0):.1f}) Climax",
                    "is_curated": False,
                    "is_conversation": False
                })
        intro_min = conv_window[0] if conv_window else (180.0 if total_duration > 600 else 1.0)
        intro_max = conv_window[1] if conv_window else min(480.0, combat_start_bound + 30.0)
        intro_hook_cand = scorer.find_active_intro_hook(min_start=intro_min, max_start=intro_max)
        print(f"👁️ [ActionSlicer] OpenCV Scorer discovered {len(cv_candidates)} high-motion climax windows within combat bounds.")
    except Exception as e:
        print(f"⚠️ [ActionSlicer] OpenCV scoring fallback: {e}")

    # ── Phase 2b: Dynamic FFmpeg Audio Volume Scan across Combat Bounds ───────
    rand_offset = random.uniform(0.0, 2.5)
    step = 4.0 if total_duration > 600 else 2.0
    t = combat_start_bound + rand_offset
    audio_candidates = []

    while t + clip_duration <= combat_end_bound:
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
                            "is_curated": False,
                            "is_conversation": False
                        })
            except Exception:
                pass
        t += step

    audio_candidates.sort(key=lambda x: x["score"], reverse=True)
    cv_candidates.sort(key=lambda x: x["score"], reverse=True)
    print(f"⚔️ [ActionSlicer] Discovered {len(audio_candidates)} audio combat & {len(cv_candidates)} CV climax moments within combat bounds.")

    # ── Phase 3: Hybrid Merge (Curated Climax + OpenCV Vision + Audio Clash) ──
    # Universal OpenCV Sakuga Gate: Filter out static bystander cutaways & reaction shots
    filtered_curated = []
    dropped_cutaways = 0
    for c in curated_candidates:
        if c.get("is_conversation", False):
            filtered_curated.append(c)
            continue
        if scorer and getattr(scorer, "window_scores", None):
            matching_cv = [w for w in scorer.window_scores if abs(w["start"] - c["start"]) < 1.5]
            if matching_cv:
                best_cv = max(matching_cv, key=lambda w: w.get("score", 0))
                # High-energy sakuga or impact collision (high motion or high particle saturation) - definitely KEEP!
                if best_cv.get("rejected", False) or (best_cv.get("avg_diff", 0.0) < 4.5 and best_cv.get("avg_highlight", 0.0) < 2.5):
                    # Reject static spectator reaction cutaways, crying shots & dark void frames
                    dropped_cutaways += 1
                    continue
                elif best_cv.get("avg_diff", 0.0) >= 5.0 or best_cv.get("avg_highlight", 0.0) >= 2.5:
                    c["score"] += best_cv.get("score", 0.0) * 0.4
        filtered_curated.append(c)

    if dropped_cutaways > 0:
        print(f"🛡️ [ActionSlicer] OpenCV Sakuga Gate filtered out {dropped_cutaways} low-motion bystander cutaways.")

    filtered_curated.sort(key=lambda x: x["score"], reverse=True)
    # Preserve pre-fight conversation candidates so they are never purged by explosive combat filters
    curated_conv_pool = [
        c for c in curated_candidates
        if (c.get("is_conversation", False) or any(kw in c.get("description", "").lower() for kw in pure_conv_keywords))
        and not _is_credit(c.get("description", ""))
        and (c["start"] >= (120.0 if total_duration > 600 else 1.0))
    ]
    explosive_curated = [c for c in filtered_curated if c["score"] >= 100.0]
    candidate_source = explosive_curated if len(explosive_curated) >= n_clips else filtered_curated
    final_candidates = []

    # Preserve dense combat candidates with 2.2s minimum spacing
    min_cand_gap = 2.2
    for c in candidate_source:
        if len(final_candidates) >= max(n_clips * 2, 40):
            break
        if not any(abs(c["start"] - s["start"]) < min_cand_gap for s in final_candidates):
            final_candidates.append(c)

    # Add OpenCV vision motion & climax candidates ONLY if more clips are needed
    if len(final_candidates) < n_clips + 8:
        for cv in cv_candidates:
            if len(final_candidates) >= n_clips + 8:
                break
            if combat_window and not (combat_start_bound <= cv["start"] <= combat_end_bound):
                continue
            if not any(abs(cv["start"] - s["start"]) < min_cand_gap for s in final_candidates):
                final_candidates.append(cv)

    # Add dynamic audio combat scenes if still needed
    if len(final_candidates) < n_clips + 12:
        for a in audio_candidates:
            if len(final_candidates) >= n_clips + 12:
                break
            if combat_window and not (combat_start_bound <= a["start"] <= combat_end_bound):
                continue
            if is_black_or_credit_frame(video_path, a["start"]):
                continue
            if not any(abs(a["start"] - s["start"]) < min_cand_gap for s in final_candidates):
                final_candidates.append(a)

    # Safe fallback if too few candidates met strict thresholds
    if len(final_candidates) < n_clips:
        print(f"⚠️ [ActionSlicer] Found {len(final_candidates)} candidates, adding paced scene fallback within combat bounds...")
        t = combat_start_bound
        while t + clip_duration <= combat_end_bound and len(final_candidates) < n_clips * 2:
            if not any(abs(t - s["start"]) < min_cand_gap for s in final_candidates):
                final_candidates.append({
                    "start": t,
                    "score": 50.0,
                    "description": "Paced Scene",
                    "tag": "🎬 Paced Scene",
                    "is_curated": False,
                    "is_conversation": False
                })
            t += 10.0

    final_candidates.sort(key=lambda x: x["score"], reverse=True)
    print(f"🎬 [ActionSlicer] Total hybrid candidate pool: {len(final_candidates)} scenes (Curated + OpenCV Vision + Audio).")

    # ── Phase 4: Intelligent Scene Orchestration for Beat Drops ───────────────
    # Invariant: Pre-drop conversation is strictly ONE continuous, contiguous sequence of at least 30s.
    # The conversation must directly precede / surround the fight scenes used for the edit.
    # Post-drop slots (i >= 1) strictly contain PURE COMBAT / SAKUGA FIGHT SCENES ONLY.
    drop_idx = 1  # Exactly 1 continuous conversation clip before the beat drop
    bridge_idx = min(n_clips - 4, max(drop_idx + 2, int(n_clips * 0.7))) if n_clips > 6 else max(0, n_clips - 2)
    last_idx = n_clips - 1

    # Find the drop climax: signature primary attack (e.g. Fire Dragon, Domain Expansion, Sixfold Lightning)
    drop_candidates = [
        c for c in final_candidates
        if any(kw in c.get("description", "").lower() for kw in ["dragon", "enbu", "giant fire", "domain expansion", "hollow purple", "sixfold", "musical score", "ninth form", "first form", "sea of fire"])
        and not c.get("is_conversation", False)
        and not any(kw in c.get("description", "").lower() for kw in pure_conv_keywords)
        and not _is_credit(c.get("description", ""))
        and (c["start"] + min(clip_duration, 3.5) <= end_bound)
        and (combat_start_bound <= c["start"] <= combat_end_bound if combat_window else True)
    ]
    if drop_candidates:
        drop_climax = max(drop_candidates, key=lambda x: x["score"])
    else:
        valid_drops = [
            c for c in final_candidates
            if not c.get("is_conversation", False)
            and not any(kw in c.get("description", "").lower() for kw in pure_conv_keywords)
            and not _is_credit(c.get("description", ""))
            and (c["start"] + min(clip_duration, 3.5) <= end_bound)
            and (combat_start_bound <= c["start"] <= combat_end_bound if combat_window else True)
        ]
        drop_climax = valid_drops[0] if valid_drops else final_candidates[0]

    # Find the true finisher: decisive strike or climax collision
    finisher_candidates = [
        c for c in final_candidates
        if c != drop_climax and any(kw in c.get("description", "").lower() for kw in ["decapitat", "neck", "sever", "cleave", "circular slash", "kamado song", "wolf hunt", "flame tiger", "disorder", "impact collision", "supreme clash"])
        and not c.get("is_conversation", False)
        and not any(kw in c.get("description", "").lower() for kw in pure_conv_keywords)
        and not _is_credit(c.get("description", ""))
        and (c["start"] + min(clip_duration, 3.5) <= end_bound)
        and (combat_start_bound <= c["start"] <= combat_end_bound if combat_window else True)
    ]
    if finisher_candidates:
        finisher = max(finisher_candidates, key=lambda x: x.get("score", 0.0))
    elif len(final_candidates) > 2:
        valid_finishers = [
            c for c in final_candidates
            if c != drop_climax
            and not c.get("is_conversation", False)
            and not any(kw in c.get("description", "").lower() for kw in pure_conv_keywords)
            and not _is_credit(c.get("description", ""))
            and (c["start"] + min(clip_duration, 3.5) <= end_bound)
            and (combat_start_bound <= c["start"] <= combat_end_bound if combat_window else True)
        ]
        finisher = max(valid_finishers, key=lambda x: x.get("score", 0.0)) if valid_finishers else drop_climax
    else:
        finisher = final_candidates[0]

    # Find secondary drop (bridge drop) - strictly combat only
    sec_candidates = [
        c for c in final_candidates
        if c != drop_climax and c != finisher
        and not c.get("is_conversation", False)
        and not any(kw in c.get("description", "").lower() for kw in pure_conv_keywords)
        and not _is_credit(c.get("description", ""))
        and (c["start"] + min(clip_duration, 3.5) <= end_bound)
        and (combat_start_bound <= c["start"] <= combat_end_bound if combat_window else True)
        and any(kw in c.get("description", "").lower() for kw in ["exploding blood", "bakketsu", "pink", "boogie woogie", "godspeed", "destructive death", "tiger", "fifth form", "air type"])
    ]
    if sec_candidates:
        sec_drop = max(sec_candidates, key=lambda x: x["score"])
    elif len(final_candidates) > 1:
        other_candidates = [
            c for c in final_candidates
            if c != drop_climax and c != finisher
            and not c.get("is_conversation", False)
            and not any(kw in c.get("description", "").lower() for kw in pure_conv_keywords)
            and not _is_credit(c.get("description", ""))
            and (c["start"] + min(clip_duration, 3.5) <= end_bound)
            and (combat_start_bound <= c["start"] <= combat_end_bound if combat_window else True)
        ]
        sec_drop = other_candidates[0] if other_candidates else final_candidates[1]
    else:
        sec_drop = drop_climax

    # ── Single Continuous Pre-Fight Conversation Selection (Directly around the fight scene) ──
    # Select candidate pre-fight dialogue/conversation scenes (never episode opener)
    all_conv_candidates = [
        c for c in (curated_conv_pool + final_candidates)
        if (c.get("is_conversation", False) or any(kw in c.get("description", "").lower() for kw in pure_conv_keywords))
        and not _is_credit(c.get("description", ""))
        and (c["start"] >= (120.0 if total_duration > 600 else 1.0))
        and (conv_window[0] - 1.0 <= c["start"] <= conv_window[1] + 1.0 if conv_window else True)
        and (c["start"] <= drop_climax["start"] + 15.0)  # Must lead directly into or surround the combat encounter
    ]
    if not all_conv_candidates:
        all_conv_candidates = [
            c for c in (curated_conv_pool + final_candidates)
            if not _is_credit(c.get("description", ""))
            and c["start"] >= (120.0 if total_duration > 600 else 1.0)
            and c not in (drop_climax, sec_drop, finisher)
            and not any(kw in c.get("description", "").lower() for kw in ["dragon", "purple", "cleave", "explosion", "collision", "decapitat"])
        ]

    # Prioritize conversation with dialogue definitions, closest to and directly preceding the combat climax
    if all_conv_candidates:
        all_conv_candidates.sort(key=lambda c: (
            0 if c.get("dialogue") else 1,
            abs(drop_climax["start"] - c.get("scene_end", c["start"]))
        ))
        best_conv = all_conv_candidates[0]
    elif intro_hook_cand and intro_hook_cand["start"] >= (180.0 if total_duration > 600 else 1.0):
        best_conv = {
            "start": intro_hook_cand["start"],
            "score": intro_hook_cand["score"],
            "description": "Active Intro Hook Shot",
            "tag": "🎯 Intro Hook",
            "is_curated": False,
            "is_conversation": True
        }
    else:
        best_conv = final_candidates[0]

    # Slot 0 is strictly the single continuous pre-fight conversation shot
    selected = [None] * n_clips
    selected[0] = best_conv
    selected[drop_idx] = drop_climax
    selected[bridge_idx] = sec_drop
    selected[last_idx] = finisher

    # Diverse combat pool selection with strict non-repetition and distance spacing
    used_counts = collections.Counter()
    for c in selected:
        if c is not None:
            used_counts[c["start"]] += 1

    available_combat = [
        c for c in final_candidates
        if c not in (drop_climax, sec_drop, finisher, best_conv)
        and not c.get("is_conversation", False)
        and not any(kw in c.get("description", "").lower() for kw in pure_conv_keywords)
        and not _is_credit(c.get("description", ""))
        and (c["start"] + min(clip_duration, 3.5) <= end_bound)
        and (combat_start_bound <= c["start"] <= combat_end_bound if combat_window else True)
    ]
    # Prioritize highest action score scenes first
    available_combat.sort(key=lambda x: x["score"], reverse=True)

    for i in range(1, n_clips):
        if selected[i] is None:
            prev_cand = selected[i - 1] if i > 0 else None
            prev_st = prev_cand["start"] if prev_cand else -999.0

            # 1. Best: Completely unused candidate with at least 8s distance from previous cut
            chosen_c = None
            for cand in available_combat:
                if used_counts[cand["start"]] > 0:
                    continue
                if abs(cand["start"] - prev_st) < 8.0:
                    continue
                chosen_c = cand
                break

            # 2. Any completely unused candidate with distance >= 4s
            if not chosen_c:
                for cand in available_combat:
                    if used_counts[cand["start"]] == 0 and abs(cand["start"] - prev_st) >= 4.0:
                        chosen_c = cand
                        break

            # 3. Any completely unused candidate
            if not chosen_c:
                for cand in available_combat:
                    if used_counts[cand["start"]] == 0:
                        chosen_c = cand
                        break

            # 4. If all candidates used at least once: pick least frequently used candidate
            if not chosen_c:
                cand_pool = available_combat if available_combat else [
                    c for c in final_candidates
                    if not c.get("is_conversation", False)
                    and not any(kw in c.get("description", "").lower() for kw in pure_conv_keywords)
                    and not _is_credit(c.get("description", ""))
                    and (c["start"] + clip_duration <= end_bound)
                    and (combat_start_bound <= c["start"] <= combat_end_bound if combat_window else True)
                ]
                if cand_pool:
                    non_adjacent = [c for c in cand_pool if abs(c["start"] - prev_st) >= 4.0]
                    pool_to_sort = non_adjacent if non_adjacent else cand_pool
                    pool_to_sort.sort(key=lambda c: (used_counts[c["start"]], -abs(c["start"] - prev_st)))
                    chosen_c = pool_to_sort[0]
                else:
                    combat_fallback = [
                        c for c in final_candidates
                        if not c.get("is_conversation", False)
                        and not any(kw in c.get("description", "").lower() for kw in pure_conv_keywords)
                        and not _is_credit(c.get("description", ""))
                    ]
                    chosen_c = combat_fallback[0] if combat_fallback else (drop_climax or final_candidates[0])

            # Invariant: Combat slots (i >= 1) MUST NEVER contain conversation or credit scenes
            if chosen_c.get("is_conversation", False) or any(kw in chosen_c.get("description", "").lower() for kw in pure_conv_keywords) or _is_credit(chosen_c.get("description", "")):
                combat_fallback = [
                    c for c in final_candidates
                    if not c.get("is_conversation", False)
                    and not any(kw in c.get("description", "").lower() for kw in pure_conv_keywords)
                    and not _is_credit(c.get("description", ""))
                ]
                chosen_c = combat_fallback[0] if combat_fallback else drop_climax

            selected[i] = chosen_c
            used_counts[chosen_c["start"]] += 1

    # Final Invariant Enforcement: Post-drop slots (i >= 1) MUST ONLY CONTAIN FIGHT SCENES
    pure_combat_candidates = [
        c for c in final_candidates
        if not c.get("is_conversation", False)
        and not any(kw in c.get("description", "").lower() for kw in pure_conv_keywords)
        and not _is_credit(c.get("description", ""))
        and (c["start"] >= (180.0 if total_duration > 600 else 1.0))
        and (combat_start_bound <= c["start"] <= combat_end_bound if combat_window else True)
    ]
    if not pure_combat_candidates:
        pure_combat_candidates = [drop_climax, sec_drop, finisher]

    for i in range(1, n_clips):
        cand = selected[i]
        if cand is None or cand.get("is_conversation", False) or any(kw in cand.get("description", "").lower() for kw in pure_conv_keywords) or _is_credit(cand.get("description", "")):
            selected[i] = pure_combat_candidates[i % len(pure_combat_candidates)]

    print(f"💥 [ActionSlicer] Mapped #1 CLIMAX scene ({drop_climax['start']:.1f}s, {drop_climax['tag']}) directly to Beat Drop (Clip 2)!")

    # Probe authentic Japanese anime audio stream mapping
    eng_audio_map = get_japanese_audio_map(video_path)

    generated_clips = []
    new_used_ts = []

    # High-clarity super-resolution upscaling & edge reconstruction (retains 100% frame data without destructive border crop)
    target_slice_w = max(1920, VIDEO_WIDTH)
    vf_chain = (
        f"scale={target_slice_w}:-2:flags=lanczos+accurate_rnd+full_chroma_int+full_chroma_inp,"
        f"scale=trunc(iw/2)*2:trunc(ih/2)*2,cas=0.60,unsharp=5:5:1.3:5:5:0.0,setsar=1,fps={FPS}"
    )

    for idx, cand in enumerate(selected):
        start = cand["start"]
        out_clip = output_dir / f"{prefix}_{idx:02d}_{int(start)}s.mp4"
        
        # Duration: intro clip needs at least 30.0s of pure continuous pre-fight conversation (zero fight cuts before drop)
        if idx < drop_idx:
            avail = max(30.0, cand.get("scene_end", start + 35.0) - start)
            target_dur = max(30.0, min(avail, 35.0))
        else:
            target_dur = min(clip_duration, 5.0)
            if combat_window:
                safe_end = min(cand.get("scene_end", combat_end_bound), combat_end_bound)
                avail = max(0.5, safe_end - start)
                target_dur = min(target_dur, avail)

        # Try 1: Probe-matched English Dub audio stream
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(video_path),
            "-t", str(target_dur),
        ] + eng_audio_map + [
            "-vf", vf_chain,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            str(out_clip)
        ]
        
        sliced_successfully = False
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=60)
            if out_clip.exists() and out_clip.stat().st_size > 40_000:
                sliced_successfully = True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            # Try 2: Generic optional audio mapping (0:v:0 + 0:a:0?)
            fallback_cmd = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", str(video_path),
                "-t", str(target_dur),
                "-map", "0:v:0", "-map", "0:a:0?",
                "-vf", vf_chain,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "48000",
                "-ac", "2",
                str(out_clip)
            ]
            try:
                subprocess.run(fallback_cmd, capture_output=True, check=True, timeout=60)
                if out_clip.exists() and out_clip.stat().st_size > 40_000:
                    sliced_successfully = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e2:
                # Try 3: Video-only stream extraction (-an) to guarantee real 1080p anime footage
                video_only_cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start),
                    "-i", str(video_path),
                    "-t", str(target_dur),
                    "-map", "0:v:0", "-an",
                    "-vf", vf_chain,
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    str(out_clip)
                ]
                try:
                    subprocess.run(video_only_cmd, capture_output=True, check=True, timeout=60)
                    if out_clip.exists() and out_clip.stat().st_size > 40_000:
                        sliced_successfully = True
                except Exception as e3:
                    err_msg = (e3.stderr.decode() if hasattr(e3, "stderr") and e3.stderr else str(e3))[-250:]
                    print(f"  ⚠️ Error cutting clip at {start}s across all audio/video attempts: {err_msg}")
        except Exception as e_unexp:
            print(f"  ⚠️ Unexpected error cutting clip at {start}s: {e_unexp}")

        # Strict validation: verify file exists, size > 40KB, and valid moov atom / stream duration via ffprobe
        is_valid = False
        if sliced_successfully and out_clip.exists() and out_clip.stat().st_size > 40_000:
            try:
                probe_test = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out_clip)],
                    capture_output=True, text=True, timeout=5
                )
                if probe_test.returncode == 0 and probe_test.stdout.strip():
                    dur_val = float(probe_test.stdout.strip())
                    if dur_val >= 0.5:
                        is_valid = True
            except Exception:
                is_valid = False

        if not is_valid:
            out_clip.unlink(missing_ok=True)
        else:
            generated_clips.append(out_clip)
            new_used_ts.append(start)
            role_tag = (
                "💥 BEAT DROP" if idx == drop_idx
                else ("⚡ SECONDARY DROP" if idx == bridge_idx
                else ("🔥 FINISHER" if idx == last_idx
                else "⚔️ Scene"))
            )
            print(f"  ✂️ Clip {idx+1:02d}/{len(selected)} sliced ({start:.1f}s - {start+target_dur:.1f}s) [{role_tag}] {cand.get('tag', '')}")

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
    title: Optional[str] = None,
    drop_index: Optional[int] = None,
    clip_duration: float = 5.5,
    target_episode: Optional[str] = None
) -> List[Path]:
    """
    Lightning-Fast Non-Repetitive Multi-Episode Google Drive Ingestion:
    1. Parses Google Drive folder index in 1s.
    2. Identifies canonical episodes for the character (or uses target_episode if specified).
    3. Downloads up to 2 distinct episodes for rich arc storytelling.
    4. Slices dialogue intro from Ep 1, and peak sakuga/ultimate forms from Ep 2 into 4:5 tall action clips.
    """
    gdrive_workdir = SCRATCH_DIR / "gdrive_workspace"
    gdrive_workdir.mkdir(parents=True, exist_ok=True)

    items = list_gdrive_folder_items(gdrive_url_or_id)
    if not items:
        print("⚠️ [GoogleDrive] No files retrieved from Google Drive folder index.")
        return []

    # Select candidate episodes: single episode by default to prevent era/arc Frankenstein clashes,
    # unless Rengoku Mugen Train continuous 2-part battle (S02E06 + S02E07)
    max_eps = 2 if (target_character == "rengoku" and not target_episode) else 1
    candidate_episodes = pick_character_episodes(items, target_character, max_episodes=max_eps, title=title, target_episode=target_episode)
    if not candidate_episodes:
        print(f"⚠️ [GoogleDrive] No matching episodes found for '{target_character}'.")
        return []

    downloaded_videos = []
    for ep_info in candidate_episodes:
        raw_vid = download_single_gdrive_file(ep_info, gdrive_workdir)
        if raw_vid and raw_vid.exists() and raw_vid.stat().st_size > 15_000_000:
            downloaded_videos.append(raw_vid)
            # Automatic Cataloging Hook for newly downloaded episode
            try:
                from core.auto_cataloger import is_episode_cataloged, auto_catalog_episode, parse_anime_identity
                p = parse_anime_identity(raw_vid.name)
                c_code = p["episode_code"]
                if not is_episode_cataloged(c_code):
                    print(f"🆕 [AutoCatalog] Uncataloged video downloaded: '{raw_vid.name}'. Automatically registering into episode catalog...")
                    auto_catalog_episode(raw_vid, forced_code=c_code, lead_character=target_character)
            except Exception as e:
                print(f"⚠️ [AutoCatalog] Ingestion cataloging notice: {e}")
        if len(downloaded_videos) >= 2:
            break

    # If primary download failed, fallback search loop
    if not downloaded_videos:
        attempted_names = {ep["name"] for ep in candidate_episodes}
        for _ in range(min(5, len(items))):
            avail = [it for it in items if it["name"] not in attempted_names]
            if not avail:
                break
            best = pick_best_file_for_character(avail, target_character, title=title, target_episode=target_episode)
            if not best:
                break
            attempted_names.add(best["name"])
            raw = download_single_gdrive_file(best, gdrive_workdir)
            if raw and raw.exists() and raw.stat().st_size > 15_000_000:
                downloaded_videos.append(raw)
                break

    if not downloaded_videos:
        print(f"⚠️ [GoogleDrive] Could not download any valid (>15MB) episode for '{target_character}'.")
        return []

    # Single-episode path
    if len(downloaded_videos) == 1:
        return slice_action_moments_from_source(
            video_path=downloaded_videos[0],
            character_key=target_character,
            output_dir=output_dir,
            n_clips=n_clips,
            clip_duration=clip_duration,
            title=title,
            drop_index=drop_index,
            clean_old=True
        )

    # Multi-Episode Ingestion: Combine Ep 1 (Setup/Intro) with Ep 2 (Peak Sakuga Climax & Finisher)
    vid_1, vid_2 = downloaded_videos[0], downloaded_videos[1]
    n_half = max(10, n_clips // 2 + 2)
    print(f"🎬 [MultiEpisode] Ingesting multi-episode arc: Ep1 '{vid_1.name}' + Ep2 '{vid_2.name}'")

    slices_1 = slice_action_moments_from_source(
        video_path=vid_1,
        character_key=target_character,
        output_dir=output_dir,
        n_clips=n_half,
        clip_duration=clip_duration,
        title=title,
        drop_index=drop_index,
        clip_prefix=f"{target_character}_gdrive_ep1",
        clean_old=True
    )

    slices_2 = slice_action_moments_from_source(
        video_path=vid_2,
        character_key=target_character,
        output_dir=output_dir,
        n_clips=max(14, n_clips - len(slices_1) + 8),
        clip_duration=clip_duration,
        title=title,
        drop_index=0,
        clip_prefix=f"{target_character}_gdrive_ep2",
        clean_old=False
    )

    if not slices_1 and not slices_2:
        return []
    if not slices_2:
        return slices_1
    if not slices_1:
        return slices_2

    # Chronological Multi-Episode Narrative Arc:
    # 1. Intro / Standoff: S02E06 dialogue hook (slices_1[0])
    # 2. Early & Mid Combat: S02E06 combat clashes (pool_1: Sea of Fire, Air clashes, Flame Tiger)
    # 3. Climax & Finisher: S02E07 Ninth Form dragon escalation (pool_2: Dragon launch & collision finisher)
    # Never interleave backwards across episodes to prevent injury continuity fractures!
    combined = [slices_1[0]]
    finisher = slices_2[-1] if slices_2 else (slices_1[-1] if len(slices_1) > 1 else combined[0])
    pool_1 = [c for c in slices_1[1:] if c != finisher]
    pool_2 = [c for c in slices_2 if c != finisher]

    n_needed = max(1, n_clips - 2)
    n_ep1 = max(1, min(len(pool_1), n_needed // 2))
    n_ep2 = max(1, min(len(pool_2), n_needed - n_ep1))

    combined.extend(pool_1[:n_ep1])
    combined.extend(pool_2[:n_ep2])

    # Fill remaining from pool_2 then pool_1 without interleaving backwards
    rem_2 = pool_2[n_ep2:]
    rem_1 = pool_1[n_ep1:]
    while len(combined) < n_clips - 1 and rem_2:
        combined.append(rem_2.pop(0))
    while len(combined) < n_clips - 1 and rem_1:
        combined.append(rem_1.pop(0))

    combined.append(finisher)
    print(f"✨ [MultiEpisode] Created chronologically escalated pool of {len(combined)} cuts across {vid_1.name} & {vid_2.name}!")
    return combined

