"""
Unit tests for detailed episode analysis and hybrid scene selection for JJK and Demon Slayer.
Tests cover timestamp metadata, character clip retrieval, title-driven intent matching,
and Google Drive non-repetitive episode selection.
"""
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.timestamp_loader import (
    load_episode_metadata,
    get_character_clips,
    find_best_episode_for_character,
    match_episode_code_from_filename,
    list_available_episodes
)
from core.title_driven_selector import parse_title_intent, get_title_driven_clips
from core.gdrive_manager import (
    pick_best_file_for_character,
    slice_action_moments_from_source
)

class TestDetailedEpisodesAndScenes(unittest.TestCase):
    def test_01_all_26_episodes_metadata_loadable(self):
        """Verify all 26 episode metadata files load with valid scenes and characters."""
        episodes = list_available_episodes()
        self.assertGreaterEqual(len(episodes), 26, "Should have at least 26 detailed combat episodes")
        
        # Verify Demon Slayer episodes exist
        ds_eps = [e for e in episodes if e.startswith("DS_")]
        self.assertGreaterEqual(len(ds_eps), 10, "Should have 10 Demon Slayer episodes")
        self.assertIn("DS_S01E17", ds_eps)
        self.assertIn("DS_S01E19", ds_eps)
        self.assertIn("DS_S01E20", ds_eps)
        self.assertIn("DS_S02E06", ds_eps)
        self.assertIn("DS_S02E07", ds_eps)
        self.assertIn("DS_S02E10", ds_eps)
        self.assertIn("DS_S03E08", ds_eps)

        # Verify JJK episodes exist
        jjk_eps = [e for e in episodes if not e.startswith("DS_")]
        self.assertGreaterEqual(len(jjk_eps), 16, "Should have 16 JJK episodes")
        self.assertIn("S01E20", jjk_eps)
        self.assertIn("S01E24", jjk_eps)
        self.assertIn("S02E04", jjk_eps)
        self.assertIn("S02E09", jjk_eps)
        self.assertIn("S02E13", jjk_eps)
        self.assertIn("S02E14", jjk_eps)
        self.assertIn("S02E17", jjk_eps)
        self.assertIn("S02E21", jjk_eps)

        for ep in episodes:
            data = load_episode_metadata(ep)
            self.assertIsNotNone(data, f"Episode {ep} must be loadable")
            self.assertIn("scenes", data)
            self.assertGreaterEqual(len(data["scenes"]), 1, f"Episode {ep} must have at least 1 scene")
            for scene in data["scenes"]:
                self.assertIn("start", scene)
                self.assertIn("end", scene)
                self.assertIn("action_score", scene)
                self.assertIn("characters_present", scene)
                self.assertGreaterEqual(scene["action_score"], 0.0)

    def test_02_filename_matching(self):
        """Test intelligent regex matching for JJK and Demon Slayer filenames."""
        # Demon Slayer cases
        self.assertEqual(match_episode_code_from_filename("Demon Slayer S01E19 Hinokami.mkv"), "DS_S01E19")
        self.assertEqual(match_episode_code_from_filename("[SubsPlease] Kimetsu no Yaiba - 17 [1080p].mkv"), "DS_S01E17")
        self.assertEqual(match_episode_code_from_filename("Demon Slayer Mugen Train Ep 07 Akaza Climax.mp4"), "DS_S02E07")
        self.assertEqual(match_episode_code_from_filename("Kimetsu no Yaiba Entertainment District Arc - 10.mkv"), "DS_S02E10")
        self.assertEqual(match_episode_code_from_filename("Demon Slayer Swordsmith Village Ep 08 Muichiro.mp4"), "DS_S03E08")

        # JJK cases
        self.assertEqual(match_episode_code_from_filename("Jujutsu Kaisen S02E17 Sukuna vs Mahoraga.mp4"), "S02E17")
        self.assertEqual(match_episode_code_from_filename("[Judas] Jujutsu Kaisen - 24 [1080p].mkv"), "S01E24")
        self.assertEqual(match_episode_code_from_filename("JJK S02E04 Gojo Awakened vs Toji.mkv"), "S02E04")
        self.assertEqual(match_episode_code_from_filename("Jujutsu Kaisen 2nd Season - 21 [1080p].mkv"), "S02E21")

    def test_03_character_clip_queries(self):
        """Verify character clip queries retrieve high-action combat moments."""
        # Demon Slayer
        tanjiro_clips = get_character_clips("DS_S01E19", "tanjiro", min_action_score=0.8)
        self.assertTrue(len(tanjiro_clips) >= 2)
        self.assertTrue(any("hinokami" in c.get("description", "").lower() for c in tanjiro_clips))

        zenitsu_clips = get_character_clips("DS_S01E17", "zenitsu", min_action_score=0.8)
        self.assertTrue(len(zenitsu_clips) >= 1)
        self.assertTrue(any("sixfold" in c.get("description", "").lower() for c in zenitsu_clips))

        rengoku_clips = get_character_clips("DS_S02E07", "rengoku", min_action_score=0.8)
        self.assertTrue(len(rengoku_clips) >= 1)
        self.assertTrue(any("ninth form" in c.get("description", "").lower() for c in rengoku_clips))

        # JJK
        sukuna_clips = get_character_clips("S02E17", "sukuna", min_action_score=0.8)
        self.assertTrue(len(sukuna_clips) >= 2)
        self.assertTrue(any("malevolent shrine" in c.get("description", "").lower() for c in sukuna_clips))

        gojo_clips = get_character_clips("S02E04", "gojo", min_action_score=0.8)
        self.assertTrue(len(gojo_clips) >= 1)
        self.assertTrue(any("purple" in c.get("description", "").lower() for c in gojo_clips))

        yuji_clips = get_character_clips("S02E21", "yuji", min_action_score=0.8)
        self.assertTrue(len(yuji_clips) >= 2)
        self.assertTrue(any("black flash" in c.get("description", "").lower() for c in yuji_clips))

    def test_04_title_intent_and_clip_selection(self):
        """Verify titles trigger correct scene types and preferred episodes."""
        t1 = "Tanjiro Awakens Hinokami Kagura Dance of the Fire God 🔥 #tanjiro"
        intent1 = parse_title_intent(t1)
        self.assertEqual(intent1["scene_type"], "hinokami kagura")
        self.assertIn("DS_S01E19", intent1["preferred_episodes"])

        clips1 = get_title_driven_clips(t1, "tanjiro", max_clips=5)
        self.assertTrue(len(clips1) >= 2)
        self.assertEqual(clips1[0]["episode"], "DS_S01E19")

        t2 = "Gojo's 0.2s Domain Expansion in Shibuya 💀 #gojo #jjk"
        intent2 = parse_title_intent(t2)
        self.assertEqual(intent2["scene_type"], "domain expansion")
        self.assertIn("S02E09", intent2["preferred_episodes"])

        clips2 = get_title_driven_clips(t2, "gojo", max_clips=5)
        self.assertTrue(len(clips2) >= 1)
        self.assertEqual(clips2[0]["episode"], "S02E09")

    def test_05_pick_best_file_for_character_with_title(self):
        """Test Google Drive episode selection prioritized by title keywords."""
        files = [
            {"name": "Kimetsu no Yaiba S01E17 Zenitsu.mkv", "id": "fid_zenitsu"},
            {"name": "Demon Slayer S01E19 Hinokami.mkv", "id": "fid_hinokami"},
            {"name": "Demon Slayer Mugen Train Ep 07.mkv", "id": "fid_rengoku"},
            {"name": "Jujutsu Kaisen S02E17 Sukuna Mahoraga.mp4", "id": "fid_sukuna"},
            {"name": "Jujutsu Kaisen S02E21 Yuji Todo Black Flash.mp4", "id": "fid_yuji"}
        ]

        # Test title matching Hinokami Kagura -> picks Ep 19
        chosen = pick_best_file_for_character(
            files=files,
            character_key="tanjiro",
            title="Tanjiro Hinokami Kagura Climax vs Rui 🔥"
        )
        self.assertIsNotNone(chosen)
        self.assertIn("19", chosen["name"])

        # Test title matching Black Flash -> picks Ep 21
        chosen_jjk = pick_best_file_for_character(
            files=files,
            character_key="yuji",
            title="Yuji & Todo Double Black Flash Combo 🔥"
        )
        self.assertIsNotNone(chosen_jjk)
        self.assertIn("21", chosen_jjk["name"])

if __name__ == "__main__":
    unittest.main()
