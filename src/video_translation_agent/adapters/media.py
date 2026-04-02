import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from video_translation_agent.adapters.asr import (
    ASRTranscriptionError,
    avfoundation_probe_payload,
)

RunCommand = Callable[..., subprocess.CompletedProcess[str]]


class MediaProbeError(RuntimeError):
    pass


class MediaProbeResult(BaseModel):
    source_path: str
    format_name: str | None = None
    duration_seconds: float | None = None
    size_bytes: int | None = None
    stream_count: int = 0
    video_stream_count: int = 0
    audio_stream_count: int = 0
    subtitle_stream_count: int = 0
    has_subtitle_stream: bool = False
    raw: dict[str, Any] = Field(default_factory=dict)


class MediaProbeAdapter:
    def __init__(
        self,
        *,
        ffprobe_bin: str = "ffprobe",
        run_command: RunCommand = subprocess.run,
    ):
        self.ffprobe_bin = ffprobe_bin
        self.run_command = run_command

    def probe(self, media_path: str | Path) -> MediaProbeResult:
        source = Path(media_path)
        command = [
            self.ffprobe_bin,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(source),
        ]

        try:
            completed = self.run_command(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            return self._fallback_probe(source, cause=exc)
        except OSError as exc:
            raise MediaProbeError(f"failed to execute ffprobe: {exc}") from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            return self._fallback_probe(
                source,
                cause=MediaProbeError(
                    f"ffprobe failed for '{source}': {stderr or 'unknown error'}"
                ),
            )

        stdout = completed.stdout or ""
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise MediaProbeError("ffprobe output is not valid JSON") from exc

        return self._build_result(source=source, payload=payload)

    def _fallback_probe(self, source: Path, *, cause: Exception) -> MediaProbeResult:
        if not source.exists():
            raise MediaProbeError("ffprobe executable not found on PATH") from cause
        try:
            payload = avfoundation_probe_payload(source)
        except ASRTranscriptionError as exc:
            raise MediaProbeError(str(cause)) from exc
        payload["raw"] = {"fallback": payload.get("fallback", "avfoundation")}
        return self._build_result(source=source, payload=payload)

    def _build_result(
        self, *, source: Path, payload: dict[str, Any]
    ) -> MediaProbeResult:
        streams = payload.get("streams") or []
        stream_codecs = [str(item.get("codec_type", "")).strip() for item in streams]
        format_payload = payload.get("format") or {}

        format_name = format_payload.get("format_name")
        duration_value = format_payload.get("duration")
        size_value = format_payload.get("size")

        duration_seconds = self._parse_float(duration_value)
        size_bytes = self._parse_int(size_value)

        return MediaProbeResult(
            source_path=str(source),
            format_name=str(format_name) if format_name is not None else None,
            duration_seconds=duration_seconds,
            size_bytes=size_bytes,
            stream_count=len(stream_codecs),
            video_stream_count=sum(1 for item in stream_codecs if item == "video"),
            audio_stream_count=sum(1 for item in stream_codecs if item == "audio"),
            subtitle_stream_count=sum(
                1 for item in stream_codecs if item == "subtitle"
            ),
            has_subtitle_stream=any(item == "subtitle" for item in stream_codecs),
            raw=payload,
        )

    @staticmethod
    def _parse_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
