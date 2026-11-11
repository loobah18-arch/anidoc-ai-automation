#!/usr/bin/env python3
"""
Unit tests for CandleGate in anidoc-ai-automation (@Jazzcreatesclips).
"""

import unittest
from pathlib import Path
from publishers.candle_gate import (
    CandleGate,
    VIEW_THRESHOLD_PER_HOUR,
    MIN_UPLOAD_SPACING_HOURS,
)

ROOT_DIR = Path(__file__).resolve().parent


class TestAnidocCandleGate(unittest.TestCase):

    def setUp(self):
        self.state_file = ROOT_DIR / "test_candle_state.json"
        self.history_file = ROOT_DIR / "test_upload_history.json"
        self.gate = CandleGate(state_file=self.state_file, history_file=self.history_file)

    def tearDown(self):
        if self.state_file.exists():
            self.state_file.unlink()
        if self.history_file.exists():
            self.history_file.unlink()

    def test_layer0_spacing_blocked_under_24h(self):
        res = self.gate.evaluate_upload_spacing(elapsed_hours=10.0)
        self.assertFalse(res["can_upload"])
        self.assertEqual(res["decision"], "UPLOAD_BLOCKED_24H_SPACING")
        self.assertEqual(res["remaining_hours"], 14.0)

    def test_layer0_spacing_cleared_after_24h(self):
        res = self.gate.evaluate_upload_spacing(elapsed_hours=26.0)
        self.assertTrue(res["can_upload"])
        self.assertEqual(res["decision"], "SPACING_CLEARED")
        self.assertEqual(res["remaining_hours"], 0.0)

    def test_layer1_early_momentum_blocks_upload(self):
        res = self.gate.evaluate_early_momentum(total_views=3500, elapsed_hours=8.0)
        self.assertFalse(res["can_upload"])
        self.assertEqual(res["decision"], "UPLOAD_BLOCKED_EARLY_MOMENTUM")

    def test_layer1_low_views_cleared(self):
        res = self.gate.evaluate_early_momentum(total_views=800, elapsed_hours=9.0)
        self.assertTrue(res["can_upload"])
        self.assertEqual(res["decision"], "LAYER_1_CLEARED")

    def test_layer1_past_24h_window_cleared(self):
        res = self.gate.evaluate_early_momentum(total_views=2500, elapsed_hours=26.0)
        self.assertTrue(res["can_upload"])
        self.assertEqual(res["decision"], "LAYER_1_CLEARED")

    def test_layer2_viral_velocity_blocked(self):
        res = self.gate.evaluate_hourly_candles(hourly_views=[1000, 2800])
        self.assertFalse(res["can_upload"])
        self.assertEqual(res["decision"], "UPLOAD_BLOCKED_ACTIVE_PUSH")

    def test_layer2_sub_threshold_cleared(self):
        res = self.gate.evaluate_hourly_candles(hourly_views=[50])
        self.assertTrue(res["can_upload"])
        self.assertEqual(res["decision"], "UPLOAD_CLEARED")

    def test_layer0_inline_wait_for_jitter(self):
        # Video uploaded 23.8 hours ago (12 min from 24h) -> triggers inline wait to avoid 24h skip
        res = self.gate.evaluate_upload_spacing(elapsed_hours=23.8)
        self.assertFalse(res["can_upload"])
        self.assertTrue(res["requires_spacing_sleep"])
        self.assertEqual(res["decision"], "SPACING_WAIT_INLINE")
        self.assertGreater(res["spacing_sleep_seconds"], 0)

        # Video uploaded 12.0 hours ago (far from 24h) -> blocked normally without inline wait
        res2 = self.gate.evaluate_upload_spacing(elapsed_hours=12.0)
        self.assertFalse(res2["can_upload"])
        self.assertFalse(res2["requires_spacing_sleep"])
        self.assertEqual(res2["decision"], "UPLOAD_BLOCKED_24H_SPACING")

    def test_layer0_inline_wait_window_covers_runner_drift(self):
        # Real-world case (2026-11-10): cron drifted ~8.5h late; active video was
        # 22.5h old with 1.5h remaining -> must inline-wait, not discard the render.
        res = self.gate.evaluate_upload_spacing(elapsed_hours=22.5)
        self.assertFalse(res["can_upload"])
        self.assertTrue(res["requires_spacing_sleep"])
        self.assertEqual(res["decision"], "SPACING_WAIT_INLINE")
        self.assertGreater(res["spacing_sleep_seconds"], 0)

        # Exactly at the 4h inline-window boundary -> still an inline wait
        res_edge = self.gate.evaluate_upload_spacing(elapsed_hours=20.0)
        self.assertTrue(res_edge["requires_spacing_sleep"])

        # Remaining wait beyond the 4h inline window -> hard block without sleep
        res_far = self.gate.evaluate_upload_spacing(elapsed_hours=19.9)
        self.assertFalse(res_far["requires_spacing_sleep"])
        self.assertEqual(res_far["decision"], "UPLOAD_BLOCKED_24H_SPACING")


if __name__ == "__main__":
    unittest.main()
