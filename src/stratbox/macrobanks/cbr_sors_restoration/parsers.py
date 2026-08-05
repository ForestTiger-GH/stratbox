from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from stratbox.macrobanks.cbr_industries import parse_cbr_0105a_debt_corp_excel_bytes
from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsRestorationFiles, SorsSourceBundle
from stratbox.macrobanks.cbr_sors_restoration.schema import FD_ALIASES, normalize_class_code, normalize_text, section_for_class

_DATE_RE = re.compile(r'(?<!\d)(\d{2})[./](\d{2})[./](\d{4})(?!\d)')


def _iso_date(value: object) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    match = _DATE_RE.search(str(value or ''))
    if match:
        d, m, y = match.groups()
        return f'{y}-{m}-{d}'
    return None


def _load_book(path: str | Path):
    return load_workbook(filename=path, read_only=True, data_only=True)


def _find_date_column(ws, as_of_date: str, header_row: int = 2) -> int:
    for cell in ws[header_row]:
        if _iso_date(cell.value) == as_of_date:
            return cell.column
    raise ValueError(f'Date {as_of_date} not found in {ws.title!r}')


def _sheet_semantics(title: str) -> tuple[str, str]:
    t = normalize_text(title).lower()
    measure = 'overdue' if 'просроч' in t else 'debt'
    if 'инвалют' in t or 'иностран' in t:
        currency = 'fx'
    elif 'итого' in t:
        currency = 'total'
    else:
        currency = 'rub'
    return measure, currency


def parse_regional_traditional(path: str | Path, as_of_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    content = Path(path).read_bytes()
    parsed = parse_cbr_0105a_debt_corp_excel_bytes(
        content,
        source_name=Path(path).name,
        source_id=f'local:{Path(path).name}',
    )
    if parsed.report_date != as_of_date:
        raise ValueError(f'Regional workbook date is {parsed.report_date}, expected {as_of_date}')
    frame = parsed.df_stream.copy()
    frame = frame[frame['report_date'].astype(str) == as_of_date].copy()

    # Parent oblast rows overlap with their explicit autonomous components.
    excluded_parent_names = {'Архангельская область', 'Тюменская область'}
    atomic = pd.DataFrame([
        {
            'region_code': r.code,
            'region_name': r.canonical_name,
            'federal_district_name': r.federal_district_name,
            'region_kind': r.region_kind,
        }
        for r in parsed.regions
        if r.region_kind not in {'country_total', 'federal_district_total'}
        and r.canonical_name not in excluded_parent_names
    ])
    if len(atomic) != 85:
        raise ValueError(f'Expected 85 mutually exclusive territories, got {len(atomic)}')
    return frame, atomic


def parse_national_okved2(path: str | Path, as_of_date: str) -> pd.DataFrame:
    wb = _load_book(path)
    rows: list[dict[str, object]] = []
    for ws in wb.worksheets:
        measure, currency = _sheet_semantics(ws.title)
        if currency == 'total':
            continue
        col = _find_date_column(ws, as_of_date, header_row=2)
        for row in range(3, ws.max_row + 1):
            raw = ws.cell(row, 1).value
            value = ws.cell(row, col).value
            if raw is None or value is None:
                continue
            code = normalize_class_code(raw)
            if not (code == 'OTHER' or re.fullmatch(r'\d{2}', code)):
                continue
            rows.append({
                'class_code': code,
                'class_name': normalize_text(raw),
                'section_code': section_for_class(code),
                'measure': measure,
                'currency': currency,
                'value': float(value),
                'source_sheet': ws.title,
                'source_row': row,
            })
    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError('No national OKVED2 observations parsed')
    return out


def _fd_section_from_header(header: str) -> str:
    h = normalize_text(header)
    if h.lower().startswith('проч'):
        return 'OTHER'
    match = re.match(r'^([A-ZА-Я])(?:\.|\s|$)', h)
    if match:
        latin = match.group(1).upper()
        # Headers in source use latin section letters.
        return latin
    return h


def parse_fd_okved2(path: str | Path, as_of_date: str) -> pd.DataFrame:
    wb = _load_book(path)
    rows: list[dict[str, object]] = []
    for ws in wb.worksheets:
        title = normalize_text(ws.title).lower()
        if 'задолж' not in title and 'просроч' not in title:
            continue
        measure = 'overdue' if 'просроч' in title else 'debt'
        # The two source sheets differ by one header row; detect the row by finding the first A.. section header.
        header_row = None
        for r in range(1, min(ws.max_row, 8) + 1):
            vals = [normalize_text(ws.cell(r, c).value) for c in range(2, min(ws.max_column, 20) + 1)]
            if sum(bool(re.match(r'^[A-Z](?:\.|\s|$)', v)) or v.lower().startswith('проч') for v in vals) >= 10:
                header_row = r
                break
        if header_row is None:
            continue
        headers = {c: _fd_section_from_header(ws.cell(header_row, c).value) for c in range(2, ws.max_column + 1)}
        for r in range(header_row + 1, ws.max_row + 1):
            fd_name = normalize_text(ws.cell(r, 1).value)
            if 'ФЕДЕРАЛЬНЫЙ ОКРУГ' not in fd_name.upper():
                continue
            for c, section in headers.items():
                value = ws.cell(r, c).value
                if value is None:
                    continue
                rows.append({
                    'federal_district_name': fd_name,
                    'federal_district_code': FD_ALIASES.get(fd_name, fd_name),
                    'section_code': section,
                    'measure': measure,
                    'value': float(value),
                    'source_sheet': ws.title,
                    'source_row': r,
                    'source_column': c,
                })
    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError('No FD OKVED2 observations parsed')
    return out


def parse_national_traditional(path: str | Path | None, as_of_date: str) -> pd.DataFrame | None:
    if path is None:
        return None
    wb = _load_book(path)
    rows: list[dict[str, object]] = []
    for ws in wb.worksheets:
        measure, currency = _sheet_semantics(ws.title)
        col = _find_date_column(ws, as_of_date, header_row=2)
        for r in range(3, ws.max_row + 1):
            name = normalize_text(ws.cell(r, 1).value)
            value = ws.cell(r, col).value
            if name and value is not None:
                rows.append({'industry_name': name, 'measure': measure, 'currency': currency, 'value': float(value)})
    return pd.DataFrame(rows)


def load_sors_sources(files: SorsRestorationFiles, as_of_date: str) -> SorsSourceBundle:
    regional, atomic = parse_regional_traditional(files.regional_traditional, as_of_date)
    national = parse_national_okved2(files.national_okved2, as_of_date)
    fd = parse_fd_okved2(files.fd_okved2, as_of_date)
    national_old = parse_national_traditional(files.national_traditional, as_of_date)
    classes = national[['class_code', 'class_name', 'section_code']].drop_duplicates('class_code').sort_values('class_code').reset_index(drop=True)
    return SorsSourceBundle(regional, national, fd, national_old, atomic, classes)
