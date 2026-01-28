"""
excel — чтение/запись Excel в DataFrame поверх FileStore.
"""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import read_bytes, write_bytes


def read_df(path: str, store: FileStore | None = None, **kwargs) -> pd.DataFrame:
    data = read_bytes(path, store=store)
    return pd.read_excel(BytesIO(data), **kwargs)


def write_df(path: str, df: pd.DataFrame, store: FileStore | None = None, **kwargs) -> None:
    bio = BytesIO()
    df.to_excel(bio, index=False, **kwargs)
    write_bytes(path, bio.getvalue(), store=store)