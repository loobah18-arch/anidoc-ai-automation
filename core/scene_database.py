"""
Scene Database Query Engine
Queries the JJK timestamp database to find scenes matching a given title/keywords.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set


class SceneDatabaseQuery:
    """Query engine for the JJK timestamp database."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "jjk_timestamp_database.json"

        self.db_path = db_path
        self.database = self._load_database()

    def _load_database(self) -> Dict[str, Any]:
        """Load the timestamp database."""
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Timestamp database not found at {self.db_path}. "
                f"Run 'python scripts/build_timestamp_database.py' first or trigger the "
                f"'Build JJK Timestamp Database' workflow."
            )

        with open(self.db_path, "r") as f:
            return json.load(f)

    def extract_keywords(self, title: str) -> Set[str]:
        """
        Extract meaningful keywords from a title.
        Removes common words and extracts character names, techniques, themes.
        """
        # Common stop words to ignore
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "through", "during",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "could", "should", "may", "might",
            "must", "can", "vs", "vs.", "jjk", "shorts", "short", "edit", "amv", "4k"
        }

        # Remove hashtags, emojis, and special chars
        clean_title = re.sub(r'[#️⚡🔥💀⚔️✨💥🌟👑]', '', title.lower())
        clean_title = re.sub(r'[^\w\s]', ' ', clean_title)

        # Extract words
        words = clean_title.split()

        # Filter out stop words and short words
        keywords = {w for w in words if len(w) > 2 and w not in stop_words}

        return keywords

    def score_scene(self, scene: Dict[str, Any], keywords: Set[str],
                    preferred_intensity: str = "action") -> float:
        """
        Score a scene based on keyword match and preferred intensity.
        Returns score 0-100.
        """
        score = 0.0

        # Base score from scene type match
        scene_type = scene.get("scene_type", "ambient")
        intensity_scores = {
            "intense_action": {"intense_action": 50, "action": 30, "dialogue": 10, "ambient": 5},
            "action": {"intense_action": 40, "action": 50, "dialogue": 20, "ambient": 10},
            "dialogue": {"intense_action": 10, "action": 20, "dialogue": 50, "ambient": 30},
            "ambient": {"intense_action": 5, "action": 10, "dialogue": 30, "ambient": 50}
        }
        score += intensity_scores.get(preferred_intensity, {}).get(scene_type, 0)

        # Audio intensity bonus (0-30 points)
        audio_intensity = scene.get("audio", {}).get("intensity", 0)
        score += audio_intensity * 3

        # Duration bonus (prefer scenes 3-8 seconds)
        duration = scene.get("duration", 0)
        if 3.0 <= duration <= 8.0:
            score += 10
        elif 2.0 <= duration <= 10.0:
            score += 5

        return score

    def query_scenes(
        self,
        title: str,
        n_scenes: int = 15,
        preferred_type: str = "action",
        min_intensity: float = 3.0,
        diversity_factor: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Query database for scenes matching the title.

        Args:
            title: Video title to match against
            n_scenes: Number of scenes to return
            preferred_type: Preferred scene type (intense_action, action, dialogue, ambient)
            min_intensity: Minimum audio intensity (0-10)
            diversity_factor: 0-1, how much to spread scenes across episodes (1=max diversity)

        Returns:
            List of scene dictionaries with file_path, timestamp, duration, etc.
        """
        keywords = self.extract_keywords(title)
        print(f"🔍 [SceneQuery] Title: {title}")
        print(f"🔍 [SceneQuery] Keywords: {', '.join(sorted(keywords))}")

        # Collect all scenes from all episodes
        all_scenes = []
        for episode_key, episode_data in self.database.get("episodes", {}).items():
            for scene in episode_data.get("scenes", []):
                # Filter by minimum intensity
                if scene.get("audio", {}).get("intensity", 0) < min_intensity:
                    continue

                # Calculate match score
                score = self.score_scene(scene, keywords, preferred_type)

                # Add episode context
                scene_with_context = {
                    **scene,
                    "episode_key": episode_key,
                    "file_path": episode_data.get("file_path"),
                    "file_name": episode_data.get("file_name"),
                    "season": episode_data.get("season"),
                    "episode": episode_data.get("episode"),
                    "match_score": score
                }
                all_scenes.append(scene_with_context)

        # Sort by score
        all_scenes.sort(key=lambda x: x["match_score"], reverse=True)

        print(f"📊 [SceneQuery] Found {len(all_scenes)} candidate scenes (after intensity filter)")

        if not all_scenes:
            raise RuntimeError(
                f"No scenes found matching criteria. "
                f"Title: '{title}', min_intensity: {min_intensity}, type: {preferred_type}"
            )

        # Select scenes with diversity
        selected_scenes = []
        used_episodes = set()
        remaining_scenes = all_scenes.copy()

        # First pass: spread across different episodes
        for scene in remaining_scenes[:]:
            if len(selected_scenes) >= n_scenes:
                break

            episode_key = scene["episode_key"]

            # If we want diversity, skip if we already used this episode too much
            episode_usage = sum(1 for s in selected_scenes if s["episode_key"] == episode_key)
            max_per_episode = max(1, int(n_scenes * (1 - diversity_factor) + 1))

            if episode_usage >= max_per_episode:
                continue

            selected_scenes.append(scene)
            used_episodes.add(episode_key)
            remaining_scenes.remove(scene)

        # Second pass: fill remaining slots with best-scoring scenes
        while len(selected_scenes) < n_scenes and remaining_scenes:
            selected_scenes.append(remaining_scenes.pop(0))

        # Sort selected scenes by timestamp for smooth narrative flow
        selected_scenes.sort(key=lambda x: (x["season"], x["episode"], x["timestamp"]))

        print(f"✅ [SceneQuery] Selected {len(selected_scenes)} scenes from {len(used_episodes)} episodes")
        print(f"📊 [SceneQuery] Score range: {selected_scenes[-1]['match_score']:.1f} - {selected_scenes[0]['match_score']:.1f}")

        return selected_scenes

    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the database."""
        total_episodes = self.database.get("total_episodes", 0)
        total_scenes = self.database.get("total_scenes", 0)

        scene_types = {"intense_action": 0, "action": 0, "dialogue": 0, "ambient": 0}
        for episode_data in self.database.get("episodes", {}).values():
            for scene in episode_data.get("scenes", []):
                scene_type = scene.get("scene_type", "ambient")
                scene_types[scene_type] = scene_types.get(scene_type, 0) + 1

        return {
            "total_episodes": total_episodes,
            "total_scenes": total_scenes,
            "scenes_by_type": scene_types,
            "generated_at": self.database.get("generated_at")
        }
