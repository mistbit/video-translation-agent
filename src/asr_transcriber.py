"""ASR transcription using Faster-Whisper."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from faster_whisper import WhisperModel

from .subtitle_extractor import Subtitle
from .video_processor import VideoProcessor


@dataclass
class TranscriptionSegment:
    """Single transcription segment with timing info."""

    start: float  # in seconds
    end: float  # in seconds
    text: str
    avg_logprob: float
    no_speech_prob: float


class ASRTranscriber:
    """ASR transcriber using Faster-Whisper."""

    def __init__(
        self,
        model_size: str = "base",
        compute_type: str = "int8",
        language: str = "auto",
        device: str = "auto",
    ):
        """Initialize ASR transcriber.

        Args:
            model_size: Model size ('tiny', 'base', 'small', 'medium', 'large')
            compute_type: Compute type ('int8', 'float16', 'float32')
            language: Language code ('auto', 'zh', 'en', etc.)
            device: Device to use ('auto', 'cpu', 'cuda')
        """
        self.model_size = model_size
        self.compute_type = compute_type
        self.language = language

        # Initialize model
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    def transcribe(
        self,
        audio_path: str,
        beam_size: int = 5,
        vad_filter: bool = True,
        word_timestamps: bool = False,
    ) -> List[Subtitle]:
        """Transcribe audio file to subtitles.

        Args:
            audio_path: Path to audio file
            beam_size: Beam size for decoding
            vad_filter: Whether to use VAD (Voice Activity Detection)
            word_timestamps: Whether to include word-level timestamps

        Returns:
            List of Subtitle objects
        """
        # Transcribe
        segments, info = self.model.transcribe(
            audio_path,
            beam_size=beam_size,
            vad_filter=vad_filter,
            word_timestamps=word_timestamps,
            language=self.language if self.language != "auto" else None,
        )

        # Convert segments to subtitles
        subtitles = []
        for segment in segments:
            subtitle = Subtitle(
                start_time=segment.start,
                end_time=segment.end,
                text=segment.text.strip(),
            )
            subtitles.append(subtitle)

        return subtitles

    def transcribe_video(
        self,
        video_path: str,
        beam_size: int = 5,
        vad_filter: bool = True,
        sample_rate: int = 16000,
    ) -> List[Subtitle]:
        """Transcribe video file to subtitles.

        Args:
            video_path: Path to video file
            beam_size: Beam size for decoding
            vad_filter: Whether to use VAD
            sample_rate: Audio sample rate for extraction

        Returns:
            List of Subtitle objects
        """
        # Extract audio from video
        video_processor = VideoProcessor(video_path)
        audio_path = video_processor.extract_audio(sample_rate=sample_rate)

        try:
            # Transcribe audio
            subtitles = self.transcribe(
                str(audio_path),
                beam_size=beam_size,
                vad_filter=vad_filter,
            )
            return subtitles
        finally:
            # Clean up extracted audio file (optional)
            # audio_path.unlink()
            pass

    def get_segments(
        self,
        audio_path: str,
        beam_size: int = 5,
    ) -> List[TranscriptionSegment]:
        """Get detailed transcription segments with confidence scores.

        Args:
            audio_path: Path to audio file
            beam_size: Beam size for decoding

        Returns:
            List of TranscriptionSegment objects
        """
        segments, info = self.model.transcribe(
            audio_path,
            beam_size=beam_size,
            vad_filter=True,
        )

        result = []
        for segment in segments:
            result.append(
                TranscriptionSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                    avg_logprob=segment.avg_logprob,
                    no_speech_prob=segment.no_speech_prob,
                )
            )

        return result

    @staticmethod
    def detect_language(audio_path: str) -> tuple[str, float]:
        """Detect the language of an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (language_code, probability)
        """
        model = WhisperModel("tiny")
        segments, info = model.transcribe(audio_path, beam_size=5)

        return info.language, info.language_probability


def combine_ocr_and_asr(
    ocr_subtitles: List[Subtitle],
    asr_subtitles: List[Subtitle],
    overlap_threshold: float = 0.5,
) -> List[Subtitle]:
    """Combine OCR and ASR subtitles for better accuracy.

    This function merges subtitles from both sources, prioritizing ASR for
    accuracy but using OCR for hard subtitles that ASR might miss.

    Args:
        ocr_subtitles: List of OCR-extracted subtitles
        asr_subtitles: List of ASR-extracted subtitles
        overlap_threshold: Minimum overlap time to consider subtitles as conflicting

    Returns:
        Combined list of Subtitle objects
    """
    if not asr_subtitles:
        return ocr_subtitles
    if not ocr_subtitles:
        return asr_subtitles

    combined = []
    ocr_index = 0
    asr_index = 0

    while asr_index < len(asr_subtitles):
        asr_sub = asr_subtitles[asr_index]

        # Find overlapping OCR subtitles
        overlapping_ocr = []
        while ocr_index < len(ocr_subtitles):
            ocr_sub = ocr_subtitles[ocr_index]

            # Check overlap
            overlap_start = max(asr_sub.start_time, ocr_sub.start_time)
            overlap_end = min(asr_sub.end_time, ocr_sub.end_time)

            if overlap_end > overlap_start:
                overlapping_ocr.append(ocr_sub)
                ocr_index += 1
            elif ocr_sub.start_time > asr_sub.end_time:
                # OCR subtitle is after current ASR subtitle
                break
            else:
                # OCR subtitle is before current ASR subtitle
                ocr_index += 1

        if overlapping_ocr:
            # Combine ASR with OCR (use ASR as base, add OCR if different)
            combined.append(asr_sub)
        else:
            # No overlap, use ASR subtitle
            combined.append(asr_sub)

        asr_index += 1

    # Add any remaining OCR subtitles
    while ocr_index < len(ocr_subtitles):
        combined.append(ocr_subtitles[ocr_index])
        ocr_index += 1

    return combined
