"""
excel_xlsb — чтение XLSB поверх FileStore.

Зависимости:
- pyxlsb (опционально; для чтения)
Ограничение:
- запись XLSB обычно не делается через pandas стандартно -> NotImplementedError

Автоподкачка:
- STRATBOX_AUTO_PIP=1 (или auto_install=True)
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import read_bytes
from stratbox.base.utils.optional_deps import ensure_import


def read_df(
    path: str,
    store: FileStore | None = None,
    *,
    auto_install: bool | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    ensure_import("pyxlsb", "pyxlsb>=1.0.10", auto_install=auto_install)

    data = read_bytes(path, store=store)
    return pd.read_excel(BytesIO(data), engine="pyxlsb", **kwargs)


def write_df(*args: Any, **kwargs: Any) -> None:
    raise NotImplementedError(
        "XLSB write is not supported in stratbox ioapi (read-only). "
        "Use .xlsx for writing."
    )