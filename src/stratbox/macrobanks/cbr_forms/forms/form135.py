"""
Форма 135 (быстрая версия):
- A = код норматива (C1_3)
- B = фактическое значение (C2_3)
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
    a_candidates=["C1_3"],
    b_candidates=["C2_3"],
)
DEFAULT_PREFER = "135_3"


def build_url(d: pd.Timestamp) -> str:
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/135-{ymd}.rar"


def _norm_regn(x) -> str:
    return re.sub(r"\D+", "", "" if x is None else str(x))


def _norm_code(x) -> str:
    s = "" if x is None else str(x)
    s = s.strip().replace(",", ".")
    s = re.sub(r"[^0-9.]+", "", s)
    return s


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
    fdf = get_formulas_for(formulas_df, form=FORM, kind="formula")
    if len(fdf) == 0:
        raise RuntimeError("No formulas for form 135 in formulas_df.")

    indicator_order = {row["name"]: i for i, row in fdf.iterrows()}

    parsed: list[tuple[str, list[str]]] = []
    for _, fr in fdf.iterrows():
        name = str(fr["name"])
        expr = str(fr["expression"])
        tokens = re.findall(r"\d+(?:\.\d+)?|[+]{1}|[-]{1}", expr)
        parsed.append((name, tokens))

    banks = [(str(r["bank"]), str(int(r["regn"]))) for _, r in banks_df.iterrows()]

    rows = []

    for date_str, df_dbf in date_dbf_list:
        if df_dbf is None or len(df_dbf) == 0:
            continue

        d = df_dbf.copy()
        d["REGN_N"] = d["REGN"].map(_norm_regn)
        d["CODE"] = d["A"].map(_norm_code)
        d["VAL"] = d["B"].map(_value_to_str)

        d = d.dropna(subset=["REGN_N", "CODE"])
        d = d.drop_duplicates(subset=["REGN_N", "CODE"], keep="first")

        reg_map: dict[str, dict[str, str]] = {}
        for regn, sub in d.groupby("REGN_N", sort=False):
            reg_map[regn] = dict(zip(sub["CODE"].tolist(), sub["VAL"].tolist()))

        for bank_name, regn_bank in banks:
            bm = reg_map.get(regn_bank, {})

            for name, tokens in parsed:
                acc = ""
                for t in tokens:
                    if t in ["+", "-"]:
                        acc += t
                    else:
                        acc += bm.get(str(t), "0")
                rows.append(
                    {"Дата": date_str, "Банк": bank_name, "Показатель": name, "Значение": "=" + acc}
                )

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
