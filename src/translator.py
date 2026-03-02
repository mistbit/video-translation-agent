"""Translation service using GLM cloud API."""

import os
from typing import List, Optional

from zhipuai import ZhipuAI

from .subtitle_extractor import Subtitle


class Translator:
    """Translator using GLM cloud service API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "glm-4",
        temperature: float = 0.3,
    ):
        """Initialize translator.

        Args:
            api_key: GLM API key. If None, reads from GLM_API_KEY environment variable
            model: Model name to use
            temperature: Temperature for generation
        """
        self.api_key = api_key or os.environ.get("GLM_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GLM API key is required. Set GLM_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model
        self.temperature = temperature
        self.client = ZhipuAI(api_key=self.api_key)

    def translate_text(
        self,
        text: str,
        target_lang: str = "en",
        source_lang: Optional[str] = None,
    ) -> str:
        """Translate a single text string.

        Args:
            text: Text to translate
            target_lang: Target language ('zh' for Chinese, 'en' for English)
            source_lang: Source language (auto-detect if None)

        Returns:
            Translated text
        """
        lang_names = {
            "zh": "中文",
            "en": "English",
            "ja": "日语",
            "ko": "韩语",
            "fr": "法语",
            "de": "德语",
            "es": "西班牙语",
        }

        target_name = lang_names.get(target_lang, target_lang)

        if source_lang:
            source_name = lang_names.get(source_lang, source_lang)
            prompt = f"请将以下{source_name}文本翻译成{target_name}，只输出翻译结果，不要添加任何解释：\n\n{text}"
        else:
            prompt = f"请将以下文本翻译成{target_name}，只输出翻译结果，不要添加任何解释：\n\n{text}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的翻译助手，只负责翻译文本，不添加任何额外内容。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"Translation failed: {e}") from e

    def translate_subtitle(
        self,
        subtitle: Subtitle,
        target_lang: str = "en",
        source_lang: Optional[str] = None,
    ) -> Subtitle:
        """Translate a single subtitle.

        Args:
            subtitle: Subtitle to translate
            target_lang: Target language code
            source_lang: Source language code

        Returns:
            New Subtitle with translated text
        """
        translated_text = self.translate_text(
            subtitle.text,
            target_lang=target_lang,
            source_lang=source_lang,
        )

        return Subtitle(
            start_time=subtitle.start_time,
            end_time=subtitle.end_time,
            text=translated_text,
        )

    def translate_subtitles(
        self,
        subtitles: List[Subtitle],
        target_lang: str = "en",
        source_lang: Optional[str] = None,
        batch_size: int = 10,
    ) -> List[Subtitle]:
        """Translate multiple subtitles with batch optimization.

        Args:
            subtitles: List of Subtitle objects
            target_lang: Target language code
            source_lang: Source language code
            batch_size: Number of subtitles to translate in a single batch

        Returns:
            List of translated Subtitle objects
        """
        translated = []

        for i in range(0, len(subtitles), batch_size):
            batch = subtitles[i : i + batch_size]

            # Combine batch into single request for efficiency
            batch_texts = [sub.text for sub in batch]
            combined_text = "\n\n".join(batch_texts)

            # Translate combined text
            translated_combined = self.translate_text(
                combined_text,
                target_lang=target_lang,
                source_lang=source_lang,
            )

            # Split translated text back into individual subtitles
            translated_lines = translated_combined.split("\n\n")

            # Create new subtitle objects with translated text
            for j, subtitle in enumerate(batch):
                if j < len(translated_lines):
                    translated_text = translated_lines[j]
                else:
                    # Fallback: translate individually
                    translated_text = self.translate_text(
                        subtitle.text,
                        target_lang=target_lang,
                        source_lang=source_lang,
                    )

                translated.append(
                    Subtitle(
                        start_time=subtitle.start_time,
                        end_time=subtitle.end_time,
                        text=translated_text,
                    )
                )

        return translated

    def translate_file(
        self,
        input_file: str,
        output_file: str,
        target_lang: str = "en",
        source_lang: Optional[str] = None,
    ) -> None:
        """Translate a subtitle file.

        Args:
            input_file: Path to input SRT file
            output_file: Path to output SRT file
            target_lang: Target language code
            source_lang: Source language code
        """
        from .subtitle_export import SubtitleExporter

        # Import subtitles from file
        exporter = SubtitleExporter()
        subtitles = exporter.import_srt(input_file)

        # Translate subtitles
        translated = self.translate_subtitles(
            subtitles,
            target_lang=target_lang,
            source_lang=source_lang,
        )

        # Export translated subtitles
        exporter.export_srt(translated, output_file)

    @staticmethod
    def detect_language(text: str) -> str:
        """Detect the language of the given text.

        Args:
            text: Text to analyze

        Returns:
            Language code ('zh', 'en', etc.)
        """
        # Simple heuristic based on character sets
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        total_chars = len(text.replace(" ", "").replace("\n", ""))

        if total_chars == 0:
            return "en"

        chinese_ratio = chinese_chars / total_chars

        if chinese_ratio > 0.3:
            return "zh"
        return "en"

    @staticmethod
    def get_inverse_language(lang: str) -> str:
        """Get the inverse language code for translation.

        Args:
            lang: Language code ('zh' or 'en')

        Returns:
            Inverse language code
        """
        lang_map = {
            "zh": "en",
            "en": "zh",
        }

        return lang_map.get(lang, lang)
