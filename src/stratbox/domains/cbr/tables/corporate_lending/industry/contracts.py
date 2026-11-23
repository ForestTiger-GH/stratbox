"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass, field

from typing import Literal, Mapping


@dataclass(frozen=True, slots=True)
class IndustrySelection:
    """Published industry codes to materialize; None means all published codes."""
    industry_codes: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class IndustrySpec:
    """Один опубликованный отраслевой показатель семейства таблиц Банка России."""

    code: str
    canonical_name_ru: str
    parent_code: str | None
    hierarchy_level: int
    order: int


@dataclass(frozen=True, slots=True)
class IndustryRegionSpec:
    """Географическая строка отраслевой публикации Банка России."""

    code: str
    source_name: str
    canonical_name: str
    region_kind: str
    federal_district_name: str | None
    order: int


@dataclass(frozen=True, slots=True)
class IndustryValidationIssue:
    """Отклонение, найденное в структуре или значениях публикации."""

    code: str
    severity: Literal["warning", "error"]
    message: str
    count: int = 1
    details: Mapping[str, object] = field(default_factory=dict)
