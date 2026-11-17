"""
Модуль содержит DBF-парсер под выгрузки Банка России.

Особенности:
- Текстовые поля часто cp866.
- Числовые поля иногда выглядят как бинарный little-endian int (например b'1\\x00\\x00\\x00').
"""

from __future__ import annotations

from decimal import Decimal

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
                return Decimal(cleaned.decode("ascii").replace(",", "."))
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
                    return Decimal(s)

    def parseI(self, field, data):
        if data is None:
            return None
        if len(data) in (2, 4, 8):
            return int.from_bytes(data, byteorder="little", signed=True)
        return super().parseI(field, data)
