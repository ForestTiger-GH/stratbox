"""
Модели данных для блока FRG.

На первом этапе здесь описываются:
- правило семейства файлов;
- активная схема внутреннего имени файла;
- запись каталога по одному найденному файлу.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class FrgFamilyRule:
    """Правило распознавания одного семейства файлов FRG."""

    code: str
    title: str
    file_label: str
    parser_group: str
    parser_key: str
    period_mode: str
    priority: int
    tokens_all: tuple[str, ...] = ()
    tokens_any: tuple[str, ...] = ()
    tokens_none: tuple[str, ...] = ()
    requires_week_marker: bool = False
    requires_q_marker: bool = False
    min_period_date: date | None = None
    note: str = ""


@dataclass(frozen=True, slots=True)
class FrgInternalNameScheme:
    """Активная схема внутреннего имени файлов FRG."""

    prefix: str = ""
    separator: str = "_"


@dataclass(frozen=True, slots=True)
class FrgCatalogRecord:
    """Одна строка каталога найденных файлов."""

    root_dir: str
    path: str
    file_name: str
    extension: str
    normalized_name: str
    name_origin: str
    name_priority: int
    family_code: str | None
    family_name: str | None
    file_label: str | None
    parser_group: str | None
    parser_key: str | None
    period_mode: str | None
    period_date: date | None
    period_date_text: str | None
    week_no: int | None
    has_week_marker: bool
    has_q_marker: bool
    snapshot_day: int | None
    is_supported_extension: bool
    is_recognized: bool
    is_valid: bool
    validity_reason: str
    size_bytes: int | None = None
    mtime: float | None = None
    mtime_iso: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Преобразует запись в обычный словарь для DataFrame."""
        return asdict(self)
