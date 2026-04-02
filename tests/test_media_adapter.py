import subprocess

import pytest

from video_translation_agent.adapters.media import MediaProbeAdapter, MediaProbeError


def test_media_probe_parses_ffprobe_json() -> None:
    def _runner(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='{"streams":[{"codec_type":"video"},{"codec_type":"audio"},{"codec_type":"subtitle"}],"format":{"duration":"12.34","size":"9876","format_name":"mov,mp4"}}',
            stderr="",
        )

    adapter = MediaProbeAdapter(run_command=_runner)
    result = adapter.probe("/tmp/demo.mp4")

    assert result.duration_seconds == pytest.approx(12.34)
    assert result.size_bytes == 9876
    assert result.video_stream_count == 1
    assert result.audio_stream_count == 1
    assert result.subtitle_stream_count == 1
    assert result.has_subtitle_stream is True


def test_media_probe_raises_clear_error_when_ffprobe_missing() -> None:
    def _runner(*args, **kwargs):
        raise FileNotFoundError("ffprobe")

    adapter = MediaProbeAdapter(run_command=_runner)
    with pytest.raises(MediaProbeError, match="ffprobe executable not found"):
        adapter.probe("/tmp/demo.mp4")
