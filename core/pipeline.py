"""
Master 6-State Pipeline Orchestrator for AniDoc AI Automation
Manages state progression, media rendering, and end-to-end documentary production.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any

from config import settings
from generators.llm_provider import LLMProvider
from generators.voiceover_generator import VoiceoverGenerator
from generators.image_generator import ImageGenerator
from generators.motion_generator import MotionGenerator
from generators.subtitle_generator import SubtitleGenerator
from renderers.video_assembler import VideoAssembler
from renderers.thumbnail_designer import ThumbnailDesigner

from core.state1_topics import TopicGenerator
from core.state2_script import ScriptWriter
from core.state3_image_prompts import ImagePromptGenerator
from core.state4_motion_prompts import MotionPromptGenerator
from core.state5_thumbnails import ThumbnailConceptGenerator
from core.state6_seo_package import SEOPackageGenerator

class AniDocPipeline:
    def __init__(self, project_name: str = None, language: str = "Hindi", llm_provider: str = None):
        self.timestamp = int(time.time())
        self.project_name = project_name or f"doc_{self.timestamp}"
        self.language = language
        
        # Project output directory
        self.project_dir = settings.OUTPUT_DIR / self.project_name
        self.project_dir.mkdir(exist_ok=True, parents=True)
        
        # Subdirectories
        self.images_dir = self.project_dir / "images"
        self.clips_dir = self.project_dir / "clips"
        self.audio_dir = self.project_dir / "audio"
        self.subs_dir = self.project_dir / "subtitles"
        
        for d in [self.images_dir, self.clips_dir, self.audio_dir, self.subs_dir]:
            d.mkdir(exist_ok=True, parents=True)

        # Initialize engines
        self.llm = LLMProvider(provider=llm_provider)
        self.topic_gen = TopicGenerator(self.llm)
        self.script_writer = ScriptWriter(self.llm)
        self.img_prompt_gen = ImagePromptGenerator(self.llm)
        self.motion_prompt_gen = MotionPromptGenerator(self.llm)
        self.thumb_concept_gen = ThumbnailConceptGenerator(self.llm)
        self.seo_gen = SEOPackageGenerator(self.llm)
        
        self.voice_gen = VoiceoverGenerator()
        self.image_gen = ImageGenerator()
        self.motion_gen = MotionGenerator()
        self.sub_gen = SubtitleGenerator()
        self.video_assembler = VideoAssembler()
        self.thumb_designer = ThumbnailDesigner()

        # State storage
        self.data: Dict[str, Any] = {
            "project_name": self.project_name,
            "language": self.language,
            "created_at": self.timestamp
        }

    def run_state1_topics(self) -> str:
        """State 1: Generate 10 viral topic ideas."""
        print("\n=======================================================")
        print("  [STATE 1] Generating 10 Viral Documentary Topics...")
        print("=======================================================")
        topics = self.topic_gen.generate_topics(self.language)
        self.data["topics"] = topics
        self._save_text("01_topics.txt", topics)
        return topics

    def run_state2_script(self, chosen_topic: str, target_length: str = "Standard Documentary (2,000-3,500 words)") -> str:
        """State 2: Generate Style DNA & Full Clean Voiceover Script."""
        print("\n=======================================================")
        print(f"  [STATE 2] Writing Deep Cinematic Script for: '{chosen_topic}'...")
        print("=======================================================")
        self.data["chosen_topic"] = chosen_topic
        script_output = self.script_writer.generate_script(chosen_topic, self.language, target_length)
        self.data["script_full_output"] = script_output
        self._save_text("02_script_full.txt", script_output)
        
        # Extract pure voiceover prose (strip style table headers if present)
        clean_prose = script_output
        if "Final Word Count" in script_output:
            clean_prose = script_output.split("Final Word Count")[0]
        if "Script generate kar raha hoon..." in clean_prose:
            clean_prose = clean_prose.split("Script generate kar raha hoon...")[-1]
            
        self.data["script_prose"] = clean_prose.strip()
        self._save_text("02_voiceover_script.txt", self.data["script_prose"])
        return script_output

    def run_state3_image_prompts(self, batch_count: int = 1) -> str:
        """State 3: Generate 2D Semi-Realistic Batch Image Prompts."""
        print("\n=======================================================")
        print("  [STATE 3] Generating AniDoc 2D Batch Image Prompts...")
        print("=======================================================")
        script = self.data.get("script_prose") or self.data.get("script_full_output", "")
        prompts_raw = self.img_prompt_gen.generate_prompts(script, batch_count)
        self.data["image_prompts_raw"] = prompts_raw
        self._save_text("03_image_prompts.txt", prompts_raw)
        
        prompt_list = self.img_prompt_gen.extract_prompt_list(prompts_raw)
        self.data["image_prompts_list"] = prompt_list
        return prompts_raw

    def run_state4_motion_prompts(self) -> str:
        """State 4: Generate Video Motion Prompts."""
        print("\n=======================================================")
        print("  [STATE 4] Generating Video Motion Prompts...")
        print("=======================================================")
        img_prompts = self.data.get("image_prompts_raw", "")
        motion_output = self.motion_prompt_gen.generate_motion_prompts(img_prompts)
        self.data["motion_prompts"] = motion_output
        self._save_text("04_motion_prompts.txt", motion_output)
        return motion_output

    def run_state5_thumbnails(self) -> str:
        """State 5: Generate 5 High-CTR Thumbnail Concepts."""
        print("\n=======================================================")
        print("  [STATE 5] Generating High-CTR Thumbnail Concepts...")
        print("=======================================================")
        topic = self.data.get("chosen_topic", "Untold Documentary")
        script = self.data.get("script_prose", "")[:1000]
        thumb_output = self.thumb_concept_gen.generate_concepts(topic, script)
        self.data["thumbnail_concepts"] = thumb_output
        self._save_text("05_thumbnail_concepts.txt", thumb_output)
        return thumb_output

    def run_state6_seo(self) -> str:
        """State 6: Generate YouTube SEO Package."""
        print("\n=======================================================")
        print("  [STATE 6] Generating Complete YouTube SEO Package...")
        print("=======================================================")
        topic = self.data.get("chosen_topic", "Untold Documentary")
        script = self.data.get("script_prose", "")[:1000]
        seo_output = self.seo_gen.generate_seo(topic, script, self.language)
        self.data["seo_package"] = seo_output
        self._save_text("06_seo_package.txt", seo_output)
        return seo_output

    def render_complete_media(self, max_images: int = 6) -> Dict[str, str]:
        """
        Synthesizes Voiceover, Generates Images, Animates Motion, Burns Subtitles,
        and Renders Final 1080p Video and Viral Thumbnail.
        """
        print("\n=======================================================")
        print("  [MEDIA RENDERING ENGINE] Building Final Documentary Assets...")
        print("=======================================================")
        
        # 1. Voiceover
        audio_file = self.audio_dir / "voiceover.mp3"
        script_text = self.data.get("script_prose") or self.data.get("chosen_topic", "Documentary voiceover")
        print(f"Step 1: Synthesizing voiceover audio ({self.language})...")
        self.voice_gen.generate(script_text[:1200], str(audio_file), self.language)
        audio_duration = self.video_assembler.get_media_duration(str(audio_file))
        print(f"  Voiceover generated: {audio_file} (Duration: {audio_duration:.1f}s)")

        # 2. Image Generation
        prompts = self.data.get("image_prompts_list", [])[:max_images]
        if not prompts:
            prompts = [
                f"Cinematic 2D illustration of {self.data.get('chosen_topic', 'investigative documentary')}, warm muted tones, dramatic side lighting, 16:9",
                "A tense secret meeting room at night, South Asian officials in vintage attire, amber lamp light, 16:9",
                "Wide establishing shot of historic parliament building under moody stormy sky, 16:9"
            ]
        print(f"Step 2: Generating {len(prompts)} 2D illustrated frames via Flux...")
        img_paths = self.image_gen.generate_batch(prompts, str(self.images_dir))

        # 3. Motion Animation
        print("Step 3: Animating frames with Ken Burns camera moves...")
        clip_duration = max(4.0, audio_duration / max(1, len(img_paths)))
        clip_paths = self.motion_gen.animate_batch(img_paths, str(self.clips_dir), duration_per_image=clip_duration)

        # 4. Synchronized Subtitles
        print("Step 4: Generating synchronized Devanagari / English subtitles...")
        srt_file = self.subs_dir / "captions.srt"
        ass_file = self.subs_dir / "captions.ass"
        self.sub_gen.create_subtitles(script_text[:1200], audio_duration, str(srt_file), str(ass_file))

        # 5. Final Video Assembly
        print("Step 5: Assembling final 1080p documentary video...")
        final_video = self.project_dir / "final_documentary.mp4"
        self.video_assembler.assemble(
            clip_paths=clip_paths,
            audio_path=str(audio_file),
            output_video_path=str(final_video),
            subtitle_path=str(ass_file)
        )

        # 6. Viral Thumbnail
        print("Step 6: Designing viral thumbnail with 2D ANIMATION badge...")
        thumb_file = self.project_dir / "thumbnail.jpg"
        thumb_headline = "सीक्रेट मिशन का सच" if self.language.lower() == "hindi" else "THE UNTOLD REALITY"
        self.thumb_designer.create_thumbnail(
            image_prompt=prompts[0],
            hindi_headline=thumb_headline,
            output_path=str(thumb_file)
        )

        print("\n Production Complete!")
        print(f"  Final Video: {final_video}")
        print(f"  Thumbnail:   {thumb_file}")
        
        self._save_metadata()
        return {
            "video": str(final_video),
            "thumbnail": str(thumb_file),
            "audio": str(audio_file),
            "subtitles": str(srt_file)
        }

    def _save_text(self, filename: str, content: str):
        path = self.project_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _save_metadata(self):
        meta_path = self.project_dir / "project_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
