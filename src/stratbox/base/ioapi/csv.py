"""
csv — чтение/запись CSV в DataFrame поверх FileStore.
"""

from __future__ import annotations

from io import StringIO

import pandas as pd

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import read_bytes, write_bytes


def read_df(path: str, store: FileStore | None = None, encoding: str = "utf-8", **kwargs) -> pd.DataFrame:
    data = read_bytes(path, store=store)
    text = data.decode(encoding, errors="replace")
    return pd.read_csv(StringIO(text), **kwargs)


def write_df(path: str, df: pd.DataFrame, store: FileStore | None = None, encoding: str = "utf-8", **kwargs) -> None:
    sio = StringIO()
    df.to_csv(sio, index=False, **kwargs)
    write_bytes(path, sio.getvalue().encode(encoding), store=store)