"""Lexical, context-free normalization of Russian territorial labels."""

from __future__ import annotations

import re
import unicodedata

_DASHES = str.maketrans({c: "-" for c in "‐‑‒–—―−﹘﹣－"})
_SPACES = re.compile(r"[\\s\\u00a0\\u2000-\\u200b\\u202f\\u205f\\u3000]+")


def normalize_region_label(value: str | None, *, fold_yo: bool = False) -> str | None:
    """Stable comparison key, preserving qualifiers such as 'without data for'."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("Region name must be a string or None")
    text = unicodedata.normalize("NFKC", value).translate(_DASHES).casefold()
    if fold_yo:
        text = text.replace("ё", "е")
    text = _SPACES.sub(" ", text).strip()
    text = re.sub(r"\\s*-\\s*", " - ", text)
    return text or None
