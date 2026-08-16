"""
Production 4K Phonk / Scene Edit Video Assembler for Marvel & Jujutsu Kaisen.
Assembles beat-synced cuts, velocity ramping, 4K HDR CC, impact flashes, and glowing ASS subtitles.
"""
import subprocess
import random
from pathlib import Path
from typing import Dict, Any, List, Optional

from config.settings import (
    OUTPUT_DIR, SCRATCH_DIR, PHONK_DIR, DIALOGUE_DIR,
    VIDEO_WIDTH, VIDEO_HEIGHT, FPS, CC_PRESETS
)
from core.beat_detector import analyze_audio_beats, BeatGrid
from core.clip_manager import get_character_scene_clips, CHARACTER_THEMES
from core.phonk_manager import get_random_or_specified_phonk
from core.effects_engine import build_cc_filter, build_beat_flash_filters, build_velocity_zoom_filter
from core.subtitle_stylizer import generate_kinetic_subtitles, SUBTITLE_STYLE_PRESETS
from core.quote_ai import generate_edit_metadata


def generate_fallback_phonk_audio(duration: float, output_path: Path) -> Path:
    """
    Generates a punchy synth-bass procedural audio track if no raw mp3 is present.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dur_str = f"{duration:.2f}"
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=55:d={dur_str}",
        "-f", "lavfi", "-i", f"sine=frequency=110:d={dur_str}",
        "-filter_complex", "[0:a]volume=0.8[b];[1:a]volume=0.4[m];[b][m]amix=inputs=2[a]",
        "-map", "[a]",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", dur_str,
        str(output_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def render_cinematic_edit(
    character_key: Optional[str] = None,
    audio_path: Optional[Path] = None,
    phonk_track: Optional[str] = None,
    output_path: Optional[Path] = None,
    target_duration: float = 22.0,
    subtitle_style: str = "viral_karaoke",
    custom_quote: Optional[str] = None,
    custom_title: Optional[str] = None,
    cc_preset: Optional[str] = None,
    github_repo: Optional[str] = None,
    auto_fetch_clips: bool = True
) -> Dict[str, Any]:
    """
    Renders an automated 4K Phonk / Scene Edit Short (9:16 Portrait, 1080x1920).
    """
    if not character_key or character_key not in CHARACTER_THEMES:
        character_key = random.choice(list(CHARACTER_THEMES.keys()))
        
    theme = CHARACTER_THEMES[character_key]
    if not output_path:
        output_path = OUTPUT_DIR / f"edit_{character_key}_{theme['universe']}_short.mp4"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n🎬 [VideoAssembler] Starting 4K Edit for: {theme['name']} ({theme['universe'].upper()})")
    
    # 1. Generate Metadata & Quotes
    metadata = generate_edit_metadata(character_key)
    quote_text = custom_quote or metadata["quote"]
    title_text = custom_title or metadata["title"]
    metadata["quote"] = quote_text
    metadata["title"] = title_text
    print(f"💬 Quote: \"{quote_text}\"")
    print(f"📌 Title: {title_text}")
    
    # 2. Audio Sourcing & Beat Analysis
    if not audio_path or not Path(audio_path).exists():
        chosen_audio = get_random_or_specified_phonk(phonk_track)
        if chosen_audio and chosen_audio.exists():
            audio_path = chosen_audio
            print(f"🎧 Using Phonk Track: {audio_path.name}")
        else:
            audio_path = SCRATCH_DIR / f"phonk_synth_{character_key}.aac"
            generate_fallback_phonk_audio(target_duration, audio_path)
            
    beat_grid = analyze_audio_beats(audio_path, target_duration=target_duration)
    segments = beat_grid.get_cut_segments()
    print(f"🎵 Beat Grid: {len(segments)} scene cuts detected across {beat_grid.duration:.1f}s (Drop at {beat_grid.drop_time:.1f}s)")
    
    # 3. Retrieve or Render Character Scene Clips
    durations = [seg["duration"] for seg in segments]
    drop_flags = [seg["is_drop"] for seg in segments]
    clip_paths = get_character_scene_clips(
        character_key=character_key,
        segment_durations=durations,
        is_drop_flags=drop_flags,
        auto_fetch_online=auto_fetch_clips,
        github_repo=github_repo
    )
    
    # 4. Generate Kinetic Karaoke Subtitles
    ass_path = SCRATCH_DIR / f"subs_{character_key}.ass"
    active_cc = cc_preset or theme["cc_preset"]
    cc_cfg = CC_PRESETS.get(active_cc, CC_PRESETS["marvel_hdr"])
    
    generate_kinetic_subtitles(
        quote_text=quote_text,
        start_time=0.2,
        end_time=min(beat_grid.duration, max(4.0, beat_grid.drop_time)),
        output_ass_path=ass_path,
        style_preset=subtitle_style,
        primary_color="&H00FFFFFF",
        active_color=cc_cfg.get("primary_color", "&H002BF5FF"),
        glow_color=None,
        character_name=theme["name"].split()[0]
    )
    
    # 5. Build FFmpeg Filtergraph
    cmd_inputs = []
    for cp in clip_paths:
        cmd_inputs.extend(["-i", str(cp)])
    cmd_inputs.extend(["-i", str(audio_path)])
    audio_inp_idx = len(clip_paths)
    
    # Per-clip scale, crop, velocity zoom & normalize SAR/FPS
    filter_chains = []
    concat_inputs = []
    for idx, (cp, seg) in enumerate(zip(clip_paths, segments)):
        zoom_filter = build_velocity_zoom_filter(seg["is_drop"], idx)
        chain = (
            f"[{idx}:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},{zoom_filter},"
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1,fps={FPS},"
            f"trim=duration={seg['duration']:.2f},setpts=PTS-STARTPTS[v{idx}]"
        )
        filter_chains.append(chain)
        concat_inputs.append(f"[v{idx}]")
        
    # Concat all segments
    concat_str = "".join(concat_inputs) + f"concat=n={len(clip_paths)}:v=1:a=0[concatenated]"
    filter_chains.append(concat_str)
    
    # Impact White Flashes on Beat Drops
    flash_filters = build_beat_flash_filters(beat_grid.beat_times, flash_duration=0.10, opacity=0.45)
    flash_str = ",".join(flash_filters) if flash_filters else "null"
    
    # 4K HDR Color Grade (CC Preset)
    cc_filter = build_cc_filter(active_cc)
    
    # Subtitle Burn-in
    ass_escaped = str(ass_path).replace(":", "\\:").replace("\\", "/")
    
    full_v_filter = (
        ";".join(filter_chains) + ";"
        f"[concatenated]{flash_str},{cc_filter},ass={ass_escaped}[vout]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        *cmd_inputs,
        "-filter_complex", full_v_filter,
        "-map", "[vout]",
        "-map", f"{audio_inp_idx}:a",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-t", f"{beat_grid.duration:.2f}",
        str(output_path)
    ]

    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("❌ FFmpeg Render Error:\n", res.stderr)
        raise RuntimeError(f"FFmpeg assembly failed: {res.stderr[:200]}")
        
    print(f"✅ Rendered 4K Edit Short successfully: {output_path.name} ({output_path.stat().st_size // 1024} KB)")
    
    return {
        "status": "success",
        "output_path": output_path,
        "metadata": metadata,
        "character_key": character_key,
        "duration": beat_grid.duration,
        "cuts_count": len(segments),
        "file_size_kb": output_path.stat().st_size // 1024,
        "audio_used": Path(audio_path).name,
        "subtitle_style": subtitle_style,
        "cc_preset": active_cc
    }
