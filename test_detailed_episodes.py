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

    def test_06_universe_quarantine_in_gdrive_selection(self):
        """Guarantee JJK characters NEVER receive Demon Slayer files, and vice versa."""
        from core.gdrive_manager import get_file_universe

        ds_only_files = [
            {"name": "Demon_Slayer_Kimetsu_no_Yaiba_480P_S01_E24.mp4", "id": "fid_ds_24"},
            {"name": "Kimetsu_no_Yaiba_S01E19_Hinokami.mkv", "id": "fid_ds_19"},
            {"name": "Demon_Slayer_Mugen_Train_Ep_07.mkv", "id": "fid_ds_07"},
        ]

        # JJK characters requested when only Demon Slayer files exist MUST return None
        for jjk_char in ["yuji", "gojo", "sukuna", "toji", "megumi"]:
            chosen = pick_best_file_for_character(ds_only_files, jjk_char)
            self.assertIsNone(chosen, f"JJK character '{jjk_char}' must NOT receive Demon Slayer files")

        jjk_only_files = [
            {"name": "Jujutsu_Kaisen_S01_E24.mp4", "id": "fid_jjk_24"},
            {"name": "JJK_S02E17_Sukuna_Mahoraga.mp4", "id": "fid_jjk_17"},
            {"name": "Jujutsu_Kaisen_S02E09_Gojo_Shibuya.mkv", "id": "fid_jjk_09"},
        ]

        # Demon Slayer characters requested when only JJK files exist MUST return None
        for ds_char in ["tanjiro", "rengoku", "zenitsu", "inosuke", "muzan", "nezuko"]:
            chosen = pick_best_file_for_character(jjk_only_files, ds_char)
            self.assertIsNone(chosen, f"Demon Slayer character '{ds_char}' must NOT receive JJK files")

    def test_07_metadata_universe_isolation_and_accurate_descriptions(self):
        """Verify titles, tags, and rich descriptions are 100% accurate and isolated."""
        from core.quote_ai import generate_edit_metadata, JJK_KEYWORDS, DEMONSLAYER_KEYWORDS

        ds_chars = ["tanjiro", "rengoku", "zenitsu", "akaza", "giyu", "tengen", "inosuke", "muzan", "nezuko", "muichiro", "gyutaro"]
        for char in ds_chars:
            meta = generate_edit_metadata(char)
            self.assertEqual(meta["universe"], "demonslayer")
            self.assertIn("Demon Slayer: Kimetsu no Yaiba (鬼滅の刃)", meta["description"])
            self.assertIn(meta["character_name"], meta["description"])
            self.assertIn(meta["title"], meta["description"])
            self.assertIn(meta["quote"], meta["description"])

            # Verify no JJK terms in tags, title, or description
            full_text = f"{meta['title']} {' '.join(meta['tags'])} {meta['description']}".lower()
            for jjk_word in ["jjk", "jujutsu", "gojo", "sukuna", "itadori", "blackflash"]:
                self.assertNotIn(jjk_word, meta["tags"], f"Demon Slayer '{char}' must not have tag '{jjk_word}'")
                self.assertNotIn(jjk_word, meta["title"].lower(), f"Demon Slayer '{char}' must not have title term '{jjk_word}'")

        jjk_chars = ["gojo", "sukuna", "toji", "yuji", "megumi", "mahito", "todo", "nobara"]
        for char in jjk_chars:
            meta = generate_edit_metadata(char)
            self.assertEqual(meta["universe"], "jjk")
            self.assertIn("Jujutsu Kaisen (呪術廻戦)", meta["description"])
            self.assertIn(meta["character_name"], meta["description"])
            self.assertIn(meta["title"], meta["description"])
            self.assertIn(meta["quote"], meta["description"])

            # Verify no Demon Slayer terms in tags, title, or description
            for ds_word in ["demonslayer", "kimetsunoyaiba", "tanjiro", "rengoku", "zenitsu", "hashira"]:
                self.assertNotIn(ds_word, meta["tags"], f"JJK '{char}' must not have tag '{ds_word}'")
                self.assertNotIn(ds_word, meta["title"].lower(), f"JJK '{char}' must not have title term '{ds_word}'")

    def test_08_filename_matching_and_universe_detection(self):
        """Verify filenames never fall through across universes."""
        from core.gdrive_manager import get_file_universe

        ds_fn = "Demon_Slayer_Kimetsu_no_Yaiba_480P_S01_E24.mp4"
        self.assertEqual(get_file_universe(ds_fn), "demonslayer")
        # Must return DS_S01E24, and NOT S01E24
        code = match_episode_code_from_filename(ds_fn)
        self.assertEqual(code, "DS_S01E24")
        self.assertNotEqual(code, "S01E24")

        jjk_fn = "Jujutsu_Kaisen_480P_S01_E24.mp4"
        self.assertEqual(get_file_universe(jjk_fn), "jjk")
        code_jjk = match_episode_code_from_filename(jjk_fn)
        self.assertEqual(code_jjk, "S01E24")

    def test_09_universal_scene_selector_and_canonical_combat_bounds(self):
        """Verify universal production scene selector bounds and bystander/aftermath rejection."""
        from core.gdrive_manager import get_episode_phase_boundaries

        # 1. Demon Slayer S02E07 (Rengoku climax): Pure combat [480.0, 876.0] strictly ending before impalement/crying
        bounds_s02e07 = get_episode_phase_boundaries("DS_S02E07", "rengoku", 1440.0)
        self.assertEqual(bounds_s02e07["combat_window"], (480.0, 876.0))
        self.assertIsNone(bounds_s02e07["conv_window"])
        combat_st_07 = [s["start"] for s in bounds_s02e07["curated_combat_scenes"]]
        # Ground truth audits: strictly reject 273s Inosuke tear, 1000s sunrise, 1140s crow/Obanai, 1234s credits, 1266s Giyu, 1398s Tanjiro
        self.assertNotIn(273.0, combat_st_07, "Inosuke weeping boar mask at 273s must be excluded")
        self.assertNotIn(1000.0, combat_st_07, "Sunrise monologue at 1000s must be excluded")
        self.assertNotIn(1140.0, combat_st_07, "Obanai daytime crow at 1140s must be excluded")
        self.assertNotIn(1234.0, combat_st_07, "Anime end credits at 1234s must be excluded")
        self.assertNotIn(1266.0, combat_st_07, "Giyu mourning at 1266s must be excluded")
        self.assertNotIn(1398.0, combat_st_07, "Tanjiro weeping at 1398s must be excluded")

        # 2. Demon Slayer S02E06 (Rengoku vs Akaza setup): Dialogue [752.0, 886.5] & Combat [886.5, 1245.0]
        bounds_s02e06 = get_episode_phase_boundaries("DS_S02E06", "rengoku", 1420.0)
        self.assertEqual(bounds_s02e06["conv_window"], (752.0, 886.5))
        self.assertEqual(bounds_s02e06["combat_window"], (886.5, 1245.0))
        self.assertTrue(all(s["start"] >= 886.5 for s in bounds_s02e06["curated_combat_scenes"]))
        self.assertTrue(all(s["start"] < 886.5 for s in bounds_s02e06["curated_conv_scenes"]))

        # 3. JJK S02E17 (Sukuna vs Mahoraga): Combat [120.0, 1080.0], Yuji crying in ruins excluded
        bounds_s02e17 = get_episode_phase_boundaries("S02E17", "sukuna", 1440.0)
        self.assertEqual(bounds_s02e17["combat_window"], (120.0, 1080.0))
        combat_st_jjk = [s["start"] for s in bounds_s02e17["curated_combat_scenes"]]
        self.assertNotIn(1080.0, combat_st_jjk, "Yuji crying in Shibuya ruins (1080s) must be excluded from Sukuna combat")

        # 4. Demon Slayer S01E17 (Zenitsu Thunderclap): Combat [480.0, 1200.0]
        bounds_s01e17 = get_episode_phase_boundaries("DS_S01E17", "zenitsu", 1440.0)
        self.assertEqual(bounds_s01e17["combat_window"], (480.0, 1200.0))
        combat_st_zen = [s["start"] for s in bounds_s01e17["curated_combat_scenes"]]
        self.assertNotIn(120.0, combat_st_zen, "Running through forest at 120s must be excluded from combat")
        self.assertNotIn(780.0, combat_st_zen, "Gramps flashback at 780s must be excluded from combat")

if __name__ == "__main__":
    unittest.main()

