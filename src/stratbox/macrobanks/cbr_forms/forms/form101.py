"""
Форма 101 (быстрая версия, вчистую).

Логика:
- По каждой дате скачивается архив 101-YYYYMMDD.rar
- Из архива выбирается B1 DBF (mmyyyyB1.dbf)
- Из DBF читаются только нужные поля:
    REGN   — регномер банка
    NUM_SC — код счета/агрегата
    A_P    — 1 актив, 2 пассив
    IITG   — исходящие остатки "итого" (на отчетную дату)
- Строится lookup:
    lookup[(regn, ap, code)] = value_str
  и fallback:
    lookup2[(regn, code)] = value_str  (если вдруг A_P отсутствует или формула без a_p)
- Формулы парсятся один раз и считаются через dict.get() (O(1)), без фильтраций pandas.

Выход:
- df_long: Дата | Банк | Показатель | Значение (Excel формула)
- indicator_order: порядок показателей из formulas.csv

Прогресс:
- trange по датам, бар исчезает (leave=False)
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
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


FORM = "101"


# ----------------------------
# URL
# ----------------------------
def build_url(d: pd.Timestamp) -> str:
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/101-{ymd}.rar"


# ----------------------------
# RAR extract (локально внутри формы)
# ----------------------------
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


# ----------------------------
# Helpers: normalize
# ----------------------------
def _norm_regn(x: Any) -> str:
    return re.sub(r"\D+", "", "" if x is None else str(x))


def _norm_code(x: Any) -> str:
    # NUM_SC может быть "45.2", "20", "123", иногда как число
    s = "" if x is None else str(x)
    s = s.strip().replace(",", ".")
    s = re.sub(r"[^0-9.]+", "", s)
    return s


def _norm_ap(x: Any) -> int:
    try:
        return int(x)
    except Exception:
        return -1


def _value_to_str(v: Any) -> str:
    if v is None:
        return "0"
    if isinstance(v, float) and np.isnan(v):
        return "0"
    s = str(v).strip().replace(",", ".")
    return s if s else "0"


# ----------------------------
# Extract DBF (pick B1)
# ----------------------------
def _pick_b1_dbf(ex_dir: Path) -> Path:
    # В 101 основная таблица: *B1.dbf
    cands = sorted(ex_dir.rglob("*B1.dbf"))
    if not cands:
        # fallback: любое .dbf
        cands = sorted(ex_dir.rglob("*.dbf"))
    if not cands:
        raise FileNotFoundError(f"No DBF found in extracted dir: {ex_dir}")
    # обычно нужный один
    return cands[0]


# ----------------------------
# Read slim DBF -> lookup
# ----------------------------
def _build_lookup_from_dbf(dbf_path: Path) -> tuple[dict[tuple[str, int, str], str], dict[tuple[str, str], str]]:
    """
    Возвращает:
      lookup_ap[(regn, ap, code)] = value
      lookup_nap[(regn, code)] = value
    """
    lookup_ap: dict[tuple[str, int, str], str] = {}
    lookup_nap: dict[tuple[str, str], str] = {}

    # dbfread: читаем построчно, это быстрее и без лишних pandas-фильтров
    dbf = DBF(str(dbf_path), load=True, ignore_missing_memofile=True)

    # подстроимся под регистры
    have_u = {f.upper(): f for f in dbf.field_names}

    # обязательные поля по документации 101:
    # REGN, NUM_SC, A_P, IITG
    reg_f = have_u.get("REGN")
    code_f = have_u.get("NUM_SC")
    ap_f = have_u.get("A_P")
    val_f = have_u.get("IITG")

    if not (reg_f and code_f and val_f):
        raise RuntimeError(f"101 DBF structure unexpected. Fields={dbf.field_names}")

    for rec in dbf:
        regn = _norm_regn(rec.get(reg_f))
        if not regn:
            continue

        code = _norm_code(rec.get(code_f))
        if not code:
            continue

        val = _value_to_str(rec.get(val_f))

        # A_P может быть отсутствующим/пустым — тогда ap=-1
        ap = _norm_ap(rec.get(ap_f)) if ap_f else -1

        # сохраняем первый встретившийся вариант (как обычно в DBF)
        if ap != -1:
            key_ap = (regn, ap, code)
            if key_ap not in lookup_ap:
                lookup_ap[key_ap] = val

        key_nap = (regn, code)
        if key_nap not in lookup_nap:
            lookup_nap[key_nap] = val

    return lookup_ap, lookup_nap


# ----------------------------
# Parse "extra" from formulas (a_p=1/2)
# ----------------------------
@dataclass(frozen=True)
class Extra101:
    a_p: int | None


def _parse_extra(extra: Any) -> Extra101:
    # ожидаем строку вида: "a_p=1" или "a_p=2"
    s = "" if extra is None else str(extra).strip()
    if not s:
        return Extra101(a_p=None)

    m = re.search(r"a_p\s*=\s*([12])", s)
    if m:
        return Extra101(a_p=int(m.group(1)))
    return Extra101(a_p=None)


# ----------------------------
# Build df_long (fast)
# ----------------------------
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
        raise RuntimeError("No formulas for form 101 in formulas_df.")

    indicator_order = {row["name"]: i for i, row in fdf.iterrows()}

    # парсим формулы один раз
    parsed: list[tuple[str, list[str], Extra101]] = []
    for _, fr in fdf.iterrows():
        name = str(fr["name"])
        expr = str(fr["expression"])
        extra = _parse_extra(fr.get("extra"))
        tokens = re.findall(r"\d+(?:\.\d+)?|[+]{1}|[-]{1}", expr)
        parsed.append((name, tokens, extra))

    # банки как список (быстрее)
    banks = [(str(r["bank"]), str(int(r["regn"]))) for _, r in banks_df.iterrows()]

    work_dir = Path(make_workdir(prefix="cbr_101_"))
    out_rows: list[dict[str, str]] = []

    try:
        it = trange(len(dates), desc="CBR 101", leave=False) if show_progress else range(len(dates))
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

            dbf_path = _pick_b1_dbf(ex_dir)

            lookup_ap, lookup_nap = _build_lookup_from_dbf(dbf_path)

            # расчёт по банкам и формулам
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

                    out_rows.append(
                        {"Дата": date_str, "Банк": bank_name, "Показатель": name, "Значение": "=" + acc}
                    )

        df_long = pd.DataFrame(out_rows)
        print(f"[INFO] 101 long rows: {len(df_long)}")
        return df_long, indicator_order

    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


# ----------------------------
# Public run()
# ----------------------------
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
