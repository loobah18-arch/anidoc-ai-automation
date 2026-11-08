"""
Unit tests for Vocal Isolation & Anime Background Music Cancellation Engine.
Verifies that original anime BGM is muted, speech intervals are gated, and combat music is silenced.
"""
import subprocess
import unittest
from pathlib import Path

from core.vocal_isolator import (
    probe_audio_channels,
    extract_speech_intervals_from_dialogue,
    build_speech_activity_expression,
    build_vocal_isolation_filter
)


class TestVocalIsolator(unittest.TestCase):
    """Test suite for vocal isolation and BGM cancellation."""

    def test_01_extract_and_merge_speech_intervals(self):
        """Verify sorting, clamping, and merging of speech intervals."""
        dialogue = [
            {"speaker": "Gojo", "start": 0.6, "end": 4.6},
            {"speaker": "Gojo", "start": 4.8, "end": 8.8},  # Adjacent to 4.6 (gap 0.2s <= 0.35s)
            {"speaker": "Toji", "start": 12.0, "end": 15.0},
            {"speaker": "Toji", "start": 32.0, "end": 35.0}, # Past drop_time 30.54s
        ]

        intervals = extract_speech_intervals_from_dialogue(dialogue, drop_time=30.54)
        self.assertEqual(len(intervals), 2)
        # First interval should be merged (0.6 to 8.8)
        self.assertAlmostEqual(intervals[0][0], 0.6, places=2)
        self.assertAlmostEqual(intervals[0][1], 8.8, places=2)
        # Second interval (12.0 to 15.0)
        self.assertAlmostEqual(intervals[1][0], 12.0, places=2)
        self.assertAlmostEqual(intervals[1][1], 15.0, places=2)

    def test_02_build_speech_activity_expression(self):
        """Verify FFmpeg expression format for speech activity."""
        intervals = [(1.0, 3.0), (5.5, 7.5)]
        expr = build_speech_activity_expression(intervals, buffer=0.20)
        self.assertIn("between(t\\,0.80\\,3.20)", expr)
        self.assertIn("between(t\\,5.30\\,7.70)", expr)
        self.assertIn("+", expr)

    def test_03_conversation_stereo_vocal_filter(self):
        """Verify conversation vocal isolation filter contains mid/side center extraction, bandpass, EQ, compressor, and gain."""
        intervals = [(1.0, 5.0)]
        filt = build_vocal_isolation_filter(
            clip_path=None,
            speech_intervals=intervals,
            is_conversation=True
        )

        self.assertIn("pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1", filt)
        self.assertIn("highpass=f=90", filt)
        self.assertIn("lowpass=f=6500", filt)
        self.assertIn("equalizer=f=1600", filt)
        self.assertIn("equalizer=f=3400", filt)
        self.assertIn("acompressor=", filt)
        self.assertIn("volume=1.85", filt)

    def test_04_combat_scene_auto_mute_anime_music(self):
        """Verify combat scenes (post-drop) mute anime audio completely so only Phonk plays."""
        filt = build_vocal_isolation_filter(is_conversation=False)
        self.assertEqual(filt, "volume=0.0")

    def test_05_ffmpeg_filter_execution_syntax(self):
        """Verify FFmpeg successfully executes the generated filter graph on synthetic audio."""
        intervals = [(0.2, 0.8)]
        filt = build_vocal_isolation_filter(
            clip_path=None,
            speech_intervals=intervals,
            is_conversation=True
        )

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=800:duration=1.2",
            "-af", f"aformat=channel_layouts=stereo,{filt}",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"FFmpeg execution failed:\n{res.stderr}")


if __name__ == "__main__":
    unittest.main()
