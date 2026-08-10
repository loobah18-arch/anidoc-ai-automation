"""
Topic Rotation & History Manager
Selects next fresh documentary topic, avoids duplicates, and updates state.
"""

import json
from pathlib import Path
from config import settings
from core.state1_topics import TopicGenerator

class TopicManager:
    def __init__(self):
        self.catalog_file = settings.CONFIG_DIR / "catalog.json"
        self.history_file = settings.BASE_DIR / "documentary_history.json"
        self.state_file = settings.BASE_DIR / "channel_state.json"

    def get_history(self) -> list:
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def get_next_topic(self, custom_topic: str = None, language: str = "Hindi") -> dict:
        """Returns the next topic to produce."""
        if custom_topic:
            return {
                "id": "custom_" + str(int(Path(settings.BASE_DIR).stat().st_mtime)),
                "topic": custom_topic,
                "language": language
            }

        # Load catalog
        catalog = []
        if self.catalog_file.exists():
            with open(self.catalog_file, "r", encoding="utf-8") as f:
                catalog = json.load(f).get("catalog", [])

        # Load history
        history_topics = [h.get("topic_name", "") for h in self.get_history()]

        # Find unproduced catalog items
        for item in catalog:
            if item["topic"] not in history_topics:
                return item

        # If all catalog items produced, generate fresh from LLM
        print("Catalog exhausted or dynamic rotation active: Generating fresh topic via LLM...")
        gen = TopicGenerator()
        topics_text = gen.generate_topics(language)
        
        # Take first line that looks like a topic
        import re
        lines = [line.strip() for line in topics_text.split("\n") if re.match(r'^\d+[\.\)]', line.strip())]
        selected_text = lines[0] if lines else "RAW Covert Mission: The Untold 1971 Espionage Operation"
        # Clean leading numbers
        clean_topic = re.sub(r'^\d+[\.\)]\s*', '', selected_text)
        
        return {
            "id": f"dynamic_{len(history_topics)+1}",
            "topic": clean_topic,
            "language": language
        }
