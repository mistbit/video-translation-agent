from pathlib import Path

import pytest

from video_translation_agent.adapters.subtitles import (
    CaptionSourceUnsupportedError,
    SubtitleParseError,
    SubtitleParser,
)


def test_subtitle_parser_parses_srt_file(tmp_path: Path) -> None:
    srt = tmp_path / "source.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:01,500\n  Hello   world  \n\n"
        "2\n00:00:01,500 --> 00:00:03,000\nSecond line\ncontinues\n",
        encoding="utf-8",
    )

    parser = SubtitleParser()
    cues = parser.parse(srt)

    assert len(cues) == 2
    assert cues[0].start_ms == 0
    assert cues[0].end_ms == 1500
    assert cues[0].text == "Hello world"
    assert cues[1].text == "Second line continues"


def test_subtitle_parser_rejects_unsupported_extension(tmp_path: Path) -> None:
    parser = SubtitleParser()
    vtt = tmp_path / "source.vtt"
    vtt.write_text("WEBVTT", encoding="utf-8")

    with pytest.raises(CaptionSourceUnsupportedError, match="only .srt"):
        parser.parse(vtt)


def test_subtitle_parser_rejects_invalid_timing(tmp_path: Path) -> None:
    parser = SubtitleParser()
    broken = tmp_path / "source.srt"
    broken.write_text("1\n00:00:03,000 --> 00:00:01,000\ninvalid\n", encoding="utf-8")

    with pytest.raises(SubtitleParseError, match="invalid SRT timing range"):
        parser.parse(broken)
