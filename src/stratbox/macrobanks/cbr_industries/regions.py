"""Локальная нормализация географических строк серии ``01_05_A_Debt_corp``."""

from __future__ import annotations

import re
from dataclasses import replace

from stratbox.macrobanks.cbr_industries.contracts import (
    Cbr0105ADebtCorpRegionSpec,
    ParsedCbr0105ADebtCorpFile,
)


# Локальные исторические варианты именно этой серии. Общий справочник регионов
# будет отдельным контуром; здесь фиксируется только уже наблюдавшееся переименование.
_CURRENT_SOURCE_ALIASES = {
    "кемеровская область": "Кемеровская область - Кузбасс",
}


def _normalize_region_name(value: object) -> str:
    text = str(value or "").replace("\xa0", " ").replace("ё", "е").replace("Ё", "Е")
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s*-\s*", " - ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _region_kind(name: str) -> str:
    normalized = _normalize_region_name(name)
    if normalized == "российская федерация":
        return "country_total"
    if "федеральный округ" in normalized:
        return "federal_district_total"
    if normalized.startswith("в том числе"):
        return "included_autonomous_area"
    if "без данных по" in normalized:
        return "exclusive_parent_area"
    return "region"


def build_cbr_0105a_debt_corp_region_specs(
    source_names: list[str] | tuple[str, ...],
) -> tuple[Cbr0105ADebtCorpRegionSpec, ...]:
    """Формирует географическую раскладку одной книги в исходном порядке."""
    if not source_names:
        raise ValueError("01_05_A_Debt_corp contains no geographic rows")

    current_federal_district: str | None = None
    out: list[Cbr0105ADebtCorpRegionSpec] = []
    for order, raw_name in enumerate(source_names, start=1):
        name = re.sub(r"\s+", " ", str(raw_name).replace("\xa0", " ")).strip()
        if not name:
            raise ValueError(f"Blank 01_05_A_Debt_corp region at order={order}")
        kind = _region_kind(name)
        if kind == "federal_district_total":
            current_federal_district = name
            federal_district_name = name
        elif kind == "country_total":
            federal_district_name = None
        else:
            federal_district_name = current_federal_district

        out.append(
            Cbr0105ADebtCorpRegionSpec(
                code=f"0105a_region_{order:03d}",
                source_name=name,
                canonical_name=_CURRENT_SOURCE_ALIASES.get(_normalize_region_name(name), name),
                region_kind=kind,
                federal_district_name=federal_district_name,
                order=order,
            )
        )
    return tuple(out)


def _validate_layout_compatible(
    current: tuple[Cbr0105ADebtCorpRegionSpec, ...],
    latest: tuple[Cbr0105ADebtCorpRegionSpec, ...],
    *,
    current_date: str,
    latest_date: str,
) -> None:
    if len(current) != len(latest):
        raise ValueError(
            "01_05_A_Debt_corp geographic layout changed and cannot be normalized by position: "
            f"date={current_date}, rows={len(current)}, latest_date={latest_date}, "
            f"latest_rows={len(latest)}"
        )

    for old, new in zip(current, latest, strict=True):
        if old.code != new.code or old.region_kind != new.region_kind:
            raise ValueError(
                "01_05_A_Debt_corp geographic structure changed: "
                f"date={current_date}, order={old.order}, old_kind={old.region_kind!r}, "
                f"latest_kind={new.region_kind!r}"
            )
        old_name = _normalize_region_name(old.source_name)
        latest_name = _normalize_region_name(new.source_name)
        if old_name != latest_name:
            mapped_name = _CURRENT_SOURCE_ALIASES.get(old_name)
            if mapped_name is None or _normalize_region_name(mapped_name) != latest_name:
                raise ValueError(
                    "01_05_A_Debt_corp geography changed without an explicit local alias: "
                    f"date={current_date}, order={old.order}, old={old.source_name!r}, "
                    f"latest={new.source_name!r}"
                )


def normalize_cbr_0105a_debt_corp_regions_to_latest(
    parsed_files: list[ParsedCbr0105ADebtCorpFile]
    | tuple[ParsedCbr0105ADebtCorpFile, ...],
) -> tuple[ParsedCbr0105ADebtCorpFile, ...]:
    """Приводит все подписи к виду последней доступной даты выбранного набора.

    Нормализация остается локальной для серии. Исходное имя всегда сохраняется в
    ``region_source_name``; общий междоменный справочник регионов здесь не создается.
    """
    if not parsed_files:
        return ()

    latest_file = max(parsed_files, key=lambda item: item.report_date)
    latest_by_code = {item.code: item for item in latest_file.regions}
    normalized_files: list[ParsedCbr0105ADebtCorpFile] = []

    for parsed in parsed_files:
        _validate_layout_compatible(
            parsed.regions,
            latest_file.regions,
            current_date=parsed.report_date,
            latest_date=latest_file.report_date,
        )
        updated_regions = tuple(
            replace(
                region,
                canonical_name=latest_by_code[region.code].canonical_name,
                federal_district_name=(
                    latest_by_code[region.code].federal_district_name
                    if region.region_kind != "country_total"
                    else None
                ),
            )
            for region in parsed.regions
        )
        canonical_names = {item.code: item.canonical_name for item in updated_regions}
        district_names = {item.code: item.federal_district_name for item in updated_regions}
        stream = parsed.df_stream.copy()
        stream["region_name"] = stream["region_code"].map(canonical_names)
        stream["federal_district_name"] = stream["region_code"].map(district_names)
        normalized_files.append(replace(parsed, regions=updated_regions, df_stream=stream))

    return tuple(sorted(normalized_files, key=lambda item: item.report_date))


__all__ = [
    "build_cbr_0105a_debt_corp_region_specs",
    "normalize_cbr_0105a_debt_corp_regions_to_latest",
]
