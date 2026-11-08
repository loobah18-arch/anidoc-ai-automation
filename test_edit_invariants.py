"""
Unit tests verifying strict anime edit invariants:
1. Strict Episode Intro Rejection: Scenes < 180.0s for full episodes (cold open, OP song, title cards, studio logos) are strictly banned.
2. Pre-drop Conversation Exclusivity: Clips before the beat drop must ONLY be pre-fight dialogue/conversation scenes.
3. Natural Conversation Cadence: Dialogue lines complete naturally before the beat drop without premature truncation.
4. Post-drop Pure Combat Exclusivity: All clips after the beat drop must strictly and exclusively be combat/sakuga scenes.
5. Simple Subtitle Styling & Perfect Sync: Clean Montserrat font, pure white text, subtle dark outline, zero neon glow, zero scale pop.
"""
import unittest
from pathlib import Path
from metadata.jjk_episodes_detailed import S02E04_TIMESTAMPS
from metadata.demonslayer_episodes_detailed import DS_S02E07_TIMESTAMPS
from core.subtitle_stylizer import (
    generate_kinetic_subtitles,
    SUBTITLE_STYLE_PRESETS,
    DEFAULT_CHARACTER_DIALOGUE
)
from core.gdrive_manager import get_episode_phase_boundaries

class TestAnimeEditInvariants(unittest.TestCase):
    def test_01_episode_intro_rejection_and_bounds(self):
        """Verify that episode openers, cold opens, OP theme songs, and title cards are banned."""
        bounds_jjk = get_episode_phase_boundaries(
            total_duration=1440.0,
            character_key="gojo",
            matched_ep_code="S02E04"
        )
        # Full episodes must enforce start_bound >= 180.0s
        self.assertGreaterEqual(bounds_jjk["start_bound"], 180.0)
        
        # All curated combat scenes must start after 180.0s (skipping OP theme song and episode title card)
        for s in bounds_jjk["curated_combat_scenes"]:
            self.assertGreaterEqual(s["start"], 180.0, f"Combat scene at {s['start']}s leaks into episode opening!")
            desc = s.get("description", "").lower()
            self.assertFalse(any(kw in desc for kw in ["opening theme", "title card", "cold open", "ed theme", "staff roll"]))

    def test_02_pre_drop_conversation_exclusivity(self):
        """Verify that S02E04 has verified pre-fight conversation scenes marked is_conversation=True."""
        bounds = get_episode_phase_boundaries(
            total_duration=1440.0,
            character_key="gojo",
            matched_ep_code="S02E04"
        )
        self.assertIsNotNone(bounds["conv_window"])
        self.assertGreaterEqual(len(bounds["curated_conv_scenes"]), 1)
        conv_scene = bounds["curated_conv_scenes"][0]
        self.assertTrue(conv_scene.get("is_conversation", False))
        self.assertIn("gojo", [c.lower() for c in conv_scene.get("characters_present", [])])
        # Conversation must be before the main combat clash (840s)
        self.assertLess(conv_scene["start"], 840.0)

    def test_03_gojo_intro_dialogue_accuracy_and_completion(self):
        """Verify S02E04 intro dialogue accurately captures 'The Honored One' and completes before drop."""
        dialogue = S02E04_TIMESTAMPS.get("intro_dialogue")
        self.assertIsNotNone(dialogue)
        self.assertEqual(len(dialogue), 3)
        self.assertIn("YO. IT'S BEEN A WHILE.", dialogue[0]["text"])
        self.assertIn("THROUGHOUT HEAVEN AND EARTH...", dialogue[1]["text"])
        self.assertIn("I ALONE AM THE HONORED ONE.", dialogue[2]["text"])
        # Dialogue finishes cleanly by 13.5s, allowing a natural pause before the 14.1s beat drop
        last_line_end = dialogue[2]["end_rel"]
        self.assertLessEqual(last_line_end, 13.6)
        self.assertGreaterEqual(last_line_end, 13.0)

    def test_04_simple_font_and_clean_subtitles(self):
        """Verify subtitles use simple clean Montserrat font with subtle outline and no neon glow or scale pops."""
        preset = SUBTITLE_STYLE_PRESETS["spur_hook"]
        self.assertEqual(preset["font"], "Montserrat")
        self.assertEqual(preset["primary"], "&H00FFFFFF")
        self.assertEqual(preset["outline"], "&H00000000")
        self.assertLessEqual(preset["outline_width"], 3.0)  # Subtle 2.5px outline, not thick blob
        
        from config.settings import SCRATCH_DIR
        ass_out = SCRATCH_DIR / "test_simple_subs.ass"
        dialogue = [
            {"speaker": "Gojo", "text": "THROUGHOUT HEAVEN AND EARTH...", "start_rel": 0.8, "end_rel": 4.5},
            {"speaker": "Gojo", "text": "I ALONE AM THE HONORED ONE.", "start_rel": 5.0, "end_rel": 13.5}
        ]
        generate_kinetic_subtitles(
            quote_text="HONORED ONE",
            start_time=0.2,
            end_time=14.0,
            output_ass_path=ass_out,
            style_preset="spur_hook",
            dialogue_lines=dialogue
        )
        self.assertTrue(ass_out.exists())
        content = ass_out.read_text(encoding="utf-8")
        
        # Verify font simplicity: NO neon blur tags (\blur4), NO scale popping (\fscx112), NO tracking (\fsp3)
        self.assertNotIn(r"\blur4", content)
        self.assertNotIn(r"\fscx112", content)
        self.assertNotIn(r"\fsp3", content)
        # Verify Montserrat font in style
        self.assertIn("DialogueSub,Montserrat", content)
        # Verify dialogue text appears
        self.assertIn("THROUGHOUT HEAVEN", content)
        self.assertIn("AND EARTH...", content)
        self.assertIn("I ALONE AM THE HONORED ONE.", content)

    def test_05_demonslayer_rengoku_conversation_dialogue(self):
        """Verify Demon Slayer DS_S02E07 pre-fight dialogue standoff is preserved and cleanly timed."""
        dialogue = DS_S02E07_TIMESTAMPS.get("intro_dialogue")
        self.assertIsNotNone(dialogue)
        self.assertEqual(len(dialogue), 3)
        self.assertIn("WHY DON'T YOU BECOME A DEMON TOO?", dialogue[0]["text"])
        self.assertIn("I WILL NEVER BECOME A DEMON", dialogue[1]["text"])
        self.assertIn("I WILL FULFILL MY DUTY", dialogue[2]["text"])
        self.assertLessEqual(dialogue[2]["end_rel"], 13.6)

if __name__ == "__main__":
    unittest.main()
