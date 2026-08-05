from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.sources.common import (
    canonicalize_observations,
    find_date_column,
    sha256_file,
    sheet_semantics,
)
from stratbox.macrobanks.cbr_sors_restoration.schema import normalize_text


def parse_national_book(
    path: str | Path,
    as_of_date: str,
    *,
    classifier_id: str,
    source_series: str,
    source_role: str,
    policy: RoundingPolicy,
) -> pd.DataFrame:
    actual = Path(path)
    digest = sha256_file(actual)
    workbook = load_workbook(actual, read_only=True, data_only=True)
    rows: list[dict[str, object]] = []
    try:
        for ws in workbook.worksheets:
            measure, currency = sheet_semantics(str(ws.cell(1, 1).value or ws.title))
            column = find_date_column(ws, as_of_date, header_row=2)
            for row_no in range(3, ws.max_row + 1):
                raw = ws.cell(row_no, 1).value
                value = ws.cell(row_no, column).value
                if raw is None or value is None:
                    continue
                rows.append(
                    {
                        'source_series': source_series,
                        'source_file_actual': actual.name,
                        'source_file_logical': actual.name,
                        'source_sha256': digest,
                        'source_sheet': ws.title,
                        'source_row': row_no,
                        'source_column': column,
                        'as_of_date': as_of_date,
                        'classifier_id': classifier_id,
                        'activity_raw': normalize_text(raw),
                        'measure': measure,
                        'currency': currency,
                        'value': float(value),
                        'geography_node_id': 'RF',
                        'geography_name': 'РОССИЙСКАЯ ФЕДЕРАЦИЯ',
                        'geography_raw': 'РОССИЙСКАЯ ФЕДЕРАЦИЯ',
                        'geography_kind': 'country_total',
                    }
                )
    finally:
        workbook.close()
    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError(f'No observations parsed from {actual}')
    return canonicalize_observations(out, policy, source_role=source_role)
