"""
Verified JJK Rendering Module
Event-first rendering with exact source resolution and verified window cutting.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess

from config.settings import (
    OUTPUT_DIR, SCRATCH_DIR,
    VIDEO_WIDTH, VIDEO_HEIGHT, FPS, CC_PRESETS
)
from core.beat_detector import analyze_audio_beats
from core.scene_database import VerifiedEventDatabase
from core.database_clip_fetcher import fetch_verified_event_clips
from core.phonk_manager import get_random_or_specified_phonk
from core.effects_engine import (
    build_cc_filter,
    build_beat_flash_filters,
    get_segment_velocity_profile,
    build_velocity_clip_filter
)
from core.subtitle_stylizer import generate_kinetic_subtitles
from core.opencut_engine import build_clip_audio_fade
from core.public_api_fetcher import check_clip_has_audio
from core.clip_manager import CHARACTER_THEMES
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


def _render_verified_jjk_edit(
    character_key: str,
    audio_path: Optional[Path],
    phonk_track: Optional[str],
    output_path: Path,
    target_duration: float,
    subtitle_style: str,
    burn_subtitles: bool,
    custom_quote: Optional[str],
    custom_title: Optional[str],
    cc_preset: Optional[str],
    gdrive_folder: Optional[str]
) -> Dict[str, Any]:
    """
    Verified JJK render: Event → Title → Source → Clips → Render.
    NO fallback sources, NO unrelated clips, NO duplicate filling.
    """
    import os

    theme = CHARACTER_THEMES[character_key]

    # 1. Audio & Beat Analysis
    if not audio_path or not Path(audio_path).exists():
        chosen_audio = get_random_or_specified_phonk(phonk_track)
        if chosen_audio and chosen_audio.exists():
            audio_path = chosen_audio
        else:
            audio_path = SCRATCH_DIR / f"phonk_synth_{character_key}.aac"
            generate_fallback_phonk_audio(target_duration, audio_path)

    print(f"🎧 Using Phonk Track: {Path(audio_path).name}")

    beat_grid = analyze_audio_beats(audio_path, target_duration=target_duration)
    segments = beat_grid.get_cut_segments()
    drop_t = max(0.5, beat_grid.drop_time)

    print(f"🎵 Beat Grid: {len(segments)} segments, drop at {drop_t:.1f}s")

    # 2. Select Verified Event
    print("\n🔍 [VerifiedJJK] Selecting verified event...")

    event_db = VerifiedEventDatabase()

    try:
        selected_event = event_db.select_event_for_render(
            custom_title=custom_title,
            prefer_unused=True
        )
    except ValueError as e:
        raise RuntimeError(f"Custom title resolution failed: {e}")
    except RuntimeError as e:
        raise RuntimeError(f"No verified events available: {e}")

    # 3. Extract metadata from event
    event_id = selected_event["event_id"]
    title_metadata = selected_event.get("title_metadata", {})

    title_text = title_metadata.get("title", f"JJK Event {event_id}")
    quote_text = custom_quote or title_metadata.get("quote", "")
    tags = title_metadata.get("tags", ["jjk", "animeedit", "4kedit", "shorts"])

    print(f"✅ Selected event: {event_id}")
    print(f"📌 Title: {title_text}")
    print(f"💬 Quote: {quote_text}")

    metadata = {
        "character_key": character_key,
        "character_name": theme["name"],
        "universe": "jjk",
        "quote": quote_text,
        "title": title_text,
        "tags": tags,
        "description": (
            f"{title_text}\n\n"
            f"\"{quote_text}\"\n\n"
            "Disclaimer: This video is a transformative fan edit created for entertainment purposes. "
            "All rights belong to their respective copyright owners.\n\n"
            + " ".join(f"#{t.lstrip('#')}" for t in tags)
        ),
        "event_id": event_id,
        "event_verified": True
    }

    # 4. Fetch clips from verified event
    gdrive_target = gdrive_folder or os.environ.get("GDRIVE_FOLDER_URL") or os.environ.get("GDRIVE_URL")

    if not gdrive_target:
        raise RuntimeError(
            "GDRIVE_FOLDER_URL not set. Verified JJK mode requires Google Drive access."
        )

    durations = [seg["duration"] for seg in segments]
    universe_dir = SCRATCH_DIR / "jjk" / "verified"
    universe_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📥 [VerifiedJJK] Fetching clips from verified event {event_id}...")

    try:
        fetch_result = fetch_verified_event_clips(
            event=selected_event,
            gdrive_folder_url=gdrive_target,
            segment_durations=durations,
            character_key=character_key,
            output_dir=universe_dir
        )
    except Exception as e:
        raise RuntimeError(f"Failed to fetch verified clips: {e}")

    clip_paths = fetch_result["clip_paths"]
    clip_manifest = fetch_result["clip_manifest"]
    source_trace = {
        "source_id": fetch_result["source_id"],
        "source_filename": fetch_result["source_filename"],
        "event_id": event_id
    }

    if len(clip_paths) != len(segments):
        raise RuntimeError(
            f"Clip count mismatch: got {len(clip_paths)}, needed {len(segments)}. "
            f"Event {event_id} has insufficient verified windows."
        )

    print(f"✅ [VerifiedJJK] {len(clip_paths)} verified clips ready")

    # 5. Render
    active_cc = cc_preset or theme.get("cc_preset", "jjk_void")
    cc_cfg = CC_PRESETS.get(active_cc, CC_PRESETS["jjk_void"])

    # Subtitles
    ass_path = None
    if burn_subtitles and quote_text:
        ass_path = SCRATCH_DIR / f"subs_{character_key}_verified.ass"
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

    # Build FFmpeg filtergraph
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

    # Per-clip filters with scene-aware velocity
    for idx, (cp, seg, has_aud, clip_meta) in enumerate(zip(clip_paths, segments, has_clip_audio_list, clip_manifest)):
        # Use scene suitability from clip manifest
        scene_suit = clip_meta.get("scene_suitability", {})

        # Override velocity profile with scene suitability if available
        if scene_suit.get("slowmo_safe") and seg.get("duration", 0) > 0.8:
            vel_profile = {"role": "verified_slowmo", "speed": 0.55, "scale_factor": 1.10, "add_bars": False, "add_flash": False}
        elif scene_suit.get("impact"):
            vel_profile = {"role": "impact_snap", "speed": 1.25, "scale_factor": 1.14, "add_bars": False, "add_flash": True}
        else:
            vel_profile = get_segment_velocity_profile(seg, idx, len(segments))

        clip_vf = build_velocity_clip_filter(
            seg_idx=idx,
            duration=seg["duration"],
            speed=vel_profile["speed"],
            scale_factor=vel_profile["scale_factor"],
            video_width=VIDEO_WIDTH,
            video_height=VIDEO_HEIGHT,
            fps=FPS,
            add_bars=vel_profile.get("add_bars", False)
        )

        v_chain = f"[{idx}:v]{clip_vf}[v{idx}]"
        filter_chains.append(v_chain)
        concat_v_inputs.append(f"[v{idx}]")

        # Audio
        audio_fade = build_clip_audio_fade(seg["duration"])
        if has_aud:
            a_chain = (
                f"[{idx}:a]atrim=duration={seg['duration']:.3f},asetpts=PTS-STARTPTS,"
                f"{audio_fade},volume=1.60,aformat=sample_rates=48000:channel_layouts=stereo[a{idx}]"
            )
        else:
            a_chain = f"aevalsrc=0:d={seg['duration']:.3f},aformat=sample_rates=48000:channel_layouts=stereo[a{idx}]"
        filter_chains.append(a_chain)
        concat_a_inputs.append(f"[a{idx}]")

    # Concatenate
    concat_v_str = "".join(concat_v_inputs) + f"concat=n={len(clip_paths)}:v=1:a=0[concatenated_v]"
    filter_chains.append(concat_v_str)

    concat_a_str = "".join(concat_a_inputs) + f"concat=n={len(clip_paths)}:v=0:a=1[clip_sfx_raw]"
    filter_chains.append(concat_a_str)

    # Flashes (beat-synced for now, can be cut-boundary later)
    flash_filters = build_beat_flash_filters(beat_grid.beat_times, flash_duration=0.09, opacity=0.60)
    flash_str = ",".join(flash_filters) if flash_filters else "null"

    # Color grade
    cc_filter = build_cc_filter(active_cc)

    # Subtitles
    if burn_subtitles and ass_path and ass_path.exists():
        ass_escaped = str(ass_path).replace(":", "\\:").replace("\\", "/")
        sub_filter = f",ass={ass_escaped}"
    else:
        sub_filter = ""

    filter_chains.append(f"[concatenated_v]{flash_str},{cc_filter}{sub_filter}[vout]")

    # Audio mix
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

    print(f"✅ Rendered verified JJK edit: {output_path.name} ({output_path.stat().st_size // 1024} KB)")

    # Mark rendered
    event_db.mark_event_rendered(event_id, {
        "output_path": output_path,
        "duration": beat_grid.duration,
        "cuts_count": len(segments)
    })

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
        "cc_preset": active_cc,
        "event_verified": True,
        "event_id": event_id,
        "source_trace": source_trace,
        "clip_manifest": clip_manifest
    }
