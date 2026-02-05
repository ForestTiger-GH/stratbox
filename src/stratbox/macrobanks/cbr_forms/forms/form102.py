"""
Форма 102: индивидуальный скелет формы (выбор DBF + извлечение значений по коду строк).

Логика аналогична 101, но:
- у 102 нет a_p в extra (в твоём formulas.csv extra пустой)
- коды обычно целые (11000, 27000, 61101, ...)

Выход:
- df_long: Дата | Банк | Показатель | Значение (Excel-формула "=...")
- indicator_order: порядок показателей (для wide-сборки)
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from dbfread import DBF

from stratbox.macrobanks.cbr_forms.common.formulas import get_formulas_for
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig
from stratbox.macrobanks.cbr_forms.common.dbf import CBRFieldParser
from stratbox.macrobanks.cbr_forms.common.dbf_picker import LayoutCandidates


FORM = "102"
DEFAULT_PREFER = "102"

DEFAULT_CANDIDATES = LayoutCandidates(
    regn_candidates=["REGN", "REG", "REG_NUM", "REGN_BNK"],
    a_candidates=["CODE", "COD", "ROW", "STR", "NUM", "C1", "C_1", "A", "NP", "N", "P"],
    b_candidates=["VALUE", "VAL", "SUM", "AMT", "C2", "C_2", "C3", "C_3", "B"],
)


def build_url(d: pd.Timestamp) -> str:
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/102-{ymd}.rar"


def _norm_regn(x) -> str:
    return re.sub(r"\D+", "", "" if x is None else str(x))


def _norm_code(x) -> str:
    if x is None:
        return ""
    s = str(x).strip().replace(",", ".")
    s2 = re.sub(r"[^0-9.]+", "", s)
    # для 102 чаще всего целые — но не режем точку насильно
    return s2


def _to_value_str(v) -> str:
    if v is None:
        return "0"
    if isinstance(v, float) and np.isnan(v):
        return "0"
    s = str(v).strip().replace(",", ".")
    return s if s else "0"


def _read_dbf_full(dbf_path: str) -> pd.DataFrame:
    dbf = DBF(dbf_path, parserclass=CBRFieldParser)
    rows = list(dbf)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _pick_cols_for_102(df: pd.DataFrame) -> tuple[str, str, str]:
    if df is None or len(df) == 0:
        raise RuntimeError("Empty DBF dataframe.")

    cols_u = {c.upper(): c for c in df.columns}

    regn_col = None
    for cand in ["REGN", "REG", "REG_NUM", "REGN_BNK"]:
        if cand in cols_u:
            regn_col = cols_u[cand]
            break
    if regn_col is None:
        raise RuntimeError(f"REGN column not found in DBF. Columns={list(df.columns)}")

    code_col = None
    for cand in ["CODE", "COD", "ROW", "STR", "NUM", "NP", "N", "P", "C1", "C_1", "A"]:
        if cand in cols_u:
            code_col = cols_u[cand]
            break
    if code_col is None:
        for c in df.columns:
            cu = c.upper()
            if "CODE" in cu or "ROW" in cu or "STR" in cu:
                code_col = c
                break
    if code_col is None:
        raise RuntimeError(f"CODE column not found in DBF. Columns={list(df.columns)}")

    val_col = None
    for cand in ["VALUE", "VAL", "SUM", "AMT", "C2", "C_2", "C3", "C_3", "B"]:
        if cand in cols_u:
            val_col = cols_u[cand]
            break
    if val_col is None:
        for c in df.columns:
            if c in [regn_col, code_col]:
                continue
            if pd.api.types.is_numeric_dtype(df[c]):
                val_col = c
                break
    if val_col is None:
        raise RuntimeError(f"VALUE column not found in DBF. Columns={list(df.columns)}")

    return regn_col, code_col, val_col


def _resolve_value_102(
    df_full: pd.DataFrame,
    regn_col: str,
    code_col: str,
    val_col: str,
    *,
    regn_bank: str,
    code: str,
) -> str:
    df = df_full.copy()
    df["__REGN__"] = df[regn_col].map(_norm_regn)
    df["__CODE__"] = df[code_col].map(_norm_code)

    df = df[df["__REGN__"] == _norm_regn(regn_bank)].copy()
    if len(df) == 0:
        return "0"

    c = _norm_code(code)
    m = df[df["__CODE__"] == c]
    if len(m) == 0:
        c2 = c.lstrip("0") or "0"
        m = df[df["__CODE__"] == c2]

    if len(m) == 0:
        return "0"

    return _to_value_str(m[val_col].iloc[0])


def build_long(
    date_dbf_paths: list[tuple[str, str]],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    fdf = get_formulas_for(formulas_df, form=FORM, kind="formula")
    if len(fdf) == 0:
        raise RuntimeError("No formulas for form 102 in formulas_df.")

    indicator_order = {row["name"]: i for i, row in fdf.iterrows()}
    rows = []

    for date_str, dbf_path in date_dbf_paths:
        df_full = _read_dbf_full(dbf_path)
        if len(df_full) == 0:
            continue

        regn_col, code_col, val_col = _pick_cols_for_102(df_full)

        for _, b in banks_df.iterrows():
            bank_name = str(b["bank"])
            regn_bank = str(int(b["regn"]))

            for _, fr in fdf.iterrows():
                name = fr["name"]
                expr = fr["expression"]

                tokens = re.findall(r"\d+|[+]{1}|[-]{1}", str(expr))
                acc = ""

                for t in tokens:
                    if t in ["+", "-"]:
                        acc += t
                        continue

                    val = _resolve_value_102(df_full, regn_col, code_col, val_col, regn_bank=regn_bank, code=str(t))
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
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    """
    Запуск формы 102:
    - скачивает/распаковывает архивы
    - выбирает DBF по кандидатурам полей
    - читает DBF целиком и строит df_long
    """
    candidates = candidates or DEFAULT_CANDIDATES
    prefer_stem_contains = prefer_stem_contains or DEFAULT_PREFER
    cfg = cfg or RunnerConfig()

    from stratbox.base.filestore import make_workdir
    import shutil
    import subprocess
    from stratbox.base.net.http import download_bytes
    from stratbox.macrobanks.cbr_forms.common.dbf_picker import pick_dbf_and_layout

    work_dir = Path(make_workdir(prefix="cbr_forms_102_"))
    out_paths: list[tuple[str, str]] = []

    try:
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

        for d in dates:
            d = pd.Timestamp(d)
            date_str = d.strftime("%d.%m.%Y")
            url = build_url(d)

            res = download_bytes(
                url=url,
                timeout=cfg.timeout,
                retries=cfg.retries,
                backoff=cfg.backoff,
                min_bytes_ok=cfg.min_bytes_ok,
                headers=None,
                plugin_only=True,
            )
            if not res.ok or not res.content:
                continue

            ymd = d.strftime("%Y%m%d")
            rar_path = work_dir / f"tmp_{ymd}.rar"
            rar_path.write_bytes(res.content)

            ex_dir = work_dir / f"ex_{ymd}"
            _extract_rar(rar_path, ex_dir)

            dbf_path, _layout = pick_dbf_and_layout(ex_dir, candidates=candidates, prefer_stem_contains=prefer_stem_contains)
            out_paths.append((date_str, str(dbf_path)))

        print(f"[INFO] 102 DBF picked: {len(out_paths)}")
        return build_long(out_paths, banks_df, formulas_df)

    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass
