#!/usr/bin/env python3
"""
AMV Pipeline Test Suite — validates gdrive_amv_builder.py and its core dependencies.
Replaces the old classic-mode test suite which tested code no longer in use.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import (
    SCRATCH_DIR, OUTPUT_DIR, PHONK_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, FPS, CC_PRESETS
)
from scripts.gdrive_amv_builder import (
    STYLE_POOL, STYLE_STATE_FILE, SOURCE_FOLDER_ID,
    pick_style, _load_style_state, _save_style_state,
    build_clip_vfx, get_cut_durations,
)
from core.effects_engine import build_cc_filter
from core.clip_manager import CHARACTER_THEMES
from core.phonk_manager import list_available_phonk_tracks, get_random_or_specified_phonk


class TestStyleRotation(unittest.TestCase):
    """VFX style rotation must advance across runs and never repeat until the full cycle is done."""

    def setUp(self):
        # Save real state, reset to known value for test
        self._real_state = _load_style_state()
        _save_style_state({"run_count": 0})

    def tearDown(self):
        _save_style_state(self._real_state)

    def test_style_pool_has_6_entries(self):
        self.assertEqual(len(STYLE_POOL), 6)

    def test_each_style_has_required_keys(self):
        required = {"name", "description", "velocity", "zoom_punch", "color_flash",
                    "letterbox", "beat_cuts", "slow_mo_peaks", "glitch"}
        for s in STYLE_POOL:
            self.assertTrue(required.issubset(s.keys()), f"Style missing keys: {s['name']}")

    def test_rotation_advances_each_run(self):
        styles_seen = [pick_style()["name"] for _ in range(6)]
        # All 6 unique names should appear
        self.assertEqual(len(set(styles_seen)), 6, f"Rotation repeated: {styles_seen}")

    def test_rotation_wraps_around(self):
        # Run 7 picks = wraps back to style 0
        for _ in range(6):
            pick_style()
        seventh = pick_style()
        self.assertEqual(seventh["name"], STYLE_POOL[0]["name"])

    def test_state_file_is_in_config_not_scratch(self):
        """State must be in config/ (tracked by git) not scratch/ (gitignored = resets on CI)."""
        self.assertIn("config", str(STYLE_STATE_FILE),
                      "STYLE_STATE_FILE must be inside config/ to persist across CI runs")
        self.assertNotIn("scratch", str(STYLE_STATE_FILE))


class TestVFXFiltergraph(unittest.TestCase):
    """VFX filtergraph builder must produce valid non-empty FFmpeg filter strings."""

    def _dummy_theme(self):
        return {"colors": ["#D200FF"], "name": "Test Char"}

    def test_velocity_rush_intro_has_setpts(self):
        style = STYLE_POOL[0]  # Velocity Rush
        vf, af, pts = build_clip_vfx(style, 0, 10, "#D200FF", False)
        self.assertIn("setpts", vf, "Intro clip must have setpts for velocity")
        self.assertGreater(pts, 1.0)  # intro is slowed, pts > 1

    def test_glitch_storm_has_mix_filter(self):
        style = next(s for s in STYLE_POOL if s["name"] == "Glitch Storm")
        vf, af, pts = build_clip_vfx(style, 3, 10, "#FF0000", False)
        self.assertIn("mix", vf, "Glitch Storm must include RGB mix filter")

    def test_zoom_punch_on_peak(self):
        style = next(s for s in STYLE_POOL if s["name"] == "Zoom Punch")
        vf, af, pts = build_clip_vfx(style, 3, 10, "#00FF00", True)
        self.assertIn("zoompan", vf, "Zoom Punch must include zoompan on peak clips")

    def test_scale_pad_always_last(self):
        for style in STYLE_POOL:
            vf, _, _ = build_clip_vfx(style, 2, 10, "#ffffff", False)
            self.assertTrue(vf.endswith(f"{VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black"),
                            f"Scale/pad must be last in chain for style '{style['name']}'")

    def test_slow_cinema_no_speed_ramp(self):
        style = next(s for s in STYLE_POOL if s["name"] == "Slow Cinema")
        vf, af, pts = build_clip_vfx(style, 3, 10, "#ffffff", False)
        # Slow Cinema has no velocity, non-peak non-intro/outro should not speed up
        self.assertNotIn("atempo=1.25", af)

    def test_letterbox_on_intro_outro(self):
        style = next(s for s in STYLE_POOL if s["name"] == "Cinematic Flash")
        vf_intro, _, _ = build_clip_vfx(style, 0, 10, "#ffffff", False)
        vf_outro, _, _ = build_clip_vfx(style, 9, 10, "#ffffff", False)
        self.assertIn("drawbox", vf_intro)
        self.assertIn("drawbox", vf_outro)


class TestColorGrades(unittest.TestCase):
    """CC presets must exist and produce non-empty FFmpeg filter strings."""

    def test_all_cc_presets_produce_filters(self):
        for preset_name in CC_PRESETS:
            result = build_cc_filter(preset_name)
            self.assertTrue(len(result) > 0, f"CC preset '{preset_name}' returned empty filter")

    def test_jjk_and_marvel_presets_exist(self):
        self.assertIn("jjk_void", CC_PRESETS)
        self.assertIn("marvel_hdr", CC_PRESETS)


class TestCharacterThemes(unittest.TestCase):
    """Character themes must be complete and universe-separated."""

    def test_no_jjk_characters_in_marvel(self):
        jjk_chars = {k for k, v in CHARACTER_THEMES.items() if v.get("universe") == "jjk"}
        marvel_chars = {k for k, v in CHARACTER_THEMES.items() if v.get("universe") == "marvel"}
        self.assertEqual(jjk_chars & marvel_chars, set(), "Characters must not appear in both universes")

    def test_all_themes_have_cc_preset(self):
        for name, theme in CHARACTER_THEMES.items():
            self.assertIn("cc_preset", theme, f"Character '{name}' missing cc_preset")
            self.assertIn(theme["cc_preset"], CC_PRESETS,
                          f"Character '{name}' has unknown cc_preset '{theme['cc_preset']}'")

    def test_all_themes_have_colors(self):
        for name, theme in CHARACTER_THEMES.items():
            self.assertIn("colors", theme)
            self.assertGreater(len(theme["colors"]), 0, f"'{name}' has no colors")


class TestPhonkLibrary(unittest.TestCase):
    """Phonk audio library must be populated and accessible."""

    def test_phonk_tracks_exist(self):
        tracks = list_available_phonk_tracks()
        self.assertGreater(len(tracks), 0, "No phonk tracks found in assets/audio/phonk/")

    def test_get_random_phonk_returns_path(self):
        path = get_random_or_specified_phonk(None)
        if path:  # may be None if no tracks on fresh checkout
            self.assertTrue(Path(str(path)).exists(), f"Phonk path does not exist: {path}")


class TestSourceFolderConfig(unittest.TestCase):
    """Source folder ID must match the user's raw footage Drive folder."""

    def test_source_folder_id_is_set(self):
        self.assertEqual(SOURCE_FOLDER_ID, "1e5_IF3GRHNr315hP5zK_qlyfsKXm3Ox4",
                         "SOURCE_FOLDER_ID must point to the raw footage Drive folder")

    def test_output_dir_exists_or_creatable(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.assertTrue(OUTPUT_DIR.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
