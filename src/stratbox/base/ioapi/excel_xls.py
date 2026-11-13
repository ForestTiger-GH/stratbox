"""
excel_xls — чтение/запись XLS (старый бинарный Excel) поверх FileStore.

Зависимости:
- Чтение: xlrd (опционально)
- Запись: xlwt (опционально, best-effort; зависит от версии pandas)

Автоподкачка:
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import write_bytes
from stratbox.base.utils.optional_deps import require_extra


def read_df(
    path: str,
    store: FileStore | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    from .workbook_input import read_workbook_df

    return read_workbook_df(path, store=store, expected="xls", **kwargs)


def write_df(
    path: str,
    df: pd.DataFrame,
    store: FileStore | None = None,
    **kwargs: Any,
) -> None:
    """
    Best-effort запись в XLS.

    Важно:
    - поддержка может зависеть от версии pandas (engine xlwt).
    - если engine недоступен — будет понятная ошибка.
    """
    require_extra("xlwt", "excel-legacy")

    bio = BytesIO()
    try:
        with pd.ExcelWriter(bio, engine="xlwt") as writer:
            df.to_excel(writer, index=False, **kwargs)
    except Exception as e:
        raise RuntimeError(
            "XLS write failed. In this environment pandas/xlwt writer may be unsupported. "
            "Consider writing to .xlsx instead."
        ) from e

    write_bytes(path, bio.getvalue(), store=store)