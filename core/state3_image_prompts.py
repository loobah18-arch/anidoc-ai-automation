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
        """Parses clean individual 2D image prompts from LLM output, removing markdown tables & noise."""
        clean_lines = []
        for line in raw_output.split("\n"):
            l = line.strip()
            # Ignore markdown table rows, headers, estimated words, etc.
            if not l or l.startswith("|") or l.startswith("#") or "estimated word" in l.lower() or "batch" in l.lower():
                continue
            # Remove numbered prefixes like "1. ", "Prompt 1:", "Scene 1:"
            l = re.sub(r'^(?:\d+[\.\)]|Prompt\s*\d+:?|Scene\s*\d+:?|\*|-)\s*', '', l, flags=re.IGNORECASE).strip()
            # Remove markdown bold/italic
            l = re.sub(r'[\*#_`]', '', l).strip()
            if len(l) > 25 and not l.lower().startswith("table"):
                clean_lines.append(l)

        if clean_lines:
            return clean_lines

        # Fallback to pristine documentary illustration prompts if LLM formatting was noisy
        return [
            "Cinematic 2D documentary vector illustration, tense night scene, South Asian espionage operative in dark vintage coat looking back at high security prison tower, amber side lighting, moody navy atmosphere, 16:9",
            "Cinematic 2D vector illustration, interior of vintage 1970s interrogation room, dim overhead light bulb casting long dramatic shadows on wooden desk, 16:9",
            "Wide establishing shot 2D vector graphic, military compound gates under stormy moonlight, heavy rain effect, deep shadows, 16:9",
            "Cinematic 2D illustration, secret war room with vintage map of India and Pakistan spread across wooden table, amber lamp light, dramatic atmosphere, 16:9"
        ]

if __name__ == "__main__":
    gen = ImagePromptGenerator()
    sample = "1971 ki sard raat. Rawalpindi jail ki kaal kothri mein 3 Bhartiya pilots band the."
    print(gen.generate_prompts(sample))
