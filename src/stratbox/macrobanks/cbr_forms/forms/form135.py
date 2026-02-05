"""
Форма 135 (быстрая версия, корректно под metric).

По документации:
- файл mmyyyy_135_3.DBF
- поля:
    REGN  (числовой)
    C1_3  (символьный)  Код норматива (например "Н1.0")
    C2_3  (числовой)    Фактическое значение, процент

В formulas.csv для формы 135 используются строки kind=metric вида:
  C1_3 == "Н1.0" -> C2_3

Логика:
- на каждой дате читается DBF в layout REGN/C1_3/C2_3
- строится lookup: regn -> {code -> value_str}
- для каждого банка и метрики берётся значение (без тяжёлых фильтраций pandas)
"""

from __future__ import annotations

import re
import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_forms.common.formulas import get_formulas_for
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig, run_dates_to_dbf_df
from stratbox.macrobanks.cbr_forms.common.dbf_picker import LayoutCandidates


FORM = "135"

DEFAULT_CANDIDATES = LayoutCandidates(
    regn_candidates=["REGN"],
    a_candidates=["C1_3"],  # код норматива
    b_candidates=["C2_3"],  # фактическое значение
)
DEFAULT_PREFER = "135_3"


def build_url(d: pd.Timestamp) -> str:
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/135-{ymd}.rar"


def _norm_regn(x) -> str:
    return re.sub(r"\D+", "", "" if x is None else str(x))


def _norm_code(x) -> str:
    # Нормативы типа "Н1.0" — важны буква+цифры+точка
    s = "" if x is None else str(x)
    s = s.strip().upper()
    s = re.sub(r"\s+", "", s)
    return s


def _value_to_str(v) -> str:
    if v is None:
        return "0"
    if isinstance(v, float) and np.isnan(v):
        return "0"
    s = str(v).strip().replace(",", ".")
    return s if s else "0"


def _parse_metric_code(expr: str) -> str:
    """
    Из выражения вида: C1_3 == "Н1.0" -> C2_3
    достаёт "Н1.0"
    """
    m = re.search(r'==\s*"(.*?)"', expr)
    if not m:
        return ""
    return _norm_code(m.group(1))


def build_long(
    date_dbf_list: list[tuple[str, pd.DataFrame]],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    # для 135 используем kind=metric
    fdf = get_formulas_for(formulas_df, form=FORM, kind="metric")
    if len(fdf) == 0:
        raise RuntimeError("No metrics for form 135 in formulas_df (expected kind=metric).")

    # порядок показателей как в CSV
    indicator_order = {row["name"]: i for i, row in fdf.iterrows()}

    metrics: list[tuple[str, str]] = []  # (name, code)
    for _, fr in fdf.iterrows():
        name = str(fr["name"])
        expr = str(fr["expression"])
        code = _parse_metric_code(expr)
        if not code:
            raise RuntimeError(f"Bad 135 metric expression: name={name}, expr={expr}")
        metrics.append((name, code))

    banks = [(str(r["bank"]), str(int(r["regn"]))) for _, r in banks_df.iterrows()]

    rows = []

    for date_str, df_dbf in date_dbf_list:
        if df_dbf is None or len(df_dbf) == 0:
            continue

        d = df_dbf.copy()
        d["REGN_N"] = d["REGN"].map(_norm_regn)
        d["CODE"] = d["A"].map(_norm_code)   # A=C1_3
        d["VAL"] = d["B"].map(_value_to_str) # B=C2_3

        d = d.dropna(subset=["REGN_N", "CODE"])
        d = d.drop_duplicates(subset=["REGN_N", "CODE"], keep="first")

        # lookup: regn -> {code -> val}
        reg_map: dict[str, dict[str, str]] = {}
        for regn, sub in d.groupby("REGN_N", sort=False):
            reg_map[regn] = dict(zip(sub["CODE"].tolist(), sub["VAL"].tolist()))

        for bank_name, regn_bank in banks:
            bm = reg_map.get(regn_bank, {})
            for name, code in metrics:
                val = bm.get(code, "0")
                rows.append({"Дата": date_str, "Банк": bank_name, "Показатель": name, "Значение": val})

    df_long = pd.DataFrame(rows)
    print(f"[INFO] 135 long rows: {len(df_long)}")
    return df_long, indicator_order


def run(
    *,
    dates: list[pd.Timestamp],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
    candidates: LayoutCandidates | None = None,
    prefer_stem_contains: str | None = None,
    cfg: RunnerConfig | None = None,
    show_progress: bool = True,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    candidates = candidates or DEFAULT_CANDIDATES
    prefer_stem_contains = prefer_stem_contains or DEFAULT_PREFER
    cfg = cfg or RunnerConfig()

    date_dbf_list = run_dates_to_dbf_df(
        dates=dates,
        build_url=build_url,
        candidates=candidates,
        prefer_stem_contains=prefer_stem_contains,
        cfg=cfg,
        show_progress=show_progress,
        progress_desc="CBR 135",
    )
    return build_long(date_dbf_list, banks_df, formulas_df)
