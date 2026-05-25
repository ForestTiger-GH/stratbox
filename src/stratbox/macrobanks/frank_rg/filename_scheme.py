"""
Активная схема внутренних имён файлов Frank RG.

Идея:
- исходные файлы Frank RG распознаются по "сырому" имени поставщика;
- файлы, которые уже переименовала библиотека, распознаются по отдельной внутренней схеме;
- в коде поддерживается только одна активная внутренняя схема, которую можно централизованно поменять.
"""

from __future__ import annotations

import re

from stratbox.macrobanks.frank_rg.models import FrankInternalNameScheme


_FORBIDDEN_FILENAME_CHARS_RE = re.compile(r'[<>:"/\|?*]')
_ACTIVE_INTERNAL_NAME_SCHEME = FrankInternalNameScheme(
    prefix="",
    separator="_",
)


def get_active_internal_name_scheme() -> FrankInternalNameScheme:
    """Возвращает активную схему внутреннего имени файлов."""
    return _ACTIVE_INTERNAL_NAME_SCHEME



def sanitize_filename_part(text: str) -> str:
    """Подготавливает часть имени файла без потери основного смысла."""
    value = str(text).strip()
    value = value.replace(" ", " ")
    value = _FORBIDDEN_FILENAME_CHARS_RE.sub(" ", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .")
    return value



def build_internal_file_name(
    period_text: str | None,
    file_label: str | None,
    extension: str | None,
    *,
    scheme: FrankInternalNameScheme | None = None,
) -> str:
    """Формирует имя файла по активной внутренней схеме."""
    active_scheme = scheme or get_active_internal_name_scheme()
    ext = str(extension or "").strip().lower()
    prefix = sanitize_filename_part(active_scheme.prefix)
    left = sanitize_filename_part(period_text or "unknown-period")
    right = sanitize_filename_part(file_label or "Unknown family")

    parts = [part for part in (prefix, left, right) if part]
    if ext and not ext.startswith("."):
        ext = f".{ext}"

    return f"{active_scheme.separator.join(parts)}{ext}"
