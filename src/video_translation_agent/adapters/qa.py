from dataclasses import dataclass

from video_translation_agent.domain.models import SegmentRecord


@dataclass(frozen=True)
class QAPolicy:
    asr_low_confidence_threshold: float = 0.80
    ocr_low_confidence_threshold: float = 0.85
    max_tts_overrun_ratio: float = 0.10
    max_tts_overrun_ms: int = 1000
    pause_on_missing_translation: bool = True
    pause_on_audio_clipping_risk: bool = True


class QAAdapter:
    def __init__(self, *, policy: QAPolicy | None = None):
        self.policy = policy or QAPolicy()

    def evaluate_segment(self, segment: SegmentRecord) -> list[str]:
        flags: list[str] = []
        if (segment.subtitle_text or "").strip() == "" or (
            segment.dubbing_text or ""
        ).strip() == "":
            flags.append("missing_translation")

        if (
            segment.asr_confidence is not None
            and segment.asr_confidence < self.policy.asr_low_confidence_threshold
        ):
            flags.append("asr_low_confidence")

        if (
            segment.ocr_confidence is not None
            and segment.ocr_confidence < self.policy.ocr_low_confidence_threshold
        ):
            flags.append("ocr_low_confidence")

        target_duration_ms = max(0, segment.end_ms - segment.start_ms)
        if segment.tts_duration_ms is None:
            flags.append("duration_mismatch")
        elif (
            segment.tts_duration_ms
            > target_duration_ms + self.policy.max_tts_overrun_ms
        ):
            flags.append("tts_duration_overrun")

        return sorted(set(flags))
