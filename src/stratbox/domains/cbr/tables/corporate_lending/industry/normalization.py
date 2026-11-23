"""Semantic normalization shared by 01_05_A and 01_04_A layouts."""

from __future__ import annotations

import re


def normalize_industry_text(value: object) -> str:
    """Нормализует текст источника, сохраняя его экономический смысл."""
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").replace("ё", "е").replace("Ё", "Е")
    text = re.sub(r"_+", " ", text)
    text = re.sub(r"\bиз\s+них\b\s*:?,?", " ", text, flags=re.I)
    text = re.sub(r"[^0-9A-Za-zА-Яа-я]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()

