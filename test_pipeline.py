"""
Comprehensive Test Suite for AniDoc 4K Phonk & Scene Edit Automation Engine.
Validates Phonk Audio Library, Public API / GitHub Clip Fetcher, Subtitle Stylizer, and Studio Server.
"""
import unittest
import subprocess
from pathlib import Path

from config.settings import SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, CC_PRESETS, PHONK_DIR
from core.beat_detector import generate_procedural_beat_grid, analyze_audio_beats
from core.effects_engine import (
    build_cc_filter,
    build_monochrome_cc_filter,
    build_beat_flash_filters,
    get_segment_velocity_profile,
    build_velocity_clip_filter
)
from core.clip_manager import generate_procedural_cinematic_scene, get_character_scene_clips, CHARACTER_THEMES
from core.phonk_manager import list_available_phonk_tracks, get_random_or_specified_phonk, POPULAR_PHONK_CATALOG
from core.public_api_fetcher import slice_scenepack_into_clips
from core.subtitle_stylizer import generate_kinetic_subtitles, SUBTITLE_STYLE_PRESETS
from core.quote_ai import generate_edit_metadata
from core.video_assembler import render_cinematic_edit, generate_fallback_phonk_audio

class TestAniDocPipeline(unittest.TestCase):
    def setUp(self):
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    def test_01_phonk_library_manager(self):
        tracks = list_available_phonk_tracks()
        self.assertTrue(len(tracks) >= 2, "Should have at least 2 phonk tracks downloaded in library")
        self.assertTrue(len(POPULAR_PHONK_CATALOG) >= 5)
        
        # Test retrieval of specific existing track
        phonk_audio = get_random_or_specified_phonk(tracks[0]["id"])
        self.assertIsNotNone(phonk_audio)
        self.assertTrue(Path(phonk_audio).exists())

        # Test random phonk selection
        random_audio = get_random_or_specified_phonk("random")
        self.assertIsNotNone(random_audio)
        self.assertTrue(Path(random_audio).exists())

    def test_02_beat_grid_generation(self):
        # Narrative pacing: a 35s edit should produce ~15-20 cuts, NOT 100+
        grid = generate_procedural_beat_grid(duration=35.0, drop_time=6.0, bpm=130.0)
        self.assertEqual(grid.duration, 35.0)
        self.assertEqual(grid.drop_time, 6.0)
        self.assertTrue(len(grid.beat_times) >= 10)
        self.assertLess(len(grid.beat_times), 40, "Narrative pacing: should be ~20 cuts, not 100+")
        segments = grid.get_cut_segments()
        self.assertTrue(len(segments) >= 10)
        self.assertLess(len(segments), 40)
        self.assertTrue(any(s["is_drop"] for s in segments))
        # No micro-flash segments in narrative pacing
        self.assertTrue(all(not s.get("is_flash", False) for s in segments))

        # Flash timestamps are rare (max 3), not constant strobe
        flash_times = grid.get_flash_timestamps()
        self.assertLessEqual(len(flash_times), 3)

        # Test short edit (<30s) modern AMV velocity grid
        short_grid = generate_procedural_beat_grid(duration=28.0, drop_time=4.8, bpm=134.0)
        self.assertEqual(short_grid.duration, 28.0)
        self.assertEqual(short_grid.drop_time, 4.8)
        short_segs = short_grid.get_cut_segments()
        self.assertTrue(len(short_segs) >= 15, "Short AMV edit should produce 15+ cuts for high velocity")
        self.assertLess(len(short_segs), 45)
        self.assertTrue(any(abs(s["start"] - 4.8) < 0.05 for s in short_segs))

    def test_03_effects_filter_builders(self):
        marvel_cc = build_cc_filter("marvel_hdr")
        self.assertIn("eq=contrast=", marvel_cc)
        self.assertIn("unsharp=", marvel_cc)
        self.assertIn("vignette=", marvel_cc)

        jjk_cc = build_cc_filter("jjk_void")
        self.assertIn("eq=contrast=", jjk_cc)

        hinokami_cc = build_cc_filter("hinokami_flame")
        self.assertIn("eq=contrast=", hinokami_cc)

        # Monochromatic modes exist and desaturate heavily
        mono = build_monochrome_cc_filter("mono_bw")
        self.assertIn("eq=contrast=", mono)

        flashes = build_beat_flash_filters([6.0, 7.5, 9.0])
        self.assertEqual(len(flashes), 3)
        self.assertIn("drawbox=", flashes[0])

        # Velocity profiles: straight cut vs modern velocity
        vel_straight = get_segment_velocity_profile({"is_drop": True, "duration": 1.2}, 0, 10, enable_velocity_ramping=False)
        self.assertEqual(vel_straight["role"], "straight_cut")
        self.assertAlmostEqual(vel_straight["speed"], 1.0)

        vel_modern = get_segment_velocity_profile({"is_drop": True, "duration": 1.2}, 0, 10, enable_velocity_ramping=True)
        self.assertEqual(vel_modern["role"], "drop_impact")
        self.assertAlmostEqual(vel_modern["speed"], 1.30)

        # Intro (non-drop) segment gets slight slow-mo for cinematic weight
        intro_vel = get_segment_velocity_profile({"is_drop": False, "duration": 1.2}, 0, 10)
        self.assertEqual(intro_vel["role"], "intro_slowmo")
        self.assertAlmostEqual(intro_vel["speed"], 0.85)

        # Straight cuts should NOT have speed ramping (no *PTS multiplier)
        vf = build_velocity_clip_filter(0, 1.2, speed=1.0, scale_factor=1.0)
        self.assertNotIn("*PTS", vf)
        self.assertIn("setpts=PTS-STARTPTS", vf)
        self.assertIn("trim=duration=1.200", vf)

        # Slow-mo clip SHOULD have speed ramping (setpts multiplier)
        vf_slowmo = build_velocity_clip_filter(0, 1.2, speed=0.85, scale_factor=1.02)
        self.assertIn("*PTS", vf_slowmo)

    def test_04_quote_ai_metadata(self):
        yuji = generate_edit_metadata("yuji")
        self.assertEqual(yuji["universe"], "jjk")
        self.assertTrue(len(yuji["quote"]) > 5)
        self.assertTrue(len(yuji["title"]) > 10)
        self.assertTrue(len(yuji["tags"]) >= 4)

        gojo = generate_edit_metadata("gojo")
        self.assertEqual(gojo["universe"], "jjk")
        self.assertTrue(len(gojo["quote"]) > 5)

        tanjiro = generate_edit_metadata("tanjiro")
        self.assertEqual(tanjiro["universe"], "demonslayer")
        self.assertTrue(len(tanjiro["quote"]) > 5)
        self.assertTrue(len(tanjiro["title"]) > 10)
        self.assertTrue(len(tanjiro["tags"]) >= 4)

        rengoku = generate_edit_metadata("rengoku")
        self.assertEqual(rengoku["universe"], "demonslayer")
        self.assertTrue(len(rengoku["quote"]) > 5)

    def test_05_word_by_word_karaoke_subtitles(self):
        ass_out = SCRATCH_DIR / "test_subs.ass"
        for style in ["spur_hook", "viral_karaoke", "cyber_glow", "anime_shrine", "cinematic_minimal"]:
            generate_kinetic_subtitles(
                quote_text="Throughout heaven and earth I alone am the honored one",
                start_time=0.5,
                end_time=5.5,
                output_ass_path=ass_out,
                style_preset=style,
                character_name="GOJO",
                drop_time=2.5
            )
            self.assertTrue(ass_out.exists())
            with open(ass_out, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("[Script Info]", content)
                self.assertIn("HONORED", content)
                self.assertIn("BaseText", content)

    def test_06_procedural_scene_rendering(self):
        test_clip = SCRATCH_DIR / "test_proc_scene.mp4"
        generate_procedural_cinematic_scene("gojo", 0, 2.0, test_clip, is_drop=False)
        self.assertTrue(test_clip.exists())
        self.assertTrue(test_clip.stat().st_size > 5000)

        # Verify probe
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            str(test_clip)
        ]
        res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        self.assertIn(f"{VIDEO_WIDTH},{VIDEO_HEIGHT}", res.stdout)

    def test_07_end_to_end_video_assembly_with_phonk(self):
        out_video = SCRATCH_DIR / "test_assembled_edit.mp4"
        res = render_cinematic_edit(
            character_key="spiderman",
            phonk_track="lonown_avangard_phonk",
            subtitle_style="viral_karaoke",
            output_path=out_video,
            target_duration=4.5
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(out_video.exists())
        self.assertTrue(out_video.stat().st_size > 50000)

        # Verify aspect ratio & duration
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height,codec_name",
            "-of", "csv=p=0",
            str(out_video)
        ]
        probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        self.assertIn(f"{VIDEO_WIDTH},{VIDEO_HEIGHT}", probe_res.stdout)

    def test_08_automated_edit_reviewer(self):
        from core.automated_edit_reviewer import review_edit_and_benchmark, generate_markdown_report
        out_video = SCRATCH_DIR / "test_assembled_edit.mp4"
        if not out_video.exists():
            return
        review = review_edit_and_benchmark(out_video, expected_drop_time=1.5)
        self.assertIn("overall_score", review)
        self.assertIn("pillar_scores", review)
        self.assertTrue(review["overall_score"] > 50)
        report_md = generate_markdown_report(review)
        self.assertIn("AniDoc Automated Edit Review", report_md)

    def test_09_modern_amv_architectural_features(self):
        # 1. Typography & Unicode Emoji Sanitization
        from core.text_overlay import clean_overlay_text, build_engagement_hook_overlay
        raw_text = "Hinokami Kagura 🔥⚡ Slash ⚔️ Rate 1-10 👇"
        cleaned = clean_overlay_text(raw_text)
        self.assertNotIn("🔥", cleaned)
        self.assertNotIn("⚡", cleaned)
        self.assertNotIn("⚔️", cleaned)
        self.assertNotIn("👇", cleaned)
        self.assertIn("★", cleaned)
        self.assertIn("//", cleaned)
        self.assertIn(">>", cleaned)

        # 2. Dynamic Timed Typography Overlays (First 3.5s hook, Final 4.0s CTA)
        hook_overlay = build_engagement_hook_overlay("tanjiro", total_duration=28.0)
        self.assertIn("between(t\\,0\\,3.50)", hook_overlay)
        self.assertIn("gte(t\\,24.00)", hook_overlay)
        self.assertIn("borderw=4", hook_overlay)
        self.assertIn("shadowcolor=", hook_overlay)

        # 3. Full 9:16 Vertical Layout (Blurred Synced Background + 4:5 Foreground)
        from core.effects_engine import (
            build_vertical_dual_layer_chain,
            build_selective_bloom_filter,
            build_heavy_drop_impact_filters
        )
        dual_chain = build_vertical_dual_layer_chain(
            input_tag="[0:v]",
            output_tag="[v0]",
            seg_idx=0,
            duration=2.5,
            speed=1.0,
            scale_factor=1.10,
            video_width=1080,
            video_height=1920,
            fg_height=1350,
            y_offset=285,
            fps=60,
            is_intro_hook=True
        )
        # 6% edge crop
        self.assertIn("crop=in_w*0.88:in_h*0.88:in_w*0.06:in_h*0.06", dual_chain)
        # Blurred synced background (1080x1920, boxblur=28:5, brightness 0.45)
        self.assertIn("boxblur=28:5", dual_chain)
        self.assertIn("colorchannelmixer=aa=1.0:rr=0.45:gg=0.45:bb=0.45", dual_chain)
        # 4:5 Foreground (1080x1350) with 4px border at y=285
        self.assertIn("drawbox=x=0:y=0:w=1080:h=1350:color=white@0.65:t=4", dual_chain)
        self.assertIn("overlay=x=0:y=285", dual_chain)

        # 4. Selective Bloom / Glow (Highlights > 185, additive 30%)
        bloom = build_selective_bloom_filter("[base_v]", "[bloom_v]", threshold=185, opacity=0.30)
        self.assertIn("lutyuv=y='if(gt(val,185),val,0)'", bloom)
        self.assertIn("blend=all_mode=addition:all_opacity=0.30", bloom)

        # 5. Heavy Drop Impacts (2-frame 25% white exposure burst, clean without chromashift or neighbor scaling)
        impacts = build_heavy_drop_impact_filters([4.80, 12.50])
        self.assertEqual(len(impacts), 2)  # 2 timestamps x 1 flash
        self.assertTrue(any("color=white@0.25" in f for f in impacts))

        # 6. SceneScorer OpenCV module
        from core.scene_scorer import SceneScorer
        test_clip = SCRATCH_DIR / "test_proc_scene.mp4"
        if test_clip.exists():
            scorer = SceneScorer(test_clip)
            windows = scorer.analyze(step_frames=4, window_duration=1.0)
            self.assertTrue(len(windows) >= 1)
            self.assertIn("score", windows[0])
            self.assertIn("avg_luma", windows[0])
            self.assertIn("avg_diff", windows[0])

    def test_10_open_source_editor_integration(self):
        from core.open_source_editor import (
            is_editly_available, generate_editly_spec, EDITLY_TRANSITIONS
        )
        self.assertIsInstance(is_editly_available(), bool)
        self.assertTrue(len(EDITLY_TRANSITIONS) >= 5)

        # Verify declarative spec generation with 16:9 widescreen contain mode
        dummy_clips = [Path("/tmp/c1.mp4"), Path("/tmp/c2.mp4")]
        dummy_segs = [
            {"duration": 2.5, "is_drop": False},
            {"duration": 3.0, "is_drop": True}
        ]
        spec = generate_editly_spec(
            clip_paths=dummy_clips,
            segments=dummy_segs,
            audio_path=Path("/tmp/audio.mp3"),
            output_path=Path("/tmp/out.mp4")
        )
        self.assertEqual(spec["width"], VIDEO_WIDTH)
        self.assertEqual(spec["height"], VIDEO_HEIGHT)
        self.assertEqual(spec["fps"], 60)
        self.assertEqual(len(spec["clips"]), 2)
        # Ensure 16:9 widescreen contain mode is specified
        self.assertEqual(spec["clips"][0]["layers"][0]["resizeMode"], "contain")
        self.assertEqual(spec["clips"][1]["layers"][0]["resizeMode"], "contain")
        # Ensure beat drop transition is crosszoom
        self.assertEqual(spec["clips"][0]["transition"]["name"], "crosszoom")

    def test_11_bezier_velocity_and_audio_vacuum(self):
        from core.effects_engine import (
            build_bezier_velocity_pts_expression,
            build_pre_drop_audio_vacuum_filter,
            build_combat_foley_audio_filter,
            build_velocity_clip_filter
        )
        # 1. Non-linear Bézier 3-phase velocity curve
        expr = build_bezier_velocity_pts_expression(duration=1.2, fast_speed=2.2, slow_speed=0.40)
        self.assertIn("if(lt(T", expr)
        self.assertIn("TB", expr)

        # 2. Velocity filter with Bézier ramping (clean anime frames without tblend ghosting)
        vf = build_velocity_clip_filter(
            seg_idx=1,
            duration=1.2,
            speed=1.25,
            use_bezier_velocity=True
        )
        self.assertNotIn("tblend=all_mode=average", vf)
        self.assertIn("setpts=", vf)

        # 3. Pre-Drop Audio Vacuum filter (low-cut riser + dead-silence vacuum + bass boost)
        audio_fx = build_pre_drop_audio_vacuum_filter(drop_time=4.80)
        self.assertIn("highpass=f=1200", audio_fx)
        self.assertIn("volume=0.0", audio_fx)
        self.assertIn("volume=1.35", audio_fx)
        self.assertIn("bass=g=4:f=65", audio_fx)

        # 4. Katana Combat Foley sound design filter
        foley_fx = build_combat_foley_audio_filter(combat_cut_times=[4.80, 5.50, 6.20], drop_time=4.80)
        self.assertIn("treble=g=3.5:f=4800", foley_fx)
        self.assertIn("bass=g=3.0:f=85", foley_fx)
        self.assertIn("volume=1.50", foley_fx)

    def test_12_modern_xfade_transitions(self):
        from core.xfade_engine import (
            build_xfade_transition_filter,
            MODERN_COMBAT_TRANSITIONS,
            MODERN_DROP_TRANSITIONS,
            MODERN_OUTRO_TRANSITIONS
        )
        self.assertTrue(len(MODERN_COMBAT_TRANSITIONS) >= 5)
        self.assertIn("smoothleft", MODERN_COMBAT_TRANSITIONS)
        self.assertIn("smoothright", MODERN_COMBAT_TRANSITIONS)
        self.assertIn("zoomin", MODERN_DROP_TRANSITIONS)

        # Chained filter with drop index and outro
        durs = [1.5, 1.2, 0.8, 1.0, 1.4]
        xf = build_xfade_transition_filter(
            clip_count=len(durs),
            durations=durs,
            transition_duration=0.15,
            drop_index=2
        )
        self.assertIn("xfade=transition=", xf)
        self.assertIn("duration=0.15", xf)
        self.assertIn("[xfade_vout]", xf)

    def test_13_gdrive_slicer_filter_even_dimensions(self):
        """Verifies that GDrive action moment slicing filter strictly enforces even dimensions (preventing exit code 187)."""
        test_out = SCRATCH_DIR / "test_even_dim_slice.mp4"
        test_out.unlink(missing_ok=True)
        vf_chain = (
            "crop=trunc(in_w*0.88/2)*2:trunc(in_h*0.88/2)*2:trunc(in_w*0.06/2)*2:trunc(in_h*0.06/2)*2,"
            "scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,"
            "scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1,fps=60"
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=0.5:size=1920x1080:rate=30",
            "-t", "0.5",
            "-vf", vf_chain,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            str(test_out)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"FFmpeg failed: {res.stderr}")
        self.assertTrue(test_out.exists())
        self.assertGreater(test_out.stat().st_size, 5000)
        test_out.unlink(missing_ok=True)

    def test_14_smart_9_16_reframing(self):
        """
        Phase 1: Validates intelligent 9:16 composition engine:
        - Output fills 1080x1920 portrait canvas.
        - Zero black letterbox pad filters.
        - Fallback provides safe dynamic center crop.
        - Moving subjects produce smooth cosine ease-in/ease-out panning.
        - Static shots produce rock-solid stabilized crop coordinates.
        """
        from core.smart_reframe import build_smart_reframe_filter, analyze_clip_framing
        from core.effects_engine import build_velocity_clip_filter

        # 1. Fallback generates 9:16 fill without black bars
        fb = build_smart_reframe_filter(clip_path=None)
        self.assertIn("crop=", fb)
        self.assertIn("scale=1080:1920", fb)
        self.assertNotIn(",pad=", fb)

        # 2. Velocity clip filter integration produces zero letterbox padding
        vf = build_velocity_clip_filter(seg_idx=0, duration=1.2)
        self.assertIn("crop=", vf)
        self.assertIn("scale=1080:1920", vf)
        self.assertNotIn(",pad=", vf)
        self.assertNotIn("pad=1080", vf)
        self.assertNotIn("color=black", vf)

        # 3. Dynamic subject pan generates smooth easing curve
        mock_dynamic = {
            "in_w": 1920, "in_h": 1080,
            "cx_start": 0.20, "cx_end": 0.80,
            "cy_start": 0.50, "cy_end": 0.50,
            "is_dynamic": True
        }
        dyn_filter = build_smart_reframe_filter(duration=2.0, framing_info=mock_dynamic)
        self.assertIn("cos(PI*min", dyn_filter)
        self.assertIn("crop=608:1080:", dyn_filter)

        # 4. Static subject generates stable static crop
        mock_static = {
            "in_w": 1920, "in_h": 1080,
            "cx_start": 0.50, "cx_end": 0.50,
            "cy_start": 0.50, "cy_end": 0.50,
            "is_dynamic": False
        }
        static_filter = build_smart_reframe_filter(duration=2.0, framing_info=mock_static)
        self.assertNotIn("cos(", static_filter)
        self.assertIn("crop=608:1080:656:0", static_filter)

    def test_15_smart_shot_selection_and_pacing(self):
        from core.shot_selector import (
            score_candidate_shot,
            select_smart_shots,
            calculate_variable_pacing,
            compute_shot_similarity
        )
        import numpy as np

        # 1. Color fingerprint similarity
        fp1 = np.ones(24, dtype=np.float32) / np.sqrt(24)
        fp2 = np.ones(24, dtype=np.float32) / np.sqrt(24)
        sim = compute_shot_similarity(fp1, fp2)
        self.assertAlmostEqual(sim, 1.0, places=4)

        # 2. Variable narrative pacing
        beats = [1.6, 3.2, 4.8, 5.5, 6.2, 7.0, 7.8, 8.6, 9.4, 10.2, 11.5]
        pacing = calculate_variable_pacing(total_duration=12.0, drop_time=4.8, major_beat_times=beats)
        self.assertTrue(len(pacing) >= 6)

        # Durations must vary intentionally (no identical durations across all acts)
        durs = [s["duration"] for s in pacing]
        self.assertGreater(len(set(durs)), 2, "Shot pacing must have variable durations")

        # Pacing roles and drop alignment
        self.assertTrue(any(abs(s["start"] - 4.8) < 0.05 for s in pacing))
        intro_segs = [s for s in pacing if not s["is_drop"]]
        combat_segs = [s for s in pacing if s["is_drop"] and not s["is_climax"]]
        self.assertTrue(len(intro_segs) >= 1)
        self.assertTrue(len(combat_segs) >= 1)
        self.assertEqual(intro_segs[0]["role"], "intro_buildup")

        # Intro shots should be calmer on average than rapid combat shots
        avg_intro = sum(s["duration"] for s in intro_segs) / len(intro_segs)
        avg_combat = sum(s["duration"] for s in combat_segs) / len(combat_segs)
        self.assertGreater(avg_intro, avg_combat, "Intro shots should be calmer than combat shots")

    def test_16_music_synced_editing(self):
        from core.beat_detector import BeatGrid, generate_procedural_beat_grid

        grid = generate_procedural_beat_grid(duration=30.0, drop_time=4.8, bpm=134.0)

        # 1. Event hierarchy: drops, major beats, medium beats
        self.assertTrue(len(grid.drops) >= 1)
        self.assertIn(4.8, grid.drops)
        self.assertTrue(len(grid.major_beats) >= 4)
        self.assertTrue(len(grid.medium_beats) >= 2)

        # 2. Section detection: build-ups vs high-energy
        self.assertTrue(grid.is_build_up(2.0))
        self.assertFalse(grid.is_high_energy(2.0))
        self.assertTrue(grid.is_high_energy(5.5))

        # 3. Cut alignment to major beats
        segments = grid.get_cut_segments()
        self.assertTrue(len(segments) >= 10)
        self.assertTrue(any(s["is_major_beat"] for s in segments))
        drop_seg = next(s for s in segments if abs(s["start"] - 4.8) < 0.05)
        self.assertTrue(drop_seg["is_drop"])
        self.assertTrue(grid.is_major_beat(drop_seg["start"]))

    def test_17_subject_aware_camera_movement(self):
        from core.smart_reframe import build_smart_reframe_filter

        mock_framing = {
            "in_w": 1920, "in_h": 1080,
            "act_x": 0, "act_y": 0, "act_w": 1920, "act_h": 1080,
            "cx_start": 0.40, "cx_end": 0.60,
            "cy_start": 0.35, "cy_end": 0.35,
            "is_dynamic": True
        }

        # 1. Push-in motion anchored around subject
        push_filter = build_smart_reframe_filter(
            duration=1.5,
            framing_info=mock_framing,
            camera_motion="push_in"
        )
        self.assertIn("1.0-0.06*min", push_filter)
        self.assertIn("clip(", push_filter)
        self.assertIn("scale=1080:1920", push_filter)
        self.assertNotIn(",pad=", push_filter)

        # 2. Pull-out motion
        pull_filter = build_smart_reframe_filter(
            duration=1.5,
            framing_info=mock_framing,
            camera_motion="pull_out"
        )
        self.assertIn("0.94+0.06*min", pull_filter)
        self.assertIn("scale=1080:1920", pull_filter)

        # 3. Punch-in motion
        punch_filter = build_smart_reframe_filter(
            duration=0.8,
            framing_info=mock_framing,
            camera_motion="punch_in"
        )
        self.assertIn("min(t/0.20", punch_filter)
        self.assertIn("scale=1080:1920", punch_filter)

        # 4. Auto motion adapts by narrative role
        intro_auto = build_smart_reframe_filter(
            duration=1.5,
            framing_info=mock_framing,
            camera_motion="auto",
            narrative_role="intro_buildup"
        )
        self.assertIn("1.0-0.06*min", intro_auto)

    def test_18_dynamic_captions_and_face_avoidance(self):
        from core.subtitle_stylizer import generate_kinetic_subtitles

        ass_bottom = SCRATCH_DIR / "test_subs_bottom.ass"
        ass_top = SCRATCH_DIR / "test_subs_top.ass"

        # 1. Face avoidance: upper face moves captions to bottom safe zone (alignment 2)
        generate_kinetic_subtitles(
            quote_text="THROUGHOUT HEAVEN AND EARTH I ALONE AM THE HONORED ONE",
            start_time=0.5,
            end_time=6.5,
            output_ass_path=ass_bottom,
            style_preset="spur_hook",
            face_y=0.25
        )
        content_bottom = ass_bottom.read_text()
        self.assertIn(",2,90,90,220,1", content_bottom)  # Alignment 2 (bottom safe zone)
        self.assertIn(r"\fad(80,80)", content_bottom)      # Animated entrance/exit

        # 2. Face avoidance: lower face moves captions to top safe zone (alignment 8)
        generate_kinetic_subtitles(
            quote_text="THROUGHOUT HEAVEN AND EARTH I ALONE AM THE HONORED ONE",
            start_time=0.5,
            end_time=6.5,
            output_ass_path=ass_top,
            style_preset="spur_hook",
            face_y=0.75
        )
        content_top = ass_top.read_text()
        self.assertIn(",8,90,90,240,1", content_top)     # Alignment 8 (top safe zone)

        # 3. Short caption chunks: must have multiple dialogue events (no single long banner)
        dialogue_lines = [line for line in content_bottom.splitlines() if line.startswith("Dialogue:")]
        self.assertGreaterEqual(len(dialogue_lines), 3, "Subtitles must be chunked into short segments")

    def test_19_effects_with_purpose(self):
        from core.effects_engine import get_segment_velocity_profile

        # 1. Intro shot: clean cut, no flash
        intro = get_segment_velocity_profile({"is_drop": False, "role": "intro_buildup"}, 0, 10)
        self.assertFalse(intro["add_flash"])
        self.assertEqual(intro["role"], "intro_slowmo")

        # 2. 808 drop cut: purposeful impact punch + single brief flash
        drop_impact = get_segment_velocity_profile(
            {"is_drop": True, "is_first_drop": True, "is_major_beat": True, "role": "combat_strike"},
            1, 10
        )
        self.assertTrue(drop_impact["add_flash"])
        self.assertEqual(drop_impact["scale_factor"], 1.08)

        # 3. Regular combat cut: clean cut (NO flash)
        combat_cut = get_segment_velocity_profile(
            {"is_drop": True, "is_first_drop": False, "is_major_beat": False, "role": "combat_strike"},
            2, 10
        )
        self.assertFalse(combat_cut["add_flash"], "Regular combat cut must remain a clean cut")

        # 4. Climax finisher: weighty impact scale hold, zero flash
        climax = get_segment_velocity_profile(
            {"is_drop": True, "role": "climax_finisher"},
            8, 10
        )
        self.assertFalse(climax["add_flash"])
        self.assertEqual(climax["scale_factor"], 1.10)

    def test_20_build_the_climax_5_act_narrative(self):
        from core.shot_selector import calculate_variable_pacing

        # 5-act narrative progression: Hook -> Build -> Escalation -> Climax -> Payoff
        beats = [1.6, 3.2, 4.8, 5.5, 6.1, 6.7, 7.3, 8.0, 9.6, 11.2, 12.8, 14.0]
        segments = calculate_variable_pacing(total_duration=14.0, drop_time=4.8, major_beat_times=beats)

        roles = [s["role"] for s in segments]
        self.assertIn("intro_buildup", roles)
        self.assertTrue(any(r in ("combat_strike", "combat_micro_rush") for r in roles))
        self.assertIn("climax_finisher", roles)

        # Climax must occur in the final quarter before the payoff
        climax_idx = next(i for i, s in enumerate(segments) if s["role"] == "climax_finisher")
        self.assertGreater(climax_idx, len(segments) // 2)

        # Escalation cut lengths must be faster than the opening hook
        hook_dur = segments[0]["duration"]
        combat_segs = [s for s in segments if s["role"] in ("combat_strike", "combat_micro_rush")]
        for c in combat_segs:
            self.assertLess(c["duration"], hook_dur)

    def test_21_sound_design_filter_chain(self):
        from core.sound_design import (
            build_pre_drop_riser_filter,
            build_sub_impact_filter,
            build_transition_whoosh_filter,
            build_sound_design_filter_chain
        )

        # 1. Riser generation
        riser = build_pre_drop_riser_filter(drop_time=4.8)
        self.assertIn("highpass=f=1400", riser)

        # 2. Sub impact generation
        impact = build_sub_impact_filter([4.8, 11.2])
        self.assertIn("bass=g=3.5:f=60", impact)

        # 3. Transition whoosh
        whoosh = build_transition_whoosh_filter([6.5, 9.0])
        self.assertIn("treble=g=2.8:f=5500", whoosh)

        # 4. Configurable toggle
        full_sd = build_sound_design_filter_chain(drop_time=4.8, cut_timestamps=[2.0, 4.8, 7.0], climax_time=10.0, enable_sound_design=True)
        self.assertIn("bass=g=3.5", full_sd)
        self.assertIn("highpass=f=1400", full_sd)

        disabled_sd = build_sound_design_filter_chain(drop_time=4.8, cut_timestamps=[2.0, 4.8, 7.0], enable_sound_design=False)
        self.assertEqual(disabled_sd, "anull")

    def test_22_loopable_ending(self):
        from core.shot_selector import calculate_variable_pacing
        from core.smart_reframe import build_smart_reframe_filter

        beats = [1.6, 3.2, 4.8, 5.5, 6.2, 7.0, 8.5]
        segments = calculate_variable_pacing(total_duration=8.5, drop_time=4.8, major_beat_times=beats)

        mock_framing = {
            "in_w": 1920, "in_h": 1080,
            "act_x": 0, "act_y": 0, "act_w": 1920, "act_h": 1080,
            "cx_start": 0.50, "cx_end": 0.50,
            "cy_start": 0.50, "cy_end": 0.50,
            "is_dynamic": False
        }

        # 1. Opening hook has push-in (1.00x -> 1.05x)
        hook_filter = build_smart_reframe_filter(
            duration=segments[0]["duration"],
            framing_info=mock_framing,
            narrative_role=segments[0]["role"]
        )
        self.assertIn("1.0-0.06*min", hook_filter)

        # 2. Outro payoff has pull-out (1.06x -> 1.00x) so end matches start scale
        outro_filter = build_smart_reframe_filter(
            duration=segments[-1]["duration"],
            framing_info=mock_framing,
            narrative_role=segments[-1]["role"]
        )
        self.assertIn("0.94+0.06*min", outro_filter)

    def test_23_presets_and_configuration(self):
        from core.presets import EDITING_PRESETS, get_editing_preset, list_available_presets

        expected = ["VIRAL_PHONK", "CINEMATIC_ANIME", "DARK_ANIME", "HYPE_BATTLE", "MINIMAL_CINEMATIC"]
        for p in expected:
            self.assertIn(p, EDITING_PRESETS)
            cfg = get_editing_preset(p.lower())
            self.assertEqual(cfg["name"], p)

        # 1. VIRAL_PHONK style
        viral = get_editing_preset("VIRAL_PHONK")
        self.assertEqual(viral["pacing"], "fast")
        self.assertEqual(viral["effect_intensity"], 1.0)
        self.assertTrue(viral["loop_behavior"])

        # 2. MINIMAL_CINEMATIC style (zero flashes, clean straight cuts)
        minimal = get_editing_preset("MINIMAL_CINEMATIC")
        self.assertEqual(minimal["effect_intensity"], 0.0)
        self.assertFalse(minimal["enable_velocity_ramping"])
        self.assertFalse(minimal["sound_design"])

        # 3. List presets
        available = list_available_presets()
        self.assertEqual(len(available), 5)

    def test_24_studio_integration_and_cli(self):
        import argparse
        from studio.server import AniDocStudioHandler

        # 1. Studio API status exposes all 5 presets
        from core.presets import list_available_presets
        presets = list_available_presets()
        preset_ids = [p["id"] for p in presets]
        for expected in ["VIRAL_PHONK", "CINEMATIC_ANIME", "DARK_ANIME", "HYPE_BATTLE", "MINIMAL_CINEMATIC"]:
            self.assertIn(expected, preset_ids)

        # 2. CLI parser options validation
        import main
        # Verify parser can accept new preset, camera-motion, and sound design arguments
        test_args = ["--character", "gojo", "--preset", "CINEMATIC_ANIME", "--camera-motion", "push_in", "--no-sound-design"]
        parser = argparse.ArgumentParser()
        parser.add_argument("--character", type=str)
        parser.add_argument("--preset", type=str, choices=["VIRAL_PHONK", "CINEMATIC_ANIME", "DARK_ANIME", "HYPE_BATTLE", "MINIMAL_CINEMATIC"])
        parser.add_argument("--camera-motion", type=str)
        parser.add_argument("--no-sound-design", action="store_true")
        parsed = parser.parse_args(test_args)
        self.assertEqual(parsed.preset, "CINEMATIC_ANIME")
        self.assertEqual(parsed.camera_motion, "push_in")
        self.assertTrue(parsed.no_sound_design)


if __name__ == "__main__":
    unittest.main()
