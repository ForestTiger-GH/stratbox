"""
run_form101_debug.py — отладочный прогон формы 101 с индикацией этапов.

Запуск:
  python -m stratbox.macrobanks.cbr_forms.run_form101_debug --from 2024-01-01 --to 2024-12-01 --freq M --anchor start --banks legacy --out-xlsx "Сводка 101ф.xlsx"

Показывает по каждой дате:
- URL
- download size / time
- extract time
- picked dbf name
- dbf read time (lookup size)
Дальше:
- compute time
- export time
"""

from __future__ import annotations

import argparse
import time
import shutil
from pathlib import Path

import pandas as pd
from tqdm.auto import trange

from stratbox.common.time.periods import period_points
from stratbox.macrobanks.cbr_forms.common.banks import load_legacy_banks
from stratbox.macrobanks.cbr_forms.common.formulas import load_formulas, get_formulas_for
from stratbox.macrobanks.cbr_forms.common.output import make_and_export_wide
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig
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
    banks_df = load_legacy_banks()
    print(f"[INFO] Banks loaded: {len(banks_df)}")

    # 2) Формулы
    formulas_df = load_formulas()
    print(f"[INFO] Formulas loaded: {len(formulas_df)}")

    # 3) Конфиг сети
    cfg = RunnerConfig(timeout=60, retries=2, backoff=0.5, min_bytes_ok=512)

    # 4) WORK_DIR
    work_dir = Path(make_workdir(prefix="cbr_101_dbg_"))
    print(f"[INFO] WORK_DIR: {work_dir}")

    # 5) Скачаем/распакуем/построим lookup по каждой дате
    date_lookup_list = []  # (date_str, lookup_ap, lookup_nap)
    try:
        it = trange(len(dates), desc="CBR 101", leave=False)
        for i in it:
            d = dates[i]
            date_str = d.strftime("%d.%m.%Y")
            ymd = d.strftime("%Y%m%d")

            t0 = time.perf_counter()
            url = form101.build_url(d)
            print(f"\n[DATE] {date_str}  url={url}")

            # download
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

            # extract
            te0 = time.perf_counter()
            ex_dir = work_dir / f"ex_{ymd}"
            form101._extract_rar(rar_path, ex_dir)
            te1 = time.perf_counter()
            print(f"[OK] extracted: {ex_dir.name}  dt={te1-te0:.2f}s")

            # pick dbf (B1)
            tp0 = time.perf_counter()
            dbf_path = form101._pick_b1_dbf(ex_dir)
            tp1 = time.perf_counter()
            print(f"[OK] dbf picked: {dbf_path.name}  dt={tp1-tp0:.2f}s")

            # build lookup from dbf
            tr0 = time.perf_counter()
            lookup_ap, lookup_nap = form101._build_lookup_from_dbf(dbf_path)
            tr1 = time.perf_counter()
            print(
                f"[OK] lookup built: ap={len(lookup_ap)} nap={len(lookup_nap)}  dt={tr1-tr0:.2f}s"
            )

            date_lookup_list.append((date_str, lookup_ap, lookup_nap))

            t1 = time.perf_counter()
            print(f"[OK] date total dt={t1-t0:.2f}s")

        # 6) compute long
        print("\n[STEP] computing 101 long...")
        tc0 = time.perf_counter()

        fdf = get_formulas_for(formulas_df, form="101", kind="formula")
        if len(fdf) == 0:
            raise RuntimeError("No formulas for form 101 in formulas_df.")
        indicator_order = {row["name"]: i for i, row in fdf.iterrows()}

        # парсим формулы один раз (используем парсер формы)
        parsed = []
        for _, fr in fdf.iterrows():
            name = str(fr["name"])
            expr = str(fr["expression"])
            extra = form101._parse_extra(fr.get("extra"))
            tokens = __import__("re").findall(r"\d+(?:\.\d+)?|[+]{1}|[-]{1}", expr)
            parsed.append((name, tokens, extra))

        banks = [(str(r["bank"]), str(int(r["regn"]))) for _, r in banks_df.iterrows()]

        rows = []
        for date_str, lookup_ap, lookup_nap in date_lookup_list:
            for bank_name, regn in banks:
                for name, tokens, extra in parsed:
                    acc = ""
                    for t in tokens:
                        if t in ["+", "-"]:
                            acc += t
                        else:
                            code = str(t)
                            if extra.a_p in (1, 2):
                                acc += lookup_ap.get((regn, extra.a_p, code), lookup_nap.get((regn, code), "0"))
                            else:
                                acc += lookup_nap.get((regn, code), "0")

                    rows.append({"Дата": date_str, "Банк": bank_name, "Показатель": name, "Значение": "=" + acc})

        df_long = pd.DataFrame(rows)
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
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
