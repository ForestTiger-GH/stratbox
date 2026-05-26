"""
rows — распознавание иерархической структуры строк в таблице по регионам.

Файл ЦБ содержит разные типы строк:
- федеральный округ;
- субъект РФ;
- итог по РФ.

Парсер явно различает эти типы и сохраняет исходный порядок строк.
"""

from __future__ import annotations

import math
import re

import pandas as pd

from stratbox.macrobanks.escrow.models import EscrowParsedRow


_RF_TOTAL_NORMALIZED = "итого по рф"


def cell_to_text(value: object) -> str | None:
    """Приводит ячейку к нормализованному тексту или возвращает None."""
    if value is None:
        return None
    if pd.isna(value):
        return None

    text = str(value).replace("\u00a0", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return None
    normalized_lower = text.lower()
    if normalized_lower in {"nan", "none"}:
        return None
    return text


def normalize_entity_name(value: object) -> str | None:
    """Нормализует отображаемое имя строки таблицы."""
    text = cell_to_text(value)
    if text is None:
        return None
    if text.lower() == "итого":
        return "Итого по РФ"
    return text


def normalize_row_text_for_match(value: object) -> str:
    """Нормализует текст ячейки для структурного распознавания."""
    text = cell_to_text(value)
    if text is None:
        return ""
    text = text.replace("ё", "е").replace("Ё", "Е")
    text = re.sub(r"[^0-9A-Za-zА-Яа-я]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def is_number_like(value: object) -> bool:
    """Проверяет, что значение похоже на номер субъекта РФ."""
    if value is None:
        return False
    if pd.isna(value):
        return False

    if isinstance(value, bool):
        return False

    if isinstance(value, int):
        return True

    if isinstance(value, float):
        if math.isnan(value):
            return False
        return float(value).is_integer()

    text = str(value).strip()
    if not text:
        return False
    return bool(re.fullmatch(r"\d+", text))


def parse_region_number(value: object) -> int:
    """Извлекает номер субъекта РФ из первого столбца."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return int(str(value).strip())


def is_rf_total_row(first_value: object, second_value: object) -> bool:
    """Проверяет, что строка соответствует итогу по Российской Федерации."""
    if cell_to_text(second_value) is not None:
        return False
    first_text = normalize_row_text_for_match(first_value)
    return first_text == _RF_TOTAL_NORMALIZED


def is_federal_district_row(first_value: object, second_value: object) -> bool:
    """Проверяет, что строка соответствует федеральному округу."""
    first_text = normalize_entity_name(first_value)
    second_text = normalize_entity_name(second_value)

    if not first_text or second_text:
        return False

    lowered = first_text.lower()
    return "фо" in lowered and lowered != "итого по рф"


def is_region_row(first_value: object, second_value: object) -> bool:
    """Проверяет, что строка соответствует субъекту РФ."""
    return is_number_like(first_value) and normalize_entity_name(second_value) is not None


def parse_escrow_rows(data_df: pd.DataFrame) -> list[EscrowParsedRow]:
    """
    Распознает полезные строки таблицы и возвращает их в исходном порядке.

    Парсер останавливается на строке "Итого по РФ" и не читает сноски,
    идущие ниже итоговой строки.
    """
    parsed_rows: list[EscrowParsedRow] = []
    current_federal_district: str | None = None
    has_started = False
    has_total = False

    for source_row_index in range(len(data_df)):
        first_value = data_df.iat[source_row_index, 0]
        second_value = data_df.iat[source_row_index, 1]

        first_text = normalize_entity_name(first_value)
        second_text = normalize_entity_name(second_value)

        if first_text is None and second_text is None:
            continue

        if is_rf_total_row(first_value, second_value):
            parsed_rows.append(
                EscrowParsedRow(
                    source_row_index=source_row_index,
                    display_order=len(parsed_rows) + 1,
                    row_kind="rf_total",
                    entity_name="Итого по РФ",
                    federal_district_name=None,
                    region_number=None,
                )
            )
            has_total = True
            break

        if is_federal_district_row(first_value, second_value):
            current_federal_district = first_text
            has_started = True
            parsed_rows.append(
                EscrowParsedRow(
                    source_row_index=source_row_index,
                    display_order=len(parsed_rows) + 1,
                    row_kind="federal_district",
                    entity_name=first_text,
                    federal_district_name=current_federal_district,
                    region_number=None,
                )
            )
            continue

        if is_region_row(first_value, second_value):
            if current_federal_district is None:
                raise ValueError(
                    "Escrow region row is found before the first federal district row"
                )

            parsed_rows.append(
                EscrowParsedRow(
                    source_row_index=source_row_index,
                    display_order=len(parsed_rows) + 1,
                    row_kind="region",
                    entity_name=second_text or "",
                    federal_district_name=current_federal_district,
                    region_number=parse_region_number(first_value),
                )
            )
            continue

        if has_started:
            raise ValueError(
                "Unexpected non-empty escrow row before RF total row: "
                f"row_index={source_row_index}, first={first_text!r}, second={second_text!r}"
            )

    if not parsed_rows:
        raise ValueError("Escrow data rows are not found in the source file")

    if not has_total:
        raise ValueError('Escrow total row "Итого по РФ" is not found')

    return parsed_rows


__all__ = [
    "cell_to_text",
    "is_federal_district_row",
    "is_number_like",
    "is_region_row",
    "is_rf_total_row",
    "normalize_entity_name",
    "normalize_row_text_for_match",
    "parse_escrow_rows",
    "parse_region_number",
]
