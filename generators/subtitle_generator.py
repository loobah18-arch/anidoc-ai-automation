"""
Subtitle Generator Module for 2D Documentary Videos
Generates high-retention .srt and styled .ass subtitles for Devanagari & English.
"""

import re
from pathlib import Path
from typing import List

class SubtitleGenerator:
    def __init__(self, font_name="Arial", font_size=24, primary_color="&H00FFFFFF", highlight_color="&H0000FFFF"):
        self.font_name = font_name
        self.font_size = font_size
        self.primary_color = primary_color
        self.highlight_color = highlight_color

    def create_subtitles(self, script_text: str, total_duration_sec: float, output_srt: str, output_ass: str = None):
        """Generates synchronized SRT and ASS subtitle files based on sentence pacing."""
        output_srt = Path(output_srt)
        output_srt.parent.mkdir(exist_ok=True, parents=True)
        
        # Clean and split into sentences
        clean_text = re.sub(r'\[.*?\]', '', script_text)
        # Split by Hindi Purna Viram (| or ।), periods, or question marks
        raw_sentences = re.split(r'[।\.\?\!\n]+', clean_text)
        sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 3]
        
        if not sentences:
            sentences = [clean_text]

        # Calculate word counts and proportional timestamps
        total_words = sum(len(s.split()) for s in sentences) or 1
        time_per_word = total_duration_sec / total_words

        srt_entries = []
        ass_events = []
        current_time = 0.0

        for idx, sentence in enumerate(sentences):
            words_in_sent = len(sentence.split())
            sent_duration = max(1.5, words_in_sent * time_per_word)
            start_time = current_time
            end_time = min(total_duration_sec, current_time + sent_duration)
            current_time = end_time

            # Format SRT timestamp
            srt_start = self._format_srt_time(start_time)
            srt_end = self._format_srt_time(end_time)
            srt_entries.append(f"{idx+1}\n{srt_start} --> {srt_end}\n{sentence}\n")

            # Format ASS event
            ass_start = self._format_ass_time(start_time)
            ass_end = self._format_ass_time(end_time)
            ass_events.append(f"Dialogue: 0,{ass_start},{ass_end},Default,,0,0,0,,{sentence}")

        with open(output_srt, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_entries))

        if output_ass:
            output_ass = Path(output_ass)
            ass_content = self._build_ass_file(ass_events)
            with open(output_ass, "w", encoding="utf-8") as f:
                f.write(ass_content)

        return str(output_srt)

    def _format_srt_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _format_ass_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"

    def _build_ass_file(self, events: List[str]) -> str:
        header = f"""[Script Info]
Title: AniDoc 2D Documentary Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.font_name},{self.font_size},{self.primary_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,60,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        return header + "\n".join(events)
