"""Расчетные отрасли для потока Банка России ``01_05_A_Debt_corp``."""

from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_industries.contracts import (
    Cbr0105ADebtCorpApkCalculationResult,
    Cbr0105ADebtCorpIndustrySpec,
)
from stratbox.macrobanks.cbr_industries.parser import (
    STREAM_COLUMNS,
    concat_cbr_0105a_debt_corp_streams,
    optimize_cbr_0105a_debt_corp_stream_dtypes,
)


CBR_0105A_DEBT_CORP_APK_INDUSTRY_SPEC = Cbr0105ADebtCorpIndustrySpec(
    code="apk",
    canonical_name_ru="АПК",
    parent_code=None,
    hierarchy_level=0,
    order=27,
)

CBR_0105A_DEBT_CORP_LPK_FORMULA_RU = (
    "Обработка древесины и производство изделий из дерева "
    "+ Сельское хозяйство, охота и лесное хозяйство "
    "− Сельское хозяйство, охота и предоставление услуг в этих областях"
)
CBR_0105A_DEBT_CORP_APK_FORMULA_RU = (
    "Сельское хозяйство, охота и предоставление услуг в этих областях "
    "+ Производство пищевых продуктов, включая напитки, и табака "
    "+ Производство машин и оборудования для сельского и лесного хозяйства "
    "+ ЛПК"
)

_AGRICULTURE_CODE = "agriculture_hunting_services"
_AGRICULTURE_AND_FORESTRY_CODE = "agriculture_hunting_forestry"
_FOOD_CODE = "manufacturing_food_beverages_tobacco"
_AGRICULTURAL_MACHINERY_CODE = "manufacturing_machinery_agriculture_forestry"
_WOOD_PRODUCTS_CODE = "manufacturing_wood_products"

CBR_0105A_DEBT_CORP_APK_SOURCE_INDUSTRY_CODES: tuple[str, ...] = (
    _AGRICULTURE_CODE,
    _AGRICULTURE_AND_FORESTRY_CODE,
    _FOOD_CODE,
    _AGRICULTURAL_MACHINERY_CODE,
    _WOOD_PRODUCTS_CODE,
)

_OBSERVATION_KEY = (
    "report_date",
    "measure",
    "currency_scope",
    "region_code",
)
_REQUIRED_COLUMNS = set(STREAM_COLUMNS)


class Cbr0105ADebtCorpDerivedIndustryError(ValueError):
    """Структурированная ошибка расчета производной отрасли."""

    def __init__(self, code: str, message: str, *, details: dict[str, object] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def _raise(code: str, message: str, **details: object) -> None:
    raise Cbr0105ADebtCorpDerivedIndustryError(code, message, details=details)


def _object_frame(df_stream: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    frame = df_stream.loc[:, list(columns)].copy()
    for column in columns:
        frame[column] = frame[column].astype("object")
    return frame


def calculate_cbr_0105a_debt_corp_apk_industry(
    df_stream: pd.DataFrame,
) -> Cbr0105ADebtCorpApkCalculationResult:
    """Добавляет в поток расчетную отрасль ``АПК``.

    Расчет выполняется отдельно для каждой комбинации даты, региона, вида
    задолженности и валютного охвата. ЛПК используется как промежуточный компонент:

    ``деревообработка + (сельское хозяйство, охота и лесное хозяйство
    - сельское хозяйство, охота и услуги)``.

    АПК затем равен сельскому хозяйству, пищевой промышленности, производству
    техники для сельского и лесного хозяйства и рассчитанному ЛПК.
    """
    if df_stream.empty:
        _raise("APK_EMPTY_INPUT", "Невозможно рассчитать АПК: поток пуст.")

    missing_columns = sorted(_REQUIRED_COLUMNS - set(df_stream.columns))
    if missing_columns:
        _raise(
            "APK_MISSING_COLUMNS",
            f"В потоке отсутствуют обязательные поля: {missing_columns}",
            columns=tuple(missing_columns),
        )

    industry_values = df_stream["industry_code"].astype("object")
    if industry_values.eq(CBR_0105A_DEBT_CORP_APK_INDUSTRY_SPEC.code).any():
        _raise(
            "APK_ALREADY_PRESENT",
            "Поток уже содержит расчетную отрасль АПК.",
            industry_code=CBR_0105A_DEBT_CORP_APK_INDUSTRY_SPEC.code,
        )

    source_codes = set(industry_values.dropna().astype(str).unique())
    missing_industries = tuple(
        code
        for code in CBR_0105A_DEBT_CORP_APK_SOURCE_INDUSTRY_CODES
        if code not in source_codes
    )
    if missing_industries:
        _raise(
            "APK_MISSING_SOURCE_INDUSTRIES",
            "Невозможно рассчитать АПК: отсутствуют исходные отрасли.",
            industry_codes=missing_industries,
        )

    component_columns = (*_OBSERVATION_KEY, "industry_code", "value")
    components = df_stream.loc[
        industry_values.isin(CBR_0105A_DEBT_CORP_APK_SOURCE_INDUSTRY_CODES),
        list(component_columns),
    ].copy()
    for column in (*_OBSERVATION_KEY, "industry_code"):
        components[column] = components[column].astype("object")

    duplicate_mask = components.duplicated(
        [*_OBSERVATION_KEY, "industry_code"],
        keep=False,
    )
    if duplicate_mask.any():
        preview = components.loc[
            duplicate_mask,
            [*_OBSERVATION_KEY, "industry_code"],
        ].head(10)
        _raise(
            "APK_DUPLICATE_COMPONENT",
            "Исходный поток содержит несколько наблюдений одного компонента АПК.",
            duplicate_rows=int(duplicate_mask.sum()),
            examples=tuple(preview.to_dict("records")),
        )

    expected_groups = _object_frame(df_stream, _OBSERVATION_KEY).drop_duplicates()
    expected_index = pd.MultiIndex.from_frame(expected_groups, names=_OBSERVATION_KEY)

    values = components.pivot(
        index=list(_OBSERVATION_KEY),
        columns="industry_code",
        values="value",
    )
    values = values.reindex(
        index=expected_index,
        columns=list(CBR_0105A_DEBT_CORP_APK_SOURCE_INDUSTRY_CODES),
    )
    values = values.astype("Float64")

    missing_mask = values.isna()
    if missing_mask.any(axis=None):
        missing_by_industry = {
            str(column): int(missing_mask[column].sum())
            for column in values.columns
            if int(missing_mask[column].sum()) > 0
        }
        _raise(
            "APK_INCOMPLETE_COMPONENT_VALUES",
            (
                "Невозможно рассчитать АПК: для части комбинаций даты, региона, "
                "показателя и валютного охвата отсутствуют компоненты или значения."
            ),
            group_count=int(missing_mask.any(axis=1).sum()),
            missing_by_industry=missing_by_industry,
        )

    forestry_component = (
        values[_AGRICULTURE_AND_FORESTRY_CODE]
        - values[_AGRICULTURE_CODE]
    )
    lpk_value = values[_WOOD_PRODUCTS_CODE] + forestry_component
    apk_value = (
        values[_AGRICULTURE_CODE]
        + values[_FOOD_CODE]
        + values[_AGRICULTURAL_MACHINERY_CODE]
        + lpk_value
    )

    calculated = apk_value.rename("apk_value").reset_index()
    template = df_stream.loc[
        industry_values.eq(_AGRICULTURE_CODE),
        list(STREAM_COLUMNS),
    ].copy()
    for column in _OBSERVATION_KEY:
        template[column] = template[column].astype("object")
    duplicate_template = template.duplicated(list(_OBSERVATION_KEY), keep=False)
    if duplicate_template.any():
        _raise(
            "APK_DUPLICATE_TEMPLATE",
            "Невозможно однозначно сформировать строки АПК из исходного потока.",
            duplicate_rows=int(duplicate_template.sum()),
        )

    derived = template.merge(
        calculated,
        on=list(_OBSERVATION_KEY),
        how="inner",
        validate="one_to_one",
        sort=False,
    )
    if len(derived) != len(expected_groups):
        _raise(
            "APK_GROUP_COUNT_MISMATCH",
            "Количество рассчитанных строк АПК не совпадает с числом наблюдений.",
            expected_groups=int(len(expected_groups)),
            actual_groups=int(len(derived)),
        )

    for column in (
        "industry_code",
        "industry_name_ru",
        "industry_source_name",
        "industry_parent_code",
        "source_column",
    ):
        derived[column] = derived[column].astype("object")

    spec = CBR_0105A_DEBT_CORP_APK_INDUSTRY_SPEC
    derived["industry_code"] = spec.code
    derived["industry_name_ru"] = spec.canonical_name_ru
    derived["industry_source_name"] = "Расчетный показатель Stratbox: АПК"
    derived["industry_parent_code"] = spec.parent_code
    derived["industry_hierarchy_level"] = spec.hierarchy_level
    derived["industry_order"] = spec.order
    derived["value"] = pd.array(derived.pop("apk_value"), dtype="Float64")
    # Производная строка относится к той же исходной строке региона и листу,
    # но не к одной конкретной ячейке/колонке Excel.
    derived["source_column"] = None

    df_apk = derived.loc[:, list(STREAM_COLUMNS)]
    df_apk = optimize_cbr_0105a_debt_corp_stream_dtypes(df_apk)
    augmented = concat_cbr_0105a_debt_corp_streams((df_stream, df_apk))
    augmented = augmented.sort_values(
        ["report_date", "sheet_order", "region_order", "industry_order"],
        kind="stable",
    ).reset_index(drop=True)

    return Cbr0105ADebtCorpApkCalculationResult(
        industry=spec,
        source_industry_codes=CBR_0105A_DEBT_CORP_APK_SOURCE_INDUSTRY_CODES,
        lpk_formula_ru=CBR_0105A_DEBT_CORP_LPK_FORMULA_RU,
        apk_formula_ru=CBR_0105A_DEBT_CORP_APK_FORMULA_RU,
        df_apk=df_apk,
        df_stream=augmented,
        source_rows_used=int(len(components)),
        groups_calculated=int(len(df_apk)),
        rows_added=int(len(df_apk)),
    )


__all__ = [
    "CBR_0105A_DEBT_CORP_APK_FORMULA_RU",
    "CBR_0105A_DEBT_CORP_APK_INDUSTRY_SPEC",
    "CBR_0105A_DEBT_CORP_APK_SOURCE_INDUSTRY_CODES",
    "CBR_0105A_DEBT_CORP_LPK_FORMULA_RU",
    "Cbr0105ADebtCorpDerivedIndustryError",
    "calculate_cbr_0105a_debt_corp_apk_industry",
]
