"""
Общий движок прямых наборов данных отчетных форм Банка России.

Движок разделяет три уровня:
- Python-модуль формы описывает физические поля DBF;
- ``models/formXXX.csv`` описывает семантические строки;
- общий код соединяет физические данные с моделью и формирует canonical long.

Один dataset может иметь несколько физических каналов значений. Например,
форма 802 хранит ``total`` и три вида консолидационных корректировок, тогда
как стандартная пользовательская витрина использует ``total``.
"""

from __future__ import annotations

from typing import Any
from decimal import Decimal, InvalidOperation

import numpy as np
import pandas as pd

from stratbox.domains.cbr.calculations.reporting_forms.model import get_model_rows
from stratbox.domains.cbr.methods.tables.reporting_forms.layouts.schema import DirectDatasetSpec, normalize_regn, _build_alias_map, _normalize_code, _is_missing_scalar


def _value_to_output(value: Any) -> int | Decimal | str:
    """
    Функция сохраняет различие между пустым значением и настоящим нулем.
    """
    if _is_missing_scalar(value):
        return ""
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, Decimal):
        return value

    text = str(value).strip()
    if not text:
        return ""

    numeric = text.replace(" ", "").replace("\xa0", "").replace(",", ".")
    try:
        decimal = Decimal(numeric)
    except InvalidOperation:
        return text
    if not decimal.is_finite():
        return text
    return int(decimal) if decimal == decimal.to_integral_value() else decimal


def build_direct_long(
    *,
    date_raw_list: list[tuple[str, pd.DataFrame]],
    banks_df: pd.DataFrame,
    model_df: pd.DataFrame,
    spec: DirectDatasetSpec,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Функция соединяет normalized raw с семантической моделью direct-строк.
    """
    direct_model = get_model_rows(model_df, kind="direct", dataset=spec.dataset)
    if len(direct_model) == 0:
        raise RuntimeError(f"No direct model rows for form={spec.form}, dataset={spec.dataset}.")

    physical_measures = {**spec.measure_fields, **spec.optional_measure_fields}
    unknown_measures = sorted(set(direct_model["measure"]) - set(physical_measures))
    if unknown_measures:
        raise RuntimeError(
            f"Model {spec.form}/{spec.dataset} uses measures absent in physical spec: {unknown_measures}"
        )

    alias_map = _build_alias_map(spec)
    indicators: list[dict[str, Any]] = []
    for _, row in direct_model.iterrows():
        indicators.append(
            {
                "id": str(row["id"]),
                "order": int(row["order"]),
                "source_code": _normalize_code(row["source_code"], spec, alias_map),
                "display_code": str(row["source_code"]),
                "measure": str(row["measure"]),
                "name": str(row["name"]),
                "section": str(row["section"]),
                "unit": str(row["unit"]),
            }
        )

    indicator_order = {item["id"]: item["order"] for item in indicators}
    banks = [(str(row["bank"]), normalize_regn(row["regn"])) for _, row in banks_df.iterrows()]

    output_rows: list[dict[str, Any]] = []
    for date_str, raw in date_raw_list:
        frame = raw.copy()
        duplicate_mask = frame.duplicated(subset=["REGN", "CODE"], keep=False)
        if duplicate_mask.any():
            sample = frame.loc[duplicate_mask, ["REGN", "CODE"]].head(10)
            raise RuntimeError(
                f"Duplicate physical keys for form={spec.form}, dataset={spec.dataset}: "
                f"{sample.to_dict('records')}"
            )

        bank_map: dict[str, dict[str, dict[str, Any]]] = {}
        for regn, group in frame.groupby("REGN", sort=False):
            codes: dict[str, dict[str, Any]] = {}
            for _, source_row in group.iterrows():
                code = str(source_row["CODE"])
                codes[code] = {
                    measure: source_row.get(measure)
                    for measure in physical_measures
                }
            bank_map[str(regn)] = codes

        for bank_name, bank_regn in banks:
            source_codes = bank_map.get(bank_regn, {})
            for indicator in indicators:
                source = source_codes.get(indicator["source_code"], {})
                value = _value_to_output(source.get(indicator["measure"]))
                output_rows.append(
                    {
                        "Форма": spec.form,
                        "Дата": date_str,
                        "REGN": bank_regn,
                        "Банк": bank_name,
                        "IndicatorId": indicator["id"],
                        "Код": indicator["display_code"],
                        "Показатель": indicator["name"],
                        "Раздел": indicator["section"],
                        "Measure": indicator["measure"],
                        "Значение": value,
                        "Единица": indicator["unit"],
                    }
                )

    columns = [
        "Форма",
        "Дата",
        "REGN",
        "Банк",
        "IndicatorId",
        "Код",
        "Показатель",
        "Раздел",
        "Measure",
        "Значение",
        "Единица",
    ]
    result = pd.DataFrame(output_rows, columns=columns)
    return result, indicator_order
