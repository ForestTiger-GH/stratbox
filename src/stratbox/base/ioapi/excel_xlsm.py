"""
excel_xlsm — чтение/запись XLSM поверх FileStore.

Важно:
- pandas/openpyxl НЕ сохраняют VBA-макросы при обычной записи DataFrame.
- Для “бережной” работы с макросами нужен отдельный путь через openpyxl.load_workbook(keep_vba=True)
  и ручная модификация, это другой уровень сложности.

Зависимости:
- pandas
- openpyxl (опционально; автоподкачка через STRATBOX_AUTO_PIP=1)
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.excel_xlsx import read_df as _read_xlsx_df
from stratbox.base.ioapi.excel_xlsx import write_df as _write_xlsx_df


def read_df(
    path: str,
    store: FileStore | None = None,
    *,
    auto_install: bool | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    return _read_xlsx_df(path, store=store, auto_install=auto_install, **kwargs)


def write_df(
    path: str,
    df: pd.DataFrame,
    store: FileStore | None = None,
    *,
    auto_install: bool | None = None,
    **kwargs: Any,
) -> None:
    # Запись DataFrame в xlsm возможна, но макросы не гарантируются.
    _write_xlsx_df(path, df, store=store, auto_install=auto_install, **kwargs)