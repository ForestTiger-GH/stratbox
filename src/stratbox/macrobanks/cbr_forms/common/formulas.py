"""
common/formulas.py

Задача:
- читать табличные модели формул из macrobanks/cbr_forms/models/formulas.csv
- давать удобные функции фильтрации под конкретную форму и режим работы

Важно:
- Формулы могут меняться (formulas2 и т.п.). Поэтому:
  * функции принимают path как параметр (по умолчанию берут models/formulas.csv)
  * фильтрация максимально простая (form/kind)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


def _default_models_dir() -> Path:
    """
    Возвращает путь к папке models рядом с этим модулем.
    """
    return Path(__file__).resolve().parents[1] / "models"


def load_formulas(csv_path: str | Path | None = None) -> pd.DataFrame:
    """
    Загружает formulas.csv в DataFrame.

    Ожидаемые колонки:
      - form
      - kind
      - name
      - expression
      - extra (может быть пустой)

    Возвращает DataFrame (строки как есть из CSV).
    """
    if csv_path is None:
        csv_path = _default_models_dir() / "formulas.csv"
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"formulas.csv not found: {csv_path}")

    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    need = {"form", "kind", "name", "expression", "extra"}
    miss = need - set(df.columns)
    if miss:
        raise RuntimeError(f"formulas.csv missing columns: {sorted(miss)}; got={list(df.columns)}")

    # минимальная нормализация
    df["form"] = df["form"].astype(str).str.strip()
    df["kind"] = df["kind"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    df["expression"] = df["expression"].astype(str).str.strip()
    df["extra"] = df["extra"].astype(str).str.strip()

    return df


def get_formulas_for(
    df_formulas: pd.DataFrame,
    *,
    form: str,
    kind: str | None = None,
) -> pd.DataFrame:
    """
    Фильтрует формулы под конкретную форму и (опционально) kind.

    Примеры:
      - get_formulas_for(df, form="123", kind="formula")
      - get_formulas_for(df, form="135", kind="metric")
      - get_formulas_for(df, form="101")  # все виды
    """
    f = str(form).strip()
    out = df_formulas[df_formulas["form"].astype(str) == f].copy()

    if kind is not None:
        k = str(kind).strip()
        out = out[out["kind"].astype(str) == k].copy()

    return out.reset_index(drop=True)
