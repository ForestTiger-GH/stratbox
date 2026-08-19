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
from stratbox.macrobanks.cbr_forms.common.models import get_model_for, load_models
from stratbox.macrobanks.cbr_forms.common.output import export_form_excel
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig
from stratbox.macrobanks.cbr_forms.forms.registry import resolve_forms


def _resolve_form_dates(
    *,
    entry,
    date_from: str,
    date_to: str | None,
    default_freq: str,
    default_anchor: str,
) -> list[pd.Timestamp]:
    """
    Функция строит сетку дат с учетом собственной периодичности формы.

    Если периодичность в реестре не задана, используется общая сетка Run All.
    """
    freq = entry.reporting_freq or default_freq
    anchor = entry.reporting_anchor if entry.reporting_freq else default_anchor
    return [
        pd.Timestamp(d)
        for d in period_points(
            freq,
            date_from,
            date_to,
            anchor=anchor,
        )
    ]


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
    default_dates = [
        pd.Timestamp(d)
        for d in period_points(freq, date_from, date_to, anchor=anchor)
    ]

    if banks_mode != "legacy":
        raise ValueError("Only banks_mode='legacy' is supported right now.")
    banks_df = load_legacy_banks()

    models_df = load_models()
    cfg = RunnerConfig(timeout=timeout, retries=retries, backoff=backoff, min_bytes_ok=min_bytes_ok)

    out_dir_p = Path(out_dir).resolve()
    out_dir_p.mkdir(parents=True, exist_ok=True)

    form_entries = resolve_forms(forms)
    codes = [entry.code for entry in form_entries]

    print(f"[START] forms={codes} dates={len(default_dates)} banks={len(banks_df)} out_dir={out_dir_p}")

    out_paths: dict[str, str] = {}
    iterator = trange(len(form_entries), desc="CBR forms", leave=False) if show_progress else range(len(form_entries))

    for i in iterator:
        entry = form_entries[i]
        code = entry.code
        module = entry.module
        form_dates = _resolve_form_dates(
            entry=entry,
            date_from=date_from,
            date_to=date_to,
            default_freq=freq,
            default_anchor=anchor,
        )

        if not form_dates:
            print(f"[FORM] {code} skipped: no reporting dates in requested range")
            continue

        print(f"[FORM] {code} start dates={len(form_dates)}")

        model_df = get_model_for(models_df, form=code)
        df_long, indicator_order = module.run(
            dates=form_dates,
            banks_df=banks_df,
            model_df=model_df,
            cfg=cfg,
            show_progress=show_progress,
        )

        banks_tag = str(banks_mode).upper()
        out_path = out_dir_p / f"CBR_{entry.title}_{banks_tag}.xlsx"

        export_form_excel(
            out_path=str(out_path),
            excel_profile=entry.excel_profile,
            df_long=df_long,
            df_banks=banks_df,
            model_df=model_df,
            indicator_order=indicator_order,
        )

        out_paths[code] = str(out_path)
        print(f"[FORM] {code} done -> {out_path.name}")

    print("[DONE] all forms exported")
    return out_paths
