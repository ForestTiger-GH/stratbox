"""
rosstat_okved2.py — ОКВЭД2 (Росстат), хранится в виде трёх CSV в ресурсах пакета.

Принцип обновления:
- в папку src/stratbox/registries/_resources/rosstat_okved2/ кладутся файлы:
  - data*.csv       (основной список)  <-- ЭТО ЕДИНСТВЕННОЕ, ЧТО НУЖНО ДЛЯ РАБОТЫ read()
  - meta*.csv       (метаданные)       <-- может быть кривым, читается отдельно и мягко
  - structure*.csv  (описание полей)   <-- может быть кривым, читается отдельно и мягко
- имена могут быть любыми (как скачались)
- если файлов несколько — берём самый свежий для каждого типа (по времени изменения)

Важно по формату твоих файлов:
- encoding = cp1251
- separator = ';'
- строки часто в кавычках

Выход read():
- DataFrame с каноническими колонками:
  - section (Razdel)
  - code (Code)
  - name (Name)
- строки без code (например секционные описания вида "A; ; ...") удаляются
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from stratbox.registries._loader import pick_latest_by_prefix, read_resource_bytes

_PACKAGE = "stratbox.registries"
_REL_DIR = "_resources/rosstat_okved2"


def _read_csv_strict(prefix: str) -> pd.DataFrame:
    """
    Строгое чтение CSV (ожидаем корректный формат).
    Используется для data*.csv, который нам реально нужен.
    """
    rf = pick_latest_by_prefix(_PACKAGE, _REL_DIR, prefix=prefix, suffix=".csv")
    raw = read_resource_bytes(_PACKAGE, rf.path)

    if prefix == "data":
        # В файле data*.csv заголовков нет, первая строка — это данные.
        df = pd.read_csv(
            BytesIO(raw),
            encoding="cp1251",
            sep=";",
            dtype=str,
            engine="python",
            header=None,
            names=["Razdel", "Code", "Name"],
        )
    else:
        # meta/structure можно читать как есть (если понадобится)
        df = pd.read_csv(
            BytesIO(raw),
            encoding="cp1251",
            sep=";",
            dtype=str,
            engine="python",
        )

    return df


def _read_csv_soft(prefix: str) -> pd.DataFrame:
    """
    Мягкое чтение CSV: предназначено для meta/structure, которые иногда бывают "кривые".
    Если строгий парсер падает — пробует прочитать максимально терпимо.
    """
    rf = pick_latest_by_prefix(_PACKAGE, _REL_DIR, prefix=prefix, suffix=".csv")
    raw = read_resource_bytes(_PACKAGE, rf.path)

    try:
        return pd.read_csv(
            BytesIO(raw),
            encoding="cp1251",
            sep=";",
            dtype=str,
            engine="python",
        )
    except Exception:
        # fallback: читаем построчно и пропускаем "плохие" строки
        return pd.read_csv(
            BytesIO(raw),
            encoding="cp1251",
            sep=";",
            dtype=str,
            engine="python",
            on_bad_lines="skip",
        )


def read_meta() -> pd.DataFrame:
    """
    Возвращает meta*.csv (если нужно человеку/диагностике).
    Не используется в основном read().
    """
    return _read_csv_soft("meta")


def read_structure() -> pd.DataFrame:
    """
    Возвращает structure*.csv (если нужно человеку/диагностике).
    Не используется в основном read().
    """
    return _read_csv_soft("structure")


def read() -> pd.DataFrame:
    """
    Возвращает нормализованный справочник ОКВЭД2: section/code/name.
    """
    df = _read_csv_strict("data").copy()

    # ожидаемые колонки: Razdel, Code, Name
    cols = {c.lower(): c for c in df.columns}
    need = ["razdel", "code", "name"]
    if not all(k in cols for k in need):
        raise ValueError(
            f'OKVED2 registry: expected columns {need}; got columns={list(df.columns)}'
        )

    out = pd.DataFrame(
        {
            "section": df[cols["razdel"]].astype(str).str.strip(),
            "code": df[cols["code"]].astype(str).str.strip(),
            "name": df[cols["name"]].astype(str).str.strip(),
        }
    )
    out["code"] = out["code"].astype(str).str.strip().replace({"nan": ""})

    # Удаляем строки без кода (в файле есть секционные строки с пустым Code)
    out = out[out["code"].astype(str).str.strip().ne("")]


    # Правильная фильтрация:
    out = out[out["code"].astype(str).str.strip().ne("")]

    # Сброс индекса:
    out = out.reset_index(drop=True)
    return out


def lookup(code: str) -> dict | None:
    """
    Поиск названия по коду ОКВЭД2.
    """
    if code is None:
        return None

    key = str(code).strip()
    df = read()
    hit = df[df["code"] == key]
    if hit.empty:
        return None
    return hit.iloc[0].to_dict()
