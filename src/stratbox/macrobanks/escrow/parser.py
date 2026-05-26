"""
parser — парсинг одного Excel-файла ЦБ по счетам эскроу в "длинный" поток данных.

Возвращаемая структура:
- Регион
- Показатель
- Значение
- Дата

Дополнительно парсер возвращает порядок показателей в исходном файле,
чтобы позднее можно было сохранить порядок листов в итоговом Excel.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

import pandas as pd


_DATE_RE = re.compile(r"(\d{2})(\d{2})(\d{4})")  # DDMMYYYY


@dataclass(frozen=True)
class ParsedEscrowFile:
    """Результат парсинга одного Excel-файла по счетам эскроу."""

    source_name: str
    file_date: str | None
    indicators_order: list[str]
    df_long: pd.DataFrame



def extract_date_from_filename(name: str) -> str | None:
    """Извлекает дату вида YYYY-MM-DD из имени файла по шаблону DDMMYYYY."""
    match = _DATE_RE.search(str(name))
    if not match:
        return None
    return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"



def clean_indicator_name(value: object) -> str:
    """Удаляет хвостовые сноски, пробелы, цифры и звёздочки у названия показателя."""
    text = str(value)
    text = re.sub(r"[\s\*\d]+$", "", text).rstrip()
    return text



def parse_escrow_excel_bytes(file_bytes: bytes, *, source_name: str) -> ParsedEscrowFile:
    """
    Читает один xlsx-файл и возвращает "длинные" данные плюс порядок показателей.
    """
    file_date = extract_date_from_filename(source_name)
    raw_df = pd.read_excel(BytesIO(file_bytes), header=3)

    if raw_df.shape[1] < 3:
        raise ValueError("Escrow Excel has too few columns to parse")

    region_col = raw_df.columns[1]
    raw_df[region_col] = raw_df[region_col].fillna(raw_df.iloc[:, 0])
    raw_df = raw_df.iloc[:, 1:]

    indicators_order = [clean_indicator_name(col) for col in raw_df.columns[1:].tolist()]

    long_df = raw_df.melt(id_vars=[region_col], var_name="Показатель", value_name="Значение")
    long_df = long_df.rename(columns={region_col: "Регион"})
    long_df["Дата"] = file_date

    long_df["Показатель"] = long_df["Показатель"].apply(clean_indicator_name)
    long_df["Регион"] = (
        long_df["Регион"]
        .astype(str)
        .apply(lambda x: re.sub(r"\d+$", "", x).strip())
        .replace("Итого", "Итого по РФ")
    )

    long_df["Значение"] = long_df["Значение"].replace(r"^\s*$", 0, regex=True)
    long_df["Значение"] = pd.to_numeric(long_df["Значение"], errors="coerce")
    long_df = long_df.dropna(subset=["Значение"]).reset_index(drop=True)

    return ParsedEscrowFile(
        source_name=source_name,
        file_date=file_date,
        indicators_order=indicators_order,
        df_long=long_df,
    )


__all__ = [
    "ParsedEscrowFile",
    "clean_indicator_name",
    "extract_date_from_filename",
    "parse_escrow_excel_bytes",
]
