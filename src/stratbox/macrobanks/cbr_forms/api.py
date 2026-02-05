"""
Публичный API для ноутбуков: один вызов — все формы скачаны и выгружены в Excel.

Особенности:
- минимум печати: старт/финиш по формам + общий итог
- прогресс по датам внутри каждой формы уже есть (forms используют trange leave=False)
- тут добавлен внешний прогресс по формам (по очереди)
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

from stratbox.macrobanks.cbr_forms.forms import form101, form102, form123, form135


def run_all_forms_to_xlsx(
    *,
    date_from: str,
    date_to: str | None,
    freq: str = "M",
    anchor: str = "start",
    banks_mode: str = "legacy",
    out_dir: str = ".",
    timeout: int = 60,
    retries: int = 2,
    backoff: float = 0.5,
    min_bytes_ok: int = 512,
    show_progress: bool = True,
) -> dict[str, str]:
    """
    Запускает 101/102/123/135 за ряд дат и сохраняет каждую форму в отдельный xlsx.
    Возвращает dict: { "101": "/path/Сводка 101ф.xlsx", ... }.
    """
    # 1) Даты
    dates = [pd.Timestamp(d) for d in period_points(freq, date_from, date_to, anchor=anchor)]

    # 2) Банки
    if banks_mode != "legacy":
        raise ValueError("Only banks_mode='legacy' is supported right now.")
    banks_df = load_legacy_banks()

    # 3) Формулы
    formulas_df = load_formulas()

    # 4) Конфиг сети
    cfg = RunnerConfig(timeout=timeout, retries=retries, backoff=backoff, min_bytes_ok=min_bytes_ok)

    out_dir_p = Path(out_dir).resolve()
    out_dir_p.mkdir(parents=True, exist_ok=True)

    forms = [
        ("101", form101),
        ("102", form102),
        ("123", form123),
        ("135", form135),
    ]

    print(f"[START] forms={len(forms)} dates={len(dates)} banks={len(banks_df)} out_dir={out_dir_p}")

    out_paths: dict[str, str] = {}

    # Внешний прогресс — по списку форм (не мешает внутреннему trange по датам)
    it = trange(len(forms), desc="CBR forms", leave=False) if show_progress else range(len(forms))

    for i in it:
        code, mod = forms[i]
        print(f"[FORM] {code} start")

        df_long, indicator_order = mod.run(
            dates=dates,
            banks_df=banks_df,
            formulas_df=formulas_df,
            cfg=cfg,
            show_progress=show_progress,  # внутри формы будет trange по датам (leave=False)
        )

        out_path = out_dir_p / f"Сводка {code}ф.xlsx"

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
