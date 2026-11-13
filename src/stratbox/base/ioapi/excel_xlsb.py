"""
excel_xlsb — чтение XLSB поверх FileStore.

Зависимости:
- pyxlsb (опционально; для чтения)
Ограничение:
- запись XLSB обычно не делается через pandas стандартно -> NotImplementedError

Автоподкачка:
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from stratbox.base.filestore.base import FileStore


def read_df(
    path: str,
    store: FileStore | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    from .workbook_input import read_workbook_df

    return read_workbook_df(path, store=store, expected="xlsb", **kwargs)


def write_df(*args: Any, **kwargs: Any) -> None:
    raise NotImplementedError(
        "XLSB write is not supported in stratbox ioapi (read-only). "
        "Use .xlsx for writing."
    )