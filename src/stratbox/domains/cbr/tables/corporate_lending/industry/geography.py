"""Published industry geography layout, aliases and source-row validation."""
from __future__ import annotations

import re
from dataclasses import replace

from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustryRegionSpec as Cbr0105ADebtCorpRegionSpec


CBR_0105A_DEBT_CORP_REGION_REFERENCE_DATE = "2026-06-01"
CBR_0105A_DEBT_CORP_EXPECTED_REGION_COUNT = 96

_CBR_0105A_DEBT_CORP_CURRENT_REGION_NAMES: tuple[str, ...] = (
    "РОССИЙСКАЯ ФЕДЕРАЦИЯ",
    "ЦЕНТРАЛЬНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ",
    "Белгородская область",
    "Брянская область",
    "Владимирская область",
    "Воронежская область",
    "Ивановская область",
    "Калужская область",
    "Костромская область",
    "Курская область",
    "Липецкая область",
    "Московская область",
    "Орловская область",
    "Рязанская область",
    "Смоленская область",
    "Тамбовская область",
    "Тверская область",
    "Тульская область",
    "Ярославская область",
    "г. Москва",
    "СЕВЕРО-ЗАПАДНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ",
    "Республика Карелия",
    "Республика Коми",
    "Архангельская область",
    "в том числе Ненецкий автономный округ",
    "Архангельская область без данных по Ненецкому автономному округу",
    "Вологодская область",
    "Калининградская область",
    "Ленинградская область",
    "Мурманская область",
    "Новгородская область",
    "Псковская область",
    "г. Санкт-Петербург",
    "ЮЖНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ",
    "Республика Адыгея (Адыгея)",
    "Республика Калмыкия",
    "Республика Крым",
    "Краснодарский край",
    "Астраханская область",
    "Волгоградская область",
    "Ростовская область",
    "г. Севастополь",
    "СЕВЕРО-КАВКАЗСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ",
    "Республика Дагестан",
    "Республика Ингушетия",
    "Кабардино-Балкарская Республика",
    "Карачаево-Черкесская Республика",
    "Республика Северная Осетия - Алания",
    "Чеченская Республика",
    "Ставропольский край",
    "ПРИВОЛЖСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ",
    "Республика Башкортостан",
    "Республика Марий Эл",
    "Республика Мордовия",
    "Республика Татарстан (Татарстан)",
    "Удмуртская Республика",
    "Чувашская Республика - Чувашия",
    "Пермский край",
    "Кировская область",
    "Нижегородская область",
    "Оренбургская область",
    "Пензенская область",
    "Самарская область",
    "Саратовская область",
    "Ульяновская область",
    "УРАЛЬСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ",
    "Курганская область",
    "Свердловская область",
    "Тюменская область",
    "в том числе Ханты-Мансийский автономный округ - Югра",
    "в том числе Ямало-Ненецкий автономный округ",
    "Тюменская область без данных по Ханты-Мансийскому автономному округу - Югре и Ямало-Ненецкому автономному округу",
    "Челябинская область",
    "СИБИРСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ",
    "Республика Алтай",
    "Республика Тыва",
    "Республика Хакасия",
    "Алтайский край",
    "Красноярский край",
    "Иркутская область",
    "Кемеровская область - Кузбасс",
    "Новосибирская область",
    "Омская область",
    "Томская область",
    "ДАЛЬНЕВОСТОЧНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ",
    "Республика Бурятия",
    "Республика Саха (Якутия)",
    "Забайкальский край",
    "Камчатский край",
    "Приморский край",
    "Хабаровский край",
    "Амурская область",
    "Магаданская область",
    "Сахалинская область",
    "Еврейская автономная область",
    "Чукотский автономный округ",
)

# Номер соответствует order в таблице (нумерация с 1).
_CBR_0105A_DEBT_CORP_SOURCE_ALIASES_BY_ORDER: dict[int, tuple[str, ...]] = {
    81: ("Кемеровская область",),
}


def normalize_cbr_0105a_region_name(value: object) -> str:
    """Strict CBR-series label key, retaining its published 96-row semantics."""
    from stratbox.shared.reference.geography.names import normalize_region_label

    return normalize_region_label(str(value or ""), fold_yo=True) or ""

def _region_kind(name: str) -> str:
    normalized = normalize_cbr_0105a_region_name(name)
    if normalized == "российская федерация":
        return "country_total"
    if "федеральный округ" in normalized:
        return "federal_district_total"
    if normalized.startswith("в том числе"):
        return "included_autonomous_area"
    if "без данных по" in normalized:
        return "exclusive_parent_area"
    return "region"


def _build_reference_layout() -> tuple[Cbr0105ADebtCorpRegionSpec, ...]:
    current_federal_district: str | None = None
    out: list[Cbr0105ADebtCorpRegionSpec] = []
    for order, canonical_name in enumerate(_CBR_0105A_DEBT_CORP_CURRENT_REGION_NAMES, start=1):
        kind = _region_kind(canonical_name)
        if kind == "federal_district_total":
            current_federal_district = canonical_name
            federal_district_name = canonical_name
        elif kind == "country_total":
            federal_district_name = None
        else:
            federal_district_name = current_federal_district
        out.append(
            Cbr0105ADebtCorpRegionSpec(
                code=f"0105a_region_{order:03d}",
                source_name=canonical_name,
                canonical_name=canonical_name,
                region_kind=kind,
                federal_district_name=federal_district_name,
                order=order,
            )
        )
    return tuple(out)


CBR_0105A_DEBT_CORP_REGION_LAYOUT = _build_reference_layout()


def build_cbr_0105a_debt_corp_region_specs(
    source_names: list[str] | tuple[str, ...],
) -> tuple[Cbr0105ADebtCorpRegionSpec, ...]:
    """Строго сопоставляет 96 географических строк с локальным реестром серии."""
    if len(source_names) != CBR_0105A_DEBT_CORP_EXPECTED_REGION_COUNT:
        raise ValueError(
            "01_05_A_Debt_corp geographic row count changed: "
            f"expected={CBR_0105A_DEBT_CORP_EXPECTED_REGION_COUNT}, actual={len(source_names)}"
        )

    out: list[Cbr0105ADebtCorpRegionSpec] = []
    for raw_name, reference in zip(
        source_names,
        CBR_0105A_DEBT_CORP_REGION_LAYOUT,
        strict=True,
    ):
        source_name = re.sub(r"\s+", " ", str(raw_name).replace("\xa0", " ")).strip()
        actual = normalize_cbr_0105a_region_name(source_name)
        allowed = {normalize_cbr_0105a_region_name(reference.canonical_name)}
        allowed.update(
            normalize_cbr_0105a_region_name(alias)
            for alias in _CBR_0105A_DEBT_CORP_SOURCE_ALIASES_BY_ORDER.get(reference.order, ())
        )
        if actual not in allowed:
            raise ValueError(
                "01_05_A_Debt_corp geographic label changed without an explicit local alias: "
                f"order={reference.order}, expected={reference.canonical_name!r}, "
                f"actual={source_name!r}"
            )
        out.append(replace(reference, source_name=source_name))
    return tuple(out)
