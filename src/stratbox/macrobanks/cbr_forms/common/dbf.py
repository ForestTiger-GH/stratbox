"""
Модуль содержит DBF-парсер под выгрузки Банка России.

Особенности:
- Текстовые поля часто cp866.
- Числовые поля иногда выглядят как бинарный little-endian int (например b'1\\x00\\x00\\x00').
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from dbfread import DBF
from dbfread.field_parser import FieldParser


class CBRFieldParser(FieldParser):
    """
    Парсер DBF для форм Банка России.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.encoding = "cp866"
        self.char_decode_errors = "replace"

    def parseN(self, field, data):
        if data is None:
            return None

        cleaned = data.replace(b"\x00", b"").strip()
        if cleaned == b"":
            return None

        try:
            return int(cleaned)
        except Exception:
            try:
                return float(cleaned.replace(b",", b"."))
            except Exception:
                # Бинарный вариант
                if len(data) in (2, 4, 8):
                    return int.from_bytes(data, byteorder="little", signed=False)
                s = cleaned.decode("ascii", errors="ignore").replace(",", ".").strip()
                if s == "":
                    return None
                try:
                    return int(s)
                except Exception:
                    return float(s)

    def parseI(self, field, data):
        if data is None:
            return None
        if len(data) in (2, 4, 8):
            return int.from_bytes(data, byteorder="little", signed=True)
        return super().parseI(field, data)


@dataclass(frozen=True)
class DBFLayout:
    """
    Описание фактических имён полей в выбранном DBF.
    """
    regn: str
    a: str
    b: str


def read_dbf_fields(path: str) -> list[str]:
    """
    Возвращает список полей DBF без загрузки записей.
    """
    dbf = DBF(path, parserclass=CBRFieldParser, load=False)
    return list(dbf.field_names)


def read_dbf_to_df(path: str, layout: DBFLayout) -> pd.DataFrame:
    """
    Читает DBF и возвращает DataFrame с колонками:
      - REGN
      - A
      - B

    Примечание:
    - Конкретный смысл A/B зависит от формы:
      * для 123: A=номер счета, B=значение
      * для 135: A=метка, B=значение
    """
    dbf = DBF(path, parserclass=CBRFieldParser)

    regn_list = []
    a_list = []
    b_list = []

    for rec in dbf:
        regn_list.append(rec.get(layout.regn))
        a_list.append(rec.get(layout.a))
        b_list.append(rec.get(layout.b))

    return pd.DataFrame({"REGN": regn_list, "A": a_list, "B": b_list})
