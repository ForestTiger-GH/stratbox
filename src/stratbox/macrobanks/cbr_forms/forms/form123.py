"""
Форма 123: расчёт показателей по формулам из models/formulas.csv.

Особенность:
- формулы — выражения из кодов (000, 102+105, ...)
- в DBF: A = ACC (код), B = значение, REGN = банк
- формирование df_long:
    Дата | Банк | Показатель | Значение (Excel-формула вида "=...")

Скрипт не привязан к банкам/legacy — banks_df приходит параметром.
Скрипт не привязан к набору формул — formulas_df приходит параметром.
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
    regn_candidates=["REGN", "REG", "REG_NUM", "REGN_BNK"],
    a_candidates=["C1", "C_1", "NUM_SC", "SC", "SCHET", "ACCOUNT", "NOM_SCH", "NOMER"],
    b_candidates=["C3", "C_3", "IITG", "SUM", "VALUE", "VAL", "C2", "C_2"],
)

DEFAULT_PREFER = "123"


def build_url(d: pd.Timestamp) -> str:
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/123-{ymd}.rar"


def _norm_regn(x) -> str:
    return re.sub(r"\D+", "", "" if x is None else str(x))


def _norm_acc_to_int(x) -> int:
    s = "" if x is None else str(x)
    s = re.sub(r"\D+", "", s)
    return int(s) if s else -1


def _value_to_str(v) -> str:
    if v is None:
        return "0"
    if isinstance(v, float) and np.isnan(v):
        return "0"
    return str(v).strip().replace(",", ".")


def build_long(
    date_dbf_list: list[tuple[str, pd.DataFrame]],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    """
    Преобразует (дата, df_dbf) + банки + формулы -> df_long.

    formulas_df должен содержать строки form=123, kind=formula:
      name, expression
    """
    fdf = get_formulas_for(formulas_df, form=FORM, kind="formula")
    if len(fdf) == 0:
        raise RuntimeError("No formulas for form 123 in formulas_df.")

    indicator_order = {row["name"]: i for i, row in fdf.iterrows()}

    rows = []

    for date_str, df_dbf in date_dbf_list:
        df = df_dbf.copy()

        # df_dbf: REGN/A/B
        df["REGN_N"] = df["REGN"].map(_norm_regn)
        df["ACC"] = df["A"].map(_norm_acc_to_int)
        df["VAL"] = df["B"]

        for _, b in banks_df.iterrows():
            bank_name = str(b["bank"])
            regn_bank = str(int(b["regn"]))

            sub = df[df["REGN_N"] == regn_bank].copy()

            for _, fr in fdf.iterrows():
                name = fr["name"]
                expr = fr["expression"]

                # токены: числа и +/-
                tokens = re.findall(r"\d+|[+]{1}|[-]{1}", str(expr))
                formula = ""

                for t in tokens:
                    if t in ["+", "-"]:
                        formula += t
                        continue

                    acc = int(t)
                    m = sub[sub["ACC"] == acc]
                    val = _value_to_str(m["VAL"].iloc[0]) if len(m) else "0"
                    formula += val

                rows.append(
                    {
                        "Дата": date_str,
                        "Банк": bank_name,
                        "Показатель": name,
                        "Значение": "=" + formula,
                    }
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
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    """
    Универсальный запуск формы 123 в режиме df_long.

    Возвращает:
      - df_long
      - indicator_order (для wide-сборки)
    """
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
    return build_long(date_dbf_list, banks_df, formulas_df)
