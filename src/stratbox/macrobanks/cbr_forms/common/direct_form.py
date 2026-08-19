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

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_forms.common.models import get_model_rows
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig, run_dates_to_selected_dbf_df


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
    return "" if value is None else str(value).strip()


def normalize_code_metric(value: Any) -> str:
    """
    Функция нормализует коды нормативов, включая кириллическую/латинскую H.
    """
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", "", text.strip().upper())
    return text.replace("Н", "H")


def _value_to_output(value: Any) -> float | str:
    """
    Функция сохраняет различие между пустым значением и настоящим нулем.
    """
    if value is None:
        return ""
    if isinstance(value, (float, np.floating)) and np.isnan(value):
        return ""
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)

    text = str(value).strip()
    if not text:
        return ""

    numeric = text.replace(" ", "").replace("\xa0", "").replace(",", ".")
    try:
        return float(numeric)
    except Exception:
        return text


@dataclass(frozen=True)
class DirectDatasetSpec:
    """
    Класс описывает физическую структуру одного логического dataset формы.

    ``measure_fields`` задается как ``semantic_measure -> варианты поля DBF``.
    Семантическая модель при этом содержит только имя measure, но не знает
    конкретного физического поля источника.
    """

    form: str
    dataset: str
    progress_desc: str
    build_url: Callable[[pd.Timestamp], str]
    bank_fields: tuple[str, ...]
    code_fields: tuple[str, ...]
    measure_fields: dict[str, tuple[str, ...]]
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


def run_direct_dataset_raw(
    *,
    dates: list[pd.Timestamp],
    spec: DirectDatasetSpec,
    cfg: RunnerConfig | None = None,
    show_progress: bool = True,
) -> list[tuple[str, pd.DataFrame]]:
    """
    Функция загружает физические данные dataset и возвращает normalized raw.

    Каждый DataFrame содержит ``REGN``, ``CODE`` и все семантические measure,
    заявленные в ``spec.measure_fields``. Пустые исходные значения не заменяются
    нулями.
    """
    field_candidates: dict[str, list[str] | tuple[str, ...]] = {
        "REGN": spec.bank_fields,
        "CODE": spec.code_fields,
    }
    field_candidates.update(spec.measure_fields)

    loaded = run_dates_to_selected_dbf_df(
        dates=dates,
        build_url=spec.build_url,
        field_candidates=field_candidates,
        prefer_stem_contains=spec.prefer_stem_contains,
        cfg=cfg,
        show_progress=show_progress,
        progress_desc=spec.progress_desc,
    )

    alias_map = _build_alias_map(spec)
    normalized: list[tuple[str, pd.DataFrame]] = []
    for date_str, raw in loaded:
        frame = raw.copy()
        frame["REGN"] = frame["REGN"].map(normalize_regn)
        frame["CODE"] = frame["CODE"].map(lambda value: _normalize_code(value, spec, alias_map))
        frame = frame[(frame["REGN"] != "") & (frame["CODE"] != "")].copy()
        normalized.append((date_str, frame.reset_index(drop=True)))

    return normalized


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

    unknown_measures = sorted(set(direct_model["measure"]) - set(spec.measure_fields))
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
        frame = frame.drop_duplicates(subset=["REGN", "CODE"], keep="first")

        bank_map: dict[str, dict[str, dict[str, Any]]] = {}
        for regn, group in frame.groupby("REGN", sort=False):
            codes: dict[str, dict[str, Any]] = {}
            for _, source_row in group.iterrows():
                code = str(source_row["CODE"])
                codes[code] = {
                    measure: source_row.get(measure)
                    for measure in spec.measure_fields
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
    print(f"[INFO] {spec.form} long rows: {len(result)}")
    return result, indicator_order


def run_direct_form(
    *,
    dates: list[pd.Timestamp],
    banks_df: pd.DataFrame,
    model_df: pd.DataFrame,
    spec: DirectDatasetSpec,
    cfg: RunnerConfig | None = None,
    show_progress: bool = True,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Функция выполняет полный цикл одного direct-dataset формы.
    """
    raw = run_direct_dataset_raw(
        dates=dates,
        spec=spec,
        cfg=cfg,
        show_progress=show_progress,
    )
    return build_direct_long(
        date_raw_list=raw,
        banks_df=banks_df,
        model_df=model_df,
        spec=spec,
    )
