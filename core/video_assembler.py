"""
Production 4K Phonk / Scene Edit Video Assembler for Marvel & Jujutsu Kaisen.
Assembles beat-synced cuts, velocity ramping, 4K HDR CC, impact flashes, and glowing ASS subtitles.
Features true character dialogue voiceover, low-pass Phonk intro into explosive drop, and commercial audio mastering.

OpenCut-Inspired Engine: Uses xfade transitions, per-clip speed ramps, cinematic bars, and
Audio fade handles — all ported from OpenCut's browser editor to FFmpeg filtergraph.

Smart Downloader: Multi-source clip fetching via yt-dlp → Archive.org → Pixabay/Pexels fallback.
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
from core.voice_engine import get_character_dialogue_audio
from core.public_api_fetcher import check_clip_has_audio
from core.effects_engine import build_cc_filter, build_beat_flash_filters, build_velocity_zoom_filter
from core.subtitle_stylizer import generate_kinetic_subtitles, SUBTITLE_STYLE_PRESETS
from core.quote_ai import generate_edit_metadata
from core.opencut_engine import (
    build_opencut_clip_filter,
    build_clip_audio_fade,
)
from core.smart_downloader import smart_fetch_clips


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
    auto_fetch_clips: bool = True,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Renders an automated 4K Phonk / Scene Edit Short (9:16 Portrait, 1080x1920).
    Features genuine character dialogue, low-pass intro, explosive Phonk drop, and commercial mastering.
    
    OpenCut-inspired edits: xfade transitions, speed ramps, cinematic bars, audio clip fades.
    Smart downloader: yt-dlp → Archive.org → Pixabay/Pexels fallback chain.
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
    drop_t = max(0.5, beat_grid.drop_time)
    print(f"🎵 Beat Grid: {len(segments)} scene cuts detected across {beat_grid.duration:.1f}s (Drop at {drop_t:.1f}s)")
    
    # 3. Retrieve Character Dialogue Audio
    dialogue_path = get_character_dialogue_audio(character_key, quote_text)
    
    # 4a. Smart Multi-Source Clip Download (yt-dlp → Archive.org → Pixabay/Pexels)
    durations = [seg["duration"] for seg in segments]
    drop_flags = [seg["is_drop"] for seg in segments]

    universe_dir = SCRATCH_DIR / theme.get("universe", "marvel")
    universe_dir.mkdir(parents=True, exist_ok=True)

    local_clips_count = len(list(universe_dir.glob(f"{character_key}*.mp4")))
    if force_refresh or local_clips_count < 4:
        print(f"🌐 [SmartDownloader] Fetching fresh clips for {character_key}...")
        try:
            smart_fetch_clips(
                character_key=character_key,
                universe_dir=universe_dir,
                max_clips=12,
                use_archive=True,
                use_pixabay=True,
                use_pexels=True
            )
        except Exception as e:
            print(f"⚠️  [SmartDownloader] Failed: {e} — using cached clips.")

    # 4b. Get assembled clip paths from clip manager
    clip_paths = get_character_scene_clips(
        character_key=character_key,
        segment_durations=durations,
        is_drop_flags=drop_flags,
        auto_fetch_online=auto_fetch_clips,
        github_repo=github_repo,
        force_refresh=force_refresh
    )
    
    # 5. Generate Kinetic Karaoke Subtitles (Safe-Zone Alignment)
    ass_path = SCRATCH_DIR / f"subs_{character_key}.ass"
    active_cc = cc_preset or theme["cc_preset"]
    cc_cfg = CC_PRESETS.get(active_cc, CC_PRESETS["marvel_hdr"])
    
    generate_kinetic_subtitles(
        quote_text=quote_text,
        start_time=0.2,
        end_time=min(beat_grid.duration, max(4.0, drop_t)),
        output_ass_path=ass_path,
        style_preset=subtitle_style,
        primary_color="&H00FFFFFF",
        active_color=cc_cfg.get("primary_color", "&H002BF5FF"),
        glow_color=None,
        character_name=theme["name"].split()[0]
    )
    
    # 6. Build Multi-Layer FFmpeg Filtergraph (OpenCut-Inspired)
    cmd_inputs = []
    has_clip_audio_list = []
    
    for cp in clip_paths:
        cmd_inputs.extend(["-i", str(cp)])
        has_clip_audio_list.append(check_clip_has_audio(cp))
        
    phonk_inp_idx = len(clip_paths)
    cmd_inputs.extend(["-i", str(audio_path)])
    
    dialogue_inp_idx = len(clip_paths) + 1
    cmd_inputs.extend(["-i", str(dialogue_path)])
    
    filter_chains = []
    concat_v_inputs = []
    concat_a_inputs = []
    
    # Build per-clip video filters (OpenCut: speed ramps, watermark crop, cinematic bars)
    for idx, (cp, seg, has_aud) in enumerate(zip(clip_paths, segments, has_clip_audio_list)):
        zoom_filter = build_velocity_zoom_filter(seg["is_drop"], idx)
        
        # OpenCut-style per-clip filter: crop + scale + speed ramp + SAR + FPS
        opencut_vf = build_opencut_clip_filter(
            seg_idx=idx,
            duration=seg["duration"],
            is_drop=seg["is_drop"],
            video_width=VIDEO_WIDTH,
            video_height=VIDEO_HEIGHT,
            fps=FPS,
            add_bars=(idx == 0)  # Cinematic bars only on first clip (dramatic intro)
        )
        
        v_chain = f"[{idx}:v]{opencut_vf},{zoom_filter},scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1[v{idx}]"
        filter_chains.append(v_chain)
        concat_v_inputs.append(f"[v{idx}]")
        
        # OpenCut-style per-clip audio fades + extraction
        audio_fade = build_clip_audio_fade(seg["duration"])
        if has_aud:
            a_chain = (
                f"[{idx}:a]atrim=duration={seg['duration']:.2f},asetpts=PTS-STARTPTS,"
                f"{audio_fade},volume=0.85,aformat=sample_rates=48000:channel_layouts=stereo[a{idx}]"
            )
        else:
            a_chain = f"aevalsrc=0:d={seg['duration']:.2f},aformat=sample_rates=48000:channel_layouts=stereo[a{idx}]"
        filter_chains.append(a_chain)
        concat_a_inputs.append(f"[a{idx}]")

    # OpenCut xfade-based video concat (replaces plain concat)
    # Use xfade if we have multiple clips and a supported ffmpeg version
    if len(clip_paths) > 1:
        # Build sequential xfade chain with contextual transitions
        XFADE_DUR = 0.10
        from core.opencut_engine import pick_transition
        
        current_label = "[v0]"
        seg_offset = 0.0
        for i in range(1, len(clip_paths)):
            transition = pick_transition(is_drop=drop_flags[i] if i < len(drop_flags) else True)
            seg_offset += durations[i - 1] - XFADE_DUR
            out_label = f"[xf{i}]" if i < len(clip_paths) - 1 else "[concatenated_v]"
            
            chain = (
                f"{current_label}[v{i}]xfade=transition={transition}:"
                f"duration={XFADE_DUR:.3f}:offset={seg_offset:.3f}{out_label}"
            )
            filter_chains.append(chain)
            current_label = out_label
    else:
        concat_v_str = f"{concat_v_inputs[0]}null[concatenated_v]"
        filter_chains.append(concat_v_str)

    # Concat all clip audio segments
    concat_a_str = "".join(concat_a_inputs) + f"concat=n={len(clip_paths)}:v=0:a=1[clip_sfx_raw]"
    filter_chains.append(concat_a_str)
    
    # Impact White Flashes on Beat Drops
    flash_filters = build_beat_flash_filters(beat_grid.beat_times, flash_duration=0.09, opacity=0.60)
    flash_str = ",".join(flash_filters) if flash_filters else "null"
    
    # 4K HDR Color Grade (CC Preset with S-curve colorlevels)
    cc_filter = build_cc_filter(active_cc)
    
    # Subtitle Burn-in
    ass_escaped = str(ass_path).replace(":", "\\:").replace("\\", "/")
    
    # Video Post-processing (Concatenated + Flash + CC + ASS)
    filter_chains.append(f"[concatenated_v]{flash_str},{cc_filter},ass={ass_escaped}[vout]")
    
    # Audio Dynamic Structure:
    # 1. Dialogue track (isolated, prominent, volume boosted during intro)
    # 2. Phonk track (low-pass filtered muffled during intro, explosive at drop)
    # 3. Clip SFX (combat punches/impacts)
    # 4. Master volume normalization & compression
    filter_chains.append(
        f"[{dialogue_inp_idx}:a]volume=1.5,dynaudnorm,atrim=0:{drop_t:.2f},asetpts=PTS-STARTPTS[dialogue_clean];"
        f"[{phonk_inp_idx}:a]asplit=2[p_intro_in][p_drop_in];"
        f"[p_intro_in]atrim=0:{drop_t:.2f},asetpts=PTS-STARTPTS,lowpass=f=650,volume=0.35[p_intro];"
        f"[p_drop_in]atrim={drop_t:.2f}:{beat_grid.duration:.2f},asetpts=PTS-STARTPTS,volume=0.95[p_drop];"
        f"[p_intro][p_drop]concat=n=2:v=0:a=1[phonk_dynamic];"
        f"[clip_sfx_raw]volume=0.85,dynaudnorm[clip_sfx];"
        f"[phonk_dynamic][dialogue_clean][clip_sfx]amix=inputs=3:duration=first:dropout_transition=2,"
        f"volume=1.70,loudnorm=I=-11:TP=-0.5:LRA=7[aout]"
    )
    
    full_filter_complex = ";".join(filter_chains)
    
    cmd = [
        "ffmpeg", "-y",
        *cmd_inputs,
        "-filter_complex", full_filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
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
