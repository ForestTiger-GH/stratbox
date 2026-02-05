"""
run_form101_debug.py — отладочный прогон формы 101 с индикацией этапов.

Запуск:
  python -m stratbox.macrobanks.cbr_forms.run_form101_debug --from 2024-01-01 --to 2024-12-01 --freq M --anchor start --banks legacy --out-xlsx "Сводка 101ф.xlsx"
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
from tqdm.auto import trange

from stratbox.common.time.periods import period_points
from stratbox.macrobanks.cbr_forms.common.banks import load_legacy_banks
from stratbox.macrobanks.cbr_forms.common.formulas import load_formulas
from stratbox.macrobanks.cbr_forms.common.output import make_and_export_wide
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig
from stratbox.macrobanks.cbr_forms.common.dbf_picker import pick_dbf_and_layout
from stratbox.macrobanks.cbr_forms.common.dbf import read_dbf_to_df
from stratbox.macrobanks.cbr_forms.forms import form101

from stratbox.base.filestore import make_workdir
from stratbox.base.net.http import download_bytes


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="date_from", required=True)
    p.add_argument("--to", dest="date_to", required=False, default=None)
    p.add_argument("--freq", dest="freq", required=False, default="M", choices=["Y", "Q", "M", "W", "D"])
    p.add_argument("--anchor", dest="anchor", required=False, default="start", choices=["start", "end"])
    p.add_argument("--banks", dest="banks_mode", required=False, default="legacy", choices=["legacy"])
    p.add_argument("--out-xlsx", dest="out_xlsx", required=False, default="Сводка 101ф.xlsx")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    # 0) Даты
    ds = period_points(args.freq, args.date_from, args.date_to, anchor=args.anchor)
    dates = [pd.Timestamp(d) for d in ds]
    print(f"[INFO] Dates generated: {len(dates)}")

    # 1) Банки
    if args.banks_mode == "legacy":
        banks_df = load_legacy_banks()
    else:
        raise RuntimeError(f"Unsupported banks_mode: {args.banks_mode}")
    print(f"[INFO] Banks loaded: {len(banks_df)}")

    # 2) Формулы
    formulas_df = load_formulas()
    print(f"[INFO] Formulas loaded: {len(formulas_df)}")

    # 3) Конфиг сети
    cfg = RunnerConfig(timeout=60, retries=2, backoff=0.5, min_bytes_ok=512)

    # 4) Рабочая папка
    work_dir = Path(make_workdir(prefix="cbr_101_dbg_"))
    print(f"[INFO] WORK_DIR: {work_dir}")

    # 5) Соберём (date_str, df_dbf_slim) для каждой даты
    # Сразу читаем DBF в "узком" виде: только REGN/NUM_SC/A_P/IITG (через read_dbf_to_df/layout)
    # Это быстро и достаточно для расчётов.
    date_df_list: list[tuple[str, pd.DataFrame]] = []

    try:
        it = trange(len(dates), desc="CBR 101", leave=False)
        for i in it:
            d = dates[i]
            date_str = d.strftime("%d.%m.%Y")
            ymd = d.strftime("%Y%m%d")

            t0 = time.perf_counter()
            url = form101.build_url(d)
            print(f"\n[DATE] {date_str}  url={url}")

            # 5.1 download
            td0 = time.perf_counter()
            res = download_bytes(
                url=url,
                timeout=cfg.timeout,
                retries=cfg.retries,
                backoff=cfg.backoff,
                min_bytes_ok=cfg.min_bytes_ok,
                headers=None,
            )
            td1 = time.perf_counter()
            if not res.ok or not res.content:
                print(f"[WARN] download failed: ok={res.ok}, status={res.status_code}")
                continue
            print(f"[OK] downloaded: {len(res.content)/1024:.1f} KB  dt={td1-td0:.2f}s")

            rar_path = work_dir / f"tmp_{ymd}.rar"
            rar_path.write_bytes(res.content)

            # 5.2 extract
            te0 = time.perf_counter()
            ex_dir = work_dir / f"ex_{ymd}"
            ex_dir.mkdir(parents=True, exist_ok=True)
            form101._extract_rar(rar_path, ex_dir)  # используем ту же распаковку, что в form101
            te1 = time.perf_counter()
            print(f"[OK] extracted: {ex_dir.name}  dt={te1-te0:.2f}s")

            # 5.3 pick DBF
            tp0 = time.perf_counter()
            dbf_path, layout = pick_dbf_and_layout(
                ex_dir,
                candidates=form101.DEFAULT_CANDIDATES,
                prefer_stem_contains=form101.DEFAULT_PREFER,
            )
            tp1 = time.perf_counter()
            print(f"[OK] dbf picked: {Path(dbf_path).name}  dt={tp1-tp0:.2f}s")

            # 5.4 read DBF (slim)
            tr0 = time.perf_counter()
            df_dbf = read_dbf_to_df(str(dbf_path), layout)
            tr1 = time.perf_counter()
            print(f"[OK] dbf read: rows={len(df_dbf)} cols={list(df_dbf.columns)}  dt={tr1-tr0:.2f}s")

            date_df_list.append((date_str, df_dbf))
            t1 = time.perf_counter()
            print(f"[OK] date total dt={t1-t0:.2f}s")

        # 6) compute long (используем build_long формы, но подаём уже готовые df)
        # Для этого добавим маленький адаптер: build_long ожидает paths, а у нас df.
        # Поэтому считаем прямо тут, повторяя формульную логику, но используя resolve формы.
        print("\n[STEP] computing 101 long...")
        tc0 = time.perf_counter()
        df_long, indicator_order = form101.build_long_from_preloaded(date_df_list, banks_df, formulas_df)
        tc1 = time.perf_counter()
        print(f"[OK] long built: rows={len(df_long)} dt={tc1-tc0:.2f}s")

        # 7) export
        out_xlsx = Path(args.out_xlsx).resolve()
        print("\n[STEP] exporting wide...")
        tw0 = time.perf_counter()
        make_and_export_wide(
            out_path=str(out_xlsx),
            df_long=df_long,
            df_banks=banks_df,
            indicator_order=indicator_order,
            date_col="Дата",
            bank_col="Банк",
            indicator_col="Показатель",
            value_col="Значение",
        )
        tw1 = time.perf_counter()
        print(f"[OK] exported: {out_xlsx.name} dt={tw1-tw0:.2f}s")

    finally:
        # чистим времянку
        try:
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
