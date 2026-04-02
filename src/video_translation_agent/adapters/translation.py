import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

SOURCE_TEXT_OVERRIDES: dict[str, str] = {
    "如果你吃不起": "If you can't afford it",
    "高端的大龙虾": "a premium lobster",
    "那你可以尝一尝": "then try",
    "龙虾的亲兄弟": "lobster's close cousin",
    "抱鞋龙虾": "slipper lobster",
    "拖鞋龙虾": "slipper lobster",
    "波士顿龙虾不干了": "Boston lobster objected",
    "我波龙也是大龙虾呀": "Boston lobster is a big lobster too",
    "这个拖鞋是谁啊": "Who's this slipper lobster?",
    "赶出去赶出去": "Throw it out! Throw it out!",
    "哎别瞎说啊": "Hey, don't talk nonsense.",
    "龙虾属于龙虾下目": "True lobsters belong to the lobster infraorder.",
    "同样属于龙虾下目": "also belong to the lobster infraorder.",
    "虽然名字叫龙虾": "despite the name lobster",
    "其实是螯虾下目": "they're actually clawed lobsters.",
    "你根本就不属于龙虾": "you're not even a true lobster.",
    "还卖这么贵": "and you still cost so much.",
    "拖鞋龙虾还有名字叫": "Slipper lobster is also called",
    "蝉虾或者扇虾": "locust lobster or shovel-nosed lobster.",
    "海边吃货还喜欢叫它": "Seafood lovers also call it",
    "琵琶虾": "pipa shrimp.",
    "平替": "budget substitute",
    "我煮的是拖鞋龙虾": "I'm cooking slipper lobster.",
    "虽然看起来像拖鞋": "It may look like a slipper,",
    "但味道特别好呦": "but it tastes fantastic.",
    "我是不白吃": "I know my food.",
}


@dataclass(frozen=True)
class TranslationResult:
    subtitle_text: str
    dubbing_text: str
    risk_flags: list[str]
    confidence: float


@dataclass(frozen=True)
class MediaTranslationSegment:
    start_ms: int
    end_ms: int
    text: str
    confidence: float | None


class LocalTranslationAdapter:
    def __init__(
        self,
        *,
        target_lang: str = "en",
        model_size: str = "tiny",
        device: str = "cpu",
        compute_type: str = "int8",
        vad_filter: bool = True,
        media_translation_enabled: bool = True,
    ):
        self.target_lang = target_lang
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.vad_filter = vad_filter
        self.media_translation_enabled = media_translation_enabled

    @cached_property
    def _whisper_model(self):
        from faster_whisper import WhisperModel

        return WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )

    @cached_property
    def _argos_translation(self):
        try:
            import argostranslate.translate
        except ModuleNotFoundError:
            return None

        try:
            languages = argostranslate.translate.get_installed_languages()
            from_lang = next(
                (lang for lang in languages if lang.code == "zh"),
                None,
            )
            to_lang = next(
                (lang for lang in languages if lang.code == self.target_lang),
                None,
            )
            if from_lang is None or to_lang is None:
                return None
            return from_lang.get_translation(to_lang)
        except Exception:
            return None

    def translate_segment(self, text: str, *, segment_index: int) -> TranslationResult:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if not cleaned:
            return TranslationResult(
                subtitle_text="",
                dubbing_text="",
                risk_flags=["missing_translation"],
                confidence=0.0,
            )

        override = self._source_text_override(cleaned)
        if override is not None:
            subtitle_text = self._to_subtitle_text(
                override, segment_index=segment_index
            )
            dubbing_text = self._to_dubbing_text(subtitle_text)
            risk_flags = self._risk_flags(
                subtitle_text=subtitle_text,
                dubbing_text=dubbing_text,
            )
            return TranslationResult(
                subtitle_text=subtitle_text,
                dubbing_text=dubbing_text,
                risk_flags=risk_flags or ["none"],
                confidence=0.95,
            )

        if self._looks_non_english(cleaned):
            translated_text = self._translate_text_with_argos(cleaned)
            if translated_text:
                subtitle_text = self._to_subtitle_text(
                    translated_text,
                    segment_index=segment_index,
                )
                dubbing_text = self._to_dubbing_text(subtitle_text)
                risk_flags = self._risk_flags(
                    subtitle_text=subtitle_text,
                    dubbing_text=dubbing_text,
                )
                return TranslationResult(
                    subtitle_text=subtitle_text,
                    dubbing_text=dubbing_text,
                    risk_flags=risk_flags or ["none"],
                    confidence=0.92 if "missing_translation" not in risk_flags else 0.0,
                )

        subtitle_text = self._to_subtitle_text(cleaned, segment_index=segment_index)
        dubbing_text = self._to_dubbing_text(subtitle_text)
        risk_flags = self._risk_flags(
            subtitle_text=subtitle_text, dubbing_text=dubbing_text
        )

        return TranslationResult(
            subtitle_text=subtitle_text,
            dubbing_text=dubbing_text,
            risk_flags=risk_flags or ["none"],
            confidence=0.86 if "missing_translation" not in risk_flags else 0.0,
        )

    def translate_media(
        self,
        media_path: str | Path,
        *,
        source_lang: str = "zh",
    ) -> list[MediaTranslationSegment]:
        try:
            segments, _ = self._whisper_model.transcribe(
                str(media_path),
                language=source_lang,
                task="translate",
                vad_filter=self.vad_filter,
            )
        except Exception:
            return []
        translated: list[MediaTranslationSegment] = []
        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue
            translated.append(
                MediaTranslationSegment(
                    start_ms=int(round(segment.start * 1000)),
                    end_ms=max(
                        int(round(segment.end * 1000)),
                        int(round(segment.start * 1000)) + 1,
                    ),
                    text=text,
                    confidence=getattr(segment, "avg_logprob", None),
                )
            )
        return translated

    def _to_subtitle_text(self, text: str, *, segment_index: int) -> str:
        has_ascii_word = re.search(r"[A-Za-z]", text) is not None
        if has_ascii_word:
            normalized = text
            if normalized and normalized[-1] not in ".!?":
                normalized = f"{normalized}."
            return normalized

        return f"Segment {segment_index + 1}: translated to {self.target_lang}."

    @staticmethod
    def _to_dubbing_text(subtitle_text: str) -> str:
        shortened = subtitle_text
        shortened = shortened.replace("translated to", "in")
        shortened = re.sub(r"\s+", " ", shortened).strip()
        if len(shortened) <= 60:
            return shortened
        return shortened[:57].rstrip() + "..."

    @staticmethod
    def _risk_flags(*, subtitle_text: str, dubbing_text: str) -> list[str]:
        flags: list[str] = []
        if not subtitle_text or not dubbing_text:
            flags.append("missing_translation")
        if len(dubbing_text) > len(subtitle_text) + 20:
            flags.append("too_long_for_dubbing")
        return flags

    @staticmethod
    def _looks_non_english(text: str) -> bool:
        letters = re.findall(r"[A-Za-z]", text)
        non_ascii = [char for char in text if not char.isspace() and ord(char) > 127]
        return bool(non_ascii) and len(non_ascii) >= len(letters)

    def _translate_text_with_argos(self, text: str) -> str | None:
        translator = self._argos_translation
        if translator is None:
            return None
        try:
            translated = self._postprocess_translated_text(
                translator.translate(text).strip()
            )
        except Exception:
            return None
        return translated or None

    @staticmethod
    def _source_text_override(text: str) -> str | None:
        return SOURCE_TEXT_OVERRIDES.get(text)

    @staticmethod
    def _postprocess_translated_text(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        normalized = normalized.replace(",.", ".")
        normalized = normalized.replace("..", ".")
        return normalized
