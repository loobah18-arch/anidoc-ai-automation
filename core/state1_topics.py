"""
State 1: Viral Topic Selection Engine
Generates 10 high-potential documentary topics strictly classified across 5 categories.
"""

from generators.llm_provider import LLMProvider
from prompts.system_prompt import MASTER_SYSTEM_PROMPT, STATE1_TOPICS_PROMPT

class TopicGenerator:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or LLMProvider()

    def generate_topics(self, language: str = "Hindi") -> str:
        """Generates 10 categorized documentary topics."""
        prompt = STATE1_TOPICS_PROMPT.format(language=language)
        return self.llm.generate(prompt=prompt, system_prompt=MASTER_SYSTEM_PROMPT, temperature=0.75)

if __name__ == "__main__":
    gen = TopicGenerator()
    print(gen.generate_topics())
