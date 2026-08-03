"""Явная схема серии Банка России ``01_05_A_Debt_corp``."""

from __future__ import annotations

import re

from stratbox.macrobanks.cbr_industries.contracts import (
    Cbr0105ADebtCorpIndustrySpec,
    Cbr0105ADebtCorpSheetSpec,
)


CBR_0105A_DEBT_CORP_SERIES_CODE = "01_05_A_Debt_corp"
CBR_0105A_DEBT_CORP_UNIT = "million_rubles"
CBR_0105A_DEBT_CORP_UNIT_NAME_RU = "млн руб."


CBR_0105A_DEBT_CORP_SHEET_SPECS: tuple[Cbr0105ADebtCorpSheetSpec, ...] = (
    Cbr0105ADebtCorpSheetSpec(
        code="debt_rubles",
        measure="debt",
        measure_name_ru="Задолженность",
        currency_scope="rubles",
        currency_scope_name_ru="В рублях",
        order=1,
    ),
    Cbr0105ADebtCorpSheetSpec(
        code="overdue_debt_rubles",
        measure="overdue_debt",
        measure_name_ru="Просроченная задолженность",
        currency_scope="rubles",
        currency_scope_name_ru="В рублях",
        order=2,
    ),
    Cbr0105ADebtCorpSheetSpec(
        code="debt_foreign_currency_and_precious_metals",
        measure="debt",
        measure_name_ru="Задолженность",
        currency_scope="foreign_currency_and_precious_metals",
        currency_scope_name_ru="В иностранной валюте и драгоценных металлах",
        order=3,
    ),
    Cbr0105ADebtCorpSheetSpec(
        code="overdue_debt_foreign_currency_and_precious_metals",
        measure="overdue_debt",
        measure_name_ru="Просроченная задолженность",
        currency_scope="foreign_currency_and_precious_metals",
        currency_scope_name_ru="В иностранной валюте и драгоценных металлах",
        order=4,
    ),
    Cbr0105ADebtCorpSheetSpec(
        code="debt_total",
        measure="debt",
        measure_name_ru="Задолженность",
        currency_scope="total",
        currency_scope_name_ru="Итого",
        order=5,
    ),
    Cbr0105ADebtCorpSheetSpec(
        code="overdue_debt_total",
        measure="overdue_debt",
        measure_name_ru="Просроченная задолженность",
        currency_scope="total",
        currency_scope_name_ru="Итого",
        order=6,
    ),
)


CBR_0105A_DEBT_CORP_INDUSTRY_SPECS: tuple[Cbr0105ADebtCorpIndustrySpec, ...] = (
    Cbr0105ADebtCorpIndustrySpec("total", "ВСЕГО", None, 0, 1),
    Cbr0105ADebtCorpIndustrySpec("mining", "Добыча полезных ископаемых", None, 1, 2),
    Cbr0105ADebtCorpIndustrySpec(
        "mining_fuel_energy",
        "Добыча топливно-энергетических полезных ископаемых",
        "mining",
        2,
        3,
    ),
    Cbr0105ADebtCorpIndustrySpec("manufacturing", "Обрабатывающие производства", None, 1, 4),
    Cbr0105ADebtCorpIndustrySpec(
        "manufacturing_food_beverages_tobacco",
        "Производство пищевых продуктов, включая напитки, и табака",
        "manufacturing",
        2,
        5,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "manufacturing_wood_products",
        "Обработка древесины и производство изделий из дерева",
        "manufacturing",
        2,
        6,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "manufacturing_pulp_paper_publishing_printing",
        "Целлюлозно-бумажное производство, издательская и полиграфическая деятельность",
        "manufacturing",
        2,
        7,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "manufacturing_coke_petroleum_nuclear_materials",
        "Производство кокса, нефтепродуктов и ядерных материалов",
        "manufacturing",
        2,
        8,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "manufacturing_chemicals",
        "Химическое производство",
        "manufacturing",
        2,
        9,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "manufacturing_non_metallic_mineral_products",
        "Производство прочих неметаллических минеральных продуктов",
        "manufacturing",
        2,
        10,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "manufacturing_metallurgy_metal_products",
        "Металлургическое производство и производство готовых металлических изделий",
        "manufacturing",
        2,
        11,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "manufacturing_machinery_equipment",
        "Производство машин и оборудования",
        "manufacturing",
        2,
        12,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "manufacturing_machinery_agriculture_forestry",
        "Производство машин и оборудования для сельского и лесного хозяйства",
        "manufacturing_machinery_equipment",
        3,
        13,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "manufacturing_transport_equipment",
        "Производство транспортных средств и оборудования",
        "manufacturing",
        2,
        14,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "manufacturing_automobiles",
        "Производство автомобилей",
        "manufacturing_transport_equipment",
        3,
        15,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "electricity_gas_water",
        "Производство и распределение электроэнергии, газа и воды",
        None,
        1,
        16,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "agriculture_hunting_forestry",
        "Сельское хозяйство, охота и лесное хозяйство",
        None,
        1,
        17,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "agriculture_hunting_services",
        "Сельское хозяйство, охота и предоставление услуг в этих областях",
        "agriculture_hunting_forestry",
        2,
        18,
    ),
    Cbr0105ADebtCorpIndustrySpec("construction", "Строительство", None, 1, 19),
    Cbr0105ADebtCorpIndustrySpec(
        "construction_buildings_structures",
        "Строительство зданий и сооружений",
        "construction",
        2,
        20,
    ),
    Cbr0105ADebtCorpIndustrySpec("transport_communications", "Транспорт и связь", None, 1, 21),
    Cbr0105ADebtCorpIndustrySpec(
        "air_transport_scheduled_and_unscheduled",
        "Деятельность воздушного транспорта, подчиняющегося и не подчиняющегося расписанию",
        "transport_communications",
        2,
        22,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "wholesale_retail_trade_motor_vehicles_household_goods",
        "Оптовая и розничная торговля, ремонт автотранспортных средств, мотоциклов, бытовых изделий и предметов личного пользования",
        None,
        1,
        23,
    ),
    Cbr0105ADebtCorpIndustrySpec(
        "real_estate_renting_business_services",
        "Операции с недвижимым имуществом, аренда и предоставление услуг",
        None,
        1,
        24,
    ),
    Cbr0105ADebtCorpIndustrySpec("other_activities", "Прочие виды деятельности", None, 1, 25),
    Cbr0105ADebtCorpIndustrySpec(
        "completion_of_settlements",
        "На завершение расчетов",
        None,
        1,
        26,
    ),
)


def normalize_cbr_0105a_text(value: object) -> str:
    """Нормализует текст источника, сохраняя его экономический смысл."""
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").replace("ё", "е").replace("Ё", "Е")
    text = re.sub(r"_+", " ", text)
    text = re.sub(r"\bиз\s+них\b\s*:?,?", " ", text, flags=re.I)
    text = re.sub(r"[^0-9A-Za-zА-Яа-я]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def clean_cbr_0105a_source_label(value: object) -> str:
    """Убирает служебные подчеркивания и маркер ``из них`` из подписи."""
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ")
    text = re.sub(r"_+", " ", text)
    text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    text = re.sub(r",?\s*из\s+них\s*:?\s*$", "", text, flags=re.I).strip(" ,:")
    return text


def resolve_cbr_0105a_debt_corp_sheet_spec(title: object) -> Cbr0105ADebtCorpSheetSpec:
    """Распознает смысл листа по полному заголовку в A1, а не по имени вкладки."""
    normalized = normalize_cbr_0105a_text(title)
    required = (
        "задолженность",
        "кредитам",
        "юридическим",
        "лицам",
        "индивидуальным",
        "предпринимателям",
    )
    if not all(token in normalized.split() for token in required):
        raise ValueError(f"01_05_A_Debt_corp sheet title is not recognized: {title!r}")

    measure = "overdue_debt" if "просроченная" in normalized.split() else "debt"
    if "иностранной валюте" in normalized and "драгоценных металлах" in normalized:
        currency_scope = "foreign_currency_and_precious_metals"
    elif "в рублях" in normalized:
        currency_scope = "rubles"
    else:
        currency_scope = "total"

    for spec in CBR_0105A_DEBT_CORP_SHEET_SPECS:
        if spec.measure == measure and spec.currency_scope == currency_scope:
            return spec
    raise ValueError(
        "Unsupported 01_05_A_Debt_corp sheet semantics: "
        f"measure={measure!r}, currency_scope={currency_scope!r}"
    )


def resolve_cbr_0105a_debt_corp_industries(
    headers: list[object] | tuple[object, ...],
) -> tuple[Cbr0105ADebtCorpIndustrySpec, ...]:
    """Строго сопоставляет 26 отраслевых столбцов с явным реестром."""
    non_empty = [value for value in headers if normalize_cbr_0105a_text(value)]
    if len(non_empty) != len(CBR_0105A_DEBT_CORP_INDUSTRY_SPECS):
        raise ValueError(
            "01_05_A_Debt_corp industry header count changed: "
            f"expected={len(CBR_0105A_DEBT_CORP_INDUSTRY_SPECS)}, actual={len(non_empty)}"
        )

    for source_value, spec in zip(non_empty, CBR_0105A_DEBT_CORP_INDUSTRY_SPECS, strict=True):
        actual = normalize_cbr_0105a_text(source_value)
        expected = normalize_cbr_0105a_text(spec.canonical_name_ru)
        if actual != expected:
            raise ValueError(
                "01_05_A_Debt_corp industry header changed: "
                f"order={spec.order}, expected={spec.canonical_name_ru!r}, "
                f"actual={source_value!r}, normalized_actual={actual!r}"
            )
    return CBR_0105A_DEBT_CORP_INDUSTRY_SPECS


__all__ = [
    "CBR_0105A_DEBT_CORP_INDUSTRY_SPECS",
    "CBR_0105A_DEBT_CORP_SERIES_CODE",
    "CBR_0105A_DEBT_CORP_SHEET_SPECS",
    "CBR_0105A_DEBT_CORP_UNIT",
    "CBR_0105A_DEBT_CORP_UNIT_NAME_RU",
    "clean_cbr_0105a_source_label",
    "normalize_cbr_0105a_text",
    "resolve_cbr_0105a_debt_corp_industries",
    "resolve_cbr_0105a_debt_corp_sheet_spec",
]
