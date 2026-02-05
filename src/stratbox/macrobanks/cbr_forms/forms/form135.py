"""
Форма 135: показатели H1.0/H1.1/H1.2 из DBF.

В formulas.csv это хранится как kind=metric.
Сами expression сейчас носят описательный характер, поэтому:
- используем name (H1.0/H1.1/H1.2) как список показателей
- правило извлечения по умолчанию: label содержит "1.0"/"1.1"/"1.2"
  (устойчиво к кодировкам типа "ì1.x")

Скрипт параметризуем:
- banks_df (любой набор банков)
- formulas_df (любой набор metric, можно заменить на formulas2)
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


def _to_value_str(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip().replace(",", ".")
    if isinstance(v, (int, float, np.number)):
        x = float(v)
        if x.is_integer():
            return str(int(x))
        return str(x)
    return str(v).strip().replace(",", ".")


def _default_label_to_hkey(label: str) -> str | None:
    s = "" if label is None else str(label)
    if "1.0" in s:
        return "H1.0"
    if "1.1" in s:
        return "H1.1"
    if "1.2" in s:
        return "H1.2"
    return None


def build_long(
    date_dbf_list: list[tuple[str, pd.DataFrame]],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
    *,
    label_to_key=_default_label_to_hkey,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    """
    label_to_key можно подменять снаружи (если поменяются правила распознавания меток).
    """
    mdf = get_formulas_for(formulas_df, form=FORM, kind="metric")
    if len(mdf) == 0:
        raise RuntimeError("No metrics for form 135 in formulas_df.")

    metrics = mdf["name"].astype(str).tolist()
    indicator_order = {m: i for i, m in enumerate(metrics)}

    rows = []

    for date_str, df_dbf in date_dbf_list:
        df = df_dbf.copy()
        df["REGN_N"] = df["REGN"].map(_norm_regn)
        df["KEY"] = df["A"].map(label_to_key)
        df["VAL"] = df["B"]

        for _, b in banks_df.iterrows():
            bank_name = str(b["bank"])
            regn_bank = str(int(b["regn"]))

            sub = df[df["REGN_N"] == regn_bank].copy()

            for key in metrics:
                m = sub[sub["KEY"] == key]
                val = _to_value_str(m["VAL"].iloc[0]) if len(m) else ""

                rows.append(
                    {
                        "Дата": date_str,
                        "Банк": bank_name,
                        "Показатель": key,
                        "Значение": val,
                    }
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
    label_to_key=_default_label_to_hkey,
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
    )
    return build_long(date_dbf_list, banks_df, formulas_df, label_to_key=label_to_key)
