"""
Модуль содержит функции работы со списком банков для задач CBR forms.

Требование пользователя:
- legacy-список банков формируется из registries.cbr_banks.read()
- используется колонка is_legacy:
    * число (порядковый номер для сортировки legacy)
    * False, если банк не в legacy
- для выгрузок по умолчанию используется нормализованное краткое имя банка,
  если в реестре доступна колонка bank_name_norm
"""

from __future__ import annotations

import pandas as pd

from stratbox.registries import cbr_banks


def _pick_display_name(df: pd.DataFrame) -> pd.Series:
    """
    Возвращает Series с отображаемым именем банка для CBR forms.

    Приоритет выбора имени:
    1) bank_name_norm — краткое нормализованное имя (по умолчанию для выгрузок)
    2) bank
    3) name
    4) bank_name

    Если приоритетная колонка существует, но значение пустое / NAN,
    используется следующий доступный вариант.
    """
    candidate_cols = ["bank_name_norm", "bank", "name", "bank_name"]
    available_cols = [col for col in candidate_cols if col in df.columns]
    if not available_cols:
        raise RuntimeError(
            f"Cannot find bank name column in cbr_banks.read(): {list(df.columns)}"
        )

    result = pd.Series(index=df.index, dtype="object")

    for col in available_cols:
        values = df[col].astype(str).str.strip()
        values = values.mask(values.eq(""), pd.NA)
        values = values.mask(values.str.upper().isin(["NAN", "NONE", "NULL"]), pd.NA)
        if result.isna().all():
            result = values
        else:
            result = result.fillna(values)

    return result.fillna("").astype(str)


def load_legacy_banks() -> pd.DataFrame:
    """
    Возвращает DataFrame для legacy-банков:
      - bank (str)  : имя банка для выгрузки
      - regn (int)  : регистрационный номер
      - sort (int)  : порядок (из is_legacy)

    Примечание:
    - Если is_legacy=False — банк исключается.
    - По умолчанию для bank используется bank_name_norm, если колонка есть.
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

    if "regn" not in df.columns:
        raise RuntimeError(f"Cannot find 'regn' column in cbr_banks.read(): {list(df.columns)}")

    display_name = _pick_display_name(df)

    out = pd.DataFrame(
        {
            "bank": display_name,
            "regn": pd.to_numeric(df["regn"], errors="coerce").fillna(-1).astype(int),
            "sort": df["sort"].astype(int),
        }
    )

    out = out[out["regn"] > 0].copy()
    out = out.sort_values("sort").reset_index(drop=True)

    return out
