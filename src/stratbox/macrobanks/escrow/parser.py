"""
parser — полноценный парсинг одного Excel-файла ЦБ по счетам эскроу.

Парсер не склеивает "на глаз" первые два столбца.
Он распознает:
- строку заголовков;
- набор показателей;
- тип каждой строки иерархической таблицы;
- текущий федеральный округ для каждого субъекта РФ.

Результат содержит:
- семантическую таблицу строк;
- "длинный" поток значений;
- метаданные о распознанных столбцах.
"""

from __future__ import annotations

import re
from io import BytesIO

import pandas as pd

from stratbox.macrobanks.escrow.columns import (
    HEADER_SUBJECT_REQUIRED_TOKENS,
    is_subject_header_cell,
    resolve_indicator_columns,
    resolve_indicator_spec_by_header,
)
from stratbox.macrobanks.escrow.models import ParsedEscrowFile
from stratbox.macrobanks.escrow.rows import parse_escrow_rows


_DATE_RE = re.compile(r"(\d{2})(\d{2})(\d{4})")  # DDMMYYYY


def extract_date_from_filename(name: str) -> str | None:
    """Извлекает дату вида YYYY-MM-DD из имени файла по шаблону DDMMYYYY."""
    match = _DATE_RE.search(str(name))
    if not match:
        return None
    return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"


def clean_indicator_name(value: object) -> str:
    """Возвращает каноническое название показателя по сырому заголовку."""
    spec = resolve_indicator_spec_by_header(value)
    return spec.canonical_name


def _coerce_numeric_value(value: object) -> float | int | None:
    """Надежно переводит значение ячейки в число или возвращает None."""
    if value is None:
        return None
    if pd.isna(value):
        return None

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return value

    text = str(value).replace("\u00a0", " ").strip()
    if not text:
        return None

    text = text.replace(" ", "")
    text = text.replace(",", ".")
    number = pd.to_numeric([text], errors="coerce")[0]
    if pd.isna(number):
        return None
    return number


def _find_header_row(sheet_df: pd.DataFrame) -> tuple[int, list[object]]:
    """Находит строку заголовков и возвращает ее индекс и полный набор значений."""
    max_probe = min(len(sheet_df), 25)
    last_error: Exception | None = None

    for row_index in range(max_probe):
        row_values = sheet_df.iloc[row_index].tolist()
        if len(row_values) < 3:
            continue

        if not is_subject_header_cell(row_values[1] if len(row_values) > 1 else None):
            continue

        try:
            resolve_indicator_columns(row_values)
        except Exception as exc:
            last_error = exc
            continue

        return row_index, row_values

    message = (
        "Escrow header row is not found. "
        f"The second column must contain tokens={HEADER_SUBJECT_REQUIRED_TOKENS}"
    )
    if last_error is not None:
        message += f". Last resolve error: {last_error}"
    raise ValueError(message)


def _select_sheet_with_header(file_bytes: bytes) -> tuple[str, pd.DataFrame, int, list[object]]:
    """Выбирает лист с таблицей по регионам и возвращает его вместе с заголовком."""
    excel_file = pd.ExcelFile(BytesIO(file_bytes))
    prioritized = sorted(
        excel_file.sheet_names,
        key=lambda name: (0 if "регион" in str(name).lower() else 1, str(name).lower()),
    )

    last_error: Exception | None = None
    for sheet_name in prioritized:
        sheet_df = pd.read_excel(BytesIO(file_bytes), sheet_name=sheet_name, header=None)
        try:
            header_row_index, header_values = _find_header_row(sheet_df)
            return sheet_name, sheet_df, header_row_index, header_values
        except Exception as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise ValueError(f"Escrow sheet with header row is not found. Last error: {last_error}")
    raise ValueError("Escrow sheet with header row is not found")


def _build_rows_frame(parsed_rows) -> pd.DataFrame:
    """Преобразует распознанные строки в DataFrame с сохранением порядка."""
    df_rows = pd.DataFrame(
        {
            "display_order": [item.display_order for item in parsed_rows],
            "row_kind": [item.row_kind for item in parsed_rows],
            "Регион": [item.entity_name for item in parsed_rows],
            "federal_district_name": [item.federal_district_name for item in parsed_rows],
            "region_number": [item.region_number for item in parsed_rows],
        }
    )
    return df_rows


def parse_escrow_excel_bytes(file_bytes: bytes, *, source_name: str) -> ParsedEscrowFile:
    """
    Читает один xlsx-файл и возвращает семантически распознанные данные.

    Структура результата:
    - df_rows: строки итоговой витрины с типом и порядком;
    - df_long: длинный поток значений с метаданными строки и показателя.
    """
    file_date = extract_date_from_filename(source_name)
    sheet_name, sheet_df, header_row_index, header_values = _select_sheet_with_header(file_bytes)
    resolved_columns = resolve_indicator_columns(header_values)

    useful_columns_count = max([resolved.source_index for resolved in resolved_columns], default=1) + 1
    data_df = sheet_df.iloc[header_row_index + 1 :, :useful_columns_count].copy()
    data_df.columns = header_values[:useful_columns_count]
    data_df = data_df.reset_index(drop=True)

    parsed_rows = parse_escrow_rows(data_df)
    df_rows = _build_rows_frame(parsed_rows)

    records: list[dict[str, object]] = []
    for parsed_row in parsed_rows:
        for resolved_column in resolved_columns:
            value = _coerce_numeric_value(
                data_df.iat[parsed_row.source_row_index, resolved_column.source_index]
            )
            if value is None:
                continue

            records.append(
                {
                    "Регион": parsed_row.entity_name,
                    "Показатель": resolved_column.spec.canonical_name,
                    "Значение": value,
                    "Дата": file_date,
                    "row_kind": parsed_row.row_kind,
                    "display_order": parsed_row.display_order,
                    "federal_district_name": parsed_row.federal_district_name,
                    "region_number": parsed_row.region_number,
                    "indicator_code": resolved_column.spec.code,
                    "sheet_code": resolved_column.spec.sheet_code,
                    "value_kind": resolved_column.spec.value_kind,
                    "source_name": source_name,
                }
            )

    df_long = pd.DataFrame.from_records(
        records,
        columns=[
            "Регион",
            "Показатель",
            "Значение",
            "Дата",
            "row_kind",
            "display_order",
            "federal_district_name",
            "region_number",
            "indicator_code",
            "sheet_code",
            "value_kind",
            "source_name",
        ],
    )

    return ParsedEscrowFile(
        source_name=source_name,
        file_date=file_date,
        sheet_name=sheet_name,
        header_row_index=header_row_index,
        resolved_columns=resolved_columns,
        rows=parsed_rows,
        df_rows=df_rows,
        df_long=df_long,
    )


__all__ = [
    "ParsedEscrowFile",
    "clean_indicator_name",
    "extract_date_from_filename",
    "parse_escrow_excel_bytes",
]
