from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, timedelta

import pandas as pd

from stratbox.base.ioapi.workbook_input import open_ooxml_workbook
from stratbox.data import SourcePayload

from stratbox.macrobanks.cbr_sors_restoration.metrics import source_metric
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.schema import normalize_text

_DATE_RE = re.compile(r'(?<!\d)(\d{2})[./](\d{2})[./](\d{4})(?!\d)')


def open_source_workbook(source: SourcePayload):
    return open_ooxml_workbook(source.data)


def iso_date(value: object) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float)) and 1 <= float(value) <= 100000:
        origin = datetime(1899, 12, 30)
        return (origin + timedelta(days=float(value))).date().isoformat()
    match = _DATE_RE.search(str(value or ''))
    if match:
        day, month, year = match.groups()
        return f'{year}-{month}-{day}'
    return None


def find_date_column(ws, as_of_date: str, header_row: int = 2) -> int:
    for cell in ws[header_row]:
        if iso_date(cell.value) == as_of_date:
            return int(cell.column)
    raise ValueError(f'Date {as_of_date} not found in sheet {ws.title!r}')


def sheet_semantics(title: str) -> tuple[str, str]:
    value = normalize_text(title).lower()
    measure = 'overdue' if 'просроч' in value else 'debt'
    if 'инвалют' in value or 'иностран' in value:
        currency = 'fx'
    elif 'итого' in value or ('в рублях' not in value and 'иностран' not in value):
        currency = 'total'
    else:
        currency = 'rub'
    return measure, currency


def stable_observation_id(
    source_series: str,
    source_sheet: object,
    source_row: object,
    source_column: object,
    as_of_date: str,
) -> str:
    raw = '|'.join(
        map(str, (source_series, source_sheet, source_row, source_column, as_of_date))
    )
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]
    return f'{source_series}:{digest}'


def canonicalize_observations(
    frame: pd.DataFrame,
    policy: RoundingPolicy,
    *,
    source_role: str,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    out = frame.copy()
    intervals = out['value'].astype(float).map(policy.interval)
    out['published_lower'] = [item.lower for item in intervals]
    out['published_upper'] = [item.upper for item in intervals]
    out['published_lower_attained'] = [item.lower_attained for item in intervals]
    out['published_upper_attained'] = [item.upper_attained for item in intervals]
    out['metric'] = [
        source_metric(measure, currency)
        for measure, currency in zip(out['measure'], out['currency'], strict=True)
    ]
    out['unit'] = 'million_rubles'
    out['source_role'] = source_role
    out['record_origin'] = 'PUBLISHED'
    out['observation_id'] = [
        stable_observation_id(
            str(row.source_series),
            row.source_sheet,
            row.source_row,
            row.source_column,
            str(row.as_of_date),
        )
        for row in out.itertuples(index=False)
    ]
    return out


def source_manifest_record(
    source_series: str,
    source: SourcePayload,
    rows: int,
    *,
    required: bool,
    role: str,
) -> dict[str, object]:
    return {
        'source_series': source_series,
        'source_role': role,
        'required': bool(required),
        'source_file_actual': source.source_id or source_series,
        'sha256': source.identity.sha256,
        'size_bytes': source.identity.size,
        'rows': int(rows),
    }
