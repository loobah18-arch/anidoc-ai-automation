#!/usr/bin/env python3
"""
GDrive AMV Builder v2 — Professional Velocity Edit Engine
==========================================================
Reads raw footage from Google Drive, assembles a 60-90s AMV with
techniques matching professional human-made edits:

  - True velocity curves: 0.3x intro -> 1.5x drop -> 1.8x drop2 -> 0.45x slow-mo
  - Beat-synced timeline: intro/drop1/breakdown/drop2/outro phases
  - Variable clip lengths: 2-3s intro, 0.2-0.5s drops, 0.15-0.3s drop2
  - Flash frames (1-2 frame white/black cuts) between action clips
  - Motion blur via tblend on fast sections
  - Scale zoom-punch (no zoompan jitter)
  - Audio: loudnorm + compressor + EQ for punchy phonk
  - Per-character CC presets

References: MRurnn3AxyA / xT4qeJwVnDI / lX7bIlY_KEE

Usage:
  python3 scripts/gdrive_amv_builder.py \\
      --universe jjk --character gojo --duration 75 \\
      --upload-youtube --upload-gdrive
"""
import argparse
import json
import os
import random
import shutil
import subprocess
import sys
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

# ── constants ─────────────────────────────────────────────────────────────────
SOURCE_FOLDER_ID = "1e5_IF3GRHNr315hP5zK_qlyfsKXm3Ox4"
# In config/ (git-tracked) — persists rotation across CI runs
STYLE_STATE_FILE = Path(__file__).resolve().parent.parent / "config" / "amv_style_rotation.json"

# ── VFX Style Pool ────────────────────────────────────────────────────────────
STYLE_POOL = [
    {
        "name": "Velocity Rush",
        "description": "0.3x intro -> 1.5x drop snap -> 0.45x slow-mo peaks",
        "velocity": True, "zoom_punch": True, "color_flash": True,
        "letterbox": True, "beat_cuts": True, "slow_mo_peaks": True,
        "glitch": False, "flash_frames": True, "motion_blur": True,
    },
    {
        "name": "Glitch Storm",
        "description": "RGB split chromatic aberration + fast cuts + color flash",
        "velocity": True, "zoom_punch": False, "color_flash": True,
        "letterbox": False, "beat_cuts": True, "slow_mo_peaks": False,
        "glitch": True, "flash_frames": True, "motion_blur": False,
    },
    {
        "name": "Zoom Punch",
        "description": "Scale zoom-in on impact + slow-mo release + letterbox",
        "velocity": False, "zoom_punch": True, "color_flash": True,
        "letterbox": True, "beat_cuts": True, "slow_mo_peaks": True,
        "glitch": False, "flash_frames": False, "motion_blur": True,
    },
    {
        "name": "Cinematic Flash",
        "description": "Letterbox bars + color leaks on beat + slow-mo climax",
        "velocity": True, "zoom_punch": False, "color_flash": True,
        "letterbox": True, "beat_cuts": True, "slow_mo_peaks": True,
        "glitch": False, "flash_frames": True, "motion_blur": False,
    },
    {
        "name": "Full VFX Stack",
        "description": "All effects: velocity + glitch + zoom + flash + blur + slow-mo",
        "velocity": True, "zoom_punch": True, "color_flash": True,
        "letterbox": True, "beat_cuts": True, "slow_mo_peaks": True,
        "glitch": True, "flash_frames": True, "motion_blur": True,
    },
    {
        "name": "Slow Cinema",
        "description": "Cinematic bars, slow-mo peaks, minimal cuts, dramatic tension",
        "velocity": False, "zoom_punch": False, "color_flash": False,
        "letterbox": True, "beat_cuts": False, "slow_mo_peaks": True,
        "glitch": False, "flash_frames": False, "motion_blur": True,
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
    state = _load_style_state()
    idx = state["run_count"] % len(STYLE_POOL)
    style = STYLE_POOL[idx]
    state["run_count"] += 1
    _save_style_state(state)
    print(f"🎨 [Style] Run #{state['run_count']} -> '{style['name']}': {style['description']}")
    return style


# ════════════════════════════════════════════════════════════════════════════
#  Beat timeline builder
# ════════════════════════════════════════════════════════════════════════════

def get_beat_timeline(audio_path: Path, target_duration: float) -> list:
    """
    Returns structured segments: [{start, duration, is_drop, is_peak, role}]

    Structure matching reference video analysis:
      Intro (0-20%):    slow holds 1.5-3s, atmospheric
      Drop 1 (20-55%):  fast cuts 0.2-0.5s, action bursts
      Breakdown (55-70%): medium 0.8-1.5s, slower
      Drop 2 (70-90%):  ultra-fast 0.12-0.3s
      Outro (90-100%):  slow cinematic hold
    """
    try:
        beats = analyze_audio_beats(str(audio_path))
        if beats and beats.beat_times and len(beats.beat_times) >= 8:
            raw = [t for t in beats.beat_times if t < target_duration]
            segments = []
            n = len(raw)
            drop_threshold = 0.38  # beat gap < this = fast section = drop
            in_drop = False
            drop_count = 0

            for i in range(len(raw) - 1):
                bt = raw[i]
                gap = raw[i+1] - bt
                was_drop = in_drop
                in_drop = gap < drop_threshold
                if not was_drop and in_drop:
                    drop_count += 1

                # Assign role and duration
                if i < 6:
                    role = "intro"
                    dur = min(gap * 2.5, 3.0)
                elif in_drop and drop_count == 1:
                    role = "drop1"
                    dur = max(gap * 0.8, 0.18)
                elif not in_drop and drop_count >= 1:
                    role = "breakdown"
                    dur = min(gap * 1.5, 2.0)
                elif in_drop and drop_count >= 2:
                    role = "drop2"
                    dur = max(gap * 0.6, 0.12)
                else:
                    role = "mid"
                    dur = gap

                segments.append({
                    "start": bt,
                    "duration": round(max(dur, 0.12), 3),
                    "is_drop": in_drop,
                    "is_peak": (i % 4 == 0) and in_drop,
                    "role": role,
                })

            # Outro
            if raw:
                rem = target_duration - raw[-1]
                if rem > 1.0:
                    segments.append({
                        "start": raw[-1],
                        "duration": round(rem, 3),
                        "is_drop": False, "is_peak": False, "role": "outro",
                    })

            total = sum(s["duration"] for s in segments)
            print(f"  🎵 Beat timeline: {len(segments)} cuts, {total:.1f}s, {drop_count} drops detected")
            return segments
    except Exception as e:
        print(f"  ⚠️ Beat analysis error: {e} — using structured fallback")

    return _fallback_timeline(target_duration)


def _fallback_timeline(dur: float) -> list:
    segs = []
    t = 0.0

    # Intro: 6 slow clips
    for i in range(6):
        d = random.uniform(1.8, 2.5)
        segs.append({"start": t, "duration": d, "is_drop": False, "is_peak": False, "role": "intro"})
        t += d
        if t >= dur * 0.22: break

    # Drop 1: fast clips for ~18s
    end1 = min(t + 18.0, dur * 0.55)
    idx = 0
    while t < end1:
        d = random.uniform(0.20, 0.45)
        segs.append({"start": t, "duration": d, "is_drop": True, "is_peak": idx % 4 == 0, "role": "drop1"})
        t += d; idx += 1

    # Breakdown: 5 medium clips
    end2 = min(t + 9.0, dur * 0.72)
    while t < end2:
        d = random.uniform(1.0, 1.8)
        segs.append({"start": t, "duration": d, "is_drop": False, "is_peak": False, "role": "breakdown"})
        t += d

    # Drop 2: ultra-fast
    end3 = min(t + 14.0, dur - 5.0)
    while t < end3:
        d = random.uniform(0.12, 0.28)
        segs.append({"start": t, "duration": d, "is_drop": True, "is_peak": idx % 3 == 0, "role": "drop2"})
        t += d; idx += 1

    # Outro
    rem = dur - t
    if rem > 1.0:
        segs.append({"start": t, "duration": rem, "is_drop": False, "is_peak": False, "role": "outro"})

    print(f"  🎵 Fallback timeline: {len(segs)} cuts")
    return segs


# ════════════════════════════════════════════════════════════════════════════
#  Velocity curves
# ════════════════════════════════════════════════════════════════════════════

def get_velocity(seg: dict, style: dict) -> float:
    """
    Professional velocity curves matching reference video analysis:
      intro:     0.30x — atmospheric slow tension, holds on face
      drop1:     1.50x — explosive snap, burst action
      breakdown: 0.70x — slightly slow for clarity
      drop2:     1.80x — even faster, ultra-cut frenzy
      peak:      0.45x — sakuga slow-mo on key moments
      outro:     0.40x — dramatic fade into black
    """
    role = seg.get("role", "mid")
    is_peak = seg.get("is_peak", False)

    # Slow Cinema: no speed changes
    if not style.get("velocity") and not style.get("slow_mo_peaks"):
        return 1.0

    if style.get("slow_mo_peaks") and is_peak:
        return 0.45

    return {
        "intro":     0.30 if style.get("velocity") else 0.60,
        "drop1":     1.50 if style.get("velocity") else 1.00,
        "breakdown": 0.70 if style.get("velocity") else 0.85,
        "drop2":     1.80 if style.get("velocity") else 1.20,
        "mid":       1.10,
        "outro":     0.40 if style.get("velocity") else 0.50,
    }.get(role, 1.0)


# ════════════════════════════════════════════════════════════════════════════
#  FFmpeg filter builders
# ════════════════════════════════════════════════════════════════════════════

def _motion_blur(speed: float) -> str:
    """Frame-blend motion blur on fast sections only."""
    return "tblend=all_mode=average" if speed > 1.2 else ""


def _zoom_punch(scale: float = 1.08) -> str:
    """
    Smooth zoom punch: scale-in over 14 frames then ease back to 1.0x.
    Uses zoompan for eased curve (ease-down looks more professional than snap crop).
    scale: peak zoom factor (1.08 = 8% zoom on drops, 1.12 on drop2).
    """
    # Ease-down from scale to 1.0 over 14 frames
    return (
        f"zoompan=z='if(lte(in,14),{scale:.3f}-({scale:.3f}-1.0)*(in/14.0),1.0)'"
        f":d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS}"
    )


def _glitch() -> str:
    """
    Chromatic aberration using rgbashift (faster than geq split, same visual).
    R channel +6px right, B channel -6px left — matches reference video analysis.
    Fallback to geq mix if rgbashift unavailable.
    """
    # Try rgbashift first (ffmpeg 4.3+)
    return "rgbashift=rh=6:bh=-6"


def _camera_shake() -> str:
    """
    Impact displacement shake — ±14px translate burst on first 8 frames.
    Alternates left/right per frame for maximum visceral punch feel.
    Matches: geq displacement method from reference analysis.
    """
    return (
        "geq="
        "lum='p(X+(if(lt(N,8),if(eq(mod(N,2),0),14,-14),0)),Y)'"
        ":cb='cb(X+(if(lt(N,8),if(eq(mod(N,2),0),14,-14),0)),Y)'"
        ":cr='cr(X+(if(lt(N,8),if(eq(mod(N,2),0),14,-14),0)),Y)'"
    )


def _pre_drop_flicker(clip_duration: float) -> str:
    """
    Sinusoidal brightness flicker in the last 1.5s of a clip before the drop.
    3Hz oscillation at amplitude 0.08 — builds subconscious tension.
    Only applied to the last pre-drop clip (breakdown -> drop1 boundary).
    """
    start = max(0.0, clip_duration - 1.5)
    return f"eq=brightness='if(between(t,{start:.2f},{clip_duration:.2f}),sin(t*6.28*3)*0.08,0)'"


def _flash_and_dip(flash_t: float = 0.0, flash_dur: float = 0.06, dip_dur: float = 0.04) -> str:
    """
    White impact flash followed by brief dark dip — professional drop transition.
    flash_t: time within clip when drop hits.
    Produces: white@0.85 for flash_dur, then black@0.65 for dip_dur.
    """
    dip_t = flash_t + flash_dur
    end_t = dip_t + dip_dur
    return (
        f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.85:t=fill:"
        f"enable='between(t,{flash_t:.3f},{dip_t:.3f})',"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.65:t=fill:"
        f"enable='between(t,{dip_t:.3f},{end_t:.3f})'"
    )


def _color_flash(hex_c: str, opacity: float, dur: float) -> str:
    return f"drawbox=t=fill:color=#{hex_c}@{opacity}:enable='lt(t,{dur})'"


def _letterbox(bar_h: int = 72) -> str:
    return (
        f"drawbox=y=0:w={VIDEO_WIDTH}:h={bar_h}:color=black@1:t=fill,"
        f"drawbox=y={VIDEO_HEIGHT-bar_h}:w={VIDEO_WIDTH}:h={bar_h}:color=black@1:t=fill"
    )


def _scale_pad() -> str:
    return (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"
    )


def build_clip_vfx(style: dict, seg: dict, accent_hex: str, next_role: str = "") -> tuple:
    """
    Returns (vf_str, af_str, speed) for one clip segment.

    Implements research-backed professional AMV techniques:
    - Velocity: 0.30x intro / 1.50x drop1 / 1.80x drop2 / 0.45x peak slow-mo
    - Camera shake: ±14px displacement on first 8 frames of drops
    - Chromatic aberration: rgbashift R+6/B-6 on drops
    - Zoom punch: smooth ease-down over 14 frames
    - Flash+dark-dip: white 0.06s then black 0.04s on drop entry
    - Pre-drop flicker: 3Hz sinusoidal brightness in last 1.5s before drop
    - Motion blur: tblend on fast sections
    """
    role = seg.get("role", "mid")
    is_peak = seg.get("is_peak", False)
    speed = get_velocity(seg, style)
    uses_glitch = style.get("glitch") and role not in ("intro", "outro")
    is_drop = role in ("drop1", "drop2")
    dur = seg.get("duration", 1.0)

    vf = []
    af = []

    # ── 1. Velocity setpts ────────────────────────────────────────────────
    if speed != 1.0:
        vf.append(f"setpts={1.0/speed:.4f}*PTS")
        if speed < 0.5:
            af.append(f"atempo=0.5,atempo={speed/0.5:.3f}")
        elif speed > 2.0:
            af.append(f"atempo=2.0,atempo={speed/2.0:.3f}")
        else:
            af.append(f"atempo={speed:.3f}")

    # ── 2. Motion blur on fast sections ──────────────────────────────────
    if style.get("motion_blur") and not uses_glitch:
        mb = _motion_blur(speed)
        if mb:
            vf.append(mb)

    # ── 3. Chromatic aberration on drops (uses rgbashift, no filter_complex) ──
    if uses_glitch and is_drop:
        vf.append("rgbashift=rh=6:bh=-6")

    # ── 4. Camera shake on drop entry ─────────────────────────────────────
    if is_drop and (style.get("zoom_punch") or style.get("glitch")):
        vf.append(_camera_shake())

    # ── 5. Zoom punch with ease-down curve ───────────────────────────────
    if style.get("zoom_punch") and (is_peak or is_drop):
        factor = 1.14 if role == "drop2" else 1.09
        vf.append(_zoom_punch(factor))

    # ── 6. Pre-drop flicker (last clip before drop) ───────────────────────
    if style.get("beat_cuts") and role == "breakdown" and next_role in ("drop1", "drop2"):
        vf.append(_pre_drop_flicker(dur))

    # ── 7. Flash + dark dip on first drop frame ───────────────────────────
    if style.get("flash_frames") and is_drop and is_peak:
        vf.append(_flash_and_dip(flash_t=0.0, flash_dur=0.06, dip_dur=0.04))

    # ── 8. Color flash on beat cuts ───────────────────────────────────────
    if style.get("color_flash") and style.get("beat_cuts") and not is_peak:
        hex_c = accent_hex.lstrip("#")[:6] if accent_hex else "ffffff"
        try: int(hex_c, 16)
        except ValueError: hex_c = "ffffff"
        opacity = 0.85 if is_drop else 0.50
        fdur = 0.03 if is_drop else 0.05
        vf.append(_color_flash(hex_c, opacity, fdur))

    # ── 9. Letterbox on non-action sections ──────────────────────────────
    if style.get("letterbox") and role in ("intro", "breakdown", "outro"):
        vf.append(_letterbox(80))

    # ── 10. Always scale pad last ─────────────────────────────────────────
    vf.append(_scale_pad())

    return ",".join(vf), (",".join(af) if af else "anull"), speed


def make_flash_frame(color: str, dur: float, out: Path) -> Path:
    """Single-color clip for flash transitions (white or black)."""
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={color}:size={VIDEO_WIDTH}x{VIDEO_HEIGHT}:rate={FPS}",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-t", f"{dur:.4f}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
        str(out),
    ], capture_output=True)
    return out


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

    print(f"\n🎬 [Assembler v2] {len(clips)} source clips | {target_duration:.0f}s | {style['name']}")

    timeline = get_beat_timeline(audio_path, target_duration)
    if not timeline:
        raise RuntimeError("Failed to build beat timeline.")

    accent = character_theme.get("colors", ["#ffffff"])[0]
    trimmed_dir = SCRATCH_DIR / "amv_trimmed"
    shutil.rmtree(trimmed_dir, ignore_errors=True)
    trimmed_dir.mkdir(parents=True, exist_ok=True)

    # Pre-generate flash frames
    white_flash = trimmed_dir / "flash_white.mp4"
    black_flash = trimmed_dir / "flash_black.mp4"
    if style.get("flash_frames"):
        make_flash_frame("white", 0.05, white_flash)
        make_flash_frame("black", 0.05, black_flash)

    # Shuffle clips so we don't repeat the same source footage
    clip_pool = list(clips)
    random.shuffle(clip_pool)

    trimmed_clips = []
    print(f"  ✂️  Processing {len(timeline)} segments...")

    for i, seg in enumerate(timeline):
        out_seg = trimmed_dir / f"seg_{i:04d}.mp4"
        clip_path = clip_pool[i % len(clip_pool)]
        dur = seg["duration"]
        role = seg.get("role", "mid")
        uses_glitch = style.get("glitch") and role not in ("intro", "outro")

        next_role = timeline[i+1].get("role", "") if i < len(timeline) - 1 else ""
        vf, af, speed = build_clip_vfx(style, seg, accent, next_role=next_role)

        # Read more source frames proportional to speed
        src_dur = dur * speed

        # Random seek within source clip (avoids repetition)
        try:
            p = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", str(clip_path)],
                capture_output=True, text=True
            )
            clip_len = float(p.stdout.strip() or "3.2")
        except Exception:
            clip_len = 3.2

        max_ss = max(0.0, clip_len - src_dur - 0.05)
        ss = random.uniform(0.0, max_ss) if max_ss > 0 else 0.0

        # All filters now use -vf (rgbashift doesn't need filter_complex)
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{ss:.3f}", "-t", f"{src_dur:.3f}",
            "-i", str(clip_path),
            "-vf", vf,
        ]

        if af != "anull":
            cmd += ["-af", af]

        cmd += [
            "-c:v", "libx264", "-preset", "fast", "-crf", "17",
            "-c:a", "aac", "-b:a", "192k",
            "-r", str(FPS), "-pix_fmt", "yuv420p",
            "-t", f"{dur:.3f}",
            str(out_seg),
        ]

        result = subprocess.run(cmd, capture_output=True)

        # Fallback: plain cut if VFX fails
        if result.returncode != 0 or not out_seg.exists():
            subprocess.run([
                "ffmpeg", "-y",
                "-ss", f"{ss:.3f}", "-t", f"{dur:.3f}",
                "-i", str(clip_path),
                "-vf", _scale_pad(),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                "-r", str(FPS), "-pix_fmt", "yuv420p",
                str(out_seg),
            ], capture_output=True)

        if out_seg.exists() and out_seg.stat().st_size > 500:
            trimmed_clips.append(out_seg)

            # Insert flash frames between consecutive drop cuts
            if style.get("flash_frames") and role in ("drop1", "drop2") and i < len(timeline) - 1:
                next_role = timeline[i+1].get("role", "")
                if next_role in ("drop1", "drop2"):
                    flash_seg = trimmed_dir / f"flash_{i:04d}.mp4"
                    src_flash = white_flash if i % 2 == 0 else black_flash
                    if src_flash.exists():
                        shutil.copy(src_flash, flash_seg)
                        trimmed_clips.append(flash_seg)

    if not trimmed_clips:
        raise RuntimeError("All clip trimming failed.")

    print(f"  ✅ {len(trimmed_clips)} segments ready (incl. flash frames)")

    # Concatenate
    list_file = SCRATCH_DIR / "amv_concat.txt"
    with open(list_file, "w") as f:
        for tc in trimmed_clips:
            f.write(f"file '{tc.resolve()}'\n")

    concat_out = SCRATCH_DIR / "amv_concat_raw.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", str(concat_out),
    ], check=True, capture_output=True)

    cc_filter = build_cc_filter(cc_preset)
    print(f"  🎨 CC: {cc_preset} | 🎵 {audio_path.name}")

    # Final encode with punchy audio chain
    audio_chain = (
        f"[1:a]atrim=0:{target_duration},"
        "loudnorm=I=-14:TP=-1:LRA=11,"
        "acompressor=threshold=-18dB:ratio=4:attack=5:release=80:makeup=3dB,"
        "equalizer=f=10000:t=h:width=3000:g=3,"
        f"afade=t=out:st={target_duration-2.0:.3f}:d=2.0,"
        "aformat=sample_rates=48000[ac]"
    )

    r = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(concat_out),
        "-stream_loop", "-1", "-i", str(audio_path),
        "-filter_complex", f"[0:v]{cc_filter}[vc];{audio_chain}",
        "-map", "[vc]", "-map", "[ac]",
        "-t", f"{target_duration:.3f}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-c:a", "aac", "-b:a", "320k",
        "-movflags", "+faststart", "-pix_fmt", "yuv420p",
        str(output_path),
    ], capture_output=True)

    if r.returncode != 0:
        # Fallback without loudnorm
        audio_chain_fb = (
            f"[1:a]atrim=0:{target_duration},"
            "acompressor=threshold=-18dB:ratio=4:attack=5:release=80:makeup=3dB,"
            f"afade=t=out:st={target_duration-2.0:.3f}:d=2.0,"
            "aformat=sample_rates=48000[ac]"
        )
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(concat_out),
            "-stream_loop", "-1", "-i", str(audio_path),
            "-filter_complex", f"[0:v]{cc_filter}[vc];{audio_chain_fb}",
            "-map", "[vc]", "-map", "[ac]",
            "-t", f"{target_duration:.3f}",
            "-c:v", "libx264", "-preset", "slow", "-crf", "16",
            "-c:a", "aac", "-b:a", "320k",
            "-movflags", "+faststart", "-pix_fmt", "yuv420p",
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


def _gdrive_api(token, method, url, payload=None):
    import urllib.request
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _find_or_create_folder(token, name, parent_id):
    import urllib.parse
    q = urllib.parse.quote(
        f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed=false"
    )
    r = _gdrive_api(token, "GET", f"https://www.googleapis.com/drive/v3/files?q={q}&fields=files(id)")
    files = r.get("files", [])
    if files:
        return files[0]["id"]
    return _gdrive_api(token, "POST", "https://www.googleapis.com/drive/v3/files", {
        "name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id],
    })["id"]


def _upload_file(token, file_path, folder_id):
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


def _snapshot_code(label):
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

    print(f"\n🚀 [GDrive AMV Builder v2]  {label}")
    print(f"   Source  : drive.google.com/drive/folders/{source_folder}")
    print(f"   Universe: {universe.upper()} | Character: {character or 'auto'}")
    print(f"   Duration: {target_duration:.0f}s | Style: {style['name']}")

    # Resolve character theme
    theme = {}
    if character and character in CHARACTER_THEMES:
        theme = CHARACTER_THEMES[character]
    else:
        universe_chars = [k for k, v in CHARACTER_THEMES.items() if v.get("universe") == universe]
        if universe_chars:
            character = random.choice(universe_chars)
            theme = CHARACTER_THEMES[character]
            print(f"   Auto-character: {character}")
    cc_preset = theme.get("cc_preset", "jjk_void" if universe == "jjk" else "marvel_hdr")

    # Step 1: Fetch clips
    print(f"\n📥 [1/5] Fetching footage from Drive...")
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
            character_key=character, output_dir=fallback_dir, n_clips=20,
        )
    if not clips:
        raise RuntimeError(f"No clips found for '{character}'. Check Drive folder.")
    print(f"  ✅ {len(clips)} clips ready")

    # Step 2: Phonk audio
    print(f"\n🎵 [2/5] Sourcing phonk audio...")
    audio_path = get_random_or_specified_phonk(phonk_name)
    if not audio_path or not Path(str(audio_path)).exists():
        from core.video_assembler import generate_fallback_phonk_audio
        audio_path = generate_fallback_phonk_audio(target_duration, SCRATCH_DIR / f"fb_phonk_{ts}.aac")
    print(f"  ✅ {Path(str(audio_path)).name}")

    # Step 3: Assemble
    print(f"\n🎬 [3/5] Assembling AMV...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{label}.mp4"
    assemble_amv(
        clips=clips,
        audio_path=Path(str(audio_path)),
        output_path=output_path,
        style=style,
        character_theme=theme,
        target_duration=target_duration,
        cc_preset=cc_preset,
    )

    # Step 4: Drive upload
    drive_url = None
    if upload_gdrive:
        print(f"\n☁️  [4/5] Uploading to Drive AMV_Outputs/...")
        try:
            token = _gdrive_token()
            amv_out_id = _find_or_create_folder(token, "AMV_Outputs", source_folder)
            run_folder_id = _find_or_create_folder(token, label, amv_out_id)
            _upload_file(token, output_path, run_folder_id)
            snap = _snapshot_code(label)
            _upload_file(token, snap, run_folder_id)
            drive_url = f"https://drive.google.com/drive/folders/{run_folder_id}"
            print(f"  ✅ Drive folder: {drive_url}")
        except Exception as e:
            print(f"  ⚠️ Drive upload error: {e}")

    # Step 5: YouTube upload
    if upload_youtube:
        print(f"\n🎬 [5/5] Uploading to YouTube...")
        try:
            from publishers.youtube_publisher import upload_video_to_youtube
            char_name = theme.get("name", (character or universe).title())
            yt_title = (
                f"{char_name} AMV 🔥 {style['name']} Edit | "
                f"{'JJK' if universe == 'jjk' else 'Marvel'} {datetime.now().strftime('%Y')} #anime #shorts"
            )[:95]
            yt_desc = (
                f"🎬 {char_name} AMV Edit\n🎨 Style: {style['name']}\n🎵 Music: Phonk\n"
                f"#anime #amv #jjk #marvel #phonk #edit #shorts #viral"
            )
            result = upload_video_to_youtube(
                video_path=output_path, title=yt_title, description=yt_desc,
                tags=[char_name, universe.upper(), "AMV", "anime edit", "phonk", "Shorts", "2026"],
                privacy_status="public",
            )
            if result.get("status") == "success":
                print(f"  ✅ YouTube: {result.get('url')}")
            else:
                print(f"  ⚠️ YouTube: {result.get('reason') or result.get('error')}")
        except Exception as e:
            print(f"  ⚠️ YouTube upload error: {e}")

    if not upload_youtube and not upload_gdrive:
        print(f"\n✅ Done (local only): {output_path}")
    else:
        parts = []
        if upload_gdrive: parts.append(f"Drive: {drive_url or 'see above'}")
        if upload_youtube: parts.append("YouTube: see above")
        print(f"\n✅ Run complete. {' | '.join(parts)}")

    shutil.rmtree(SCRATCH_DIR / "amv_trimmed", ignore_errors=True)
    return output_path


# ════════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="GDrive AMV Builder v2 — Professional Velocity Edit Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/gdrive_amv_builder.py --universe jjk --character gojo --duration 75 --upload-youtube --upload-gdrive
  python3 scripts/gdrive_amv_builder.py --universe marvel --duration 60 --upload-gdrive
  python3 scripts/gdrive_amv_builder.py --list-styles
""",
    )
    parser.add_argument("--source-folder", default=SOURCE_FOLDER_ID)
    parser.add_argument("--universe", choices=["jjk", "marvel"], default="jjk")
    parser.add_argument("--character", default=None)
    parser.add_argument("--duration", type=float, default=75.0)
    parser.add_argument("--phonk", default=None)
    parser.add_argument("--upload-youtube", action="store_true",
                        help="Upload MP4 to YouTube Shorts. Code snapshot NOT uploaded here.")
    parser.add_argument("--upload-gdrive", action="store_true",
                        help="Upload MP4 + code snapshot ZIP to Drive AMV_Outputs/")
    parser.add_argument("--list-styles", action="store_true")
    args = parser.parse_args()

    if args.list_styles:
        state = _load_style_state()
        current = state["run_count"] % len(STYLE_POOL)
        print("\n🎨 VFX Style Pool:\n")
        for i, s in enumerate(STYLE_POOL):
            marker = " <-- NEXT RUN" if i == current else ""
            print(f"  [{i}] {s['name']:<22} {s['description']}{marker}")
            fx = [k for k, v in s.items() if isinstance(v, bool) and v]
            print(f"       FX: {', '.join(fx)}\n")
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
