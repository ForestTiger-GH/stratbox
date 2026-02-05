"""
Форма 102 (быстрая версия, вчистую).

По документации:
- DBF: QYYYY_P1.dbf (нужен P1)
- Поля:
    REGN      — регномер банка
    CODE      — код символа
    SIM_ITOGO — итог

Логика:
- По каждой дате скачиваем 102-YYYYMMDD.rar
- Из архива выбираем DBF, предпочитаем содержащий "P1"
- Строим lookup: lookup[(regn, code)] = value_str
- Формулы считаются через dict.get(), без фильтраций pandas.

Прогресс: trange по датам, исчезает.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dbfread import DBF
from tqdm.auto import trange

from stratbox.base.filestore import make_workdir
from stratbox.base.net.http import download_bytes
from stratbox.macrobanks.cbr_forms.common.formulas import get_formulas_for
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig


FORM = "102"
DEFAULT_PREFER = "P1"


def build_url(d: pd.Timestamp) -> str:
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/102-{ymd}.rar"


def _pick_rar_tool() -> str:
    for c in ["unrar", "7z", "7zz"]:
        if shutil.which(c):
            return c
    raise RuntimeError("No 'unrar' or '7z' found. Install unrar or p7zip.")


def _extract_rar(archive_path: Path, out_dir: Path) -> None:
    tool = _pick_rar_tool()
    out_dir.mkdir(parents=True, exist_ok=True)

    if tool == "unrar":
        cmd = [tool, "x", "-o+", str(archive_path), str(out_dir)]
    else:
        cmd = [tool, "x", f"-o{out_dir}", str(archive_path), "-y"]

    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("Archive extract failed:\n" + (p.stderr or p.stdout or ""))


def _norm_regn(x: Any) -> str:
    return re.sub(r"\D+", "", "" if x is None else str(x))


def _norm_code(x: Any) -> str:
    s = "" if x is None else str(x)
    s = s.strip()
    s = re.sub(r"\s+", "", s)
    return s


def _value_to_str(v: Any) -> str:
    if v is None:
        return "0"
    if isinstance(v, float) and np.isnan(v):
        return "0"
    s = str(v).strip().replace(",", ".")
    return s if s else "0"


def _pick_102_dbf(ex_dir: Path) -> Path:
    # предпочитаем dbf, где в имени есть P1
    cands = sorted(ex_dir.rglob("*.dbf"))
    if not cands:
        raise FileNotFoundError(f"No DBF found in extracted dir: {ex_dir}")

    def score(p: Path) -> int:
        n = p.name.upper()
        s = 0
        if "P1" in n:
            s += 10
        if n.endswith(".DBF"):
            s += 1
        return s

    cands = sorted(cands, key=score, reverse=True)
    return cands[0]


def _build_lookup_from_dbf(dbf_path: Path) -> dict[tuple[str, str], str]:
    lookup: dict[tuple[str, str], str] = {}

    # dbfread: читаем построчно, это быстрее и без лишних pandas-фильтров
    # DBF ЦБ иногда имеет нестабильные/битые текстовые поля, поэтому:
    # - задаём типичную для DBF кодировку (cp866 / cp1251)
    # - ошибки декодирования игнорируем
    try:
        dbf = DBF(
            str(dbf_path),
            load=True,
            ignore_missing_memofile=True,
            encoding="cp866",
            char_decode_errors="ignore",
        )
    except Exception:
        dbf = DBF(
            str(dbf_path),
            load=True,
            ignore_missing_memofile=True,
            encoding="cp1251",
            char_decode_errors="ignore",
        )
    
    have_u = {f.upper(): f for f in dbf.field_names}

    reg_f = have_u.get("REGN")
    code_f = have_u.get("CODE")
    val_f = have_u.get("SIM_ITOGO") or have_u.get("SIM_ITOG") or have_u.get("SIM_R")

    if not (reg_f and code_f and val_f):
        raise RuntimeError(f"102 DBF structure unexpected. Fields={dbf.field_names}")

    for rec in dbf:
        regn = _norm_regn(rec.get(reg_f))
        if not regn:
            continue
        code = _norm_code(rec.get(code_f))
        if not code:
            continue
        val = _value_to_str(rec.get(val_f))
        key = (regn, code)
        if key not in lookup:
            lookup[key] = val

    return lookup


def build_long(
    *,
    dates: list[pd.Timestamp],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
    cfg: RunnerConfig,
    show_progress: bool,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    fdf = get_formulas_for(formulas_df, form=FORM, kind="formula")
    if len(fdf) == 0:
        raise RuntimeError("No formulas for form 102 in formulas_df.")

    indicator_order = {row["name"]: i for i, row in fdf.iterrows()}

    parsed: list[tuple[str, list[str]]] = []
    for _, fr in fdf.iterrows():
        name = str(fr["name"])
        expr = str(fr["expression"])
        # для 102 код обычно целочисленный, но оставим как \w+
        tokens = re.findall(r"[A-Za-zА-Яа-я0-9]+|[+]{1}|[-]{1}", expr)
        parsed.append((name, tokens))

    banks = [(str(r["bank"]), str(int(r["regn"]))) for _, r in banks_df.iterrows()]

    work_dir = Path(make_workdir(prefix="cbr_102_"))
    out_rows: list[dict[str, str]] = []

    try:
        it = trange(len(dates), desc="CBR 102", leave=False) if show_progress else range(len(dates))
        for i in it:
            d = pd.Timestamp(dates[i])
            date_str = d.strftime("%d.%m.%Y")
            ymd = d.strftime("%Y%m%d")

            url = build_url(d)

            res = download_bytes(
                url=url,
                timeout=cfg.timeout,
                retries=cfg.retries,
                backoff=cfg.backoff,
                min_bytes_ok=cfg.min_bytes_ok,
                headers=None,
            )
            if not res.ok or not res.content:
                continue

            rar_path = work_dir / f"tmp_{ymd}.rar"
            rar_path.write_bytes(res.content)

            ex_dir = work_dir / f"ex_{ymd}"
            _extract_rar(rar_path, ex_dir)

            dbf_path = _pick_102_dbf(ex_dir)
            lookup = _build_lookup_from_dbf(dbf_path)

            for bank_name, regn in banks:
                for name, tokens in parsed:
                    acc = ""
                    for t in tokens:
                        if t in ["+", "-"]:
                            acc += t
                        else:
                            acc += lookup.get((regn, str(t)), "0")
                    out_rows.append(
                        {"Дата": date_str, "Банк": bank_name, "Показатель": name, "Значение": "=" + acc}
                    )

        df_long = pd.DataFrame(out_rows)
        print(f"[INFO] 102 long rows: {len(df_long)}")
        return df_long, indicator_order

    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


def run(
    *,
    dates: list[pd.Timestamp],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
    cfg: RunnerConfig | None = None,
    show_progress: bool = True,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    cfg = cfg or RunnerConfig()
    return build_long(dates=dates, banks_df=banks_df, formulas_df=formulas_df, cfg=cfg, show_progress=show_progress)
