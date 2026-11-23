"""Shared published industry dimension used by loan stock and loan flow tables."""

from __future__ import annotations

import re

from stratbox.domains.cbr.tables.corporate_lending.industry.normalization import normalize_industry_text

from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySpec as Cbr0105ADebtCorpIndustrySpec


CBR_0105A_DEBT_CORP_UNIT = "million_rubles"
CBR_0105A_DEBT_CORP_UNIT_NAME_RU = "млн руб."




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



def clean_cbr_0105a_source_label(value: object) -> str:
    """Убирает служебные подчеркивания и маркер ``из них`` из подписи."""
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ")
    text = re.sub(r"_+", " ", text)
    text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    text = re.sub(r",?\s*из\s+них\s*:?\s*$", "", text, flags=re.I).strip(" ,:")
    return text




def resolve_cbr_0105a_debt_corp_industries(
    headers: list[object] | tuple[object, ...],
) -> tuple[Cbr0105ADebtCorpIndustrySpec, ...]:
    """Resolve the complete method input in the published column order."""
    known = {normalize_industry_text(spec.canonical_name_ru): spec
             for spec in CBR_0105A_DEBT_CORP_INDUSTRY_SPECS}
    resolved = tuple(known.get(normalize_industry_text(value)) for value in headers)
    if None in resolved or len(set(resolved)) != len(resolved) or len(resolved) != len(known):
        raise ValueError("CBR industry headers are incomplete or ambiguous")
    return resolved


def select_industry_headers(headers):
    known = {normalize_industry_text(spec.canonical_name_ru) for spec in CBR_0105A_DEBT_CORP_INDUSTRY_SPECS}
    included, unmapped = [], []
    for index, label in headers:
        (included if normalize_industry_text(label) in known else unmapped).append((index, label))
    specs = resolve_cbr_0105a_debt_corp_industries([label for _, label in included])
    return included, specs, tuple(clean_cbr_0105a_source_label(label) for _, label in unmapped)
