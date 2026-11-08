"""
Unit tests for Scene-Aware & Non-Repeating Engaging Questions Manager.
Verifies scene/character grounding, zero repetition, and subtitle integration.
"""
import unittest
from pathlib import Path

from core.question_manager import (
    get_engaging_question,
    _load_question_history,
    _save_question_history,
    QUESTION_HISTORY_FILE
)
from core.subtitle_stylizer import generate_kinetic_subtitles


class TestQuestionManager(unittest.TestCase):
    """Test suite for engaging questions engine."""

    def setUp(self):
        # Backup history
        self._orig_history = _load_question_history()
        # Reset history for clean deterministic tests
        _save_question_history([])

    def tearDown(self):
        # Restore history
        _save_question_history(self._orig_history)

    def test_01_scene_grounded_questions(self):
        """Verify questions are directly grounded in the specific battle scene."""
        # Gojo vs Toji S02E04
        q_toji = get_engaging_question("gojo", episode_code="S02E04")
        self.assertIn(" | ", q_toji)
        self.assertTrue(any(k in q_toji for k in ["TOJI", "HONORED ONE", "PURPLE", "INVERTED"]))

        # Sukuna vs Mahoraga S02E17
        q_maho = get_engaging_question("sukuna", episode_code="S02E17")
        self.assertIn(" | ", q_maho)
        self.assertTrue(any(k in q_maho for k in ["MAHORAGA", "MALEVOLENT", "FUGA", "WHEEL"]))

        # Rengoku vs Akaza DS_S02E06
        q_rengoku = get_engaging_question("rengoku", episode_code="DS_S02E06")
        self.assertIn(" | ", q_rengoku)
        self.assertTrue(any(k in q_rengoku for k in ["RENGOKU", "AKAZA", "FLAME TIGER", "SLAYER MARK"]))

    def test_02_zero_repetition_guarantee(self):
        """Verify that sequential calls never repeat the same question until exhaustion."""
        seen_questions = set()
        # S02E04 has 4 curated questions
        for _ in range(4):
            q = get_engaging_question("gojo", episode_code="S02E04")
            self.assertNotIn(q, seen_questions, f"Question repeated prematurely: {q}")
            seen_questions.add(q)

        self.assertEqual(len(seen_questions), 4)

    def test_03_character_specific_fallback(self):
        """Verify character-specific questions when episode code is not in the scene database."""
        q_denji = get_engaging_question("denji")
        self.assertIn(" | ", q_denji)
        self.assertIn("DENJI", q_denji)

        q_jinwoo = get_engaging_question("sungjinwoo")
        self.assertIn(" | ", q_jinwoo)
        self.assertTrue("SHADOW MONARCH" in q_jinwoo or "SUNG JIN-WOO" in q_jinwoo)

    def test_04_subtitle_both_upper_question_and_lower_dialogue(self):
        """Verify that ASS subtitles render both upper-third hook question and lower-third dialogue."""
        out_ass = Path("metadata/episodes/temp_test_subs.ass")
        dialogue = [
            {"speaker": "Gojo", "text": "THROUGHOUT HEAVEN AND EARTH...", "start": 0.5, "end": 4.5},
            {"speaker": "Gojo", "text": "I ALONE AM THE HONORED ONE.", "start": 5.0, "end": 9.0}
        ]
        q_text = "TOJI THOUGHT HE FINISHED HIM | WHO SURVIVES THE HONORED ONE?"

        try:
            generate_kinetic_subtitles(
                quote_text=q_text,
                start_time=0.2,
                end_time=15.0,
                output_ass_path=out_ass,
                style_preset="spur_hook",
                character_name="GOJO",
                drop_time=10.0,
                dialogue_lines=dialogue
            )

            self.assertTrue(out_ass.exists())
            with open(out_ass, "r", encoding="utf-8") as f:
                content = f.read()

            # Verify upper-third hook question lines (BaseText) are present and positioned in top mobile safe zone
            self.assertIn("BaseText", content)
            self.assertIn("TOJI THOUGHT", content)
            self.assertIn("HONORED ONE", content)
            # Alignment 8 (top center) in BaseText style line
            self.assertTrue(any("Style: BaseText" in line and ",8," in line for line in content.splitlines()))

            # Verify lower-third dialogue lines (DialogueSub) are also present in bottom mobile safe zone
            self.assertIn("DialogueSub", content)
            self.assertIn("THROUGHOUT HEAVEN", content)
            self.assertIn("HONORED ONE", content)
            # Alignment 2 (bottom center) with safe MarginV >= 440 (587 on 1440p)
            self.assertTrue(any("Style: DialogueSub" in line and ",2," in line and any(m in line for m in ["440", "586", "587"]) for line in content.splitlines()))

        finally:
            if out_ass.exists():
                out_ass.unlink()

    def test_05_multi_character_episode_isolation(self):
        """Verify that multi-character episodes like DS_S01E20 isolate questions per character."""
        # Shinobu must get Shinobu-specific questions in DS_S01E20
        q_shinobu = get_engaging_question("shinobu", episode_code="DS_S01E20")
        self.assertIn(" | ", q_shinobu)
        self.assertTrue(
            any(k in q_shinobu for k in ["SHINOBU", "WISTERIA", "INSECT", "BUTTERFLY", "SPIDER SISTER"]),
            f"Shinobu got non-Shinobu question: {q_shinobu}"
        )
        self.assertNotIn("GIYU", q_shinobu)
        self.assertNotIn("DEAD CALM", q_shinobu)

        # Giyu must get Giyu-specific questions in DS_S01E20
        q_giyu = get_engaging_question("giyu", episode_code="DS_S01E20")
        self.assertIn(" | ", q_giyu)
        self.assertTrue(
            any(k in q_giyu for k in ["GIYU", "DEAD CALM", "WATER BREATHING", "ELEVENTH FORM", "RUI"]),
            f"Giyu got non-Giyu question: {q_giyu}"
        )
        self.assertNotIn("SHINOBU", q_giyu)
        self.assertNotIn("WISTERIA", q_giyu)


if __name__ == "__main__":
    unittest.main()
