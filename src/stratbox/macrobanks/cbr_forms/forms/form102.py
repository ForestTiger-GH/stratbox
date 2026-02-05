"""
Форма 102: каркас обработки.

Аналогично 101:
- формулы (ЧПД, ЧКД, ...) задаются в formulas.csv
- но "как достать значение по коду строки 11000/12000/.../61101" зависит от DBF,
  поэтому используется value_resolver(...) извне.

Значение формируется как Excel-формула "=...".
"""

from __future__ import annotations

import re
import pandas as pd

from stratbox.macrobanks.cbr_forms.common.formulas import get_formulas_for
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig, run_dates_to_dbf_df
from stratbox.macrobanks.cbr_forms.common.dbf_picker import LayoutCandidates
from stratbox.macrobanks.cbr_forms.forms._typing import ValueResolver


FORM = "102"

DEFAULT_CANDIDATES = None
DEFAULT_PREFER = "102"


def build_url(d: pd.Timestamp) -> str:
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/102-{ymd}.rar"


def build_long(
    date_dbf_list: list[tuple[str, pd.DataFrame]],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
    *,
    value_resolver: ValueResolver,
    resolver_ctx: dict | None = None,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    resolver_ctx = resolver_ctx or {}

    fdf = get_formulas_for(formulas_df, form=FORM, kind="formula")
    if len(fdf) == 0:
        raise RuntimeError("No formulas for form 102 in formulas_df.")

    indicator_order = {row["name"]: i for i, row in fdf.iterrows()}
    rows = []

    for date_str, df_dbf in date_dbf_list:
        for _, b in banks_df.iterrows():
            bank_name = str(b["bank"])
            regn_bank = str(int(b["regn"]))

            for _, fr in fdf.iterrows():
                name = fr["name"]
                expr = fr["expression"]

                tokens = re.findall(r"\d+|[+]{1}|[-]{1}", str(expr))
                acc = ""

                ctx = dict(resolver_ctx)
                ctx["form"] = FORM

                for t in tokens:
                    if t in ["+", "-"]:
                        acc += t
                        continue

                    val = value_resolver(df_dbf, regn_bank, str(t), ctx)
                    val = "0" if (val is None or str(val).strip() == "") else str(val).strip()
                    acc += val

                rows.append(
                    {
                        "Дата": date_str,
                        "Банк": bank_name,
                        "Показатель": name,
                        "Значение": "=" + acc,
                    }
                )

    df_long = pd.DataFrame(rows)
    print(f"[INFO] 102 long rows: {len(df_long)}")
    return df_long, indicator_order


def run(
    *,
    dates: list[pd.Timestamp],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
    candidates: LayoutCandidates | None = None,
    prefer_stem_contains: str | None = None,
    cfg: RunnerConfig | None = None,
    value_resolver: ValueResolver | None = None,
    resolver_ctx: dict | None = None,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    if value_resolver is None:
        raise ValueError("form102.run requires value_resolver=... (see forms/_typing.py)")

    candidates = candidates or DEFAULT_CANDIDATES
    prefer_stem_contains = prefer_stem_contains or DEFAULT_PREFER
    cfg = cfg or RunnerConfig()

    if candidates is None:
        raise ValueError("form102.run requires candidates=LayoutCandidates (fields depend on DBF).")

    date_dbf_list = run_dates_to_dbf_df(
        dates=dates,
        build_url=build_url,
        candidates=candidates,
        prefer_stem_contains=prefer_stem_contains,
        cfg=cfg,
    )
    return build_long(date_dbf_list, banks_df, formulas_df, value_resolver=value_resolver, resolver_ctx=resolver_ctx)
