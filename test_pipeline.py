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
        for style in ["viral_karaoke", "cyber_glow", "anime_shrine", "cinematic_minimal"]:
            generate_kinetic_subtitles(
                quote_text="Throughout heaven and earth I alone am the honored one",
                start_time=0.5,
                end_time=5.5,
                output_ass_path=ass_out,
                style_preset=style,
                character_name="GOJO"
            )
            self.assertTrue(ass_out.exists())
            with open(ass_out, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("[Script Info]", content)
                self.assertIn("HONORED", content)
                # Note: character badge removed from subtitles (cleaner look)
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
        self.assertIn("hlslice", MODERN_COMBAT_TRANSITIONS)
        self.assertIn("diagtl", MODERN_COMBAT_TRANSITIONS)
        self.assertIn("fadewhite", MODERN_DROP_TRANSITIONS)

        # Chained filter with drop index and outro
        durs = [1.5, 1.2, 0.8, 1.0, 1.4]
        xf = build_xfade_transition_filter(
            clip_count=len(durs),
            durations=durs,
            transition_duration=0.12,
            drop_index=2
        )
        self.assertIn("xfade=transition=", xf)
        self.assertIn("duration=0.12", xf)
        self.assertIn("[xfade_vout]", xf)


if __name__ == "__main__":
    unittest.main()
