from video_translation_agent.adapters.normalization import normalize_caption_text


def test_normalization_collapses_whitespace_and_duplicate_tokens() -> None:
    text = "Hello   hello\n\nWORLD  world"
    assert normalize_caption_text(text) == "Hello WORLD"


def test_normalization_unifies_common_punctuation() -> None:
    text = "你好！！ 这是，测试。"
    assert normalize_caption_text(text) == "你好! 这是,测试."
