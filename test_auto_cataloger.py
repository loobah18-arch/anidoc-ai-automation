"""
Unit tests for AniDoc Auto-Cataloger Engine.
Verifies automatic detection and indexing of newly added anime series and episodes.
"""
import os
import json
import shutil
import unittest
from pathlib import Path

from core.auto_cataloger import (
    parse_anime_identity,
    is_episode_cataloged,
    auto_catalog_episode,
    scan_and_catalog_directory,
    METADATA_DIR
)
from core.clip_manager import CHARACTER_THEMES, ensure_character_theme
from core.timestamp_loader import (
    match_episode_code_from_filename,
    load_episode_metadata,
    list_available_episodes
)
from core.gdrive_manager import get_file_universe


class TestAutoCataloger(unittest.TestCase):
    """Test suite for automatic anime & episode cataloging."""

    def test_01_parse_known_and_new_anime_identities(self):
        """Verify accurate identification of diverse anime universes and episode codes."""
        test_cases = [
            ("[SubsPlease] Chainsaw Man - 08 (1080p).mkv", "chainsawman", "CSM_S01E08", 1, 8),
            ("[Erai-raws] Solo Leveling - 11 [1080p].mkv", "sololeveling", "SL_S01E11", 1, 11),
            ("[Judas] Jujutsu Kaisen - S02E18 [1080p].mkv", "jjk", "S02E18", 2, 18),
            ("Demon Slayer - S04E01.mp4", "demonslayer", "DS_S04E01", 4, 1),
            ("Bleach TYBW S02E06.mp4", "bleach", "BLEACH_S02E06", 2, 6),
            ("Attack on Titan The Final Season - 28.mkv", "aot", "AOT_S01E28", 1, 28),
            ("Kaiju No 8 - 10.mp4", "kaijuno8", "KAIJU_S01E10", 1, 10),
            ("Dandadan - 03.mkv", "dandadan", "DDD_S01E03", 1, 3),
            ("[SubsPlease] Wind Breaker - 05 (1080p).mkv", "windbreaker", "WINDBREAKER_S01E05", 1, 5),
        ]

        for filename, expected_uni, expected_code, expected_s, expected_ep in test_cases:
            info = parse_anime_identity(filename)
            self.assertEqual(info["universe"], expected_uni, f"Failed universe for {filename}")
            self.assertEqual(info["episode_code"], expected_code, f"Failed code for {filename}")
            self.assertEqual(info["season"], expected_s, f"Failed season for {filename}")
            self.assertEqual(info["episode"], expected_ep, f"Failed episode for {filename}")

    def test_02_get_file_universe_dynamic_fallback(self):
        """Verify that get_file_universe detects new anime franchises dynamically."""
        self.assertEqual(get_file_universe("Chainsaw_Man_08.mkv"), "chainsawman")
        self.assertEqual(get_file_universe("Solo_Leveling_11.mkv"), "sololeveling")
        self.assertEqual(get_file_universe("Bleach_TYBW_S02E06.mp4"), "bleach")
        self.assertEqual(get_file_universe("JJK_S02E18.mkv"), "jjk")
        self.assertEqual(get_file_universe("Demon_Slayer_S04E01.mp4"), "demonslayer")

    def test_03_match_episode_code_fallback(self):
        """Verify match_episode_code_from_filename returns canonical codes for new anime."""
        self.assertEqual(match_episode_code_from_filename("Chainsaw Man - 08.mkv"), "CSM_S01E08")
        self.assertEqual(match_episode_code_from_filename("Solo Leveling - 11.mkv"), "SL_S01E11")
        self.assertEqual(match_episode_code_from_filename("Jujutsu Kaisen - S02E18.mkv"), "S02E18")

    def test_04_ensure_character_theme_dynamic_registration(self):
        """Verify unknown characters are registered without throwing exceptions."""
        char_key = "test_custom_hero_99"
        self.assertNotIn(char_key, CHARACTER_THEMES)

        theme = ensure_character_theme(char_key, universe="mycustomanime")
        self.assertIn(char_key, CHARACTER_THEMES)
        self.assertEqual(theme["universe"], "mycustomanime")
        self.assertEqual(theme["name"], "Test Custom Hero 99")
        self.assertIn("colors", theme)
        self.assertIn("cc_preset", theme)

        # Cleanup
        del CHARACTER_THEMES[char_key]

    def test_05_auto_catalog_episode_lifecycle(self):
        """Verify end-to-end auto-cataloging of a mock newly added episode."""
        mock_file = Path("metadata/episodes/temp_test_mock_csm_s01e99.mp4")
        test_ep_code = "CSM_S01E99"
        catalog_json = METADATA_DIR / f"{test_ep_code.lower()}_timestamps.json"

        # Ensure clean state
        if catalog_json.exists():
            catalog_json.unlink()

        self.assertFalse(is_episode_cataloged(test_ep_code))

        try:
            # Trigger auto-cataloging
            meta = auto_catalog_episode(mock_file, forced_code=test_ep_code, lead_character="Denji")

            # 1. Verify JSON file was written
            self.assertTrue(catalog_json.exists())
            self.assertTrue(is_episode_cataloged(test_ep_code))

            # 2. Verify schema compliance
            self.assertEqual(meta["episode_code"], test_ep_code)
            self.assertEqual(meta["universe"], "chainsawman")
            self.assertTrue(len(meta["scenes"]) >= 2)

            # 3. Verify continuous pre-fight conversation exists (>= 30.0s, CALM)
            conv_scenes = [s for s in meta["scenes"] if s.get("is_conversation")]
            self.assertTrue(len(conv_scenes) >= 1)
            self.assertGreaterEqual(conv_scenes[0]["duration"], 30.0)
            self.assertEqual(conv_scenes[0]["action_level"], "CALM")

            # 4. Verify combat climax scene exists (EXPLOSIVE, high priority)
            climax_scenes = [s for s in meta["scenes"] if s.get("action_level") == "EXPLOSIVE"]
            self.assertTrue(len(climax_scenes) >= 1)
            self.assertEqual(climax_scenes[0]["priority"], "high")

            # 5. Verify timestamp_loader immediately discovers this newly cataloged episode
            loaded = load_episode_metadata(test_ep_code)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["episode_code"], test_ep_code)
            self.assertIn(test_ep_code, list_available_episodes())

        finally:
            # Clean up test artifact
            if catalog_json.exists():
                catalog_json.unlink()


if __name__ == "__main__":
    unittest.main()
