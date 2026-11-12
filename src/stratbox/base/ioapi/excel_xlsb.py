"""
excel_xlsb — чтение XLSB поверх FileStore.

Зависимости:
- pyxlsb (опционально; для чтения)
Ограничение:
- запись XLSB обычно не делается через pandas стандартно -> NotImplementedError

Автоподкачка:
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import read_bytes
from stratbox.base.utils.optional_deps import require_extra


def read_df(
    path: str,
    store: FileStore | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    require_extra("pyxlsb", "excel-binary")

    data = read_bytes(path, store=store)
    return pd.read_excel(BytesIO(data), engine="pyxlsb", **kwargs)


def write_df(*args: Any, **kwargs: Any) -> None:
    raise NotImplementedError(
        "XLSB write is not supported in stratbox ioapi (read-only). "
        "Use .xlsx for writing."
    )