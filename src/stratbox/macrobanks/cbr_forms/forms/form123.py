"""
Форма 123 (быстрая версия):
- строится lookup по каждой дате: regn -> {acc:int -> value:str}
- формулы парсятся один раз
- дальше только dict.get(), без фильтраций DataFrame в глубоких циклах
"""

from __future__ import annotations

import re
import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_forms.common.formulas import get_formulas_for
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig, run_dates_to_dbf_df
from stratbox.macrobanks.cbr_forms.common.dbf_picker import LayoutCandidates


FORM = "123"

DEFAULT_CANDIDATES = LayoutCandidates(
    regn_candidates=["REGN"],
    a_candidates=["C1"],   # код строки/показателя
    b_candidates=["C3"],   # значение
)
DEFAULT_PREFER = "123D"


def build_url(d: pd.Timestamp) -> str:
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/123-{ymd}.rar"


def _norm_regn(x) -> str:
    return re.sub(r"\D+", "", "" if x is None else str(x))


def _norm_acc_int(x) -> int:
    s = "" if x is None else str(x)
    s = re.sub(r"\D+", "", s)
    return int(s) if s else -1


def _value_to_str(v) -> str:
    if v is None:
        return "0"
    if isinstance(v, float) and np.isnan(v):
        return "0"
    s = str(v).strip().replace(",", ".")
    return s if s else "0"


def build_long(
    date_dbf_list: list[tuple[str, pd.DataFrame]],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    """
    (дата, df_dbf) + банки + формулы -> df_long.
    """
    fdf = get_formulas_for(formulas_df, form=FORM, kind="formula")
    if len(fdf) == 0:
        raise RuntimeError("No formulas for form 123 in formulas_df.")

    # порядок показателей
    indicator_order = {row["name"]: i for i, row in fdf.iterrows()}

    # парсим формулы один раз
    parsed: list[tuple[str, list[str]]] = []
    for _, fr in fdf.iterrows():
        name = str(fr["name"])
        expr = str(fr["expression"])
        tokens = re.findall(r"\d+|[+]{1}|[-]{1}", expr)
        parsed.append((name, tokens))

    # подготовим список банков (быстрее, чем iterrows каждый раз)
    banks = [(str(r["bank"]), str(int(r["regn"]))) for _, r in banks_df.iterrows()]

    rows = []

    for date_str, df_dbf in date_dbf_list:
        if df_dbf is None or len(df_dbf) == 0:
            continue

        # строим lookup: regn -> {acc -> val}
        d = df_dbf.copy()
        d["REGN_N"] = d["REGN"].map(_norm_regn)
        d["ACC"] = d["A"].map(_norm_acc_int)
        d["VAL"] = d["B"].map(_value_to_str)

        # drop duplicates по (REGN, ACC) — оставляем первый (как и раньше)
        d = d.dropna(subset=["REGN_N"])
        d = d.drop_duplicates(subset=["REGN_N", "ACC"], keep="first")

        reg_map: dict[str, dict[int, str]] = {}
        for regn, sub in d.groupby("REGN_N", sort=False):
            reg_map[regn] = dict(zip(sub["ACC"].tolist(), sub["VAL"].tolist()))

        # считаем
        for bank_name, regn_bank in banks:
            bm = reg_map.get(regn_bank, {})

            for name, tokens in parsed:
                acc = ""
                for t in tokens:
                    if t in ["+", "-"]:
                        acc += t
                    else:
                        acc += bm.get(int(t), "0")
                rows.append(
                    {"Дата": date_str, "Банк": bank_name, "Показатель": name, "Значение": "=" + acc}
                )

    df_long = pd.DataFrame(rows)
    print(f"[INFO] 123 long rows: {len(df_long)}")
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
        progress_desc="CBR 123",
    )
    return build_long(date_dbf_list, banks_df, formulas_df)
