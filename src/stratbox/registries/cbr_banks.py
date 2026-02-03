"""
cbr_banks.py — реестр банков (ЦБ), хранится в виде XLSX в ресурсах пакета.

Принцип обновления:
- в папку src/stratbox/registries/_resources/cbr_banks/ кладётся новый xlsx
- имя файла может быть любым
- если xlsx несколько — будет выбран самый свежий по времени изменения

Выход:
- DataFrame с каноническими колонками:
  - regn (строка)
  - bank_name (исходное название)
  - bank_name_norm (нормализованное название; пока заглушка)
  - lic_status (если есть)
  - остальные колонки сохраняются как есть
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from stratbox.registries._loader import pick_latest_by_suffix, read_resource_bytes
from stratbox.text.banks import normalize_bank_name

_PACKAGE = "stratbox.registries"
_REL_DIR = "_resources/cbr_banks"


def _load_raw_xlsx() -> pd.DataFrame:
    """
    Читает самый свежий XLSX из ресурсов и возвращает DataFrame как есть.
    """
    rf = pick_latest_by_suffix(_PACKAGE, _REL_DIR, ".xlsx")
    raw = read_resource_bytes(_PACKAGE, rf.path)

    # engine обычно определяется автоматически; если в окружении нет openpyxl,
    # pandas выдаст понятную ошибку.
    df = pd.read_excel(BytesIO(raw))
    return df


def read() -> pd.DataFrame:
    """
    Возвращает нормализованный DataFrame реестра банков.

    Канонические поля:
    - regn: регистрационный номер (строка)
    - bank_name: исходное имя банка
    - bank_name_norm: нормализованное имя (пока заглушка)
    """
    df = _load_raw_xlsx()

    # ожидаемые колонки в файле ЦБ (по твоему примеру):
    # cregnum, bnk_name, lic_status, ...
    cols = {c.lower(): c for c in df.columns}

    if "cregnum" not in cols or "bnk_name" not in cols:
        raise ValueError(
            f'Banks registry: expected columns "cregnum" and "bnk_name"; got columns={list(df.columns)}'
        )

    creg = cols["cregnum"]
    bname = cols["bnk_name"]

    out = df.copy()

    # regn — всегда строка, без .0, пробелов и т.п.
    out["regn"] = out[creg].astype(str).str.replace(".0", "", regex=False).str.strip()
    out["bank_name"] = out[bname].astype(str).str.strip()

    # место под будущую нормализацию
    out["bank_name_norm"] = out["bank_name"].map(normalize_bank_name)

    # lic_status, если есть — сохраняем в каноническое поле
    if "lic_status" in cols:
        out["lic_status"] = out[cols["lic_status"]]

    return out


def lookup(regn: str) -> dict | None:
    """
    Быстрый поиск банка по regn.
    Возвращает dict (строку таблицы) или None.
    """
    if regn is None:
        return None

    key = str(regn).strip()
    df = read()
    hit = df[df["regn"] == key]
    if hit.empty:
        return None
    return hit.iloc[0].to_dict()
