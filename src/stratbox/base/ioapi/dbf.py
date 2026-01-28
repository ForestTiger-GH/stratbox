"""
dbf — чтение/запись DBF поверх FileStore.

DBF — старый, но живой формат (часто встречается в отчетности/выгрузках).
Важно: для работы нужны дополнительные библиотеки.

Чтение (рекомендуется):
  - pip install dbfread

Запись (best effort, опционально):
  - pip install dbf

Политика:
- Если нужной библиотеки нет, функция поднимает ImportError с понятным текстом.
- Для чтения используется загрузка в память (BytesIO), чтобы работать поверх Samba.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import read_bytes, write_bytes


def read_df(path: str, encoding: str = "cp866", store: FileStore | None = None, **kwargs: Any) -> pd.DataFrame:
    """
    Читает DBF и возвращает pandas.DataFrame.

    Параметры:
    - encoding: часто для русских DBF подходит cp866 или cp1251 (зависит от источника)
    - kwargs: пробрасывается в dbfread.DBF(...)
    """
    try:
        from dbfread import DBF  # type: ignore
    except Exception as e:
        raise ImportError(
            "DBF support requires optional dependency 'dbfread'. "
            "Install: pip install dbfread"
        ) from e

    
    data = read_bytes(path, store=store)

    import tempfile
    from pathlib import Path

    # dbfread надёжнее всего работает с файловым путём.
    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td) / "tmp.dbf"
        tmp_path.write_bytes(data)

        table = DBF(str(tmp_path), encoding=encoding, **kwargs)
        records = list(table)  # список dict
        return pd.DataFrame.from_records(records)


def write_df(path: str, df: pd.DataFrame, store: FileStore | None = None) -> None:
    """
    Best-effort запись DataFrame в DBF.

    Важно:
    - DBF накладывает ограничения на типы и длины строк.
    - Эта функция рассчитана на простые выгрузки (без идеального контроля схемы).
    - Для точного контроля лучше писать специализированный экспорт под конкретный формат.

    Требует: pip install dbf
    """
    try:
        import dbf  # type: ignore
    except Exception as e:
        raise ImportError(
            "DBF write support requires optional dependency 'dbf'. "
            "Install: pip install dbf"
        ) from e

    def _field_spec(col: str, series: pd.Series) -> str:
        # Упрощенные правила:
        # - int -> N(18,0)
        # - float -> N(18,6)
        # - bool -> L
        # - datetime -> D
        # - str/other -> C(254) (макс. безопасная длина без тонкой настройки)
        s = series
        if pd.api.types.is_bool_dtype(s):
            return f"{col} L"
        if pd.api.types.is_datetime64_any_dtype(s):
            return f"{col} D"
        if pd.api.types.is_integer_dtype(s):
            return f"{col} N(18,0)"
        if pd.api.types.is_float_dtype(s):
            return f"{col} N(18,6)"
        return f"{col} C(254)"

    # DBF не любит пробелы/символы в именах полей -> приводим к безопасным
    safe_cols = []
    col_map = {}
    for c in df.columns.astype(str):
        safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in c).upper()
        safe = safe[:10] if len(safe) > 10 else safe  # типичный лимит DBF на имя
        if not safe:
            safe = "FIELD"
        # избегаем дублей
        base = safe
        k = 1
        while safe in safe_cols:
            tail = str(k)
            safe = (base[: max(0, 10 - len(tail))] + tail)
            k += 1
        safe_cols.append(safe)
        col_map[safe] = c

    df2 = df.copy()
    df2.columns = safe_cols

    spec = "; ".join(_field_spec(c, df2[c]) for c in df2.columns)

    # Пишем во временный байтовый буфер через временный файл в памяти не получится.
    # dbf.Table требует файловую систему, поэтому используем NamedTemporaryFile.
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        tmp_path = Path(td) / "tmp.dbf"
        table = dbf.Table(str(tmp_path), spec)
        table.open(mode=dbf.READ_WRITE)

        try:
            for _, row in df2.iterrows():
                rec = []
                for c in df2.columns:
                    v = row[c]
                    if pd.isna(v):
                        rec.append(None)
                    else:
                        rec.append(v)
                table.append(tuple(rec))
        finally:
            table.close()

        data = tmp_path.read_bytes()
        write_bytes(path, data, store=store)
