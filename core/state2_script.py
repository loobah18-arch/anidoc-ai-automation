"""
State 2: Style DNA Analysis & Deep Cinematic Scriptwriting
Generates full voiceover-ready scripts and extracts pure clean narrative prose for TTS.
"""

import re
from typing import Tuple
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

    def extract_pure_voiceover(self, raw_output: str) -> str:
        """
        Strips all metadata, Style DNA tables, estimated word counts, section headers,
        and bracketed markers (like [TENSION PEAK], [SCENE 1], [MUSIC]) to leave 100% pure
        narration prose for TTS voiceover synthesis.
        """
        text = raw_output

        # 1. If explicit delimiter exists
        if "=== START VOICEOVER SCRIPT ===" in text:
            text = text.split("=== START VOICEOVER SCRIPT ===")[-1]
        if "=== END VOICEOVER SCRIPT ===" in text:
            text = text.split("=== END VOICEOVER SCRIPT ===")[0]

        # 2. Strip Style DNA table if delimiter wasn't found
        if "ESTIMATED WORDS:" in text or "ESTIMATED WORDS" in text:
            parts = re.split(r'ESTIMATED WORDS.*?\n', text, flags=re.IGNORECASE | re.DOTALL)
            if len(parts) > 1:
                text = parts[-1]

        # Strip any remaining bullet metadata lines like "- NICHE:", "- TARGET AUDIENCE:", "- HOOK TYPE:"
        lines = []
        for line in text.split("\n"):
            l = line.strip()
            # Ignore metadata bullet lines
            if re.match(r'^(?:[-*•]\s*)?(?:NICHE|TARGET AUDIENCE|HOOK TYPE|SCRIPT FLOW|TONE|ESTIMATED WORDS|WORD COUNT|DURATION|FINAL WORD COUNT)\s*:', l, flags=re.IGNORECASE):
                continue
            if l.startswith("Final Word Count") or l.startswith("Estimated Duration") or "WPM" in l:
                continue
            lines.append(line)

        clean_text = "\n".join(lines).strip()

        # 3. Strip bracketed markers: [TENSION PEAK], [HOOK], [MUSIC], [SFX], [SCENE 1]
        clean_text = re.sub(r'\[(?:TENSION PEAK|HOOK|SCENE\s*\d+|MUSIC|SFX|PAUSE|AUDIO|PROMPT\s*\d+)\]', '', clean_text, flags=re.IGNORECASE)

        # 4. Remove markdown bold/header symbols # and *
        clean_text = re.sub(r'[\*#_`]', '', clean_text)
        
        # Clean double blank lines
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text).strip()

        return clean_text if clean_text else raw_output.strip()

if __name__ == "__main__":
    writer = ScriptWriter()
    test_raw = """
    - NICHE: True Crime
    - TARGET AUDIENCE: 18-45
    ESTIMATED WORDS: 3200
    
    17 December 1971 ki wo aitihasik raat thi. [TENSION PEAK] RAW ke gupt agents ne Rawalpindi jail me dakhila liya.
    """
    print(writer.extract_pure_voiceover(test_raw))
