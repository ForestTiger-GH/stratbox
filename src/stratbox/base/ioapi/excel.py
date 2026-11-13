"""
excel — фасад для чтения/записи Excel в DataFrame поверх FileStore.

Важно:
- сам файл НЕ тянет тяжёлые зависимости
- реальная библиотека подхватывается только когда вызывается read_df/write_df
- выбор реализации делается по расширению файла

Поддержка:
- .xlsx -> excel_xlsx
- .xlsm -> excel_xlsm
- .xls  -> excel_xls
- .xlsb -> excel_xlsb
"""

from __future__ import annotations

from typing import Any

from typing import TYPE_CHECKING

from stratbox.base.filestore.base import FileStore

if TYPE_CHECKING:
    import pandas as pd


def _ext(path: str) -> str:
    """
    Возвращает расширение в виде ".xlsx" (с точкой) или "".

    Учитывает:
    - file:///... (копипаста из Windows/Excel)
    - обратные слэши
    - query/fragment (на всякий случай)
    """
    s = str(path).strip()

    # отрезает query/fragment, если внезапно прилетели
    for sep in ("?", "#"):
        if sep in s:
            s = s.split(sep, 1)[0]

    # нормализует слэши
    s = s.replace("\\", "/")

    low = s.lower()
    if low.startswith("file://"):
        s = s[len("file://") :]
        s = s.lstrip("/")

    name = s.split("/")[-1]
    if "." not in name:
        return ""

    return "." + name.rsplit(".", 1)[1].lower()


def read_df(
    path: str,
    store: FileStore | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    from .workbook_input import read_workbook_df

    return read_workbook_df(path, store=store, **kwargs)


def write_df(
    path: str,
    df: pd.DataFrame,
    store: FileStore | None = None,
    **kwargs: Any,
) -> None:
    ext = _ext(path)

    if ext == ".xlsx":
        from stratbox.base.ioapi import excel_xlsx

        return excel_xlsx.write_df(path, df, store=store, **kwargs)

    if ext == ".xlsm":
        from stratbox.base.ioapi import excel_xlsm

        return excel_xlsm.write_df(path, df, store=store, **kwargs)

    if ext == ".xls":
        from stratbox.base.ioapi import excel_xls

        return excel_xls.write_df(path, df, store=store, **kwargs)

    if ext == ".xlsb":
        from stratbox.base.ioapi import excel_xlsb

        return excel_xlsb.write_df(path, df, store=store, **kwargs)

    # Фоллбек: пишем как xlsx
    from stratbox.base.ioapi import excel_xlsx

    return excel_xlsx.write_df(path, df, store=store, **kwargs)
