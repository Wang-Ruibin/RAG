"""Utility functions used across the application."""

import re


def normalize_question(text: str) -> str:
    """Normalize question text for cache key matching.

    1. Strip leading/trailing whitespace
    2. Collapse multiple whitespace to single space
    3. Fullwidth punctuation → halfwidth（，。！？；：等）
    4. Strip trailing question marks, exclamation marks (tone not semantic)
    5. Lowercase (for English parts)
    """
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    # Fullwidth → halfwidth punctuation
    text = text.replace("，", ",").replace("。", ".").replace("！", "!")
    text = text.replace("？", "?").replace("；", ";").replace("：", ":")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    # Strip trailing question/exclamation marks (tone does not affect semantics)
    text = text.rstrip("!??")
    text = text.lower()
    return text.strip()
