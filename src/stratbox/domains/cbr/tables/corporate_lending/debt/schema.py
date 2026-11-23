"""Debt-stock source sheets for the 01_05_A publication profile."""
from __future__ import annotations
from stratbox.domains.cbr.tables.corporate_lending.industry.normalization import normalize_industry_text
from .contracts import Cbr0105ADebtCorpSheetSpec



CBR_0105A_DEBT_CORP_SHEET_SPECS: tuple[Cbr0105ADebtCorpSheetSpec, ...] = (
    Cbr0105ADebtCorpSheetSpec(
        code="debt_rubles",
        measure="debt",
        measure_name_ru="Задолженность",
        currency_scope="rubles",
        currency_scope_name_ru="В рублях",
        workbook_sheet_name="в рублях",
        order=1,
    ),
    Cbr0105ADebtCorpSheetSpec(
        code="overdue_debt_rubles",
        measure="overdue_debt",
        measure_name_ru="Просроченная задолженность",
        currency_scope="rubles",
        currency_scope_name_ru="В рублях",
        workbook_sheet_name="в т.ч. просроч. в рублях",
        order=2,
    ),
    Cbr0105ADebtCorpSheetSpec(
        code="debt_foreign_currency_and_precious_metals",
        measure="debt",
        measure_name_ru="Задолженность",
        currency_scope="foreign_currency_and_precious_metals",
        currency_scope_name_ru="В иностранной валюте и драгоценных металлах",
        workbook_sheet_name="в инвалюте",
        order=3,
    ),
    Cbr0105ADebtCorpSheetSpec(
        code="overdue_debt_foreign_currency_and_precious_metals",
        measure="overdue_debt",
        measure_name_ru="Просроченная задолженность",
        currency_scope="foreign_currency_and_precious_metals",
        currency_scope_name_ru="В иностранной валюте и драгоценных металлах",
        workbook_sheet_name="в т.ч. просроч. в инвалюте",
        order=4,
    ),
    Cbr0105ADebtCorpSheetSpec(
        code="debt_total",
        measure="debt",
        measure_name_ru="Задолженность",
        currency_scope="total",
        currency_scope_name_ru="Итого",
        workbook_sheet_name="итого",
        order=5,
    ),
    Cbr0105ADebtCorpSheetSpec(
        code="overdue_debt_total",
        measure="overdue_debt",
        measure_name_ru="Просроченная задолженность",
        currency_scope="total",
        currency_scope_name_ru="Итого",
        workbook_sheet_name="в т.ч. просроч. итого",
        order=6,
    ),
)


def resolve_cbr_0105a_debt_corp_sheet_spec(
    title: object, *, allow_unrelated: bool = False,
) -> Cbr0105ADebtCorpSheetSpec | None:
    """Распознает смысл листа по полному заголовку в A1, а не по имени вкладки."""
    normalized = normalize_industry_text(title)
    required = (
        "задолженность",
        "кредитам",
        "юридическим",
        "лицам",
        "индивидуальным",
        "предпринимателям",
    )
    if not all(token in normalized.split() for token in required):
        if allow_unrelated:
            return None
        raise ValueError(f"01_05_A_Debt_corp sheet title is not recognized: {title!r}")

    measure = "overdue_debt" if "просроченная" in normalized.split() else "debt"
    if "иностранной валюте" in normalized and "драгоценных металлах" not in normalized:
        raise ValueError("Unrecognized currency scope")
    if "иностранной валюте" in normalized and "в рублях" not in normalized:
        currency_scope = "foreign_currency_and_precious_metals"
    elif "в рублях" in normalized and "иностранной валюте" not in normalized:
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
