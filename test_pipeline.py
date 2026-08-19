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
from core.beatsync_analyzer import analyze_audio_beatsync
from core.stem_separator import get_best_beat_source
from core.deadframe_detector import measure_clip_motion, filter_action_packed_clips
from core.storyline_planner import StorylinePlanner

class TestAniDocPipeline(unittest.TestCase):
    def setUp(self):
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    def test_01_phonk_library_manager(self):
        tracks = list_available_phonk_tracks()
        self.assertTrue(len(tracks) >= 2, "Should have at least 2 phonk tracks downloaded in library")
        self.assertTrue(len(POPULAR_PHONK_CATALOG) >= 5)
        
        # Test retrieval
        phonk_audio = get_random_or_specified_phonk("tokyo_drift_phonk")
        self.assertIsNotNone(phonk_audio)
        self.assertTrue(Path(phonk_audio).exists())

    def test_02_beat_grid_generation(self):
        grid = generate_procedural_beat_grid(duration=20.0, drop_time=6.0, bpm=130.0)
        self.assertEqual(grid.duration, 20.0)
        self.assertEqual(grid.drop_time, 6.0)
        self.assertTrue(len(grid.beat_times) >= 10)
        segments = grid.get_cut_segments()
        self.assertTrue(len(segments) >= 10)
        self.assertTrue(any(s["is_drop"] for s in segments))

    def test_03_effects_filter_builders(self):
        marvel_cc = build_cc_filter("marvel_hdr")
        self.assertIn("eq=contrast=", marvel_cc)
        self.assertIn("unsharp=", marvel_cc)
        self.assertIn("vignette=", marvel_cc)

        jjk_cc = build_cc_filter("jjk_void")
        self.assertIn("eq=contrast=", jjk_cc)

        flashes = build_beat_flash_filters([6.0, 7.5, 9.0])
        self.assertEqual(len(flashes), 6)
        self.assertIn("drawbox=", flashes[0])

        vel = get_segment_velocity_profile({"is_drop": True, "duration": 1.2}, 0, 10)
        self.assertEqual(vel["role"], "power_slowmo")
        self.assertAlmostEqual(vel["speed"], 0.45)

        vf = build_velocity_clip_filter(0, 1.2, speed=vel["speed"], scale_factor=vel["scale_factor"])
        self.assertIn("setpts=", vf)
        self.assertIn("trim=duration=1.200", vf)

    def test_04_quote_ai_metadata(self):
        spidey = generate_edit_metadata("spiderman")
        self.assertEqual(spidey["universe"], "marvel")
        self.assertTrue(len(spidey["quote"]) > 5)
        self.assertTrue(len(spidey["title"]) > 10)
        self.assertTrue(len(spidey["tags"]) >= 4)

        gojo = generate_edit_metadata("gojo")
        self.assertEqual(gojo["universe"], "jjk")
        self.assertTrue(len(gojo["quote"]) > 5)

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

    def test_08_beatsync_engine_hpss(self):
        phonk_audio = get_random_or_specified_phonk("tokyo_drift_phonk")
        self.assertIsNotNone(phonk_audio)
        bs_res = analyze_audio_beatsync(phonk_audio, target_duration=8.0)
        self.assertTrue(len(bs_res.beat_times) >= 4)
        self.assertTrue(bs_res.tempo > 50.0)
        self.assertTrue(len(bs_res.sections) >= 1)
        segs = bs_res.get_cut_segments()
        self.assertTrue(len(segs) >= 2)
        self.assertIn("energy", segs[0])
        self.assertIn("kick", segs[0])

    def test_09_ultimate_amv_stem_and_deadframe(self):
        phonk_audio = get_random_or_specified_phonk("tokyo_drift_phonk")
        self.assertIsNotNone(phonk_audio)
        beat_src = get_best_beat_source(phonk_audio, SCRATCH_DIR)
        self.assertTrue(Path(beat_src).exists())

        # Test deadframe & motion measurement on procedural clip
        test_clip = SCRATCH_DIR / "test_proc_scene.mp4"
        if test_clip.exists():
            motion_res = measure_clip_motion(test_clip, max_duration=2.0)
            self.assertIn("action_score", motion_res)
            self.assertIn("deadframe_ratio", motion_res)
            filtered = filter_action_packed_clips([test_clip])
            self.assertTrue(len(filtered) >= 1)

    def test_10_openstoryline_arc_planner(self):
        planner = StorylinePlanner(drop_time=6.0, total_duration=20.0)
        self.assertEqual(len(planner.phases), 4)
        phase_names = [p.name for p in planner.phases]
        self.assertEqual(phase_names, ["HOOK", "BUILD", "DROP", "OUTRO"])

        # Test segment planning from simulated segments
        sim_segs = [
            {"start": 0.0, "end": 1.0, "duration": 1.0, "is_drop": False, "energy": 0.3, "kick": 0.2},
            {"start": 1.0, "end": 6.0, "duration": 5.0, "is_drop": False, "energy": 0.6, "kick": 0.5},
            {"start": 6.0, "end": 7.0, "duration": 1.0, "is_drop": True, "prev_is_drop": False, "energy": 0.95, "kick": 0.9},
            {"start": 7.0, "end": 18.0, "duration": 11.0, "is_drop": True, "prev_is_drop": True, "energy": 0.85, "kick": 0.8},
            {"start": 18.0, "end": 20.0, "duration": 2.0, "is_drop": True, "prev_is_drop": True, "energy": 0.4, "kick": 0.3},
        ]
        planned = planner.plan_from_beatsync(sim_segs)
        self.assertEqual(len(planned), 5)
        self.assertEqual(planned[0].arc_phase, "HOOK")
        self.assertEqual(planned[0].add_rack_focus, True) # Hook rack-focus
        self.assertEqual(planned[2].arc_phase, "DROP")
        self.assertEqual(planned[2].add_shake, True)      # First drop shake
        self.assertEqual(planned[2].add_chr_aber, True)   # First drop chromatic aberration
        self.assertEqual(planned[2].add_flash, True)      # First drop flash
        self.assertEqual(planned[4].arc_phase, "OUTRO")
        self.assertEqual(planned[4].add_bloom, True)      # Outro resolve bloom

        # Dict conversion
        dicts = planner.to_segment_dicts(planned)
        self.assertEqual(len(dicts), 5)
        self.assertEqual(dicts[0]["arc_phase"], "HOOK")

if __name__ == "__main__":
    unittest.main()

