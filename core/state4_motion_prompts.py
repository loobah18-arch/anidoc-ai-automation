"""
State 4: Video Motion & Camera Dynamics Prompt Generator
Generates subtle camera movements (slow push-in, pan, particles) for Google Veo 3 / Kling AI / Flow AI.
"""

from generators.llm_provider import LLMProvider
from prompts.system_prompt import MASTER_SYSTEM_PROMPT, STATE4_MOTION_PROMPTS_PROMPT

class MotionPromptGenerator:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or LLMProvider()

    def generate_motion_prompts(self, image_prompts: str) -> str:
        """Generates video motion prompts corresponding to image prompts."""
        prompt = STATE4_MOTION_PROMPTS_PROMPT.format(image_prompts=image_prompts[:5000])
        return self.llm.generate(prompt=prompt, system_prompt=MASTER_SYSTEM_PROMPT, temperature=0.6, max_tokens=3000)

if __name__ == "__main__":
    gen = MotionPromptGenerator()
    print(gen.generate_motion_prompts("1. A dark 1970s Mumbai chawl street at night..."))
