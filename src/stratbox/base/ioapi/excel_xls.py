"""
excel_xls — чтение/запись XLS (старый бинарный Excel) поверх FileStore.

Зависимости:
- Чтение: xlrd (опционально)
- Запись: xlwt (опционально, best-effort; зависит от версии pandas)

Автоподкачка:
- STRATBOX_AUTO_PIP=1 (или auto_install=True в функции)
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
    ensure_import("xlrd", "xlrd>=2.0.1", auto_install=auto_install)

    data = read_bytes(path, store=store)
    return pd.read_excel(BytesIO(data), engine="xlrd", **kwargs)


def write_df(
    path: str,
    df: pd.DataFrame,
    store: FileStore | None = None,
    *,
    auto_install: bool | None = None,
    **kwargs: Any,
) -> None:
    """
    Best-effort запись в XLS.

    Важно:
    - поддержка может зависеть от версии pandas (engine xlwt).
    - если engine недоступен — будет понятная ошибка.
    """
    ensure_import("xlwt", "xlwt>=1.3.0", auto_install=auto_install)

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