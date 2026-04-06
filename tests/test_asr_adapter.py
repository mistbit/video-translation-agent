from pathlib import Path

from video_translation_agent.adapters.asr import (
    FasterWhisperASRAdapter,
    _avg_logprob_to_confidence,
    _condition_on_previous_text_for,
    _initial_prompt_for,
    _transcribe_options_for,
)


def test_avg_logprob_to_confidence_maps_to_probability_like_range() -> None:
    low = _avg_logprob_to_confidence(-1.5)
    high = _avg_logprob_to_confidence(-0.1)

    assert low is not None
    assert high is not None
    assert 0.0 <= low <= 1.0
    assert 0.0 <= high <= 1.0
    assert high > low


def test_initial_prompt_defaults_to_chinese_caption_hint() -> None:
    assert _initial_prompt_for("zh") is not None
    assert _initial_prompt_for("en") is None


def test_medium_zh_disables_previous_text_conditioning() -> None:
    assert (
        _condition_on_previous_text_for(language="zh", model_size="medium") is False
    )
    assert _condition_on_previous_text_for(language="zh", model_size="small") is True
    assert _condition_on_previous_text_for(language="en", model_size="medium") is True


def test_transcribe_options_include_tuned_medium_policy() -> None:
    options = _transcribe_options_for(
        language="zh",
        model_size="medium",
        vad_filter=True,
    )

    assert options["task"] == "transcribe"
    assert options["beam_size"] == 8
    assert options["best_of"] == 8
    assert options["condition_on_previous_text"] is False
    assert options["vad_filter"] is True
    assert options["initial_prompt"] is not None


def test_medium_transcribe_passes_tuned_options_to_model(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"not-a-real-video")
    captured: dict[str, object] = {}

    class FakeSegment:
        start = 0.0
        end = 1.0
        text = "你好"
        avg_logprob = -0.1

    class FakeModel:
        def transcribe(self, audio, language=None, **kwargs):
            captured["audio"] = audio
            captured["language"] = language
            captured.update(kwargs)
            return iter([FakeSegment()]), object()

    adapter = FasterWhisperASRAdapter(model_size="medium")
    adapter.__dict__["_model"] = FakeModel()

    segments = adapter.transcribe(source, language="zh")

    assert len(segments) == 1
    assert captured["audio"] == str(source)
    assert captured["language"] == "zh"
    assert captured["condition_on_previous_text"] is False
    assert captured["task"] == "transcribe"
    assert captured["beam_size"] == 8
