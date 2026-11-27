import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import preflight_gate
import publish
from publishers.candle_gate import CandleGate
from publishers.youtube_publisher import check_youtube_video_status


class TestAutonomyFixes(unittest.TestCase):
    def test_strip_anime_names_removes_franchises_and_dangling_hashes(self):
        self.assertEqual(
            publish.strip_anime_names("Demon Slayer Kimetsu No Yaiba battle IQ is unreal 🔥 #shorts"),
            "battle IQ is unreal 🔥 #shorts",
        )
        self.assertEqual(
            publish.strip_anime_names("Check this out! #demonslayer #jujutsukaisen #animeedit"),
            "Check this out! #animeedit",
        )

    def test_check_youtube_video_status_waits_for_processing_and_catches_block(self):
        yt = MagicMock()
        # First poll: still processing; second poll: processing finishes and video is rejected
        yt.videos.return_value.list.return_value.execute.side_effect = [
            {
                "items": [{
                    "status": {"uploadStatus": "uploaded"},
                    "contentDetails": {},
                    "processingDetails": {"processingStatus": "processing"},
                }]
            },
            {
                "items": [{
                    "status": {"uploadStatus": "rejected", "rejectionReason": "copyright"},
                    "contentDetails": {},
                    "processingDetails": {"processingStatus": "failed", "processingFailureReason": "copyright"},
                }]
            },
        ]
        with patch("time.sleep"):
            blocked, reason, _ = check_youtube_video_status(yt, "vid123", timeout_sec=60.0, poll_interval_sec=0.0)
        self.assertTrue(blocked)
        self.assertEqual(reason, "copyright")

    def test_check_youtube_video_status_passes_only_after_succeeded(self):
        yt = MagicMock()
        yt.videos.return_value.list.return_value.execute.side_effect = [
            {
                "items": [{
                    "status": {"uploadStatus": "uploaded"},
                    "contentDetails": {},
                    "processingDetails": {"processingStatus": "processing"},
                }]
            },
            {
                "items": [{
                    "status": {"uploadStatus": "processed"},
                    "contentDetails": {},
                    "processingDetails": {"processingStatus": "succeeded"},
                }]
            },
        ]
        with patch("time.sleep"):
            blocked, reason, _ = check_youtube_video_status(yt, "vid123", timeout_sec=60.0, poll_interval_sec=0.0)
        self.assertFalse(blocked)
        self.assertIsNone(reason)

    def test_candle_gate_fallback_enforces_local_24h_spacing_on_api_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            hist_file = tmp_path / "history.json"
            state_file = tmp_path / "state.json"
            now = datetime.now(timezone.utc)
            hist_file.write_text(json.dumps([
                {
                    "video_id": "good123",
                    "title": "Previous Clean Short",
                    "timestamp": (now - timedelta(hours=10)).isoformat(),
                    "status": "uploaded",
                },
                {
                    "video_id": "blocked999",
                    "title": "Blocked Short",
                    "timestamp": (now - timedelta(hours=1)).isoformat(),
                    "status": "blocked",
                },
            ]), encoding="utf-8")

            gate = CandleGate(state_file=state_file, history_file=hist_file)
            yt = MagicMock()
            yt.videos.return_value.list.return_value.execute.side_effect = RuntimeError("API quota error")

            res = gate.evaluate_live_channel(yt)
            candle_eval = res.get("candle_evaluation", {})
            self.assertFalse(candle_eval.get("can_upload"))
            self.assertEqual(candle_eval.get("decision"), "UPLOAD_BLOCKED_24H_SPACING")
            self.assertIn("Local History Fallback", candle_eval.get("active_layer", ""))

    def test_preflight_gate_emits_remaining_seconds_and_due_at_on_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            hist_file = Path(tmp) / "history.json"
            now = datetime(2026, 11, 27, 4, 0, 0, tzinfo=timezone.utc)
            published_at = now - timedelta(hours=18)
            hist_file.write_text(json.dumps([
                {
                    "video_id": "good123",
                    "timestamp": published_at.isoformat(),
                    "status": "uploaded",
                }
            ]), encoding="utf-8")

            decision = preflight_gate.decide(
                history_path=hist_file,
                now=now,
                min_spacing_hours=23.75,
                max_inline_wait_hours=2.5,
            )
            self.assertFalse(decision["proceed"])
            self.assertEqual(decision["remaining_seconds"], int(5.75 * 3600))
            self.assertEqual(decision["due_at"], "2026-11-27T09:45:00Z")


if __name__ == "__main__":
    unittest.main()
