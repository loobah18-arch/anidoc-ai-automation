#!/usr/bin/env python3
"""
AMV Pipeline Test Suite v2 — validates gdrive_amv_builder.py v2 and core deps.
All tests use the new v2 API signatures.
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
    build_clip_vfx, get_beat_timeline, get_velocity,
    _camera_shake, _glitch, _zoom_punch, _flash_and_dip,
    _pre_drop_flicker, _motion_blur, _letterbox, _scale_pad,
)
from core.effects_engine import build_cc_filter
from core.clip_manager import CHARACTER_THEMES
from core.phonk_manager import list_available_phonk_tracks, get_random_or_specified_phonk


# ── Helper: build a segment dict (v2 API) ────────────────────────────────────
def seg(role, is_peak=False, is_drop=None, duration=1.0):
    if is_drop is None:
        is_drop = role in ("drop1", "drop2")
    return {"role": role, "is_drop": is_drop, "is_peak": is_peak, "duration": duration}


class TestStyleRotation(unittest.TestCase):
    """VFX style rotation must advance and never repeat until full cycle."""

    def setUp(self):
        self._real = _load_style_state()
        _save_style_state({"run_count": 0})

    def tearDown(self):
        _save_style_state(self._real)

    def test_style_pool_has_6_entries(self):
        self.assertEqual(len(STYLE_POOL), 6)

    def test_each_style_has_required_keys(self):
        required = {
            "name", "description", "velocity", "zoom_punch", "color_flash",
            "letterbox", "beat_cuts", "slow_mo_peaks", "glitch",
            "flash_frames", "motion_blur",
        }
        for s in STYLE_POOL:
            self.assertTrue(required.issubset(s.keys()),
                            f"Style '{s['name']}' missing keys: {required - s.keys()}")

    def test_rotation_advances_each_run(self):
        seen = [pick_style()["name"] for _ in range(6)]
        self.assertEqual(len(set(seen)), 6, f"Rotation repeated: {seen}")

    def test_rotation_wraps_around(self):
        for _ in range(6): pick_style()
        seventh = pick_style()
        self.assertEqual(seventh["name"], STYLE_POOL[0]["name"])

    def test_state_file_in_config_not_scratch(self):
        self.assertIn("config", str(STYLE_STATE_FILE))
        self.assertNotIn("scratch", str(STYLE_STATE_FILE))


class TestVelocityCurves(unittest.TestCase):
    """Velocity must match professional AMV reference values."""

    def _spd(self, role, style_name, is_peak=False):
        style = next(s for s in STYLE_POOL if s["name"] == style_name)
        return get_velocity(seg(role, is_peak=is_peak), style)

    def test_velocity_rush_intro_is_030(self):
        self.assertAlmostEqual(self._spd("intro", "Velocity Rush"), 0.30, places=2)

    def test_velocity_rush_drop1_is_150(self):
        self.assertAlmostEqual(self._spd("drop1", "Velocity Rush"), 1.50, places=2)

    def test_velocity_rush_drop2_is_180(self):
        self.assertAlmostEqual(self._spd("drop2", "Velocity Rush"), 1.80, places=2)

    def test_peak_slow_mo_is_045(self):
        self.assertAlmostEqual(self._spd("drop1", "Velocity Rush", is_peak=True), 0.45, places=2)

    def test_slow_cinema_no_speed_change(self):
        # Slow Cinema has velocity=False and slow_mo_peaks=True
        # non-peak segments should stay at or near 1.0 (it can do slow-mo on peaks)
        speed = self._spd("drop1", "Slow Cinema", is_peak=False)
        self.assertLessEqual(speed, 1.2, "Slow Cinema non-peak should not speed up significantly")


class TestVFXFiltergraph(unittest.TestCase):
    """Each filter builder must produce a valid non-empty string."""

    def test_glitch_uses_rgbashift(self):
        self.assertIn("rgbashift", _glitch())

    def test_camera_shake_uses_geq(self):
        shake = _camera_shake()
        self.assertIn("geq", shake)
        self.assertIn("14", shake)   # ±14px displacement

    def test_zoom_punch_uses_zoompan(self):
        zp = _zoom_punch(1.09)
        self.assertIn("zoompan", zp)
        self.assertIn("1.090", zp)

    def test_flash_and_dip_has_white_and_black(self):
        f = _flash_and_dip(0.0, 0.06, 0.04)
        self.assertIn("white", f)
        self.assertIn("black", f)

    def test_pre_drop_flicker_has_sin(self):
        f = _pre_drop_flicker(2.5)
        self.assertIn("sin", f)
        self.assertIn("brightness", f)

    def test_motion_blur_only_on_fast(self):
        self.assertEqual(_motion_blur(1.0), "")
        self.assertEqual(_motion_blur(1.19), "")
        self.assertIn("tblend", _motion_blur(1.5))

    def test_letterbox_has_top_and_bottom_bars(self):
        lb = _letterbox(80)
        self.assertEqual(lb.count("drawbox"), 2)
        self.assertIn("y=0", lb)

    def test_scale_pad_ends_with_black(self):
        self.assertTrue(_scale_pad().endswith("black"))


class TestBuildClipVFX(unittest.TestCase):
    """build_clip_vfx (v2 API) must return correct chains per role."""

    def _vfx(self, style_name, role, is_peak=False, duration=0.3, next_role=""):
        style = next(s for s in STYLE_POOL if s["name"] == style_name)
        s = seg(role, is_peak=is_peak, duration=duration)
        vf, af, speed = build_clip_vfx(style, s, "#3b82f6", next_role=next_role)
        return vf, af, speed

    def test_intro_has_setpts_slow(self):
        vf, _, speed = self._vfx("Velocity Rush", "intro", duration=2.5)
        self.assertIn("setpts", vf)
        self.assertAlmostEqual(speed, 0.30, places=2)

    def test_drop1_has_camera_shake(self):
        vf, _, _ = self._vfx("Velocity Rush", "drop1", duration=0.3)
        self.assertIn("geq", vf)

    def test_drop2_faster_than_drop1(self):
        _, _, spd1 = self._vfx("Velocity Rush", "drop1", duration=0.25)
        _, _, spd2 = self._vfx("Velocity Rush", "drop2", duration=0.18)
        self.assertGreater(spd2, spd1)

    def test_peak_is_slow_mo(self):
        _, _, speed = self._vfx("Velocity Rush", "drop1", is_peak=True, duration=0.3)
        self.assertAlmostEqual(speed, 0.45, places=2)

    def test_breakdown_before_drop_has_flicker(self):
        vf, _, _ = self._vfx("Velocity Rush", "breakdown", duration=1.5, next_role="drop1")
        self.assertIn("sin", vf)

    def test_glitch_storm_has_rgbashift_on_drop(self):
        vf, _, _ = self._vfx("Glitch Storm", "drop1", duration=0.3)
        self.assertIn("rgbashift", vf)

    def test_slow_cinema_no_zoom_punch(self):
        vf, _, _ = self._vfx("Slow Cinema", "drop1", duration=0.5)
        self.assertNotIn("zoompan", vf)

    def test_scale_pad_always_last(self):
        for style in STYLE_POOL:
            for role in ("intro", "drop1", "drop2", "outro"):
                vf, _, _ = self._vfx(style["name"], role, duration=0.3)
                self.assertTrue(
                    vf.endswith("black"),
                    f"Style '{style['name']}' role '{role}': scale pad must be last — got ...{vf[-40:]}"
                )

    def test_audio_tempo_chained_for_extreme_speeds(self):
        # drop2 at 1.8x — should use atempo=1.800, not chain (within 0.5-2.0 range)
        _, af, _ = self._vfx("Velocity Rush", "drop2", duration=0.18)
        self.assertIn("atempo", af)


class TestFallbackTimeline(unittest.TestCase):
    """Fallback timeline must cover the full duration with correct roles."""

    def test_fallback_covers_full_duration(self):
        from scripts.gdrive_amv_builder import _fallback_timeline
        segs = _fallback_timeline(75.0)
        total = sum(s["duration"] for s in segs)
        self.assertGreater(total, 70.0, "Fallback must cover at least 70s of 75s target")

    def test_fallback_has_all_roles(self):
        from scripts.gdrive_amv_builder import _fallback_timeline
        segs = _fallback_timeline(75.0)
        roles = {s["role"] for s in segs}
        for expected in ("intro", "drop1", "breakdown", "drop2", "outro"):
            self.assertIn(expected, roles, f"Fallback missing '{expected}' role")

    def test_fallback_drop_clips_are_short(self):
        from scripts.gdrive_amv_builder import _fallback_timeline
        segs = _fallback_timeline(75.0)
        drops = [s for s in segs if s["role"] == "drop2"]
        for d in drops:
            self.assertLessEqual(d["duration"], 0.35, f"drop2 clip too long: {d['duration']}")


class TestColorGrades(unittest.TestCase):
    """CC presets must produce non-empty filter strings."""

    def test_all_cc_presets_produce_filters(self):
        for preset in CC_PRESETS:
            self.assertGreater(len(build_cc_filter(preset)), 0,
                               f"CC preset '{preset}' returned empty filter")

    def test_jjk_and_marvel_presets_exist(self):
        self.assertIn("jjk_void", CC_PRESETS)
        self.assertIn("marvel_hdr", CC_PRESETS)


class TestCharacterThemes(unittest.TestCase):
    """Character themes must be complete and universe-separated."""

    def test_no_cross_universe_characters(self):
        jjk = {k for k, v in CHARACTER_THEMES.items() if v.get("universe") == "jjk"}
        marvel = {k for k, v in CHARACTER_THEMES.items() if v.get("universe") == "marvel"}
        self.assertEqual(jjk & marvel, set())

    def test_all_themes_have_cc_preset(self):
        for name, theme in CHARACTER_THEMES.items():
            self.assertIn("cc_preset", theme, f"'{name}' missing cc_preset")
            self.assertIn(theme["cc_preset"], CC_PRESETS,
                          f"'{name}' has unknown cc_preset '{theme['cc_preset']}'")

    def test_all_themes_have_colors(self):
        for name, theme in CHARACTER_THEMES.items():
            self.assertGreater(len(theme.get("colors", [])), 0, f"'{name}' has no colors")


class TestPhonkLibrary(unittest.TestCase):
    """Phonk library must be accessible."""

    def test_phonk_tracks_exist(self):
        tracks = list_available_phonk_tracks()
        self.assertGreater(len(tracks), 0, "No phonk tracks in assets/audio/phonk/")

    def test_get_random_phonk_returns_valid_path(self):
        path = get_random_or_specified_phonk(None)
        if path:
            self.assertTrue(Path(str(path)).exists())


class TestSourceFolderConfig(unittest.TestCase):
    def test_source_folder_id_correct(self):
        self.assertEqual(SOURCE_FOLDER_ID, "1e5_IF3GRHNr315hP5zK_qlyfsKXm3Ox4")

    def test_output_dir_creatable(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.assertTrue(OUTPUT_DIR.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
