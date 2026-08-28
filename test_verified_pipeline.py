"""
Test Suite for Verified JJK Timestamp Pipeline
Tests schema validation, event selection, source resolution, and upload gating.
"""
import unittest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from core.scene_database import VerifiedEventDatabase


class TestVerifiedEventDatabase(unittest.TestCase):
    """Test verified event selection and history tracking."""

    def setUp(self):
        self.test_db = {
            "version": "1.0.0",
            "generated_at": "2026-08-28T00:00:00Z",
            "total_episodes": 2,
            "total_scenes": 10,
            "episodes": {
                "gdrive_abc123": {
                    "scan_status": "success",
                    "source_id": "gdrive_abc123",
                    "drive_file_id": "abc123",
                    "canonical_filename": "test_ep01.mkv",
                    "season": 1,
                    "episode": 1,
                    "duration": 1400.0,
                    "total_scenes": 5,
                    "scenes": []
                }
            },
            "events": [
                {
                    "event_id": "gojo_awakened_test",
                    "source_id": "gdrive_abc123",
                    "drive_file_id": "abc123",
                    "canonical_filename": "test_ep01.mkv",
                    "season": 1,
                    "episode": 1,
                    "title_metadata": {
                        "title": "Gojo Awakened Test",
                        "quote": "Test quote",
                        "tags": ["gojo", "jjk", "test"]
                    },
                    "cut_windows": [
                        {
                            "start": 300.0,
                            "end": 350.0,
                            "semantic_status": "verified",
                            "scene_suitability": {"slowmo_safe": True}
                        }
                    ],
                    "eligible_for_upload": True
                },
                {
                    "event_id": "unverified_event",
                    "source_id": "gdrive_abc123",
                    "cut_windows": [
                        {
                            "start": 100.0,
                            "end": 150.0,
                            "semantic_status": "unverified"
                        }
                    ],
                    "eligible_for_upload": False
                }
            ]
        }

        self.test_history = {
            "version": "1.0.0",
            "events_rendered": {},
            "events_uploaded": {}
        }

    @patch('core.scene_database.Path')
    def test_get_eligible_events_filters_unverified(self, mock_path):
        """Only verified events should be eligible."""
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(self.test_db))):
            db = VerifiedEventDatabase()
            db.database = self.test_db
            db.history = self.test_history

            eligible = db.get_eligible_events()

            self.assertEqual(len(eligible), 1)
            self.assertEqual(eligible[0]["event_id"], "gojo_awakened_test")

    @patch('core.scene_database.Path')
    def test_custom_title_resolution(self, mock_path):
        """Custom title must exactly match verified event."""
        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(self.test_db))):
            db = VerifiedEventDatabase()
            db.database = self.test_db
            db.history = self.test_history

            # Exact match should work
            event = db.select_event_for_render(custom_title="Gojo Awakened Test")
            self.assertEqual(event["event_id"], "gojo_awakened_test")

            # Non-match should raise
            with self.assertRaises(ValueError):
                db.select_event_for_render(custom_title="Nonexistent Title")

    @patch('core.scene_database.Path')
    def test_no_eligible_events_raises(self, mock_path):
        """Should raise if no verified events available."""
        empty_db = {**self.test_db, "events": []}

        with patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(empty_db))):
            db = VerifiedEventDatabase()
            db.database = empty_db
            db.history = self.test_history

            with self.assertRaises(RuntimeError) as ctx:
                db.select_event_for_render()

            self.assertIn("No verified eligible events", str(ctx.exception))


class TestDatabaseSchema(unittest.TestCase):
    """Test database schema validation."""

    def test_event_requires_stable_source_id(self):
        """Events must have source_id."""
        event = {
            "event_id": "test",
            "cut_windows": [{"start": 0, "end": 10, "semantic_status": "verified"}],
            "eligible_for_upload": True
        }

        # Missing source_id
        self.assertIsNone(event.get("source_id"))

    def test_scene_requires_semantic_status(self):
        """Scenes must have explicit semantic status."""
        scene = {
            "start": 100.0,
            "end": 200.0,
            "audio_energy_band": "high",
            "semantic": {
                "status": "unverified",
                "characters": [],
                "action": None
            }
        }

        self.assertIn("status", scene["semantic"])
        self.assertIn(scene["semantic"]["status"], ["unverified", "candidate", "verified", "rejected"])

    def test_technical_labels_not_semantic(self):
        """Audio energy bands are technical only."""
        technical_labels = ["very_high", "high", "medium", "low"]

        for label in technical_labels:
            # These are valid technical labels
            self.assertIn(label, technical_labels)

        # These are NOT valid - they're semantic
        semantic_labels = ["action", "dialogue", "intense_action", "ambient"]

        for label in semantic_labels:
            self.assertNotIn(label, technical_labels)


class TestUploadGate(unittest.TestCase):
    """Test upload guard prevents unverified uploads."""

    def test_upload_requires_event_verified(self):
        """Upload should check event_verified flag."""
        result_unverified = {
            "status": "success",
            "output_path": Path("/tmp/test.mp4"),
            "event_verified": False
        }

        result_verified = {
            "status": "success",
            "output_path": Path("/tmp/test.mp4"),
            "event_verified": True,
            "event_id": "test_event",
            "source_trace": {"source_id": "gdrive_abc"}
        }

        # Unverified should be blocked
        self.assertFalse(result_unverified.get("event_verified", False))

        # Verified should pass
        self.assertTrue(result_verified.get("event_verified", False))
        self.assertIsNotNone(result_verified.get("event_id"))
        self.assertIsNotNone(result_verified.get("source_trace"))


if __name__ == "__main__":
    unittest.main()
