"""
Публичный API для ноутбуков: один вызов — отчетные формы скачаны и выгружены в Excel.

Особенности:
- список доступных форм берется из единого реестра;
- каждая форма сохраняется в отдельный xlsx;
- прогресс по формам и датам можно отключить параметром show_progress=False.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from tqdm.auto import trange

from stratbox.common.time.periods import period_points
from stratbox.macrobanks.cbr_forms.common.banks import load_legacy_banks
from stratbox.macrobanks.cbr_forms.common.formulas import load_formulas
from stratbox.macrobanks.cbr_forms.common.output import make_and_export_wide
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig
from stratbox.macrobanks.cbr_forms.forms.registry import resolve_forms


def run_all_forms_to_xlsx(
    *,
    date_from: str,
    date_to: str | None,
    freq: str = "M",
    anchor: str = "start",
    banks_mode: str = "legacy",
    out_dir: str = ".",
    forms: list[str] | tuple[str, ...] | str | None = None,
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    show_progress: bool = True,
) -> dict[str, str]:
    """
    Функция запускает выбранные формы за ряд дат и сохраняет каждую форму в отдельный xlsx.

    forms:
    - None или "all": все доступные формы;
    - "101,102,805": список через запятую;
    - ["101", "805"]: список строк.

    Возвращает словарь вида:
      {"101": "/path/CBR_0409101_LEGACY.xlsx", ...}
    """
    dates = [pd.Timestamp(d) for d in period_points(freq, date_from, date_to, anchor=anchor)]

    if banks_mode != "legacy":
        raise ValueError("Only banks_mode='legacy' is supported right now.")
    banks_df = load_legacy_banks()

    formulas_df = load_formulas()
    cfg = RunnerConfig(timeout=timeout, retries=retries, backoff=backoff, min_bytes_ok=min_bytes_ok)

    out_dir_p = Path(out_dir).resolve()
    out_dir_p.mkdir(parents=True, exist_ok=True)

    form_entries = resolve_forms(forms)
    codes = [entry.code for entry in form_entries]

    print(f"[START] forms={codes} dates={len(dates)} banks={len(banks_df)} out_dir={out_dir_p}")

    out_paths: dict[str, str] = {}
    iterator = trange(len(form_entries), desc="CBR forms", leave=False) if show_progress else range(len(form_entries))

    for i in iterator:
        entry = form_entries[i]
        code = entry.code
        module = entry.module
        print(f"[FORM] {code} start")

        df_long, indicator_order = module.run(
            dates=dates,
            banks_df=banks_df,
            formulas_df=formulas_df,
            cfg=cfg,
            show_progress=show_progress,
        )

        banks_tag = str(banks_mode).upper()
        out_path = out_dir_p / f"CBR_{entry.title}_{banks_tag}.xlsx"

        make_and_export_wide(
            out_path=str(out_path),
            df_long=df_long,
            df_banks=banks_df,
            indicator_order=indicator_order,
            date_col="Дата",
            bank_col="Банк",
            indicator_col="Показатель",
            value_col="Значение",
        )

        out_paths[code] = str(out_path)
        print(f"[FORM] {code} done -> {out_path.name}")

    print("[DONE] all forms exported")
    return out_paths
