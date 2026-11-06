#!/usr/bin/env python3
"""
Unit tests for AniDoc YouTube Publisher & Auto-Remediation Retry Engine.
Verifies:
1. YouTube status verification (clean vs rejected vs region-restricted).
2. Automated deletion of blocked YouTube uploads to maintain channel standing.
3. Metadata remediation for retry attempts.
4. Upload-and-retry lifecycle (single attempt success, retry recovery after block, and block exhaustion).
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from publishers.youtube_publisher import (
    check_youtube_video_status,
    delete_blocked_youtube_video,
    remediate_metadata_for_retry,
    upload_video_with_block_retry,
)


class TestYouTubePublisher(unittest.TestCase):

    def test_check_youtube_video_status_clean(self):
        mock_youtube = MagicMock()
        mock_youtube.videos().list().execute.return_value = {
            "items": [
                {
                    "status": {"uploadStatus": "uploaded"},
                    "processingDetails": {"processingStatus": "succeeded"},
                    "contentDetails": {},
                }
            ]
        }

        is_blocked, reason, details = check_youtube_video_status(
            mock_youtube, "clean_vid_123", timeout_sec=0.0
        )
        self.assertFalse(is_blocked)
        self.assertIsNone(reason)
        self.assertEqual(details["status"]["uploadStatus"], "uploaded")

    def test_check_youtube_video_status_rejected_copyright(self):
        mock_youtube = MagicMock()
        mock_youtube.videos().list().execute.return_value = {
            "items": [
                {
                    "status": {
                        "uploadStatus": "rejected",
                        "rejectionReason": "copyright",
                    },
                    "processingDetails": {},
                    "contentDetails": {},
                }
            ]
        }

        is_blocked, reason, details = check_youtube_video_status(
            mock_youtube, "blocked_vid_456", timeout_sec=0.0
        )
        self.assertTrue(is_blocked)
        self.assertEqual(reason, "copyright")

    def test_check_youtube_video_status_region_restricted(self):
        mock_youtube = MagicMock()
        mock_youtube.videos().list().execute.return_value = {
            "items": [
                {
                    "status": {"uploadStatus": "uploaded"},
                    "processingDetails": {"processingStatus": "processing"},
                    "contentDetails": {
                        "regionRestriction": {
                            "blocked": [f"US_{i}" for i in range(55)]
                        }
                    },
                }
            ]
        }

        is_blocked, reason, _ = check_youtube_video_status(
            mock_youtube, "restricted_vid_789", timeout_sec=0.0
        )
        self.assertTrue(is_blocked)
        self.assertEqual(reason, "region_restricted_block")

    def test_delete_blocked_youtube_video(self):
        mock_youtube = MagicMock()
        ok = delete_blocked_youtube_video(mock_youtube, "vid_to_delete")
        self.assertTrue(ok)
        mock_youtube.videos().delete.assert_called_once_with(id="vid_to_delete")

    def test_remediate_metadata_for_retry(self):
        new_title, new_desc, new_tags = remediate_metadata_for_retry(
            title="Gojo Domain Expansion",
            description="Epic fight scene",
            tags=["gojo", "jjk", "raw"],
            attempt=1,
        )
        self.assertIn("Scene Breakdown", new_title)
        self.assertIn("#Shorts", new_title)
        self.assertIn("Transformative Fair Use", new_desc)
        self.assertNotIn("raw", new_tags)
        self.assertIn("animeedit", new_tags)

    def test_upload_with_block_retry_clean_first_attempt(self):
        mock_youtube = MagicMock()
        mock_req = MagicMock()
        mock_req.next_chunk.return_value = (None, {"id": "clean_yt_100"})
        mock_youtube.videos().insert.return_value = mock_req

        mock_status = {
            "items": [
                {
                    "status": {"uploadStatus": "uploaded"},
                    "processingDetails": {"processingStatus": "succeeded"},
                    "contentDetails": {},
                }
            ]
        }
        mock_youtube.videos().list().execute.return_value = mock_status

        with patch("pathlib.Path.exists", return_value=True), \
             patch("publishers.youtube_publisher.validate_shorts_video", return_value=(True, "1080x1080, 30.0s")):
            res = upload_video_with_block_retry(
                video_path=Path("dummy_short.mp4"),
                title="Test Title",
                description="Test Desc",
                tags=["anime"],
                youtube_client=mock_youtube,
                media_upload_cls=MagicMock(),
                verify_timeout_sec=0.0,
            )

            self.assertEqual(res["status"], "success")
            self.assertEqual(res["video_id"], "clean_yt_100")
            self.assertEqual(res["attempts"], 1)

    def test_upload_with_block_retry_recovers_after_retry(self):
        mock_youtube = MagicMock()
        mock_req_1 = MagicMock()
        mock_req_1.next_chunk.return_value = (None, {"id": "blocked_id_1"})
        mock_req_2 = MagicMock()
        mock_req_2.next_chunk.return_value = (None, {"id": "clean_id_2"})
        mock_youtube.videos().insert.side_effect = [mock_req_1, mock_req_2]

        status_blocked = {
            "items": [
                {
                    "status": {"uploadStatus": "rejected", "rejectionReason": "copyright"},
                    "processingDetails": {},
                    "contentDetails": {},
                }
            ]
        }
        status_clean = {
            "items": [
                {
                    "status": {"uploadStatus": "uploaded"},
                    "processingDetails": {"processingStatus": "succeeded"},
                    "contentDetails": {},
                }
            ]
        }
        mock_youtube.videos().list().execute.side_effect = [status_blocked, status_clean]

        with patch("pathlib.Path.exists", return_value=True), \
             patch("publishers.youtube_publisher.validate_shorts_video", return_value=(True, "1080x1080, 30.0s")), \
             patch("publishers.youtube_publisher.remediate_video_for_retry", return_value=Path("remediated.mp4")):

            res = upload_video_with_block_retry(
                video_path=Path("dummy_short.mp4"),
                title="Test Title",
                description="Test Desc",
                tags=["anime"],
                youtube_client=mock_youtube,
                media_upload_cls=MagicMock(),
                max_retries=2,
                verify_timeout_sec=0.0,
            )

            self.assertEqual(res["status"], "success")
            self.assertEqual(res["video_id"], "clean_id_2")
            self.assertEqual(res["attempts"], 2)
            self.assertTrue(res["remediated"])
            mock_youtube.videos().delete.assert_called_once_with(id="blocked_id_1")

    def test_upload_with_block_retry_aborts_and_reports_blocked_after_max_retries(self):
        mock_youtube = MagicMock()
        mock_req_1 = MagicMock()
        mock_req_1.next_chunk.return_value = (None, {"id": "blocked_1"})
        mock_req_2 = MagicMock()
        mock_req_2.next_chunk.return_value = (None, {"id": "blocked_2"})
        mock_youtube.videos().insert.side_effect = [mock_req_1, mock_req_2]

        status_blocked = {
            "items": [
                {
                    "status": {"uploadStatus": "rejected", "rejectionReason": "copyright"},
                    "processingDetails": {},
                    "contentDetails": {},
                }
            ]
        }
        mock_youtube.videos().list().execute.return_value = status_blocked

        with patch("pathlib.Path.exists", return_value=True), \
             patch("publishers.youtube_publisher.validate_shorts_video", return_value=(True, "1080x1080, 30.0s")), \
             patch("publishers.youtube_publisher.remediate_video_for_retry", return_value=Path("remediated.mp4")):

            res = upload_video_with_block_retry(
                video_path=Path("dummy_short.mp4"),
                title="Test Title",
                description="Test Desc",
                tags=["anime"],
                youtube_client=mock_youtube,
                media_upload_cls=MagicMock(),
                max_retries=1,
                verify_timeout_sec=0.0,
            )

            self.assertEqual(res["status"], "blocked")
            self.assertEqual(res["rejection_reason"], "copyright")
            self.assertEqual(res["attempts"], 2)
            self.assertEqual(mock_youtube.videos().delete.call_count, 2)


if __name__ == "__main__":
    unittest.main()
