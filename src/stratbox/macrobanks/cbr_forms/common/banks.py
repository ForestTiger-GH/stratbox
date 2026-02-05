"""
Модуль содержит функции работы со списком банков для задач CBR forms.

Требование пользователя:
- legacy-список банков формируется из registries.cbr_banks.read()
- используется колонка is_legacy:
    * число (порядковый номер для сортировки legacy)
    * False, если банк не в legacy
"""

from __future__ import annotations

import pandas as pd

from stratbox.registries import cbr_banks


def load_legacy_banks() -> pd.DataFrame:
    """
    Возвращает DataFrame для legacy-банков:
      - bank (str)  : имя банка
      - regn (int)  : регистрационный номер
      - sort (int)  : порядок (из is_legacy)

    Примечание:
    - Если is_legacy=False — банк исключается.
    """
    df = cbr_banks.read().copy()

    if "is_legacy" not in df.columns:
        raise RuntimeError("cbr_banks registry has no column 'is_legacy'. Please update registry.")

    # Оставляются только legacy-банки
    mask = df["is_legacy"].apply(lambda x: x is not False and x is not None)
    df = df[mask].copy()

    # Приведение типов
    df["sort"] = pd.to_numeric(df["is_legacy"], errors="coerce")
    df = df[df["sort"].notna()].copy()
    df["sort"] = df["sort"].astype(int)

    # Имена в реестре могут называться по-разному; поддержим оба варианта
    name_col = "bank" if "bank" in df.columns else ("name" if "name" in df.columns else None)
    if name_col is None:
        # fallback: частый вариант в cbr_banks — "bank_name"
        name_col = "bank_name" if "bank_name" in df.columns else None
    if name_col is None:
        raise RuntimeError(f"Cannot find bank name column in cbr_banks.read(): {list(df.columns)}")

    if "regn" not in df.columns:
        raise RuntimeError(f"Cannot find 'regn' column in cbr_banks.read(): {list(df.columns)}")

    out = pd.DataFrame(
        {
            "bank": df[name_col].astype(str),
            "regn": pd.to_numeric(df["regn"], errors="coerce").fillna(-1).astype(int),
            "sort": df["sort"].astype(int),
        }
    )

    out = out[out["regn"] > 0].copy()
    out = out.sort_values("sort").reset_index(drop=True)

    return out
