"""
State 5: High-CTR 2D Thumbnail Concepts & Prompts Engine
Generates 5 viral thumbnail concepts with Devanagari titles, split composition, and 2D ANIMATION badge.
"""

from generators.llm_provider import LLMProvider
from prompts.system_prompt import MASTER_SYSTEM_PROMPT, STATE5_THUMBNAIL_PROMPT

class ThumbnailConceptGenerator:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or LLMProvider()

    def generate_concepts(self, topic: str, script_summary: str) -> str:
        """Generates 5 high-CTR thumbnail concepts."""
        prompt = STATE5_THUMBNAIL_PROMPT.format(
            topic=topic,
            script_summary=script_summary[:2000]
        )
        return self.llm.generate(prompt=prompt, system_prompt=MASTER_SYSTEM_PROMPT, temperature=0.7, max_tokens=3000)

if __name__ == "__main__":
    gen = ThumbnailConceptGenerator()
    print(gen.generate_concepts("Operation Sindoor", "Covert cross-border intelligence extraction mission."))
