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
    auto_install: bool | None = None,
    **kwargs: Any,
) -> None:
    ensure_import("openpyxl", "openpyxl>=3.1", auto_install=auto_install)

    bio = BytesIO()
    df.to_excel(bio, index=False, engine="openpyxl", **kwargs)
    write_bytes(path, bio.getvalue(), store=store)