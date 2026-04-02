import re

_PUNCT_MAP = str.maketrans(
    {
        "，": ",",
        "。": ".",
        "！": "!",
        "？": "?",
        "；": ";",
        "：": ":",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
    }
)


def normalize_caption_text(text: str) -> str:
    collapsed_lines = " ".join(
        part.strip() for part in text.splitlines() if part.strip()
    )
    normalized = collapsed_lines.translate(_PUNCT_MAP)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"([,.;:!?])\1+", r"\1", normalized)
    normalized = _collapse_duplicate_tokens(normalized)
    return normalized


def _collapse_duplicate_tokens(text: str) -> str:
    if not text:
        return text
    tokens = text.split(" ")
    deduped: list[str] = []
    for token in tokens:
        if deduped and deduped[-1].casefold() == token.casefold():
            continue
        deduped.append(token)
    return " ".join(deduped)
