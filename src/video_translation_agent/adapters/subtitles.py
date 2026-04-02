import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class SubtitleParseError(ValueError):
    pass


class CaptionSourceUnsupportedError(ValueError):
    pass


class SubtitleCue(BaseModel):
    index: int
    start_ms: int
    end_ms: int
    text: str


class SubtitleParser:
    _TIMING_RE = re.compile(
        r"(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})"
    )

    def parse(self, subtitle_path: str | Path) -> list[SubtitleCue]:
        source = Path(subtitle_path)
        suffix = source.suffix.lower()
        if suffix != ".srt":
            raise CaptionSourceUnsupportedError(
                f"unsupported subtitle format '{suffix or '<none>'}', only .srt is supported"
            )

        content = source.read_text(encoding="utf-8-sig")
        return self._parse_srt(content)

    def _parse_srt(self, content: str) -> list[SubtitleCue]:
        cues: list[SubtitleCue] = []
        blocks = re.split(r"\r?\n\r?\n+", content.strip())
        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if len(lines) < 2:
                continue

            index_line = lines[0]
            timing_line = lines[1]
            text_lines = lines[2:]

            try:
                index = int(index_line)
            except ValueError as exc:
                raise SubtitleParseError(
                    f"invalid SRT cue index: '{index_line}'"
                ) from exc

            match = self._TIMING_RE.fullmatch(timing_line)
            if match is None:
                raise SubtitleParseError(f"invalid SRT timing line: '{timing_line}'")

            start_ms = self._parse_timestamp(match.group("start"))
            end_ms = self._parse_timestamp(match.group("end"))
            if end_ms <= start_ms:
                raise SubtitleParseError(
                    f"invalid SRT timing range in cue {index}: {timing_line}"
                )

            text = re.sub(r"\s+", " ", " ".join(text_lines)).strip()
            cues.append(
                SubtitleCue(index=index, start_ms=start_ms, end_ms=end_ms, text=text)
            )

        return cues

    @staticmethod
    def _parse_timestamp(value: str) -> int:
        normalized = value.replace(",", ".")
        parts = normalized.split(":")
        if len(parts) != 3:
            raise SubtitleParseError(f"invalid subtitle timestamp '{value}'")

        hours, minutes, seconds = parts
        second_part, _, milli_part = seconds.partition(".")
        try:
            return (
                int(hours) * 3600 * 1000
                + int(minutes) * 60 * 1000
                + int(second_part) * 1000
                + int(milli_part)
            )
        except ValueError as exc:
            raise SubtitleParseError(f"invalid subtitle timestamp '{value}'") from exc

    @staticmethod
    def cues_to_payload(cues: list[SubtitleCue]) -> list[dict[str, Any]]:
        return [cue.model_dump(mode="json") for cue in cues]
