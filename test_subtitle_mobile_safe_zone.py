"""
Mobile Safe-Zone & Vocal Isolation Audio Verification Test Suite.
Validates:
1. Subtitle & Question placement on mobile screens (Upper-Third Alignment 8 vs Lower-Third Alignment 2).
2. Proper MarginV positioning above YouTube Shorts UI and below top header chrome.
3. Audio vocal isolation (5.1 center / stereo mid-channel) with crisp dialogue presence and anime music cancellation.
"""
import unittest
from pathlib import Path

from config.settings import SCRATCH_DIR, VIDEO_WIDTH, VIDEO_HEIGHT
from core.subtitle_stylizer import generate_kinetic_subtitles, SUBTITLE_STYLE_PRESETS
from core.vocal_isolator import build_vocal_isolation_filter


class TestMobileSafeZoneAndVocalAudio(unittest.TestCase):
    """Test suite for mobile safe zones and vocal audio intelligibility."""

    def test_01_question_upper_third_alignment_and_safe_zone(self):
        """Verify the hook question is placed at Top Center (alignment 8) in the upper mobile safe zone."""
        preset = SUBTITLE_STYLE_PRESETS["spur_hook"]
        self.assertEqual(preset["alignment"], 8, "Hook question must be aligned to Top Center (8)")
        self.assertGreaterEqual(preset["margin_v"], 180, "Top margin must be at least 180px below mobile status bar/header")
        self.assertLessEqual(preset["margin_v"], 260, "Top margin must stay in upper third")
        self.assertGreaterEqual(preset["margin_lr"], 80, "Horizontal margin must keep question inside mobile screen")

    def test_02_dialogue_lower_third_alignment_and_safe_zone(self):
        """Verify dialogue subtitles are placed at Bottom Center (alignment 2) above Shorts channel/title UI."""
        out_ass = SCRATCH_DIR / "test_safe_zone_dialogue.ass"
        dialogue = [
            {"speaker": "Giyu", "text": "WATER BREATHING...", "start": 0.5, "end": 4.0},
            {"speaker": "Giyu", "text": "ELEVENTH FORM: DEAD CALM.", "start": 5.0, "end": 10.0}
        ]

        try:
            generate_kinetic_subtitles(
                quote_text="CAN ANY DEMON BREACH | GIYU'S DEAD CALM?",
                start_time=0.2,
                end_time=12.0,
                output_ass_path=out_ass,
                style_preset="spur_hook",
                character_name="GIYU",
                drop_time=8.0,
                dialogue_lines=dialogue
            )

            self.assertTrue(out_ass.exists())
            content = out_ass.read_text(encoding="utf-8")

            # Verify BaseText style has alignment 8 (top center)
            base_style = [l for l in content.splitlines() if l.startswith("Style: BaseText")]
            self.assertTrue(len(base_style) > 0)
            base_parts = base_style[0].split(",")
            # Alignment is field index 18 (0-indexed) in Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
            self.assertEqual(base_parts[18].strip(), "8", "BaseText alignment must be 8 (top center)")

            # Verify DialogueSub style has alignment 2 (bottom center) and MarginV >= 440 (safe above bottom chrome)
            d_style = [l for l in content.splitlines() if l.startswith("Style: DialogueSub")]
            self.assertTrue(len(d_style) > 0)
            d_parts = d_style[0].split(",")
            self.assertEqual(d_parts[18].strip(), "2", "DialogueSub alignment must be 2 (bottom center)")
            d_margin_v = int(d_parts[21].strip())
            self.assertGreaterEqual(d_margin_v, 440, "DialogueSub MarginV must be >= 440px to sit above channel/title overlay")

        finally:
            out_ass.unlink(missing_ok=True)

    def test_03_vocal_isolation_preserves_dialogue_and_mutes_music(self):
        """Verify vocal isolation filters preserve human speech while cancelling stereo music."""
        # Pre-fight conversation clip:
        conv_filter = build_vocal_isolation_filter(is_conversation=True)
        self.assertIn("pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1", conv_filter)
        self.assertIn("highpass=f=90", conv_filter)
        self.assertIn("lowpass=f=6500", conv_filter)
        self.assertIn("acompressor=", conv_filter)
        self.assertIn("volume=1.85", conv_filter)
        # Invariant: Never hard-mute conversation speech to 0.0
        self.assertNotIn("volume=enable='not", conv_filter)

        # Combat sakuga clip:
        combat_filter = build_vocal_isolation_filter(is_conversation=False)
        self.assertEqual(combat_filter, "volume=0.0", "Combat anime audio must be completely muted so only Phonk hits")


if __name__ == "__main__":
    unittest.main()
