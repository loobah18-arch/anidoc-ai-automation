"""
Comprehensive Test Suite for AniDoc 4K Phonk & Scene Edit Automation Engine.
"""
import unittest
import subprocess
from pathlib import Path

from config.settings import SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, CC_PRESETS
from core.beat_detector import generate_procedural_beat_grid, analyze_audio_beats
from core.effects_engine import build_cc_filter, build_beat_flash_filters, build_velocity_zoom_filter
from core.clip_manager import generate_procedural_cinematic_scene, get_character_scene_clips, CHARACTER_THEMES
from core.subtitle_stylizer import generate_kinetic_subtitles
from core.quote_ai import generate_edit_metadata
from core.video_assembler import render_cinematic_edit, generate_fallback_phonk_audio

class TestAniDocPipeline(unittest.TestCase):
    def setUp(self):
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    def test_01_beat_grid_generation(self):
        grid = generate_procedural_beat_grid(duration=20.0, drop_time=6.0, bpm=130.0)
        self.assertEqual(grid.duration, 20.0)
        self.assertEqual(grid.drop_time, 6.0)
        self.assertTrue(len(grid.beat_times) >= 10)
        segments = grid.get_cut_segments()
        self.assertTrue(len(segments) >= 10)
        self.assertTrue(any(s["is_drop"] for s in segments))

    def test_02_effects_filter_builders(self):
        marvel_cc = build_cc_filter("marvel_hdr")
        self.assertIn("eq=contrast=", marvel_cc)
        self.assertIn("unsharp=", marvel_cc)
        self.assertIn("vignette=", marvel_cc)

        jjk_cc = build_cc_filter("jjk_void")
        self.assertIn("eq=contrast=", jjk_cc)

        flashes = build_beat_flash_filters([6.0, 7.5, 9.0])
        self.assertEqual(len(flashes), 3)
        self.assertIn("drawbox=", flashes[0])

        zoom = build_velocity_zoom_filter(is_drop=True, seg_idx=0)
        self.assertIn("scale=", zoom)

    def test_03_quote_ai_metadata(self):
        spidey = generate_edit_metadata("spiderman")
        self.assertEqual(spidey["universe"], "marvel")
        self.assertTrue(len(spidey["quote"]) > 5)
        self.assertTrue(len(spidey["title"]) > 10)
        self.assertTrue(len(spidey["tags"]) >= 4)

        gojo = generate_edit_metadata("gojo")
        self.assertEqual(gojo["universe"], "jjk")
        self.assertTrue(len(gojo["quote"]) > 5)

    def test_04_kinetic_subtitle_generation(self):
        ass_out = SCRATCH_DIR / "test_subs.ass"
        generate_kinetic_subtitles(
            quote_text="I alone am the honored one.",
            start_time=1.0,
            end_time=5.0,
            output_ass_path=ass_out,
            character_name="GOJO"
        )
        self.assertTrue(ass_out.exists())
        with open(ass_out, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("[Script Info]", content)
            self.assertIn("HONORED", content)

    def test_05_procedural_scene_rendering(self):
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
        self.assertIn("1080,1920", res.stdout)

    def test_06_end_to_end_video_assembly(self):
        out_video = SCRATCH_DIR / "test_assembled_edit.mp4"
        res = render_cinematic_edit(
            character_key="spiderman",
            output_path=out_video,
            target_duration=4.5
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(out_video.exists())
        self.assertTrue(out_video.stat().st_size > 50000)

        # Verify 9:16 aspect ratio & duration
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height,codec_name",
            "-of", "csv=p=0",
            str(out_video)
        ]
        probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        self.assertIn("1080,1920", probe_res.stdout)

if __name__ == "__main__":
    unittest.main()
