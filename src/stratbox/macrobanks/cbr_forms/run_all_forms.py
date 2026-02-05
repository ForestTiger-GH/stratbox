"""
run_all_forms.py — тестовый сценарий "как CBR_FORMS".

Скачивает архивы ЦБ за заданный период и сохраняет каждую форму
в отдельный XLSX-файл (wide-структура: Показатель | Банк | даты по столбцам).

Запуск из корня репозитория:
  python -m stratbox.macrobanks.cbr_forms.run_all_forms --from 2024-01-01 --to 2024-12-01 --freq M --anchor start --banks legacy --out-dir .

Параметры:
  --from     YYYY-MM-DD (начало)
  --to       YYYY-MM-DD (конец, опционально; если не задан — до текущей даты)
  --freq     Y/Q/M/W/D (частота точек)
  --anchor   start/end (первая/последняя дата периода)
  --banks    legacy (пока только legacy)
  --out-dir  каталог вывода
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from stratbox.common.time.periods import period_points
from stratbox.macrobanks.cbr_forms.common.formulas import load_formulas
from stratbox.macrobanks.cbr_forms.common.output import make_and_export_wide
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig
from stratbox.macrobanks.cbr_forms.common.banks import load_legacy_banks
from stratbox.macrobanks.cbr_forms.forms import form101, form102, form123, form135


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD (start)")
    p.add_argument("--to", dest="date_to", required=False, default=None, help="YYYY-MM-DD (end). If omitted -> today")
    p.add_argument("--freq", dest="freq", required=False, default="M", choices=["Y", "Q", "M", "W", "D"], help="Periods frequency")
    p.add_argument("--anchor", dest="anchor", required=False, default="start", choices=["start", "end"], help="Period anchor (start/end date of period)")
    p.add_argument("--banks", dest="banks_mode", required=False, default="legacy", choices=["legacy"], help="Bank set mode")
    p.add_argument("--out-dir", dest="out_dir", required=False, default=".", help="Output directory")
    return p.parse_args()


def _build_dates(date_from: str, date_to: str | None, freq: str, anchor: str) -> list[pd.Timestamp]:
    ds = period_points(freq, date_from, date_to, anchor=anchor)
    dates = [pd.Timestamp(d) for d in ds]
    return dates


def _ensure_out_dir(out_dir: str) -> Path:
    p = Path(out_dir).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _run_one_form(
    *,
    form_label: str,
    run_fn,
    dates: list[pd.Timestamp],
    banks_df,
    formulas_df,
    cfg: RunnerConfig,
    out_path: Path,
) -> None:
    """
    Унифицированный запуск одной формы:
    - run_fn должен вернуть (df_long, indicator_order)
    - далее собираем wide и экспортируем
    """
    print(f"[INFO] Running form {form_label}...")

    try:
        df_long, indicator_order = run_fn(
            dates=dates,
            banks_df=banks_df,
            formulas_df=formulas_df,
            cfg=cfg,
        )
    except Exception as e:
        print(f"[WARN] Form {form_label} failed: {type(e).__name__}: {e}")
        return


    if df_long is None or len(df_long) == 0:
        print(f"[WARN] Form {form_label}: empty df_long, export skipped.")
        return

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
    # print(f"[OK] Exported: {out_path.name}")


def main() -> None:
    args = _parse_args()

    out_dir = _ensure_out_dir(args.out_dir)

    # 1) Даты
    dates = _build_dates(args.date_from, args.date_to, args.freq, args.anchor)
    print(f"[INFO] Dates generated: {len(dates)}")

    # 2) Банки
    if args.banks_mode == "legacy":
        banks_df = load_legacy_banks()
    else:
        raise RuntimeError(f"Unsupported banks_mode: {args.banks_mode}")
    print(f"[INFO] Banks loaded: {len(banks_df)}")

    # 3) Формулы
    formulas_df = load_formulas()
    print(f"[INFO] Formulas loaded: {len(formulas_df)}")

    # 4) Runner config (параметры сети/повторов)
    cfg = RunnerConfig(timeout=60, retries=2, backoff=0.5, min_bytes_ok=512)

    # 5) Запуск форм и экспорт
    # Имена файлов — как в ноутбуке: "Сводка XXXф.xlsx"
    _run_one_form(
        form_label="101",
        run_fn=form101.run,
        dates=dates,
        banks_df=banks_df,
        formulas_df=formulas_df,
        cfg=cfg,
        out_path=out_dir / "Сводка 101ф.xlsx",
    )

    _run_one_form(
        form_label="102",
        run_fn=form102.run,
        dates=dates,
        banks_df=banks_df,
        formulas_df=formulas_df,
        cfg=cfg,
        out_path=out_dir / "Сводка 102ф.xlsx",
    )

    _run_one_form(
        form_label="123",
        run_fn=form123.run,
        dates=dates,
        banks_df=banks_df,
        formulas_df=formulas_df,
        cfg=cfg,
        out_path=out_dir / "Сводка 123ф.xlsx",
    )

    _run_one_form(
        form_label="135",
        run_fn=form135.run,
        dates=dates,
        banks_df=banks_df,
        formulas_df=formulas_df,
        cfg=cfg,
        out_path=out_dir / "Сводка 135ф.xlsx",
    )

    # print("[OK] All done.")


if __name__ == "__main__":
    main()
