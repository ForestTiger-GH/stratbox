"""
Форма 101: каркас обработки.

Почему каркас:
- В 101/102 критично "как из DBF достать значение по коду" (ряд/группа/раздел).
- Это может меняться между версиями DBF/структурой архива.
- Поэтому форма принимает value_resolver(...) снаружи.

Формулы берутся из formulas_df (form=101, kind=formula),
extra содержит, например, "a_p=1" / "a_p=2" (как в исходнике).
"""

from __future__ import annotations

import re
import pandas as pd

from stratbox.macrobanks.cbr_forms.common.formulas import get_formulas_for
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig, run_dates_to_dbf_df
from stratbox.macrobanks.cbr_forms.common.dbf_picker import LayoutCandidates
from stratbox.macrobanks.cbr_forms.forms._typing import ValueResolver


FORM = "101"

# Кандидаты полей для 101 зависят от конкретного DBF внутри архива.
# Здесь оставляем None по умолчанию: задаётся снаружи.
DEFAULT_CANDIDATES = None
DEFAULT_PREFER = "101"


def build_url(d: pd.Timestamp) -> str:
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/101-{ymd}.rar"


def _parse_extra(extra: str) -> dict:
    """
    Парсит extra типа "a_p=1" в dict.
    """
    out = {}
    s = "" if extra is None else str(extra)
    for part in s.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def build_long(
    date_dbf_list: list[tuple[str, pd.DataFrame]],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
    *,
    value_resolver: ValueResolver,
    resolver_ctx: dict | None = None,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    """
    value_resolver(df_dbf, regn_str, code_str, ctx) -> value_str
    """
    resolver_ctx = resolver_ctx or {}

    fdf = get_formulas_for(formulas_df, form=FORM, kind="formula")
    if len(fdf) == 0:
        raise RuntimeError("No formulas for form 101 in formulas_df.")

    indicator_order = {row["name"]: i for i, row in fdf.iterrows()}
    rows = []

    for date_str, df_dbf in date_dbf_list:
        for _, b in banks_df.iterrows():
            bank_name = str(b["bank"])
            regn_bank = str(int(b["regn"]))

            for _, fr in fdf.iterrows():
                name = fr["name"]
                expr = fr["expression"]
                extra = _parse_extra(fr.get("extra", ""))

                # формула вида "45.2" или "441+442-..."
                tokens = re.findall(r"\d+(?:\.\d+)?|[+]{1}|[-]{1}", str(expr))
                acc = ""

                ctx = dict(resolver_ctx)
                ctx.update(extra)
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
    print(f"[INFO] 101 long rows: {len(df_long)}")
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
    """
    candidates/prefer_stem_contains задаются снаружи, потому что структура 101 может отличаться.
    """
    if value_resolver is None:
        raise ValueError("form101.run requires value_resolver=... (see forms/_typing.py)")

    candidates = candidates or DEFAULT_CANDIDATES
    prefer_stem_contains = prefer_stem_contains or DEFAULT_PREFER
    cfg = cfg or RunnerConfig()

    if candidates is None:
        raise ValueError("form101.run requires candidates=LayoutCandidates (fields depend on DBF).")

    date_dbf_list = run_dates_to_dbf_df(
        dates=dates,
        build_url=build_url,
        candidates=candidates,
        prefer_stem_contains=prefer_stem_contains,
        cfg=cfg,
    )
    return build_long(date_dbf_list, banks_df, formulas_df, value_resolver=value_resolver, resolver_ctx=resolver_ctx)
