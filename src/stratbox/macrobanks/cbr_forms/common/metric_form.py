"""
Общий движок для метрических отчетных форм Банка России.

Метрическая форма — это форма, где показатель не рассчитывается из набора
строк/счетов, а берется напрямую из DBF по коду норматива или метрики.

Типовая структура после универсального чтения DBF:
- REGN: регистрационный номер банка или головной кредитной организации;
- A: код норматива/метрики;
- B: фактическое значение.

Примеры форм:
- 135: обязательные нормативы банка;
- 805: обязательные нормативы банковской группы.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
import re

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_forms.common.dbf_picker import LayoutCandidates
from stratbox.macrobanks.cbr_forms.common.formulas import get_formulas_for
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig, run_dates_to_dbf_df


@dataclass(frozen=True)
class MetricFormSpec:
    """
    Описание конкретной метрической формы.

    Поля:
    - form: короткий код формы в formulas.csv;
    - progress_desc: подпись прогресса при загрузке дат;
    - candidates: варианты имен DBF-полей для REGN/A/B;
    - prefer_stem_contains: подсказка для выбора нужного DBF внутри архива;
    - build_url: функция построения ссылки на архив Банка России;
    - code_aliases: словарь технических замен кодов, если в DBF код записан иначе;
    - missing_value: значение для отсутствующей метрики.
    """

    form: str
    progress_desc: str
    candidates: LayoutCandidates
    prefer_stem_contains: str | None
    build_url: Callable[[pd.Timestamp], str]
    code_aliases: dict[str, str] = field(default_factory=dict)
    missing_value: Any = ""


def _norm_regn(x: Any) -> str:
    """
    Функция приводит регистрационный номер к строке только из цифр.
    """
    return re.sub(r"\D+", "", "" if x is None else str(x))


def _norm_metric_code(x: Any) -> str:
    """
    Функция нормализует код норматива/метрики.

    В отчетности Банка России визуально похожие буквы могут отличаться:
    - латинская H;
    - кириллическая Н.

    Для сопоставления кодов они приводятся к латинской H. В самих названиях
    показателей из formulas.csv ничего не меняется.
    """
    s = "" if x is None else str(x)
    s = s.strip().upper()
    s = re.sub(r"\s+", "", s)
    s = s.replace("Н", "H")
    return s


def _build_alias_map(code_aliases: dict[str, str] | None) -> dict[str, str]:
    """
    Функция нормализует словарь технических замен кодов.
    """
    out: dict[str, str] = {}
    for k, v in (code_aliases or {}).items():
        kk = _norm_metric_code(k)
        vv = _norm_metric_code(v)
        if kk:
            out[kk] = vv
    return out


def _apply_code_alias(code: str, alias_map: dict[str, str]) -> str:
    """
    Функция применяет техническую замену кода, если она задана.
    """
    return alias_map.get(code, code)


def _value_to_excel(v: Any) -> float | str:
    """
    Функция приводит значение DBF к числу для Excel.

    Если значение отсутствует в исходной строке DBF, возвращается пустая строка.
    Так настоящий ноль не смешивается с отсутствием отчетного значения.
    """
    if v is None:
        return ""
    if isinstance(v, float) and np.isnan(v):
        return ""
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)

    s = str(v).strip().replace(",", ".")
    if not s:
        return ""
    try:
        return float(s)
    except Exception:
        return s


def _parse_metric_code(expr: str, alias_map: dict[str, str]) -> str:
    """
    Функция достает код метрики из выражения formulas.csv.

    Поддерживаемый формат:
      NAME_NORM == "H20.0" -> FAKT_ZN
      C1_3 == "Н1.0" -> C2_3
    """
    m = re.search(r"==\s*[\"'](.*?)[\"']", str(expr))
    if not m:
        return ""
    code = _norm_metric_code(m.group(1))
    return _apply_code_alias(code, alias_map)


def build_metric_long(
    *,
    date_dbf_list: list[tuple[str, pd.DataFrame]],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
    spec: MetricFormSpec,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    """
    Функция собирает long-таблицу для метрической формы.

    На выходе формируется таблица:
      Дата | Банк | Показатель | Значение
    """
    fdf = get_formulas_for(formulas_df, form=spec.form, kind="metric")
    if len(fdf) == 0:
        raise RuntimeError(f"No metrics for form {spec.form} in formulas_df (expected kind=metric).")

    alias_map = _build_alias_map(spec.code_aliases)
    indicator_order = {str(row["name"]): i for i, row in fdf.iterrows()}

    metrics: list[tuple[str, str]] = []
    for _, fr in fdf.iterrows():
        name = str(fr["name"])
        expr = str(fr["expression"])
        code = _parse_metric_code(expr, alias_map)
        if not code:
            raise RuntimeError(f"Bad {spec.form} metric expression: name={name}, expr={expr}")
        metrics.append((name, code))

    banks = [(str(r["bank"]), _norm_regn(r["regn"])) for _, r in banks_df.iterrows()]

    rows: list[dict[str, Any]] = []

    for date_str, df_dbf in date_dbf_list:
        if df_dbf is None or len(df_dbf) == 0:
            continue

        d = df_dbf.copy()
        d["REGN_N"] = d["REGN"].map(_norm_regn)
        d["CODE"] = d["A"].map(lambda x: _apply_code_alias(_norm_metric_code(x), alias_map))
        d["VAL"] = d["B"].map(_value_to_excel)

        d = d[(d["REGN_N"] != "") & (d["CODE"] != "")].copy()
        d = d.drop_duplicates(subset=["REGN_N", "CODE"], keep="first")

        reg_map: dict[str, dict[str, Any]] = {}
        for regn, sub in d.groupby("REGN_N", sort=False):
            reg_map[str(regn)] = dict(zip(sub["CODE"].tolist(), sub["VAL"].tolist()))

        for bank_name, regn_bank in banks:
            bank_metrics = reg_map.get(regn_bank, {})
            for name, code in metrics:
                value = bank_metrics.get(code, spec.missing_value)
                rows.append(
                    {
                        "Дата": date_str,
                        "Банк": bank_name,
                        "Показатель": name,
                        "Значение": value,
                    }
                )

    df_long = pd.DataFrame(rows, columns=["Дата", "Банк", "Показатель", "Значение"])
    print(f"[INFO] {spec.form} long rows: {len(df_long)}")
    return df_long, indicator_order


def run_metric_form(
    *,
    dates: list[pd.Timestamp],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
    spec: MetricFormSpec,
    cfg: RunnerConfig | None = None,
    show_progress: bool = True,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    """
    Функция выполняет полный цикл метрической формы:
    скачать архивы, выбрать DBF, прочитать данные и собрать long-таблицу.
    """
    cfg = cfg or RunnerConfig()

    date_dbf_list = run_dates_to_dbf_df(
        dates=dates,
        build_url=spec.build_url,
        candidates=spec.candidates,
        prefer_stem_contains=spec.prefer_stem_contains,
        cfg=cfg,
        show_progress=show_progress,
        progress_desc=spec.progress_desc,
    )
    return build_metric_long(
        date_dbf_list=date_dbf_list,
        banks_df=banks_df,
        formulas_df=formulas_df,
        spec=spec,
    )
