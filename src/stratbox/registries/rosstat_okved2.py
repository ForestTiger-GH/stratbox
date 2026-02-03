"""
rosstat_okved2.py — ОКВЭД2 (Росстат), хранится в виде трёх CSV в ресурсах пакета.

Принцип обновления:
- в папку src/stratbox/registries/_resources/rosstat_okved2/ кладутся 3 файла:
  - data*.csv       (основной список)
  - meta*.csv       (метаданные)
  - structure*.csv  (описание структуры)
- имена могут быть любыми (как скачались)
- если файлов несколько — берём самый свежий для каждого типа

Важно по формату твоих файлов:
- encoding = cp1251
- separator = ';'
- строки в кавычках

Выход:
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


def _read_csv(prefix: str) -> pd.DataFrame:
    """
    Читает самый свежий CSV с заданным prefix (meta/structure/data).
    """
    rf = pick_latest_by_prefix(_PACKAGE, _REL_DIR, prefix=prefix, suffix=".csv")
    raw = read_resource_bytes(_PACKAGE, rf.path)

    df = pd.read_csv(
        BytesIO(raw),
        encoding="cp1251",
        sep=";",
        dtype=str,
        engine="python",
    )
    return df


def read_raw_bundle() -> dict[str, pd.DataFrame]:
    """
    Возвращает "сырой комплект" data/meta/structure (как DataFrame),
    если вдруг понадобится для диагностики или расширений.
    """
    return {
        "data": _read_csv("data"),
        "meta": _read_csv("meta"),
        "structure": _read_csv("structure"),
    }


def read() -> pd.DataFrame:
    """
    Возвращает нормализованный справочник ОКВЭД2: section/code/name.
    """
    bundle = read_raw_bundle()
    df = bundle["data"].copy()

    # ожидаемые колонки: Razdel, Code, Name (как в твоём файле)
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

    # Удаляем строки без кода (в файле есть секционные строки с пустым Code)
    out = out[out["code"].astype(str).str.strip().ne("")]

// optional: сброс индекса
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
