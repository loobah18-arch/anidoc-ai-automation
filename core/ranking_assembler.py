"""
Ranking Edits Countdown Assembler for AniDoc.
Replicates the viral Top 5 Anime/Marvel Edits Countdown format (e.g. https://youtube.com/shorts/aCOocNA2Bko).

Architecture:
1. 1080x1440 (3:4 ratio) or 1080x1920 (9:16 ratio) canvas.
2. Top 440px: Gaussian-blurred ambient background + stylized 'Ranking Best JJK edits' header
   + dynamic progressive countdown board (5. 1.1M -> 4. 1.4M -> 3. 1.6M -> 2. 1.7M -> 1. 2.4M).
3. Bottom 1000px: 60fps high-octane anime action viewport with velocity curves and Cyber Phonk CC.
4. Auto-saves directly to Android/Termux Download folder with zero cloud upload.
"""
import os
import subprocess
import random
from pathlib import Path
from typing import List, Dict, Any, Optional

from config.settings import SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS
from core.download_saver import save_to_downloads
from core.clip_manager import get_character_scene_clips, CHARACTER_THEMES
from core.phonk_manager import get_random_or_specified_phonk
from core.effects_engine import build_cc_filter, build_velocity_clip_filter
from core.video_assembler import check_clip_has_audio


# Default 5-Tier Ranking Roster for JJK
JJK_RANKING_TIERS = [
    {
        "rank": 5,
        "character": "yuji",
        "title": "Choso vs Yuji (Blood Manipulation)",
        "views": "1.1M",
        "duration": 11.5,
        "highlight_color": "&H002BF5FF"
    },
    {
        "rank": 4,
        "character": "megumi",
        "title": "Yuta Okkotsu & Rika (Pure Love)",
        "views": "1.4M",
        "duration": 11.5,
        "highlight_color": "&H00FF55D2"
    },
    {
        "rank": 3,
        "character": "megumi",
        "title": "Megumi Fushiguro (Mahoraga Summon)",
        "views": "1.6M",
        "duration": 11.5,
        "highlight_color": "&H0000D2FF"
    },
    {
        "rank": 2,
        "character": "sukuna",
        "title": "Ryomen Sukuna (Malevolent Shrine & Fuga)",
        "views": "1.7M",
        "duration": 11.5,
        "highlight_color": "&H000022FF"
    },
    {
        "rank": 1,
        "character": "gojo",
        "title": "Gojo Satoru & Toji (Honored One Awakening)",
        "views": "2.4M",
        "duration": 12.5,
        "highlight_color": "&H00FF0088"
    },
]


def generate_ranking_countdown_ass(
    tiers: List[Dict[str, Any]],
    output_ass_path: Path,
    title_text: str = "Ranking Best JJK edits",
    total_duration: float = 58.5,
    canvas_w: int = 1080,
    canvas_h: int = 1440
) -> Path:
    """
    Generates a dynamic ASS subtitle script that updates the countdown board
    in real time as each tier plays from Rank 5 down to Rank 1.
    """
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {canvas_w}",
        f"PlayResY: {canvas_h}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Header,Arial,66,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,6,3,8,40,40,60,1",
        "Style: Board,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,5,2,8,40,40,150,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    # Format title with red accent for 'JJK' / 'Marvel'
    formatted_title = title_text.replace("JJK", "{\\c&H0000FF&}JJK{\\c&HFFFFFF&}").replace("Marvel", "{\\c&H0000FF&}Marvel{\\c&HFFFFFF&}")
    ass_lines.append(f"Dialogue: 0,0:00:00.00,{_sec_to_ass_ts(total_duration)},Header,,0,0,0,,{{\\pos(540,80)}}{formatted_title}")

    # Build progressive board state for each tier
    elapsed = 0.0
    for idx, t in enumerate(tiers):
        t_start = elapsed
        t_end = min(total_duration, elapsed + t["duration"])
        elapsed = t_end

        # Lines 1 to 5
        board_rows = []
        for r_num in range(1, 6):
            # Check if this rank is active or already revealed
            # Tiers are ordered 5 down to 1
            # Rank 5 is active at tier 0, Rank 4 active at tier 1, etc.
            tier_for_rank = next((x for x in tiers if x["rank"] == r_num), None)
            tier_idx_for_rank = tiers.index(tier_for_rank) if tier_for_rank else -1

            if tier_idx_for_rank <= idx and tier_for_rank:
                # Revealed
                views = tier_for_rank["views"]
                if tier_idx_for_rank == idx:
                    # Currently active rank (highlight color)
                    hl = t.get("highlight_color", "&H002BF5FF")
                    board_rows.append(f"{{\\c{hl}&}}{r_num}. {views}{{\\c&HFFFFFF&}}")
                else:
                    board_rows.append(f"{r_num}. {views}")
            else:
                board_rows.append(f"{r_num}.")

        board_text = "\\N".join(board_rows)
        ass_lines.append(
            f"Dialogue: 0,{_sec_to_ass_ts(t_start)},{_sec_to_ass_ts(t_end)},Board,,0,0,0,,{{\\pos(540,165)}}{board_text}"
        )

    output_ass_path.parent.mkdir(parents=True, exist_ok=True)
    output_ass_path.write_text("\n".join(ass_lines), encoding="utf-8")
    return output_ass_path


def _sec_to_ass_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def render_ranking_countdown_edit(
    universe: str = "jjk",
    title_text: str = "Ranking Best JJK edits",
    output_filename: str = "JJK_Top5_Best_Edits_Ranking_Countdown.mp4",
    save_to_device_downloads: bool = True
) -> Path:
    """
    Renders the complete 5-Rank compilation edit with dynamic countdown board,
    ambient blurred backdrop, high-contrast CC, and saves to device Downloads.
    """
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    out_mp4 = SCRATCH_DIR / output_filename
    tiers = JJK_RANKING_TIERS

    total_duration = sum(t["duration"] for t in tiers)
    print(f"🎬 [RankingAssembler] Starting Ranking Countdown Assembly ({total_duration:.1f}s, {len(tiers)} Tiers)")

    # 1. Gather clips and audio for each tier
    tier_clip_paths = []
    for t in tiers:
        char_key = t["character"]
        print(f"  🎯 Preparing Rank {t['rank']}: {t['title']} ({char_key})")
        clips = get_character_scene_clips(
            character_key=char_key,
            segment_durations=[t["duration"]],
            is_drop_flags=[True],
            auto_fetch_online=True
        )
        if not clips:
            from core.clip_manager import generate_procedural_cinematic_scene
            p_clip = SCRATCH_DIR / f"proc_{char_key}_rank_{t['rank']}.mp4"
            generate_procedural_cinematic_scene(char_key, 0, t["duration"], p_clip, is_drop=True)
            clips = [p_clip]
        tier_clip_paths.append(clips[0])

    # 2. Get BGM Audio
    bgm_path = get_random_or_specified_phonk()
    if not bgm_path or not bgm_path.exists():
        from core.video_assembler import generate_fallback_phonk_audio
        bgm_path = generate_fallback_phonk_audio(total_duration, SCRATCH_DIR / "ranking_bgm.aac")
    print(f"🎧 [RankingAssembler] Using Phonk Track: {bgm_path.name}")

    # 3. Generate dynamic ASS countdown board
    ass_path = SCRATCH_DIR / "ranking_countdown.ass"
    generate_ranking_countdown_ass(
        tiers=tiers,
        output_ass_path=ass_path,
        title_text=title_text,
        total_duration=total_duration,
        canvas_w=1080,
        canvas_h=1440
    )

    # 4. Build Multi-tier Concat & Split-Screen Filtergraph
    # We concatenate tier clips, scale to 1080x1000 viewport, blur background to 1080x1440,
    # overlay viewport at y=440, and burn dynamic ASS countdown board!
    cmd_inputs = []
    for cp in tier_clip_paths:
        cmd_inputs.extend(["-i", str(cp)])
    phonk_idx = len(tier_clip_paths)
    cmd_inputs.extend(["-i", str(bgm_path)])

    filter_chains = []
    concat_v_inputs = []
    concat_a_inputs = []

    for idx, (cp, t) in enumerate(zip(tier_clip_paths, tiers)):
        t_dur = t["duration"]
        has_aud = check_clip_has_audio(cp)

        # Scale each tier clip to 1080x1000 square action viewport
        v_chain = (
            f"[{idx}:v]scale=1080:1000:force_original_aspect_ratio=increase,"
            f"crop=1080:1000,setsar=1,fps={FPS},trim=duration={t_dur:.2f},setpts=PTS-STARTPTS[vt{idx}]"
        )
        filter_chains.append(v_chain)
        concat_v_inputs.append(f"[vt{idx}]")

        if has_aud:
            a_chain = (
                f"[{idx}:a]atrim=duration={t_dur:.2f},asetpts=PTS-STARTPTS,"
                f"volume=1.4,aformat=sample_rates=48000:channel_layouts=stereo[at{idx}]"
            )
        else:
            a_chain = (
                f"aevalsrc=0:d={t_dur:.2f},aformat=sample_rates=48000:channel_layouts=stereo[at{idx}]"
            )
        filter_chains.append(a_chain)
        concat_a_inputs.append(f"[at{idx}]")

    # Concat tier videos
    concat_v = "".join(concat_v_inputs) + f"concat=n={len(tier_clip_paths)}:v=1:a=0[raw_action_v]"
    filter_chains.append(concat_v)

    # Concat tier clip audio
    concat_a = "".join(concat_a_inputs) + f"concat=n={len(tier_clip_paths)}:v=0:a=1[raw_clip_a]"
    filter_chains.append(concat_a)

    # CC Color Grading
    cc_preset = build_cc_filter("cyber_phonk")

    # Split-Screen Compositing:
    # 1. Background: scale to 1080x1440, blur 30px, dim brightness -0.3
    # 2. Viewport: overlay at y=440
    # 3. Add top neon separator line at y=438
    # 4. Burn-in ASS dynamic countdown board
    ass_escaped = str(ass_path).replace(":", "\\:").replace("\\", "/")
    comp_chain = (
        f"[raw_action_v]{cc_preset},split=2[act_fg][act_bg];"
        f"[act_bg]scale=1080:1440:force_original_aspect_ratio=increase,crop=1080:1440,gblur=sigma=32,eq=brightness=-0.35[bg];"
        f"[bg][act_fg]overlay=0:440[comp_base];"
        f"[comp_base]drawbox=x=0:y=438:w=1080:h=3:color=white@0.8:t=fill,"
        f"ass={ass_escaped}[vout]"
    )
    filter_chains.append(comp_chain)

    # Audio Mixing: 35% clip audio + 65% Phonk BGM with loudnorm
    audio_mix_chain = (
        f"[{phonk_idx}:a]atrim=duration={total_duration:.2f},asetpts=PTS-STARTPTS,volume=0.70[phonk_a];"
        f"[raw_clip_a]volume=0.85[clip_a];"
        f"[clip_a][phonk_a]amix=inputs=2:duration=first:dropout_transition=2[a_mixed];"
        f"[a_mixed]loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
    )
    filter_chains.append(audio_mix_chain)

    full_filtergraph = ";".join(filter_chains)

    render_cmd = [
        "ffmpeg", "-y",
        *cmd_inputs,
        "-filter_complex", full_filtergraph,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "256k",
        "-t", f"{total_duration:.2f}",
        str(out_mp4)
    ]

    print(f"⚡ [RankingAssembler] Rendering FFmpeg Filtergraph...")
    res = subprocess.run(render_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"⚠️ FFmpeg error: {res.stderr[-800:]}")
        raise RuntimeError(f"FFmpeg rendering failed: {res.stderr[-400:]}")

    size_mb = out_mp4.stat().st_size / (1024 * 1024)
    print(f"✅ Rendered Ranking Countdown Edit successfully: {out_mp4.name} ({size_mb:.2f} MB)")

    # 5. Save to local device Download directory
    if save_to_device_downloads:
        dest = save_to_downloads(out_mp4, custom_name=output_filename)
        if dest:
            print(f"🎉 Final edit is ready in your device Downloads folder: {dest.name}")

    return out_mp4
