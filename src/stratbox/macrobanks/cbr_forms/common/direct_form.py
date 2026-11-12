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

from dataclasses import dataclass, field
from typing import Any, Callable
import re
from decimal import Decimal, InvalidOperation

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_forms.common.models import get_model_rows


def _is_missing_scalar(value: Any) -> bool:
    """
    Функция определяет пустое скалярное значение pandas/NumPy.
    """
    if value is None:
        return True
    try:
        result = pd.isna(value)
    except Exception:
        return False
    return bool(result) if isinstance(result, (bool, np.bool_)) else False


def normalize_regn(value: Any) -> str:
    """
    Функция приводит регистрационный номер к строке из цифр.

    Целочисленные значения, пришедшие из pandas как ``1000.0``, не должны
    превращаться в ``10000`` после простого удаления нецифровых символов.
    """
    if value is None:
        return ""
    if isinstance(value, (float, np.floating)):
        if np.isnan(value):
            return ""
        if float(value).is_integer():
            return str(int(value))
    if isinstance(value, (int, np.integer)):
        return str(int(value))

    text = str(value).strip()
    if re.fullmatch(r"[0-9]+\.0+", text):
        return text.split(".", 1)[0]
    return re.sub(r"\D+", "", text)


def normalize_code_plain(value: Any) -> str:
    """
    Функция нормализует строковый код только удалением крайних пробелов.

    Такой режим используется для 802: коды ``2.1.1`` и ``31.3`` являются
    идентификаторами и не должны преобразовываться в числа.
    """
    return "" if _is_missing_scalar(value) else str(value).strip()


def normalize_code_metric(value: Any) -> str:
    """
    Функция нормализует коды нормативов, включая кириллическую/латинскую H.
    """
    text = "" if _is_missing_scalar(value) else str(value)
    text = re.sub(r"\s+", "", text.strip().upper())
    return text.replace("Н", "H")


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


@dataclass(frozen=True)
class DirectDatasetSpec:
    """
    Класс описывает физическую структуру одного логического dataset формы.

    ``measure_fields`` задает обязательные каналы ``measure -> поле DBF``.
    ``optional_measure_fields`` описывает дополнительные физические каналы,
    которые могут отсутствовать в отдельных версиях схемы источника.
    Семантическая модель содержит только имя measure и не знает конкретного
    физического имени поля.
    """

    form: str
    dataset: str
    bank_fields: tuple[str, ...]
    code_fields: tuple[str, ...]
    measure_fields: dict[str, tuple[str, ...]]
    optional_measure_fields: dict[str, tuple[str, ...]] = field(default_factory=dict)
    prefer_stem_contains: str | None = None
    code_normalizer: Callable[[Any], str] = normalize_code_plain
    code_aliases: dict[str, str] = field(default_factory=dict)


def _build_alias_map(spec: DirectDatasetSpec) -> dict[str, str]:
    """
    Функция нормализует технические алиасы кодов конкретного dataset.
    """
    aliases: dict[str, str] = {}
    for source, target in spec.code_aliases.items():
        source_n = spec.code_normalizer(source)
        target_n = spec.code_normalizer(target)
        if source_n:
            aliases[source_n] = target_n
    return aliases


def _normalize_code(value: Any, spec: DirectDatasetSpec, alias_map: dict[str, str]) -> str:
    """
    Функция нормализует код строки и применяет физические алиасы формы.
    """
    code = spec.code_normalizer(value)
    return alias_map.get(code, code)


def normalize_direct_snapshot(raw: pd.DataFrame, spec: DirectDatasetSpec) -> pd.DataFrame:
    alias_map = _build_alias_map(spec)
    frame = raw.copy()
    frame["REGN"] = frame["REGN"].map(normalize_regn)
    frame["CODE"] = frame["CODE"].map(lambda value: _normalize_code(value, spec, alias_map))
    return frame.loc[frame["REGN"].ne("") & frame["CODE"].ne("")].reset_index(drop=True)


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
