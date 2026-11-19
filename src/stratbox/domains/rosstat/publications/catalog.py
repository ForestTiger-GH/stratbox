"""Versioned official landing pages, not hardcoded monthly download URLs."""

from __future__ import annotations

from .contracts import RosstatSourceSpec

_SOURCES = (
    RosstatSourceSpec(
        "rosstat.socioeconomic_russia", "Социально-экономическое положение России",
        "https://rosstat.gov.ru/compendium/document/50801",
        "socioeconomic_russia", frozenset({"pdf"}), "monthly",
    ),
    RosstatSourceSpec(
        "rosstat.socioeconomic_regions", "Социально-экономическое положение субъектов РФ",
        "https://rosstat.gov.ru/folder/11109/document/13259",
        "socioeconomic_regions", frozenset({"zip", "rar"}), "monthly",
    ),
    RosstatSourceSpec(
        "rosstat.short_term_indicators", "Краткосрочные экономические показатели РФ",
        "https://rosstat.gov.ru/compendium/document/50802",
        "short_term_indicators", frozenset({"xlsx"}), "monthly",
    ),
    RosstatSourceSpec(
        "rosstat.population_municipalities", "Численность населения по муниципальным образованиям",
        "https://rosstat.gov.ru/compendium/document/13282",
        "population_municipalities", frozenset({"xlsx"}), "annual",
    ),
)
_BY_ID = {source.series_id: source for source in _SOURCES}
if len(_BY_ID) != len(_SOURCES):
    raise RuntimeError("rosstat.catalog_duplicate")


def list_rosstat_sources() -> tuple[RosstatSourceSpec, ...]:
    return _SOURCES


def get_rosstat_source(series_id: str) -> RosstatSourceSpec:
    try:
        return _BY_ID[series_id]
    except (KeyError, TypeError):
        raise ValueError("rosstat.series_unknown") from None
