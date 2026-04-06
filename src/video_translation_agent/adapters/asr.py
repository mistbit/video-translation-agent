import json
import math
import subprocess
from functools import cached_property
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

_ZH_INITIAL_PROMPT = "以下是中文视频字幕，请输出简体中文，不要翻译，保留口语表达。"
_ZH_VAD_PARAMETERS = {
    "min_silence_duration_ms": 300,
    "speech_pad_ms": 200,
}


class ASRTranscriptionError(RuntimeError):
    pass


class ASRSegment(BaseModel):
    start_ms: int
    end_ms: int
    text: str
    confidence: float | None = None


class ASRAdapter(Protocol):
    def transcribe(
        self,
        media_path: str | Path,
        *,
        language: str = "zh",
        model_size: str | None = None,
    ) -> list[ASRSegment]: ...


class FasterWhisperASRAdapter:
    def __init__(
        self,
        *,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        vad_filter: bool = True,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.vad_filter = vad_filter

    @cached_property
    def _model(self):
        try:
            from faster_whisper import WhisperModel
        except ModuleNotFoundError as exc:
            raise ASRTranscriptionError(
                "faster-whisper is not installed; install project dependencies first"
            ) from exc

        try:
            return WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        except Exception as exc:
            raise ASRTranscriptionError(
                f"failed to initialize ASR model: {exc}"
            ) from exc

    def transcribe(
        self,
        media_path: str | Path,
        *,
        language: str = "zh",
        model_size: str | None = None,
    ) -> list[ASRSegment]:
        source = Path(media_path)
        if not source.exists():
            raise ASRTranscriptionError(f"media file not found: {source}")

        if model_size is not None and model_size != self.model_size:
            adapter = FasterWhisperASRAdapter(
                model_size=model_size,
                device=self.device,
                compute_type=self.compute_type,
                vad_filter=self.vad_filter,
            )
            return adapter.transcribe(source, language=language)

        transcribe_options = _transcribe_options_for(
            language=language,
            model_size=self.model_size,
            vad_filter=self.vad_filter,
        )

        try:
            segments, _ = self._model.transcribe(
                str(source),
                language=language,
                **transcribe_options,
            )
        except ASRTranscriptionError as exc:
            if self.model_size != "small":
                raise ASRTranscriptionError(
                    f"ASR transcription failed for '{source}': {exc}"
                ) from exc
            fallback_adapter = FasterWhisperASRAdapter(
                model_size="tiny",
                device=self.device,
                compute_type=self.compute_type,
                vad_filter=self.vad_filter,
            )
            return fallback_adapter.transcribe(source, language=language)
        except Exception as exc:
            raise ASRTranscriptionError(
                f"ASR transcription failed for '{source}': {exc}"
            ) from exc

        normalized: list[ASRSegment] = []
        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue
            normalized.append(
                ASRSegment(
                    start_ms=int(round(segment.start * 1000)),
                    end_ms=max(
                        int(round(segment.end * 1000)),
                        int(round(segment.start * 1000)) + 1,
                    ),
                    text=text,
                    confidence=_avg_logprob_to_confidence(
                        getattr(segment, "avg_logprob", None)
                    ),
                )
            )

        if not normalized:
            raise ASRTranscriptionError(
                f"ASR produced no speech segments for '{source}'"
            )

        return normalized


def _beam_size_for(language: str) -> int:
    if language.lower().startswith("zh"):
        return 8
    return 5


def _best_of_for(language: str) -> int:
    if language.lower().startswith("zh"):
        return 8
    return 5


def _initial_prompt_for(language: str) -> str | None:
    if language.lower().startswith("zh"):
        return _ZH_INITIAL_PROMPT
    return None


def _vad_parameters_for(language: str) -> dict[str, int] | None:
    if language.lower().startswith("zh"):
        return _ZH_VAD_PARAMETERS
    return None


def _avg_logprob_to_confidence(avg_logprob: float | None) -> float | None:
    if avg_logprob is None:
        return None
    try:
        return max(0.0, min(1.0, math.exp(float(avg_logprob))))
    except (TypeError, ValueError):
        return None


def _transcribe_options_for(
    *, language: str, model_size: str, vad_filter: bool
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "task": "transcribe",
        "beam_size": _beam_size_for(language),
        "best_of": _best_of_for(language),
        "temperature": 0.0,
        "condition_on_previous_text": _condition_on_previous_text_for(
            language=language,
            model_size=model_size,
        ),
        "initial_prompt": _initial_prompt_for(language),
        "vad_filter": vad_filter,
        "vad_parameters": _vad_parameters_for(language),
    }
    return options


def _condition_on_previous_text_for(*, language: str, model_size: str) -> bool:
    if language.lower().startswith("zh") and model_size == "medium":
        return False
    return True


def avfoundation_probe_payload(media_path: Path) -> dict[str, object]:
    swift_script = (
        "import Foundation;"
        "import AVFoundation;"
        "let url = URL(fileURLWithPath: CommandLine.arguments[1]);"
        "let asset = AVURLAsset(url: url);"
        "let fm = FileManager.default;"
        "let attrs = try fm.attributesOfItem(atPath: url.path);"
        "let size = (attrs[.size] as? NSNumber)?.intValue;"
        "let duration = CMTimeGetSeconds(asset.duration);"
        "let tracks = asset.tracks;"
        "let payload: [String: Any] = ["
        '"source_path": url.path,'
        '"format_name": url.pathExtension.lowercased(),'
        '"duration_seconds": duration.isFinite ? duration : NSNull(),'
        '"size_bytes": size ?? NSNull(),'
        '"stream_count": tracks.count,'
        '"video_stream_count": tracks.filter { $0.mediaType == .video }.count,'
        '"audio_stream_count": tracks.filter { $0.mediaType == .audio }.count,'
        '"subtitle_stream_count": tracks.filter { $0.mediaType == .subtitle || $0.mediaType == .text || $0.mediaType == .closedCaption }.count,'
        '"has_subtitle_stream": tracks.contains { $0.mediaType == .subtitle || $0.mediaType == .text || $0.mediaType == .closedCaption },'
        '"fallback": "avfoundation"'
        "];"
        "let data = try JSONSerialization.data(withJSONObject: payload, options: []);"
        "FileHandle.standardOutput.write(data)"
    )
    command = ["swift", "-e", swift_script, str(media_path)]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ASRTranscriptionError(
            "swift executable not found for AVFoundation fallback"
        ) from exc
    except OSError as exc:
        raise ASRTranscriptionError(
            f"failed to execute AVFoundation fallback: {exc}"
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        raise ASRTranscriptionError(
            f"AVFoundation fallback failed for '{media_path}': {stderr or 'unknown error'}"
        )

    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ASRTranscriptionError(
            "AVFoundation fallback output is not valid JSON"
        ) from exc

    return payload
