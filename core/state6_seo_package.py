"""
State 6: YouTube Growth & SEO Package Generator
Generates 5 Title options, 200-word keyword-rich Description, 15 viral hashtags, and 30 YouTube tags.
"""

from generators.llm_provider import LLMProvider
from prompts.system_prompt import MASTER_SYSTEM_PROMPT, STATE6_SEO_PROMPT

class SEOPackageGenerator:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or LLMProvider()

    def generate_seo(self, topic: str, script_summary: str, language: str = "Hindi") -> str:
        """Generates complete YouTube SEO package."""
        prompt = STATE6_SEO_PROMPT.format(
            topic=topic,
            script_summary=script_summary[:2000],
            language=language
        )
        return self.llm.generate(prompt=prompt, system_prompt=MASTER_SYSTEM_PROMPT, temperature=0.7, max_tokens=2500)

if __name__ == "__main__":
    gen = SEOPackageGenerator()
    print(gen.generate_seo("Indira Gandhi 1984 Secrets", "Historical breakdown of the events leading up to 1984."))
