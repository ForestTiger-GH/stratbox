"""
excel_xlsx — чтение/запись XLSX поверх FileStore.

Зависимости:
- pandas
- openpyxl (опционально; можно включить автоподкачку через STRATBOX_AUTO_PIP=1)
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import read_bytes, write_bytes
from stratbox.base.utils.optional_deps import ensure_import


def read_df(
    path: str,
    store: FileStore | None = None,
    *,
    auto_install: bool | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    # openpyxl нужен pandas'у как engine для xlsx
    ensure_import("openpyxl", "openpyxl>=3.1", auto_install=auto_install)

    data = read_bytes(path, store=store)
    return pd.read_excel(BytesIO(data), engine="openpyxl", **kwargs)


def write_df(
    path: str,
    df: pd.DataFrame,
    store: FileStore | None = None,
    *,
    sheet_name: str = "data",
    meta: dict[str, Any] | None = None,
    style_preset: str | None = None,
    freeze_panes: str | None = None,
    auto_install: bool | None = None,
    index: bool = False,
    **kwargs: Any,
) -> None:
    """
    Пишет DataFrame в XLSX и (опционально) применяет:
    - sheet_name
    - метаданные книги (meta)
    - форматирование (style_preset)
    """
    ensure_import("openpyxl", "openpyxl>=3.1", auto_install=auto_install)

    from openpyxl import load_workbook

    bio = BytesIO()

    # ВАЖНО: index контролируем явно, чтобы не получить конфликт kwargs
    if "index" in kwargs:
        kwargs.pop("index")

    df.to_excel(bio, index=index, engine="openpyxl", sheet_name=sheet_name, **kwargs)

    # пост-обработка через openpyxl
    bio2 = BytesIO(bio.getvalue())
    wb = load_workbook(bio2)

    # 1) метаданные
    if meta:
        props = wb.properties
        if "creator" in meta:
            props.creator = str(meta["creator"])
        if "title" in meta:
            props.title = str(meta["title"])
        if "subject" in meta:
            props.subject = str(meta["subject"])
        if "category" in meta:
            props.category = str(meta["category"])
        if "keywords" in meta:
            props.keywords = str(meta["keywords"])
        if "description" in meta:
            props.description = str(meta["description"])

    # 2) стили
    if style_preset:
        from stratbox.base.ioapi.excel_styles import apply_preset

        ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.active
        apply_preset(ws, style_preset, freeze_panes=freeze_panes)

    out = BytesIO()
    wb.save(out)

    write_bytes(path, out.getvalue(), store=store)
