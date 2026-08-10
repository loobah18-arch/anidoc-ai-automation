"""
State 3: 2D Semi-Realistic Batch Image Prompt Generator
Generates standalone 16:9 illustration prompts in batches of 20 according to AniDoc Visual DNA.
"""

from typing import List
import re
from generators.llm_provider import LLMProvider
from prompts.system_prompt import MASTER_SYSTEM_PROMPT, STATE3_IMAGE_PROMPTS_PROMPT

class ImagePromptGenerator:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or LLMProvider()

    def generate_prompts(self, script: str, batch_count: int = 1) -> str:
        """Generates structured batch image prompts."""
        prompt = STATE3_IMAGE_PROMPTS_PROMPT.format(
            script=script[:6000],
            total_batches=batch_count
        )
        return self.llm.generate(prompt=prompt, system_prompt=MASTER_SYSTEM_PROMPT, temperature=0.6, max_tokens=4000)

    def extract_prompt_list(self, raw_output: str) -> List[str]:
        """Parses individual image prompts from raw LLM code blocks."""
        # Find numbered prompts (e.g. "1. A dark 1970s Mumbai chawl...")
        prompts = []
        pattern = r'(?:^\d+[\.\)]\s+)(.+?)(?=(?:^\d+[\.\)]|\Z))'
        matches = re.findall(pattern, raw_output, flags=re.MULTILINE | re.DOTALL)
        for m in matches:
            clean = " ".join(m.strip().split())
            if len(clean) > 20:
                prompts.append(clean)
        return prompts if prompts else [raw_output.strip()]

if __name__ == "__main__":
    gen = ImagePromptGenerator()
    sample = "1971 ki sard raat. Rawalpindi jail ki kaal kothri mein 3 Bhartiya pilots band the."
    print(gen.generate_prompts(sample))
