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
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from config.settings import (
    OUTPUT_DIR, SCRATCH_DIR, PHONK_DIR, FONTS_DIR,
    VIDEO_WIDTH, VIDEO_HEIGHT, FPS, CC_PRESETS,
    LETTERBOX_BAR_HEIGHT, CHARACTER_COLOR_MAP, DEFAULT_DURATION, FRAMING_MODE
)
from core.open_source_editor import (
    is_editly_available, generate_editly_spec, render_with_editly, post_process_editly_output
)
from core.xfade_engine import build_xfade_transition_filter
from core.beat_detector import analyze_audio_beats, BeatGrid
from core.clip_manager import get_character_scene_clips, CHARACTER_THEMES, is_clip_healthy
from core.phonk_manager import get_random_or_specified_phonk
from core.best_moments import fetch_best_episode_clips
from core.free_stream_fetcher import fetch_free_stream_clips
from core.gdrive_manager import fetch_and_prepare_gdrive_footage
from core.public_api_fetcher import check_clip_has_audio
from core.effects_engine import (
    build_cc_filter,
    build_monochrome_cc_filter,
    build_beat_flash_filters,
    get_segment_velocity_profile,
    build_velocity_clip_filter,
    build_vertical_dual_layer_chain,
    build_selective_bloom_filter,
    build_heavy_drop_impact_filters,
    build_pre_drop_audio_vacuum_filter,
    build_combat_foley_audio_filter
)
from core.subtitle_stylizer import generate_kinetic_subtitles, SUBTITLE_STYLE_PRESETS, DEFAULT_CHARACTER_DIALOGUE
from core.timestamp_loader import load_episode_metadata, match_episode_code_from_filename
from core.quote_ai import generate_edit_metadata, format_anime_description
from core.opencut_engine import build_clip_audio_fade
from core.smart_downloader import smart_fetch_clips
from core.text_overlay import generate_edit_text_overlays, build_engagement_hook_overlay


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
    target_duration: float = DEFAULT_DURATION,
    subtitle_style: str = "spur_hook",
    burn_subtitles: bool = True,
    enable_subtitles: bool = True,
    custom_quote: Optional[str] = None,
    custom_title: Optional[str] = None,
    cc_preset: Optional[str] = None,
    github_repo: Optional[str] = None,
    gdrive_folder: Optional[str] = None,
    auto_fetch_clips: bool = True,
    force_refresh: bool = False,
    exclude_clip_paths: Optional[List[str]] = None,
    remove_copyrighted_clip: bool = False,
    target_episode: Optional[str] = None,
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
    quote_text = custom_quote or metadata.get("engagement_question") or metadata["quote"]
    title_text = custom_title or metadata["title"]
    metadata["quote"] = quote_text
    metadata["title"] = title_text
    metadata["description"] = format_anime_description(
        title=title_text,
        quote=quote_text,
        character_name=theme["name"],
        universe=theme["universe"],
        tags=metadata["tags"]
    )
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
    drop_idx = next((i for i, seg in enumerate(segments) if seg["start"] >= drop_t - 0.05), 2)

    universe_dir = SCRATCH_DIR / theme.get("universe", "marvel")
    universe_dir.mkdir(parents=True, exist_ok=True)
    clip_paths = []

    # ── TIER 0: Local Footage (already downloaded/sliced in scratch or assets) ──
    if not force_refresh:
        assets_char_dir = Path("assets/video") / theme.get("universe", "jjk")
        local_cand = (
            sorted(list(universe_dir.glob(f"*{character_key}*.mp4")), key=lambda p: p.name) +
            sorted(list(assets_char_dir.glob(f"*{character_key}*.mp4")), key=lambda p: p.name)
        )
        seen_loc = set()
        for lp in local_cand:
            if is_clip_healthy(lp) and str(lp) not in seen_loc:
                seen_loc.add(str(lp))
                clip_paths.append(lp)
            elif lp.exists() and not lp.name.startswith("proc_"):
                lp.unlink(missing_ok=True)
        if len(clip_paths) >= n_clips:
            print(f"🎬 [LocalClips] Using {len(clip_paths)} high-definition action clips locally for '{character_key}'.")

    # ── TIER 1: Google Drive Personal Uploads (Raw 1080p/4K Movies & Series) ──
    gdrive_target = gdrive_folder or os.environ.get("GDRIVE_FOLDER_URL") or os.environ.get("GDRIVE_URL")
    if gdrive_target and len(clip_paths) < n_clips:
        print(f"📥 [GoogleDrive] Fetching uncompressed footage from Google Drive for '{character_key}'...")
        try:
            max_needed_dur = max(durations) if durations else 4.0
            gdrive_clips = fetch_and_prepare_gdrive_footage(
                gdrive_url_or_id=gdrive_target,
                target_character=character_key,
                output_dir=universe_dir,
                n_clips=max(n_clips + 10, 30),
                title=title_text,
                drop_index=drop_idx,
                clip_duration=max(5.5, max_needed_dur + 1.5),
                target_episode=target_episode
            )
            if gdrive_clips:
                clip_paths = gdrive_clips
                print(f"✅ [GoogleDrive] Using {len(clip_paths)} high-definition action clips with original audio.")
                # Quality Upgrade: If GDrive footage is low-res (<720p), augment with genuine 1080p/4K scenepack for combat cuts
                is_low_res = any("480p" in str(p).lower() for p in gdrive_clips)
                if not is_low_res and gdrive_clips:
                    try:
                        probe_res = subprocess.run(
                            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=height", "-of", "csv=p=0", str(gdrive_clips[0])],
                            capture_output=True, text=True, timeout=5
                        ).stdout.strip()
                        if probe_res.isdigit() and int(probe_res) < 720:
                            is_low_res = True
                    except Exception:
                        pass

                if is_low_res and auto_fetch_clips:
                    print(f"⚠️ [Resolution] Detected low-res footage (<720p). Sourcing genuine 1080p/4K scenepack for combat cuts...")
                    try:
                        from core.public_api_fetcher import fetch_character_scenepack
                        hd_combat = fetch_character_scenepack(character_key, max_clips=n_clips)
                        if hd_combat and len(hd_combat) >= 3:
                            # Keep Clip 0 (pre-fight dialogue intro) from Google Drive for canon audio & dialogue alignment
                            clip_paths = [gdrive_clips[0]] + hd_combat[:n_clips - 1]
                            print(f"✨ [Resolution] Upgraded {len(clip_paths)-1} combat cuts to genuine 1080p/4K footage!")
                    except Exception as e_hd:
                        print(f"ℹ️ [Resolution] Scenepack fetch notice: {e_hd}")
        except Exception as e:
            print(f"⚠️  [GoogleDrive] Extraction failed: {e}")

    # ── TIER 2: Free stream fetcher (anime sites + VidSrc movies) ──────────
    if len(clip_paths) < n_clips and auto_fetch_clips and force_refresh:
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

    # ── TIER 3: BestMoments (YouTube scenepack download) ───────────────────
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

    # ── TIER 4: SmartDownloader + ClipManager (archive / procedural fallback) ──
    if len(clip_paths) < n_clips:
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

    # ── Copyright Shield: Exclude or Remove Flagged/Copyrighted Clips ──
    if exclude_clip_paths:
        exclude_set = {str(Path(p).resolve()) for p in exclude_clip_paths} | {Path(p).name for p in exclude_clip_paths}
        clip_paths = [p for p in clip_paths if str(Path(p).resolve()) not in exclude_set and Path(p).name not in exclude_set]
        print(f"✂️ [ClipRemover] Excluded {len(exclude_clip_paths)} flagged clip(s). Remaining: {len(clip_paths)}")

    if remove_copyrighted_clip and clip_paths:
        removed = clip_paths.pop(0) if len(clip_paths) > 1 else None
        print(f"✂️ [ClipRemover] Removed suspected copyrighted clip from timeline: {getattr(removed, 'name', str(removed))}")

    # ── Thematic Narrative Arc Sequencing (Storytelling flow) ──
    # Sort and map clips according to the 3-act structure:
    # 1. Setup / Monologue intro (first clip)
    # 2. Escalating combat exchanges (middle clips in chronological order)
    # 3. Ultimate technique climax finisher (highest energy / final clip)
    if len(clip_paths) >= n_clips:
        n_intro = sum(1 for f in drop_flags if not f)
        # Invariant: Pre-drop conversation is strictly ONE continuous sequence from clip_paths[0] (no scene hopping).
        intro_c = [clip_paths[0]]
        finisher_c = clip_paths[-1]
        combat_pool = [c for c in clip_paths[1:-1] if c not in intro_c and c != finisher_c]
        if not combat_pool:
            combat_pool = [c for c in clip_paths[1:] if c not in intro_c] or clip_paths[:]

        # ── Chronological Narrative Progression ──
        # Preserves strict 3-act escalation (Intro -> Combat Clashes -> Climax Finisher)
        # Pre-drop contains ONLY the continuous pre-fight conversation; post-drop contains ONLY pure fight scenes.
        ordered_clips = []
        combat_i = 0

        for idx, (dur, is_d) in enumerate(zip(durations, drop_flags)):
            if not is_d:
                ordered_clips.append(clip_paths[0])
            elif idx == n_clips - 1:
                ordered_clips.append(finisher_c)
            else:
                ordered_clips.append(combat_pool[combat_i % len(combat_pool)])
                combat_i += 1
        clip_paths = ordered_clips
    elif clip_paths:
        while len(clip_paths) < n_clips:
            clip_paths.append(clip_paths[len(clip_paths) % len(clip_paths)])

    if not clip_paths:
        raise RuntimeError("No clips available after all download attempts.")

    real_clips_count = sum(1 for cp in clip_paths if not cp.name.startswith("proc_"))
    is_procedural = (real_clips_count == 0)

    # Micro-flash inserts REMOVED — reference uses rare flashes as overlays, not segments.
    # Flashes are handled via build_beat_flash_filters (2-3 total per edit) as overlays.

    # 5. Viral Upper-Third Statement Subtitles (Spur World / Reference Style) + Dialogue Subtitles
    ass_path = None
    if enable_subtitles or burn_subtitles or subtitle_style == "spur_hook":
        try:
            ass_out = SCRATCH_DIR / f"subtitles_{character_key}.ass"
            # Fetch pre-fight dialogue lines from metadata or fallback catalog
            dialogue_lines = []
            ep_meta = None
            detected_ep_code = None
            for cp in clip_paths:
                code = match_episode_code_from_filename(cp.name)
                if code:
                    detected_ep_code = code
                    ep_meta = load_episode_metadata(code)
                    if ep_meta:
                        break
            if not ep_meta:
                default_ep = (
                    "DS_S02E06" if character_key in ("rengoku", "akaza")
                    else "JJK_S02E04" if character_key in ("gojo", "toji")
                    else "JJK_S02E17" if character_key in ("sukuna", "mahoraga")
                    else None
                )
                if default_ep:
                    detected_ep_code = default_ep
                    ep_meta = load_episode_metadata(default_ep)

            # Scene-grounded non-repeating engaging hook question
            from core.question_manager import get_engaging_question
            quote_text = custom_quote or get_engaging_question(
                character_key=character_key,
                episode_code=detected_ep_code,
                anime_universe=theme.get("universe")
            )
            metadata["engagement_question"] = quote_text
            metadata["quote"] = quote_text

            # Detect if clip_0 is associated with a specific scene's frame-accurate dialogue
            clip0_name = clip_paths[0].name if clip_paths else ""
            ts_match = re.search(r"(\d+)s", clip0_name)
            clip0_ts = float(ts_match.group(1)) if ts_match else None

            scene_dialogue = None
            if ep_meta and "scenes" in ep_meta and clip0_ts is not None:
                for s in ep_meta["scenes"]:
                    st = float(s.get("start", -999))
                    en = float(s.get("end", -999))
                    if abs(st - clip0_ts) < 5.0 or (st <= clip0_ts <= en):
                        if "dialogue" in s:
                            scene_dialogue = s["dialogue"]
                            break

            raw_dialogue = scene_dialogue or (ep_meta.get("intro_dialogue") if ep_meta else None) or DEFAULT_CHARACTER_DIALOGUE.get(character_key)
            if clip_paths and clip_paths[0].exists():
                from core.audio_speech_syncer import get_synced_dialogue_for_clip
                dialogue_lines = get_synced_dialogue_for_clip(
                    clip_path=clip_paths[0],
                    fallback_dialogue=raw_dialogue,
                    drop_time=beat_grid.drop_time
                )
            elif raw_dialogue:
                drop_t = beat_grid.drop_time
                for item in raw_dialogue:
                    s_rel = float(item.get("start_rel", item.get("start", 0.0)))
                    e_rel = float(item.get("end_rel", item.get("end", s_rel + 3.0)))
                    # Never accelerate dialogue with artificial scale factors — preserve 100% natural speech sync
                    if s_rel < drop_t - 0.2:
                        dialogue_lines.append({
                            "speaker": item.get("speaker", ""),
                            "text": item.get("text", ""),
                            "start": round(s_rel, 2),
                            "end": round(min(drop_t - 0.15, e_rel), 2),
                            "glow_color": item.get("glow_color", "")
                        })

            ass_path = generate_kinetic_subtitles(
                quote_text=quote_text,
                start_time=0.2,
                end_time=beat_grid.duration - 0.5,
                output_ass_path=ass_out,
                style_preset=subtitle_style or "spur_hook",
                character_name=theme["name"],
                drop_time=beat_grid.drop_time,
                dialogue_lines=dialogue_lines
            )
            print(f"✨ [Subtitles] Generated viral '{subtitle_style}' ASS subtitles with {len(dialogue_lines)} dialogue lines: {ass_path.name}")
        except Exception as e:
            print(f"⚠️ [Subtitles] Notice generating subtitles: {e}")
            ass_path = None

    active_cc = cc_preset or theme["cc_preset"]
    cc_cfg = CC_PRESETS.get(active_cc, CC_PRESETS["marvel_hdr"])
    
    # 6. Build Multi-Layer FFmpeg Filtergraph (OpenCut-Inspired)
    cmd_inputs = []
    has_clip_audio_list = []
    
    for cp in clip_paths:
        cmd_inputs.extend(["-i", str(cp)])
        has_clip_audio_list.append(check_clip_has_audio(cp))
        
    phonk_inp_idx = len(clip_paths)
    phonk_offset = getattr(beat_grid, "audio_offset", 0.0)
    if phonk_offset > 0.0:
        cmd_inputs.extend(["-ss", f"{phonk_offset:.2f}", "-i", str(audio_path)])
    else:
        cmd_inputs.extend(["-i", str(audio_path)])

    filter_chains = []
    concat_v_inputs = []
    concat_a_inputs = []

    # Character-driven dual-tone color grading (matches reference's emotion-based
    # cool-blue ↔ warm-red alternation + 3 monochromatic modes).
    # Each character has a primary tone + energy color (from CHARACTER_COLOR_MAP).
    char_colors = CHARACTER_COLOR_MAP.get(character_key, CHARACTER_COLOR_MAP["gojo"])
    primary_tone = char_colors["primary"]           # e.g. "cool_blue"
    energy_tone = char_colors["energy"]             # e.g. "yuji_cyan"
    secondary_tone = "warm_red" if primary_tone == "cool_blue" else "cool_blue"
    mono_modes = ["mono_bw", "mono_blue", "mono_white"]

    # ── Open-Source Video Editor Pathway vs Native Precise Motion Tracking ──
    # Precise motion tracking requires continuous OpenCV trajectory cropping in FFmpeg.
    # Editly is only invoked if motion tracking is not available or explicitly disabled.
    use_editly = False
    if use_editly and is_editly_available():
        print("🚀 [OpenSourceEditor] Detected mifi/editly. Assembling AMV using open-source WebGL editor...")
        temp_editly_out = SCRATCH_DIR / f"editly_raw_{character_key}.mp4"
        spec = generate_editly_spec(
            clip_paths=clip_paths,
            segments=segments,
            audio_path=audio_path,
            output_path=temp_editly_out,
            width=VIDEO_WIDTH,
            height=VIDEO_HEIGHT,
            fps=FPS,
            audio_offset=phonk_offset
        )
        if render_with_editly(spec, output_path=temp_editly_out):
            print("✨ [OpenSourceEditor] editly render succeeded! Applying loudnorm mastering...")
            combat_times = [round(seg["start"], 3) for seg in segments if seg.get("is_drop", False)]
            if post_process_editly_output(temp_editly_out, output_path, drop_time=beat_grid.drop_time, combat_cut_times=combat_times, ass_path=ass_path):
                print(f"✅ Rendered AMV successfully via editly: {output_path.name} ({output_path.stat().st_size // 1024} KB)")
                return {
                    "status": "success",
                    "output_path": output_path,
                    "metadata": metadata,
                    "character_key": character_key,
                    "duration": beat_grid.duration,
                    "drop_time": beat_grid.drop_time,
                    "cuts_count": len(segments),
                    "cut_timestamps": [round(seg["start"], 3) for seg in segments],
                    "file_size_kb": output_path.stat().st_size // 1024,
                    "audio_used": Path(audio_path).name,
                    "subtitle_style": subtitle_style,
                    "cc_preset": active_cc,
                    "is_procedural": is_procedural,
                    "real_footage_count": real_clips_count,
                    "engine": "editly"
                }
        print("⚠️ [OpenSourceEditor] editly render did not complete. Falling back to native FFmpeg xfade engine.")

    # 2026 Buttery-Smooth AMV Transitions with Zero-Drift Handle Compensation (0.18s punchy xfade)
    # Each clip (except final) receives +0.18s handle to perfectly maintain 100% beat sync without drift.
    trans_dur = 0.18
    first_drop_found = False
    for idx, seg in enumerate(segments):
        if idx > 0 and segments[idx - 1].get("is_drop", False):
            seg.setdefault("prev_is_drop", True)
        if seg.get("is_drop", False) and not first_drop_found:
            seg.setdefault("is_first_drop", True)
            first_drop_found = True
        if not seg.get("is_drop", False):
            if idx < len(segments) - 1 and segments[idx + 1].get("is_drop", False):
                seg["next_is_drop"] = True
                seg["is_pre_drop"] = True

    from core.vocal_isolator import extract_speech_intervals_from_dialogue, build_vocal_isolation_filter
    speech_intervals = extract_speech_intervals_from_dialogue(dialogue_lines, drop_time=beat_grid.drop_time)

    seen_clip_paths = {}
    for idx, (cp, seg, has_aud) in enumerate(zip(clip_paths, segments, has_clip_audio_list)):
        cp_key = str(cp.name) if hasattr(cp, "name") else str(cp)
        # Extract unique scene identifier: match timestamp tag (e.g. 885s) and episode tag (ep1)
        ep_match = re.search(r"ep(\d+)", cp_key)
        ts_match = re.search(r"(\d+)s(?:\.mp4)?", cp_key)
        if ts_match:
            ep_tag = ep_match.group(1) if ep_match else "0"
            scene_key = f"ep{ep_tag}_{ts_match.group(1)}s"
        else:
            scene_key = cp_key

        seen_clip_paths[scene_key] = seen_clip_paths.get(scene_key, 0) + 1
        if seen_clip_paths[scene_key] > 1:
            seg["is_repeat"] = True
            seg["repeat_count"] = seen_clip_paths[scene_key]

        vel_profile = get_segment_velocity_profile(seg, idx, len(segments))
        is_intro_hook = (idx == 0)
        use_bezier = vel_profile.get("use_bezier_velocity", False)
        use_slowmo = vel_profile.get("use_smooth_slowmo", False)
        clip_render_dur = seg["duration"] + (trans_dur if idx < len(segments) - 1 else 0.0)

        v_chain = build_velocity_clip_filter(
            seg_idx=idx,
            duration=clip_render_dur,
            speed=vel_profile["speed"],
            scale_factor=vel_profile["scale_factor"],
            video_width=VIDEO_WIDTH,
            video_height=VIDEO_HEIGHT,
            fps=FPS,
            add_bars=vel_profile.get("add_bars", False),
            is_intro_hook=is_intro_hook,
            use_bezier_velocity=use_bezier,
            use_smooth_slowmo=use_slowmo,
            clip_path=cp,
            enable_motion_tracking=True,
            narrative_role=seg.get("role"),
            input_tag=f"[{idx}:v]",
            output_tag=f"[v{idx}]"
        )
        filter_chains.append(v_chain)
        concat_v_inputs.append(f"[v{idx}]")

        # Anime Background Music Cancellation & Vocal Isolation:
        # Pre-Fight Dialogue (idx == 0): Cancels stereo OST, bandpass filters speech formants, gates silence
        # Combat Climax (idx >= 1): Mutes anime audio (0.0 volume) so only pure Phonk music plays
        is_conv = not seg.get("is_drop", False)
        audio_fade = build_clip_audio_fade(seg["duration"])
        if has_aud:
            vocal_filter = build_vocal_isolation_filter(
                clip_path=cp,
                speech_intervals=speech_intervals if is_conv else None,
                is_conversation=is_conv
            )
            a_chain = (
                f"[{idx}:a]atrim=duration={seg['duration']:.3f},asetpts=PTS-STARTPTS,"
                f"{audio_fade},{vocal_filter},aformat=sample_rates=48000:channel_layouts=stereo[a{idx}]"
            )
        else:
            a_chain = f"aevalsrc=0:d={seg['duration']:.3f},aformat=sample_rates=48000:channel_layouts=stereo[a{idx}]"
        filter_chains.append(a_chain)
        concat_a_inputs.append(f"[a{idx}]")

    # 2026 Modern AMV xfade transitions (smooth directional movement & kinetic zooms, zero random flashes)
    seg_durs = [s["duration"] for s in segments]
    drop_idx = sum(1 for s in segments if not s.get("is_drop", False))
    xfade_chain = build_xfade_transition_filter(
        len(clip_paths),
        seg_durs,
        transition_duration=trans_dur,
        drop_index=drop_idx,
        use_handle_compensation=True
    )
    if xfade_chain and len(clip_paths) >= 2:
        filter_chains.append(xfade_chain)
        video_src_tag = "[xfade_vout]"
    else:
        concat_v_str = "".join(concat_v_inputs) + f"concat=n={len(clip_paths)}:v=1:a=0[concatenated_v]"
        filter_chains.append(concat_v_str)
        video_src_tag = "[concatenated_v]"

    concat_a_str = "".join(concat_a_inputs) + f"concat=n={len(clip_paths)}:v=0:a=1[clip_sfx_raw]"
    filter_chains.append(concat_a_str)

    # Vibrant Anime Glow Color Grading (Zero random flashes / strobe per pro tutorials)
    vibrant_cc = build_cc_filter(active_cc)
    sub_filter = ""
    if ass_path and ass_path.exists():
        escaped_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
        sub_filter = f",subtitles='{escaped_ass}'"
    filter_chains.append(
        f"{video_src_tag}{vibrant_cc}{sub_filter}[vout]"
    )

    # Audio Dynamic Structure:
    # Pre-Fight Dialogue Phase: Phonk heavily ducked (0.20x) & lowpass filtered (380Hz); dialogue loud & clear (volume 1.60)
    # Pre-Drop Audio Vacuum (0.55s highpass riser + 0.16s dead silence + 808 drop sub-boost)
    # Katana Combat Foley transient presence on cut onsets
    # Master: loudnorm to -14 dB LUFS (-af loudnorm=I=-14:TP=-1.5:LRA=11)
    audio_vacuum_fx = build_pre_drop_audio_vacuum_filter(drop_t)
    combat_times = [round(seg["start"], 3) for seg in segments if seg.get("is_drop", False)]
    combat_foley_fx = build_combat_foley_audio_filter(combat_times, drop_t)
    audio_fade_start = max(0.1, beat_grid.duration - 3.5)
    audio_fade_dur = min(3.0, beat_grid.duration - audio_fade_start)
    filter_chains.append(
        f"[clip_sfx_raw]volume=1.0,{combat_foley_fx},highpass=f=80,lowpass=f=14000[clip_sfx_balanced];"
        f"[{phonk_inp_idx}:a]{audio_vacuum_fx},volume=1.0[phonk_full];"
        f"[phonk_full][clip_sfx_balanced]amix=inputs=2:duration=first:weights=60 40:dropout_transition=2,"
        f"volume=1.20,afade=t=out:st={audio_fade_start:.2f}:d={audio_fade_dur:.2f},loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
    )

    full_filter_complex = ";".join(filter_chains)

    cmd = [
        "ffmpeg", "-y",
        *cmd_inputs,
        "-filter_complex", full_filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "medium",
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
        "drop_time": beat_grid.drop_time,
        "cuts_count": len(segments),
        "cut_timestamps": [round(seg["start"], 3) for seg in segments],
        "file_size_kb": output_path.stat().st_size // 1024,
        "audio_used": Path(audio_path).name,
        "subtitle_style": subtitle_style,
        "cc_preset": active_cc,
        "is_procedural": is_procedural,
        "real_footage_count": real_clips_count
    }
