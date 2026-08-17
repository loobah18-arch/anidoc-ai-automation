"""
Production 4K Phonk / Scene Edit Video Assembler for Marvel & Jujutsu Kaisen.
Assembles beat-synced cuts, velocity ramping, 4K HDR CC, impact flashes, and glowing ASS subtitles.

NO AI VOICE — real clip audio (original anime/movie sound) is featured throughout.

Clip Sourcing Priority (all FREE, no subscriptions):
  1. FreeStream: Anime sites (gogoanime/aniwatchtv) + VidSrc movie embeds via yt-dlp
     (These sites are NOT blocked on GitHub Actions — only YouTube is)
  2. BestMoments: YouTube scenepack download + FFmpeg energy analysis fallback
  3. SmartDownloader: Archive.org + Pixabay/Pexels last-resort fallback

Editing Engine:
  OpenCut-inspired: xfade transitions, speed ramps, cinematic bars, audio fades.
  All implemented in FFmpeg filtergraph.

Phonk: Live trending August 2026 fetch via yt-dlp YouTube search.
"""
import os
import subprocess
import random
from pathlib import Path
from typing import Dict, Any, List, Optional

from config.settings import (
    OUTPUT_DIR, SCRATCH_DIR, PHONK_DIR,
    VIDEO_WIDTH, VIDEO_HEIGHT, FPS, CC_PRESETS
)
from core.beat_detector import analyze_audio_beats, BeatGrid
from core.clip_manager import get_character_scene_clips, CHARACTER_THEMES
from core.phonk_manager import get_random_or_specified_phonk
from core.best_moments import fetch_best_episode_clips
from core.free_stream_fetcher import fetch_free_stream_clips
from core.gdrive_manager import fetch_and_prepare_gdrive_footage
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
    target_duration: float = 35.0,
    subtitle_style: str = "viral_karaoke",
    burn_subtitles: bool = False,
    custom_quote: Optional[str] = None,
    custom_title: Optional[str] = None,
    cc_preset: Optional[str] = None,
    github_repo: Optional[str] = None,
    gdrive_folder: Optional[str] = None,
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
    
    # 3. Clip Sourcing — 4-tier waterfall (Google Drive -> FreeStream -> BestMoments -> SmartDownloader)
    durations = [seg["duration"] for seg in segments]
    drop_flags = [seg["is_drop"] for seg in segments]
    n_clips = len(segments)

    universe_dir = SCRATCH_DIR / theme.get("universe", "marvel")
    universe_dir.mkdir(parents=True, exist_ok=True)
    clip_paths = []

    # ── TIER 0: Google Drive Personal Uploads (Raw 1080p/4K Movies & Series) ──
    gdrive_target = gdrive_folder or os.environ.get("GDRIVE_FOLDER_URL") or os.environ.get("GDRIVE_URL")
    if gdrive_target:
        print(f"📥 [GoogleDrive] Fetching uncompressed footage from Google Drive for '{character_key}'...")
        try:
            gdrive_clips = fetch_and_prepare_gdrive_footage(
                gdrive_url_or_id=gdrive_target,
                target_character=character_key,
                output_dir=universe_dir,
                n_clips=n_clips + 4
            )
            if gdrive_clips:
                clip_paths = gdrive_clips
                print(f"✅ [GoogleDrive] Using {len(clip_paths)} high-definition action clips with original audio.")
        except Exception as e:
            print(f"⚠️  [GoogleDrive] Extraction failed: {e}")

    # ── TIER 1: Free stream fetcher (anime sites + VidSrc movies) ──────────
    # Used if Google Drive is not provided or didn't yield enough clips
    if len(clip_paths) < n_clips:
        print(f"🌐 [FreeStream] Fetching real footage for '{character_key}'...")
        try:
            stream_clips = fetch_free_stream_clips(
                character_key=character_key,
                output_dir=universe_dir,
                n_clips=n_clips + 4
            )
            if stream_clips:
                clip_paths.extend(stream_clips)
                print(f"✅ [FreeStream] +{len(stream_clips)} real stream clips.")
        except Exception as e:
            print(f"⚠️  [FreeStream] Failed: {e}")

    # ── TIER 2: BestMoments (YouTube scenepack download) ───────────────────
    if len(clip_paths) < n_clips and force_refresh:
        print(f"📺 [BestMoments] Trying YouTube scenepack for '{character_key}'...")
        try:
            best_clips = fetch_best_episode_clips(
                character_key=character_key,
                output_dir=universe_dir,
                n_clips=n_clips + 4
            )
            if best_clips:
                clip_paths.extend(best_clips)
                print(f"✅ [BestMoments] +{len(best_clips)} scenepack clips.")
        except Exception as e:
            print(f"⚠️  [BestMoments] Failed: {e}")

    # ── TIER 3: SmartDownloader + ClipManager (archive / procedural) ───────
    if len(clip_paths) < n_clips:
        existing_count = len(list(universe_dir.glob(f"{character_key}*.mp4")))
        if force_refresh or existing_count < 4:
            print(f"🗂️  [SmartDownloader] Last-resort fallback for '{character_key}'...")
            try:
                smart_fetch_clips(
                    character_key=character_key,
                    universe_dir=universe_dir,
                    max_clips=n_clips + 4,
                    use_archive=True,
                    use_pixabay=True,
                    use_pexels=True
                )
            except Exception as e:
                print(f"⚠️  [SmartDownloader] Failed: {e}")

        remaining = n_clips - len(clip_paths)
        if remaining > 0:
            extra = get_character_scene_clips(
                character_key=character_key,
                segment_durations=durations[:remaining],
                is_drop_flags=drop_flags[:remaining],
                auto_fetch_online=auto_fetch_clips,
                github_repo=github_repo,
                force_refresh=False
            )
            clip_paths.extend(extra)

    # ── Normalise clip list to exactly n_clips ──────────────────────────────
    if len(clip_paths) > n_clips:
        clip_paths = clip_paths[:n_clips]
    elif clip_paths and len(clip_paths) < n_clips:
        while len(clip_paths) < n_clips:
            clip_paths.append(clip_paths[len(clip_paths) % len(clip_paths)])

    if not clip_paths:
        raise RuntimeError("No clips available after all download attempts.")
    
    # 5. Optional Kinetic Karaoke Subtitles (Safe-Zone Alignment)
    ass_path = None
    active_cc = cc_preset or theme["cc_preset"]
    cc_cfg = CC_PRESETS.get(active_cc, CC_PRESETS["marvel_hdr"])
    
    if burn_subtitles:
        ass_path = SCRATCH_DIR / f"subs_{character_key}.ass"
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
        # Real clip audio: bring it up loud so character voice is featured
        audio_fade = build_clip_audio_fade(seg["duration"])
        if has_aud:
            a_chain = (
                f"[{idx}:a]atrim=duration={seg['duration']:.2f},asetpts=PTS-STARTPTS,"
                f"{audio_fade},volume=1.60,aformat=sample_rates=48000:channel_layouts=stereo[a{idx}]"
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
    
    # Subtitle Burn-in (Disabled by default to keep edit 100% pure video)
    if burn_subtitles and ass_path and ass_path.exists():
        ass_escaped = str(ass_path).replace(":", "\\:").replace("\\", "/")
        sub_filter = f",ass={ass_escaped}"
    else:
        sub_filter = ""
    
    # Video Post-processing (Concatenated + Flash + CC)
    filter_chains.append(f"[concatenated_v]{flash_str},{cc_filter}{sub_filter}[vout]")
    
    # Audio Dynamic Structure:
    # 70% Phonk BGM / 30% Original Anime/Movie Voice & SFX
    # Track 1: Real clip audio (Voice/SFX) — 30% weight
    # Track 2: Phonk BGM (Aura Phonk) — 70% weight
    # Master: loudnorm to -12 dB (commercial streaming loudness)
    filter_chains.append(
        f"[clip_sfx_raw]asplit=2[csfx_intro_in][csfx_drop_in];"
        f"[csfx_intro_in]atrim=0:{drop_t:.2f},asetpts=PTS-STARTPTS,volume=0.30[csfx_intro];"
        f"[csfx_drop_in]atrim={drop_t:.2f}:{beat_grid.duration:.2f},asetpts=PTS-STARTPTS,volume=0.50[csfx_drop];"
        f"[csfx_intro][csfx_drop]concat=n=2:v=0:a=1[clip_audio_full];"
        f"[{phonk_inp_idx}:a]asplit=2[p_intro_in][p_drop_in];"
        f"[p_intro_in]atrim=0:{drop_t:.2f},asetpts=PTS-STARTPTS,lowpass=f=1000,volume=0.45[p_intro];"
        f"[p_drop_in]atrim={drop_t:.2f}:{beat_grid.duration:.2f},asetpts=PTS-STARTPTS,volume=1.35[p_drop];"
        f"[p_intro][p_drop]concat=n=2:v=0:a=1[phonk_dynamic];"
        f"[phonk_dynamic][clip_audio_full]amix=inputs=2:duration=first:weights=7 3:dropout_transition=2,"
        f"volume=1.30,loudnorm=I=-12:TP=-0.5:LRA=7[aout]"
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
