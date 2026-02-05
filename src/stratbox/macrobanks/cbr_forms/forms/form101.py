"""
Форма 101: индивидуальный скелет формы (выбор DBF + извлечение значений по коду).

Ключевая идея:
- Формулы приходят извне (formulas_df), банки приходят извне (banks_df).
- Внутри формы зашит "резолвер": как по коду (например 401, 45.2) найти значение в DBF.
- Учитывается extra из formulas.csv, например a_p=1/2 (если в DBF есть соответствующее поле).

Выход:
- df_long: Дата | Банк | Показатель | Значение (Excel-формула "=...")
- indicator_order: порядок показателей (для wide-сборки)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from dbfread import DBF
from tqdm.auto import trange

from stratbox.macrobanks.cbr_forms.common.formulas import get_formulas_for
from stratbox.macrobanks.cbr_forms.common.runner import RunnerConfig, run_dates_to_dbf_df
from stratbox.macrobanks.cbr_forms.common.dbf import CBRFieldParser
from stratbox.macrobanks.cbr_forms.common.dbf_picker import LayoutCandidates


FORM = "101"
DEFAULT_PREFER = "101"

# Для 101 мы хотим получить "полный" df по всем полям, поэтому:
# - runner используется только как: download+extract+pick DBF,
#   а чтение DBF (всё поле целиком) делаем внутри формы.
DEFAULT_CANDIDATES = LayoutCandidates(
    # В 101 реально есть REGN
    regn_candidates=["REGN"],
    # Код счета/агрегата в 101 — NUM_SC (см. документацию)
    a_candidates=["NUM_SC"],
    # Для выбора подходящего DBF используем поля итогов:
    # IITG — исходящие остатки "итого" (на отчетную дату), VITG — входящие
    b_candidates=["IITG", "VITG"],
)



def build_url(d: pd.Timestamp) -> str:
    ymd = pd.Timestamp(d).strftime("%Y%m%d")
    return f"https://www.cbr.ru/vfs/credit/forms/101-{ymd}.rar"


def _parse_extra(extra: str) -> dict:
    """
    Парсит extra типа 'a_p=1' в dict.
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


def _norm_regn(x) -> str:
    return re.sub(r"\D+", "", "" if x is None else str(x))


def _norm_code(x) -> str:
    """
    Нормализует код из формулы и из DBF:
    - допускает значения вида 45.2
    - убирает пробелы
    """
    if x is None:
        return ""
    s = str(x).strip()
    s = s.replace(",", ".")
    # оставляем цифры и точку
    s2 = re.sub(r"[^0-9.]+", "", s)
    return s2


def _to_value_str(v) -> str:
    """
    Возвращает значение как строку для Excel-формулы.
    """
    if v is None:
        return "0"
    if isinstance(v, float) and np.isnan(v):
        return "0"
    s = str(v).strip().replace(",", ".")
    return s if s else "0"


def _read_dbf_full(dbf_path: str) -> pd.DataFrame:
    """
    Читает DBF целиком (все поля) в DataFrame.
    """
    dbf = DBF(dbf_path, parserclass=CBRFieldParser)
    rows = list(dbf)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def _pick_cols_for_101(df: pd.DataFrame) -> tuple[str, str, str]:
    """
    Пытается определить:
      regn_col: колонка с REGN
      code_col: колонка с кодом показателя (401, 45.2, ...)
      val_col : колонка со значением
    """
    if df is None or len(df) == 0:
        raise RuntimeError("Empty DBF dataframe.")

    cols_u = {c.upper(): c for c in df.columns}

    # 1) REGN
    regn_col = None
    for cand in ["REGN", "REG", "REG_NUM", "REGN_BNK"]:
        if cand in cols_u:
            regn_col = cols_u[cand]
            break
    if regn_col is None:
        raise RuntimeError(f"REGN column not found in DBF. Columns={list(df.columns)}")

    # 2) CODE
    code_col = None
    for cand in ["NUM_SC", "CODE", "COD", "ROW", "STR", "NUM", "NP", "N", "P", "C1", "C_1", "ACC", "ACCOUNT", "A"]:
        if cand in cols_u:
            code_col = cols_u[cand]
            break

    if code_col is None:
        # fallback: первая "похожая" колонка
        for c in df.columns:
            cu = c.upper()
            if "CODE" in cu or "ROW" in cu or "STR" in cu:
                code_col = c
                break
    if code_col is None:
        raise RuntimeError(f"CODE column not found in DBF. Columns={list(df.columns)}")

    # 3) VALUE
    val_col = None
    for cand in ["IITG", "VITG", "VALUE", "VAL", "SUM", "AMT", "C2", "C_2", "C3", "C_3", "B"]:
        if cand in cols_u:
            val_col = cols_u[cand]
            break

    if val_col is None:
        # fallback: попробуем найти первую числовую колонку (кроме regn/code)
        for c in df.columns:
            if c in [regn_col, code_col]:
                continue
            # простая эвристика
            if pd.api.types.is_numeric_dtype(df[c]):
                val_col = c
                break
    if val_col is None:
        raise RuntimeError(f"VALUE column not found in DBF. Columns={list(df.columns)}")

    return regn_col, code_col, val_col


def _apply_ap_filter(df: pd.DataFrame, ap: str | None) -> pd.DataFrame:
    """
    Если в DBF есть поле секции (a_p), фильтруем.
    Если поля нет — возвращаем df без изменений.
    """
    if ap is None:
        return df

    cols_u = {c.upper(): c for c in df.columns}
    # самые вероятные имена поля секции
    for cand in ["A_P", "AP", "A_P_R", "A_PRC", "SECTION", "SECT", "PART"]:
        if cand in cols_u:
            col = cols_u[cand]
            # сравниваем как строку/число
            return df[df[col].astype(str).str.strip() == str(ap).strip()].copy()

    return df


def _resolve_value_101(
    df_full: pd.DataFrame,
    regn_col: str,
    code_col: str,
    val_col: str,
    *,
    regn_bank: str,
    code: str,
    extra: dict,
) -> str:
    """
    Ищет значение по (REGN, CODE) с учётом extra (например a_p=1/2).
    """
    df = df_full.copy()
    df["__REGN__"] = df[regn_col].map(_norm_regn)
    df["__CODE__"] = df[code_col].map(_norm_code)

    # фильтр по банку
    df = df[df["__REGN__"] == _norm_regn(regn_bank)].copy()
    if len(df) == 0:
        return "0"

    # фильтр по a_p, если применимо
    ap = extra.get("a_p")
    df = _apply_ap_filter(df, ap)
    if len(df) == 0:
        return "0"

    # матч по коду
    c = _norm_code(code)
    m = df[df["__CODE__"] == c]
    if len(m) == 0:
        # fallback: убрать ведущие нули (иногда бывает)
        c2 = c.lstrip("0") or "0"
        m = df[df["__CODE__"] == c2]

    if len(m) == 0:
        return "0"

    v = m[val_col].iloc[0]
    return _to_value_str(v)


def build_long(
    date_dbf_paths: list[tuple[str, str]],
    banks_df: pd.DataFrame,
    formulas_df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    """
    date_dbf_paths: [(date_str, dbf_path), ...]
    """
    fdf = get_formulas_for(formulas_df, form=FORM, kind="formula")
    if len(fdf) == 0:
        raise RuntimeError("No formulas for form 101 in formulas_df.")

    indicator_order = {row["name"]: i for i, row in fdf.iterrows()}
    rows = []

    for date_str, dbf_path in date_dbf_paths:
        df_full = _read_dbf_full(dbf_path)
        if len(df_full) == 0:
            continue

        regn_col, code_col, val_col = _pick_cols_for_101(df_full)

        for _, b in banks_df.iterrows():
            bank_name = str(b["bank"])
            regn_bank = str(int(b["regn"]))

            for _, fr in fdf.iterrows():
                name = fr["name"]
                expr = fr["expression"]
                extra = _parse_extra(fr.get("extra", ""))

                # токены: числа (включая 45.2) и +/-
                tokens = re.findall(r"\d+(?:\.\d+)?|[+]{1}|[-]{1}", str(expr))
                acc = ""

                for t in tokens:
                    if t in ["+", "-"]:
                        acc += t
                        continue

                    val = _resolve_value_101(
                        df_full,
                        regn_col,
                        code_col,
                        val_col,
                        regn_bank=regn_bank,
                        code=str(t),
                        extra=extra,
                    )
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
) -> tuple[pd.DataFrame, dict[str, int] | None]:
    """
    Запуск формы 101:
    - скачивает/распаковывает архивы
    - выбирает DBF по кандидатурам полей
    - читает DBF целиком и строит df_long
    """
    candidates = candidates or DEFAULT_CANDIDATES
    prefer_stem_contains = prefer_stem_contains or DEFAULT_PREFER
    cfg = cfg or RunnerConfig()

    # Используем runner, чтобы получить (date_str, df_dbf_simplified),
    # но нам нужны пути DBF. Поэтому немного "хитрим":
    # run_dates_to_dbf_df сейчас отдаёт только df, без пути — поэтому делаем второй проход:
    # ВАЖНО: это место позже улучшим (runner будет возвращать path + layout).
    #
    # Пока делаем простой и надёжный путь:
    # - повторяем логику runner: скачать/распаковать/выбрать DBF
    # - но используем существующие общие функции выборки DBF, чтобы не плодить код.
    from stratbox.base.filestore import make_workdir
    import shutil
    import subprocess
    from stratbox.base.net.http import download_bytes
    from stratbox.macrobanks.cbr_forms.common.dbf_picker import pick_dbf_and_layout

    work_dir = Path(make_workdir(prefix="cbr_forms_101_"))
    out_paths: list[tuple[str, str]] = []

    try:
        # локальные функции распаковки (как в runner.py)
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

        it = trange(len(dates), desc="CBR 101", leave=False)
        for i in it:
            d = dates[i]
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

        print(f"[INFO] 101 DBF picked: {len(out_paths)}")
        return build_long(out_paths, banks_df, formulas_df)

    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass
