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
import json

import pandas as pd

from stratbox.registries._loader import pick_latest_by_suffix, pick_latest_by_prefix, read_resource_bytes
from stratbox.text.banks import normalize_bank_name


_PACKAGE = "stratbox.registries"

# Папка с XLSX от ЦБ
_REL_DIR_BANKS = "_resources/cbr_banks"

# Три кастомных реестра
_REL_DIR_REPL = "_resources/cbr_replacements"
_REL_DIR_STANDART = "_resources/cbr_standart"
_REL_DIR_LEGACY = "_resources/cbr_legacy"


def _load_raw_xlsx() -> pd.DataFrame:
    """
    Читает самый свежий XLSX из ресурсов и возвращает DataFrame как есть.
    """
    rf = pick_latest_by_suffix(_PACKAGE, _REL_DIR_BANKS, ".xlsx")
    raw = read_resource_bytes(_PACKAGE, rf.path)

    # engine обычно определяется автоматически; если в окружении нет openpyxl,
    # pandas выдаст понятную ошибку.
    df = pd.read_excel(BytesIO(raw))
    return df

def _read_latest_csv(rel_dir: str, prefix: str | None = None) -> pd.DataFrame:
    """
    Читает самый свежий CSV в указанной папке ресурсов.

    - Если prefix задан: ищет prefix*.csv
    - Если prefix не задан: берёт любой *.csv
    - Если файла нет: возвращает пустой DataFrame (чтобы библиотека не падала)
    """
    try:
        if prefix:
            rf = pick_latest_by_prefix(_PACKAGE, rel_dir, prefix=prefix, suffix=".csv")
        else:
            rf = pick_latest_by_suffix(_PACKAGE, rel_dir, ".csv")
    except FileNotFoundError:
        return pd.DataFrame()

    raw = read_resource_bytes(_PACKAGE, rf.path)
    return pd.read_csv(BytesIO(raw), dtype=str, encoding="utf-8-sig")


def _load_replacements() -> dict[str, list[str]]:
    """
    Словарь:
      CANON -> [ALIAS1, ALIAS2, ...]
    Всё приводится к UPPER и strip.
    """
    df = _read_latest_csv(_REL_DIR_REPL, prefix="cbr_replacements")
    if df.empty:
        return {}

    cols = {c.lower(): c for c in df.columns}
    need = {"canon", "alias"}
    if not need.issubset(cols.keys()):
        raise ValueError("cbr_replacements.csv must have columns: canon, alias")

    c_canon = cols["canon"]
    c_alias = cols["alias"]

    tmp = df[[c_canon, c_alias]].copy()
    tmp[c_canon] = tmp[c_canon].astype(str).str.strip().str.upper()
    tmp[c_alias] = tmp[c_alias].astype(str).str.strip().str.upper()

    out: dict[str, list[str]] = {}
    for canon, sub in tmp.groupby(c_canon):
        aliases = [a for a in sub[c_alias].tolist() if a and a != "NAN"]
        seen = set()
        uniq = []
        for a in aliases:
            if a not in seen:
                uniq.append(a)
                seen.add(a)
        out[canon] = uniq
    return out


def _load_standart_enabled() -> set[str]:
    """
    Возвращает множество банков, у которых enabled=True в cbr_standart.csv.

    Важно: чтобы коллегам не нужно было вручную следить за точным каноном,
    каждое значение bank прогоняется через normalize_bank_name().
    """
    df = _read_latest_csv(_REL_DIR_STANDART, prefix="cbr_standart")
    if df.empty:
        return set()

    cols = {c.lower(): c for c in df.columns}
    need = {"enabled", "bank"}
    if not need.issubset(cols.keys()):
        raise ValueError("cbr_standart.csv must have columns: enabled, bank")

    c_enabled = cols["enabled"]
    c_bank = cols["bank"]

    tmp = df[[c_enabled, c_bank]].copy()
    tmp[c_enabled] = tmp[c_enabled].astype(str).str.strip().str.lower()

    # Берём только enabled=True
    tmp = tmp[tmp[c_enabled].isin({"true", "1", "yes", "y"})].copy()

    # Нормализуем bank через общую функцию (включая финальные replacements)
    tmp[c_bank] = tmp[c_bank].map(
        lambda s: normalize_bank_name(s, placement="omit", case_mode="upper", drop_bank="left")
    )

    banks = tmp[c_bank].astype(str).str.strip().str.upper().tolist()
    return set([b for b in banks if b and b != "NAN"])



def _load_legacy_set() -> set[str]:
    """
    Возвращает множество legacy банков по колонке bank из cbr_legacy.csv.
    """
    df = _read_latest_csv(_REL_DIR_LEGACY, prefix="cbr_legacy")
    if df.empty:
        return set()

    cols = {c.lower(): c for c in df.columns}
    need = {"bank", "regn", "sort"}
    if not need.issubset(cols.keys()):
        raise ValueError("cbr_legacy.csv must have columns: bank, regn, sort")

    c_bank = cols["bank"]
    banks = df[c_bank].astype(str).str.strip().str.upper().tolist()
    return set([b for b in banks if b and b != "NAN"])


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

    # Нормализованное имя банка для таблиц/графиков: CAPS LOCK, без тегов, без "БАНК" слева
    out["bank_name_norm"] = out["bank_name"].map(
        lambda s: normalize_bank_name(s, placement="omit", case_mode="upper", drop_bank="left")
    )
    # --- Подмешивание кастомных реестров: standart / replacements / legacy ---

    # 1) standart: включённые канонические банки
    standart_enabled = _load_standart_enabled()
    out["is_canonical"] = out["bank_name_norm"].astype(str).str.strip().str.upper().isin(standart_enabled)

    # 2) replacements: CANON -> [ALIAS...]
    rep_map = _load_replacements()

    def _aliases_for(bank_norm: str):
        key = str(bank_norm).strip().upper()
        return rep_map.get(key, [])

    # Два представления списка замен:
    # - replacements_list: удобен для кода
    # - replacements_json: удобен для выгрузки в CSV/XLSX и универсального хранения
    out["replacements_list"] = out["bank_name_norm"].map(_aliases_for)
    out["replacements_json"] = out["replacements_list"].map(lambda x: json.dumps(x, ensure_ascii=False))

    # 3) legacy
    legacy_set = _load_legacy_set()
    out["is_legacy"] = out["bank_name_norm"].astype(str).str.strip().str.upper().isin(legacy_set)

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
