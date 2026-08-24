#!/usr/bin/env python3
"""
GDrive AMV Builder — Hybrid Action/Cinematic Edit Engine
=========================================================
Reads raw footage from a source Google Drive folder, assembles a 60-90s
hybrid AMV (action cuts + cinematic moments), applies VFX effects chosen
sequentially from a style pool, and uploads the final MP4 + a code snapshot
ZIP to AMV_Outputs/<run_label>/ inside the same Drive root.

Rules:
  - Marvel edits NEVER contain anime characters, JJK edits NEVER contain Marvel.
  - VFX style is picked sequentially so each run uses a different style.
  - Source folder : drive.google.com/drive/folders/1e5_IF3GRHNr315hP5zK_qlyfsKXm3Ox4
  - Output folder : AMV_Outputs/ (auto-created in same Drive root)

Usage:
    python3 scripts/gdrive_amv_builder.py \
        --universe jjk --character gojo --duration 75 --upload

    python3 scripts/gdrive_amv_builder.py --list-styles
"""
import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import SCRATCH_DIR, OUTPUT_DIR, PHONK_DIR, FPS, VIDEO_WIDTH, VIDEO_HEIGHT
from core.gdrive_manager import (
    list_gdrive_folder_items,
    download_single_gdrive_file,
    fetch_and_prepare_gdrive_footage,
    pick_best_file_for_character,
    slice_action_moments_from_source,
)
from core.clip_manager import CHARACTER_THEMES
from core.effects_engine import build_cc_filter
from core.phonk_manager import get_random_or_specified_phonk
from core.beat_detector import analyze_audio_beats

# ─── constants ──────────────────────────────────────────────────────────────
SOURCE_FOLDER_ID = "1e5_IF3GRHNr315hP5zK_qlyfsKXm3Ox4"
STYLE_STATE_FILE = SCRATCH_DIR / "amv_style_rotation.json"

# ─── VFX Style Pool — sequential rotation across runs ───────────────────────
STYLE_POOL = [
    {
        "name": "Velocity Rush",
        "description": "Aggressive speed ramps — slow-mo on peaks, 1.5x on drops",
        "velocity": True, "zoom_punch": False, "color_flash": True,
        "letterbox": True, "beat_cuts": True, "slow_mo_peaks": True, "glitch": False,
    },
    {
        "name": "Glitch Storm",
        "description": "Digital glitch distortion + chromatic aberration bursts",
        "velocity": True, "zoom_punch": False, "color_flash": True,
        "letterbox": False, "beat_cuts": True, "slow_mo_peaks": False, "glitch": True,
    },
    {
        "name": "Zoom Punch",
        "description": "Camera zoom punch on hard-hit moments + beat-synced cuts",
        "velocity": False, "zoom_punch": True, "color_flash": True,
        "letterbox": True, "beat_cuts": True, "slow_mo_peaks": True, "glitch": False,
    },
    {
        "name": "Cinematic Flash",
        "description": "Letterbox intro, color leaks on beat, slow-mo climax outro",
        "velocity": True, "zoom_punch": False, "color_flash": True,
        "letterbox": True, "beat_cuts": True, "slow_mo_peaks": True, "glitch": False,
    },
    {
        "name": "Full VFX Stack",
        "description": "Every effect — velocity + glitch + zoom + flash + slow-mo",
        "velocity": True, "zoom_punch": True, "color_flash": True,
        "letterbox": True, "beat_cuts": True, "slow_mo_peaks": True, "glitch": True,
    },
    {
        "name": "Slow Cinema",
        "description": "Mostly cinematic: slow-mo peaks, minimal cuts, dramatic bars",
        "velocity": False, "zoom_punch": False, "color_flash": False,
        "letterbox": True, "beat_cuts": False, "slow_mo_peaks": True, "glitch": False,
    },
]


# ════════════════════════════════════════════════════════════════════════════
#  Style rotation
# ════════════════════════════════════════════════════════════════════════════

def _load_style_state() -> dict:
    if STYLE_STATE_FILE.exists():
        try:
            with open(STYLE_STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"run_count": 0}


def _save_style_state(state: dict):
    STYLE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STYLE_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def pick_style() -> dict:
    """Picks next VFX style sequentially (round-robin rotation across runs)."""
    state = _load_style_state()
    idx = state["run_count"] % len(STYLE_POOL)
    style = STYLE_POOL[idx]
    state["run_count"] += 1
    _save_style_state(state)
    print(f"🎨 [Style] Run #{state['run_count']} -> '{style['name']}': {style['description']}")
    return style


# ════════════════════════════════════════════════════════════════════════════
#  Per-clip VFX filtergraph builders
# ════════════════════════════════════════════════════════════════════════════

def _glitch_filter() -> str:
    """Chromatic aberration RGB split glitch."""
    return (
        "split=3[r][g][b];"
        "[r]lutrgb=r=val:g=0:b=0,geq=r='r(X+5,Y)':g='g(X,Y)':b='b(X,Y)'[r2];"
        "[g]lutrgb=r=0:g=val:b=0[g2];"
        "[b]lutrgb=r=0:g=0:b=val,geq=r='r(X-5,Y)':g='g(X,Y)':b='b(X,Y)'[b2];"
        "[r2][g2][b2]mix=inputs=3"
    )


def _zoom_punch_filter(factor: float = 1.08) -> str:
    """Fast zoom-in on clip start then snap back."""
    return (
        f"zoompan=z='if(lt(on,8),{factor},1)':d=1"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS}"
    )


def _color_flash_filter(hex_color: str = "ffffff") -> str:
    """Brief color flash on the first 0.05s of the clip."""
    return f"drawbox=t=fill:color=#{hex_color}@0.55:enable='lt(t,0.05)'"


def _letterbox_filter(bar_h: int = 80) -> str:
    """Cinematic top+bottom black bars."""
    return (
        f"drawbox=y=0:w={VIDEO_WIDTH}:h={bar_h}:color=black@1:t=fill,"
        f"drawbox=y={VIDEO_HEIGHT - bar_h}:w={VIDEO_WIDTH}:h={bar_h}:color=black@1:t=fill"
    )


def _scale_pad_filter() -> str:
    return (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"
    )


def build_clip_vfx(
    style: dict,
    clip_idx: int,
    total_clips: int,
    accent_hex: str,
    is_peak: bool,
) -> tuple:
    """Returns (video_filter_str, audio_filter_str, pts_factor) for one clip."""
    vf = []
    af = []
    pts_factor = 1.0  # default: no speed change

    is_intro = clip_idx == 0
    is_outro = clip_idx == total_clips - 1

    # Velocity / speed
    if style["slow_mo_peaks"] and is_peak:
        pts_factor = 1.0 / 0.45
        vf.append(f"setpts={pts_factor:.4f}*PTS")
        af.append("atempo=0.88")
    elif style["velocity"] and is_intro:
        pts_factor = 1.0 / 0.30
        vf.append(f"setpts={pts_factor:.4f}*PTS")
        af.append("atempo=0.94")
    elif style["velocity"] and is_outro:
        pts_factor = 1.0 / 0.50
        vf.append(f"setpts={pts_factor:.4f}*PTS")
        af.append("atempo=0.94")
    elif style["velocity"] and not is_peak:
        pts_factor = 1.0 / 1.40
        vf.append(f"setpts={pts_factor:.4f}*PTS")
        af.append("atempo=1.25")

    # Glitch (not on intro/outro)
    if style["glitch"] and not is_intro and not is_outro:
        vf.append(_glitch_filter())

    # Zoom punch on peaks
    if style["zoom_punch"] and is_peak:
        vf.append(_zoom_punch_filter(1.10))

    # Color flash on beat cuts
    if style["color_flash"] and style["beat_cuts"]:
        # sanitize hex
        hex_c = accent_hex.lstrip("#")[:6] if accent_hex else "ffffff"
        try:
            int(hex_c, 16)
        except ValueError:
            hex_c = "ffffff"
        vf.append(_color_flash_filter(hex_c))

    # Letterbox on intro/outro
    if style["letterbox"] and (is_intro or is_outro):
        vf.append(_letterbox_filter(80))

    # Always scale last
    vf.append(_scale_pad_filter())

    return ",".join(vf), ",".join(af) if af else "anull", pts_factor


# ════════════════════════════════════════════════════════════════════════════
#  Beat-sync cut durations
# ════════════════════════════════════════════════════════════════════════════

def get_cut_durations(audio_path: Path, target_duration: float) -> list:
    try:
        beats = analyze_audio_beats(str(audio_path))
        if beats and beats.beat_times:
            bt = [t for t in beats.beat_times if t < target_duration]
            if len(bt) >= 3:
                durations = [bt[i+1] - bt[i] for i in range(len(bt)-1)]
                durations.append(target_duration - bt[-1])
                return [d for d in durations if d > 0.4]
    except Exception as e:
        print(f"  ⚠️ Beat detection failed: {e} — using uniform cuts")

    n = max(15, int(target_duration / 3.5))
    base = target_duration / n
    return [base + random.uniform(-0.3, 0.5) for _ in range(n)]


# ════════════════════════════════════════════════════════════════════════════
#  AMV assembler
# ════════════════════════════════════════════════════════════════════════════

def assemble_amv(
    clips: list,
    audio_path: Path,
    output_path: Path,
    style: dict,
    character_theme: dict,
    target_duration: float,
    cc_preset: str = "jjk_void",
) -> Path:
    if not clips:
        raise RuntimeError("No clips provided.")

    print(f"\n🎬 [Assembler] {len(clips)} clips | {target_duration:.0f}s | Style: {style['name']}")

    cut_durations = get_cut_durations(audio_path, target_duration)
    clips_used = [clips[i % len(clips)] for i in range(len(cut_durations))]
    accent = character_theme.get("colors", ["#ffffff"])[0]

    n_peaks = max(1, len(clips_used) // 5)
    peak_set = set(random.sample(range(1, max(2, len(clips_used)-1)), min(n_peaks, len(clips_used)-2)))
    print(f"  ✂️  {len(clips_used)} segments | peaks at: {sorted(peak_set)}")

    trimmed_dir = SCRATCH_DIR / "amv_trimmed"
    shutil.rmtree(trimmed_dir, ignore_errors=True)
    trimmed_dir.mkdir(parents=True, exist_ok=True)
    trimmed_clips = []

    for i, (clip_path, dur) in enumerate(zip(clips_used, cut_durations)):
        out_seg = trimmed_dir / f"seg_{i:04d}.mp4"
        vf, af, pts = build_clip_vfx(style, i, len(clips_used), accent, i in peak_set)

        # Adjust requested duration for speed change
        src_dur = dur * pts  # how many source seconds to read

        cmd = [
            "ffmpeg", "-y",
            "-ss", "0", "-t", f"{src_dur:.3f}",
            "-i", str(clip_path),
            "-vf", vf,
        ]
        if af != "anull":
            cmd += ["-af", af]
        cmd += [
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k",
            "-r", str(FPS), "-pix_fmt", "yuv420p",
            "-t", f"{dur:.3f}",
            str(out_seg),
        ]

        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            # Minimal fallback
            subprocess.run([
                "ffmpeg", "-y",
                "-ss", "0", "-t", f"{dur:.3f}",
                "-i", str(clip_path),
                "-vf", _scale_pad_filter(),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                "-r", str(FPS), "-pix_fmt", "yuv420p",
                str(out_seg),
            ], capture_output=True)

        if out_seg.exists():
            trimmed_clips.append(out_seg)

    if not trimmed_clips:
        raise RuntimeError("All clip trimming failed.")

    # Write concat list
    list_file = SCRATCH_DIR / "amv_concat.txt"
    with open(list_file, "w") as f:
        for tc in trimmed_clips:
            f.write(f"file '{tc.resolve()}'\n")

    concat_out = SCRATCH_DIR / "amv_concat_raw.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(concat_out),
    ], check=True)

    cc_filter = build_cc_filter(cc_preset)
    print(f"  🎨 Color grade: {cc_preset} | 🎵 Audio: {audio_path.name}")

    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(concat_out),
        "-stream_loop", "-1", "-i", str(audio_path),
        "-filter_complex",
            f"[0:v]{cc_filter}[vc];"
            f"[1:a]atrim=0:{target_duration},afade=t=out:st={target_duration-2}:d=2,"
            f"aformat=sample_rates=48000[ac]",
        "-map", "[vc]", "-map", "[ac]",
        "-t", f"{target_duration:.3f}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-c:a", "aac", "-b:a", "256k",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ], check=True)

    print(f"  ✅ AMV rendered -> {output_path}")
    return output_path


# ════════════════════════════════════════════════════════════════════════════
#  Google Drive upload helpers
# ════════════════════════════════════════════════════════════════════════════

def _gdrive_token() -> str:
    import urllib.parse, urllib.request
    data = urllib.parse.urlencode({
        "client_id": os.environ["CLIENT_ID"],
        "client_secret": os.environ["CLIENT_SECRET"],
        "refresh_token": os.environ.get("GDRIVE_REFRESH_TOKEN") or os.environ["REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["access_token"]


def _gdrive_api(token: str, method: str, url: str, payload=None) -> dict:
    import urllib.request
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _find_or_create_folder(token: str, name: str, parent_id: str) -> str:
    import urllib.parse
    q = urllib.parse.quote(
        f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed=false"
    )
    r = _gdrive_api(token, "GET", f"https://www.googleapis.com/drive/v3/files?q={q}&fields=files(id)")
    files = r.get("files", [])
    if files:
        return files[0]["id"]
    created = _gdrive_api(token, "POST", "https://www.googleapis.com/drive/v3/files", {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    })
    return created["id"]


def _upload_file(token: str, file_path: Path, folder_id: str) -> str:
    import mimetypes, urllib.request
    size = file_path.stat().st_size
    mime = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    meta = json.dumps({"name": file_path.name, "parents": [folder_id]}).encode()
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
        data=meta,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": mime,
            "X-Upload-Content-Length": str(size),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        session_url = r.headers["Location"]

    with open(file_path, "rb") as fh:
        data = fh.read()
    req2 = urllib.request.Request(session_url, data=data, method="PUT")
    req2.add_header("Content-Type", mime)
    req2.add_header("Content-Length", str(size))
    with urllib.request.urlopen(req2, timeout=600) as r2:
        fid = json.load(r2).get("id", "")

    url = f"https://drive.google.com/file/d/{fid}/view"
    print(f"  ☁️  '{file_path.name}' -> {url}")
    return url


def _snapshot_code(label: str) -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    snap = SCRATCH_DIR / f"code_snapshot_{label}.zip"
    with zipfile.ZipFile(snap, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in ["scripts", "core", "config", "main.py", "requirements.txt"]:
            p = repo_root / item
            if p.is_file():
                zf.write(p, item)
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file() and "__pycache__" not in str(f):
                        zf.write(f, str(f.relative_to(repo_root)))
    print(f"  📦 Code snapshot: {snap.name} ({snap.stat().st_size // 1024} KB)")
    return snap


# ════════════════════════════════════════════════════════════════════════════
#  Main orchestrator
# ════════════════════════════════════════════════════════════════════════════

def run_gdrive_amv(
    source_folder: str,
    universe: str,
    character,
    target_duration: float,
    upload_youtube: bool = False,
    upload_gdrive: bool = False,
    phonk_name=None,
) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    style = pick_style()
    char_label = character or universe
    label = f"AMV_{char_label.upper()}_{style['name'].replace(' ', '_')}_{ts}"

    print(f"\n🚀 [GDrive AMV Builder]  {label}")
    print(f"   Source  : drive.google.com/drive/folders/{source_folder}")
    print(f"   Universe: {universe.upper()} | Character: {character or 'auto'}")
    print(f"   Duration: {target_duration:.0f}s")

    # Resolve character
    if character and character not in CHARACTER_THEMES:
        print(f"  ⚠️ Unknown character '{character}' — auto-picking.")
        character = None
    if not character:
        candidates = [k for k, v in CHARACTER_THEMES.items() if v.get("universe") == universe]
        character = random.choice(candidates) if candidates else ("gojo" if universe == "jjk" else "ironman")
        print(f"  🎭 Auto-selected: {character}")

    theme = CHARACTER_THEMES[character]
    cc_preset = theme.get("cc_preset", "jjk_void")

    # Fetch clips from source GDrive folder
    print(f"\n📥 [1/4] Fetching footage from Drive...")
    gdrive_clip_dir = SCRATCH_DIR / "gdrive_clips"
    gdrive_clip_dir.mkdir(parents=True, exist_ok=True)
    clips = fetch_and_prepare_gdrive_footage(
        gdrive_url_or_id=source_folder,
        target_character=character,
        output_dir=gdrive_clip_dir,
        n_clips=25,
    )
    if not clips:
        print("  ⚠️ Drive clips empty — trying free-stream fallback...")
        from core.free_stream_fetcher import fetch_free_stream_clips
        fallback_dir = SCRATCH_DIR / "freestream_clips"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        clips = fetch_free_stream_clips(
            character_key=character,
            output_dir=fallback_dir,
            n_clips=20,
        )
    if not clips:
        raise RuntimeError(f"No clips found for '{character}'. Check Drive folder.")
    print(f"  ✅ {len(clips)} clips ready")

    # Get phonk audio
    print(f"\n🎵 [2/4] Sourcing phonk audio...")
    audio_path = get_random_or_specified_phonk(phonk_name)
    if not audio_path or not Path(str(audio_path)).exists():
        from core.video_assembler import generate_fallback_phonk_audio
        audio_path = generate_fallback_phonk_audio(target_duration, SCRATCH_DIR / f"fb_phonk_{ts}.aac")
    audio_path = Path(str(audio_path))
    print(f"  ✅ {audio_path.name}")

    # Assemble AMV
    print(f"\n🎬 [3/4] Assembling AMV...")
    output_path = OUTPUT_DIR / f"{label}.mp4"
    assemble_amv(
        clips=clips,
        audio_path=audio_path,
        output_path=output_path,
        style=style,
        character_theme=theme,
        target_duration=target_duration,
        cc_preset=cc_preset,
    )

    # Step 4: Upload MP4 + code snapshot to Google Drive
    drive_url = None
    if upload_gdrive:
        print(f"\n☁️  [4/5] Uploading to Drive AMV_Outputs/...")
        try:
            token = _gdrive_token()
            amv_out_id = _find_or_create_folder(token, "AMV_Outputs", source_folder)
            run_folder_id = _find_or_create_folder(token, label, amv_out_id)
            _upload_file(token, output_path, run_folder_id)   # MP4 only
            snap = _snapshot_code(label)                       # code snapshot ZIP
            _upload_file(token, snap, run_folder_id)
            drive_url = f"https://drive.google.com/drive/folders/{run_folder_id}"
            print(f"  ✅ Drive folder: {drive_url}")
        except Exception as e:
            print(f"  ⚠️ Drive upload error: {e}")
            print(f"     Local output: {output_path}")

    # Step 5: Upload MP4 ONLY to YouTube (no code snapshot)
    if upload_youtube:
        print(f"\n🎬 [5/5] Uploading to YouTube...")
        try:
            from publishers.youtube_publisher import upload_video_to_youtube
            char_name = theme.get("name", character.title())
            yt_title = (
                f"{char_name} AMV 🔥 {style['name']} Edit | "
                f"{'JJK' if universe == 'jjk' else 'Marvel'} {datetime.now().strftime('%Y')} #anime #shorts"
            )[:95]
            yt_desc = (
                f"🎬 {char_name} Hybrid Action/Cinematic AMV Edit\n"
                f"🎨 Style: {style['name']} — {style['description']}\n"
                f"🎵 Music: Phonk\n"
                f"{'🌀 Universe: Jujutsu Kaisen' if universe == 'jjk' else '⚡ Universe: Marvel'}\n\n"
                f"Auto-generated by AniDoc AMV Engine 🤖\n"
                f"Raw footage from personal Drive library.\n\n"
                f"#anime #amv #jjk #marvel #phonk #edit #shorts #viral"
            )
            yt_tags = [
                char_name, universe.upper(), "AMV", "anime edit", "phonk",
                "Shorts", "viral", "4K", style["name"],
                "jjk" if universe == "jjk" else "marvel",
                "anime", "edit", "2026",
            ]
            result = upload_video_to_youtube(
                video_path=output_path,
                title=yt_title,
                description=yt_desc,
                tags=yt_tags,
                privacy_status="public",
            )
            if result.get("status") == "success":
                print(f"  ✅ YouTube: {result.get('url')}")
            else:
                print(f"  ⚠️ YouTube upload skipped/failed: {result.get('reason') or result.get('error')}")
        except Exception as e:
            print(f"  ⚠️ YouTube upload error: {e}")

    if not upload:
        print(f"\n✅ Done (local only): {output_path}")
    else:
        print(f"\n✅ Run complete. Drive: {drive_url or 'see above'}")

    # Cleanup tmp trimmed clips
    shutil.rmtree(SCRATCH_DIR / "amv_trimmed", ignore_errors=True)
    return output_path


# ════════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="GDrive AMV Builder — Hybrid Action/Cinematic VFX Edit Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # JJK Gojo 75s with upload:
  python3 scripts/gdrive_amv_builder.py --universe jjk --character gojo --duration 75 --upload

  # Marvel auto-character 60s:
  python3 scripts/gdrive_amv_builder.py --universe marvel --duration 60 --upload

  # Custom source folder, no upload:
  python3 scripts/gdrive_amv_builder.py --source-folder FOLDER_ID --universe jjk --duration 90

  # List styles:
  python3 scripts/gdrive_amv_builder.py --list-styles
""",
    )
    parser.add_argument("--source-folder", default=SOURCE_FOLDER_ID,
                        help=f"GDrive folder ID/URL with raw footage (default: {SOURCE_FOLDER_ID})")
    parser.add_argument("--universe", choices=["jjk", "marvel"], default="jjk",
                        help="Universe: 'jjk' or 'marvel'. Characters from other universes are excluded.")
    parser.add_argument("--character", default=None,
                        help="Character key (gojo/sukuna/ironman/etc). Auto-picked if omitted.")
    parser.add_argument("--duration", type=float, default=75.0,
                        help="Target AMV duration in seconds (default: 75.0)")
    parser.add_argument("--phonk", default=None,
                        help="Specific phonk track name from library (auto-picked if omitted)")
    parser.add_argument("--upload-youtube", action="store_true",
                        help="Upload final MP4 to YouTube Shorts (public). Code snapshot is NOT uploaded here.")
    parser.add_argument("--upload-gdrive", action="store_true",
                        help="Upload final MP4 + code snapshot ZIP to AMV_Outputs/ in your Drive folder.")
    parser.add_argument("--list-styles", action="store_true",
                        help="Print all VFX styles with rotation status and exit")

    args = parser.parse_args()

    if args.list_styles:
        state = _load_style_state()
        current = state["run_count"] % len(STYLE_POOL)
        print("\n🎨 VFX Style Pool (sequential rotation):\n")
        for i, s in enumerate(STYLE_POOL):
            marker = " <-- NEXT RUN" if i == current else ""
            effects = [k.replace("_", " ").title() for k, v in s.items()
                       if isinstance(v, bool) and v]
            print(f"  [{i}] {s['name']:<22} {s['description']}{marker}")
            print(f"       FX: {', '.join(effects)}\n")
        return 0

    run_gdrive_amv(
        source_folder=args.source_folder,
        universe=args.universe,
        character=args.character,
        target_duration=args.duration,
        upload_youtube=args.upload_youtube,
        upload_gdrive=args.upload_gdrive,
        phonk_name=args.phonk,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
