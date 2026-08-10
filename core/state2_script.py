"""
State 2: Style DNA Analysis & Deep Cinematic Scriptwriting
Generates full 3,000-4,500 word Hindi / English voiceover-ready scripts with tension peaks.
"""

from generators.llm_provider import LLMProvider
from prompts.system_prompt import MASTER_SYSTEM_PROMPT, STATE2_SCRIPT_PROMPT

class ScriptWriter:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or LLMProvider()

    def generate_script(self, topic: str, language: str = "Hindi", target_length: str = "Full Depth (3,000-4,500 words)") -> str:
        """Generates the Style DNA table and full continuous voiceover script."""
        prompt = STATE2_SCRIPT_PROMPT.format(
            topic=topic,
            language=language,
            target_length=target_length
        )
        return self.llm.generate(prompt=prompt, system_prompt=MASTER_SYSTEM_PROMPT, temperature=0.7, max_tokens=4000)

if __name__ == "__main__":
    writer = ScriptWriter()
    print(writer.generate_script("The 1971 PAF Prison Escape by 3 Indian Pilots"))
