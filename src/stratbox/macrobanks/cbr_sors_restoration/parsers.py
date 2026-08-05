from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from stratbox.macrobanks.cbr_industries import parse_cbr_0105a_debt_corp_excel_bytes
from stratbox.macrobanks.cbr_industries.schema import CBR_0105A_DEBT_CORP_INDUSTRY_SPECS
from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsSourceBundle, SorsSourceFiles
from stratbox.macrobanks.cbr_sors_restoration.geography import build_geography_frames
from stratbox.macrobanks.cbr_sors_restoration.okved2 import read_okved2_classes
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.schema import FD_ALIASES, normalize_class_code, normalize_text

_DATE_RE = re.compile(r'(?<!\d)(\d{2})[./](\d{2})[./](\d{4})(?!\d)')


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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


def _find_date_column(ws, as_of_date: str, header_row: int = 2) -> int:
    for cell in ws[header_row]:
        if _iso_date(cell.value) == as_of_date:
            return int(cell.column)
    raise ValueError(f'Date {as_of_date} not found in sheet {ws.title!r}')


def _sheet_semantics(title: str) -> tuple[str, str]:
    value = normalize_text(title).lower()
    measure = 'overdue' if 'просроч' in value else 'debt'
    if 'инвалют' in value or 'иностран' in value:
        currency = 'fx'
    elif 'итого' in value or ('в рублях' not in value and 'иностран' not in value):
        currency = 'total'
    else:
        currency = 'rub'
    return measure, currency


def _canonical_records(frame: pd.DataFrame, policy: RoundingPolicy) -> pd.DataFrame:
    out = frame.copy()
    intervals = out['value'].astype(float).map(policy.interval)
    out['published_lower'] = [item.lower for item in intervals]
    out['published_upper'] = [item.upper for item in intervals]
    out['record_origin'] = 'PUBLISHED'
    return out


def parse_regional_traditional(path: str | Path, as_of_date: str, policy: RoundingPolicy):
    actual = Path(path)
    canonical_name = f'01_05_A_Debt_corp_{as_of_date.replace("-", "")}.xlsx'
    parsed = parse_cbr_0105a_debt_corp_excel_bytes(
        actual.read_bytes(),
        source_name=canonical_name,
        source_id=f'local:{actual.name}',
        source_sha256=_sha256(actual),
    )
    if parsed.report_date != as_of_date:
        raise ValueError(f'Regional workbook date {parsed.report_date} differs from {as_of_date}')
    frame = parsed.df_stream.copy()
    frame['source_series'] = '01_05_A'
    frame['source_file_actual'] = actual.name
    frame['source_file_logical'] = canonical_name
    frame['as_of_date'] = as_of_date
    frame['activity_code'] = frame['industry_code'].astype(str)
    frame['activity_name'] = frame['industry_name_ru'].astype(str)
    frame['classifier_id'] = 'cbr_traditional'
    frame['geography_node_id'] = frame['region_code'].astype(str)
    frame['geography_name'] = frame['region_name'].astype(str)
    frame['geography_kind'] = frame['region_kind'].astype(str)
    frame['currency'] = frame['currency_scope'].map({
        'rubles': 'rub', 'foreign_currency_and_precious_metals': 'fx', 'total': 'total',
    })
    frame['measure'] = frame['measure'].map({'overdue_debt': 'overdue', 'debt': 'debt'})
    frame['observation_id'] = [f'01_05_A:{i}' for i in range(len(frame))]
    geography, atomic = build_geography_frames(parsed.regions)
    return _canonical_records(frame, policy), geography, atomic


def _parse_national_book(path: str | Path, as_of_date: str, *, classifier: str, policy: RoundingPolicy) -> pd.DataFrame:
    actual = Path(path)
    wb = load_workbook(actual, read_only=True, data_only=True)
    rows: list[dict[str, object]] = []
    try:
        for ws in wb.worksheets:
            measure, currency = _sheet_semantics(str(ws.cell(1, 1).value or ws.title))
            col = _find_date_column(ws, as_of_date, header_row=2)
            for row_no in range(3, ws.max_row + 1):
                raw = ws.cell(row_no, 1).value
                value = ws.cell(row_no, col).value
                if raw is None or value is None:
                    continue
                rows.append({
                    'source_sheet': ws.title,
                    'source_row': row_no,
                    'source_column': col,
                    'raw_activity': normalize_text(raw),
                    'measure': measure,
                    'currency': currency,
                    'value': float(value),
                })
    finally:
        wb.close()
    out = pd.DataFrame(rows)
    if out.empty:
        raise ValueError(f'No observations parsed from {actual}')
    out['source_file_actual'] = actual.name
    out['source_sha256'] = _sha256(actual)
    out['as_of_date'] = as_of_date
    out['classifier_id'] = classifier
    return _canonical_records(out, policy)


def parse_national_okved2(path: str | Path, as_of_date: str, policy: RoundingPolicy) -> pd.DataFrame:
    out = _parse_national_book(path, as_of_date, classifier='okved2', policy=policy)
    out['activity_code'] = out['raw_activity'].map(normalize_class_code)
    out = out[out['activity_code'].eq('PUBLISHED_OTHER') | out['activity_code'].str.fullmatch(r'\d{2}')].copy()
    out['activity_name'] = out['raw_activity']
    out['source_series'] = '01_02_C'
    out['geography_node_id'] = 'RF'
    out['geography_name'] = 'РОССИЙСКАЯ ФЕДЕРАЦИЯ'
    out['geography_kind'] = 'country_total'
    out['observation_id'] = [f'01_02_C:{i}' for i in range(len(out))]
    return out


def parse_national_traditional(path: str | Path, as_of_date: str, policy: RoundingPolicy) -> pd.DataFrame:
    out = _parse_national_book(path, as_of_date, classifier='cbr_traditional', policy=policy)
    specs = list(CBR_0105A_DEBT_CORP_INDUSTRY_SPECS)
    chunks: list[pd.DataFrame] = []
    for _, group in out.groupby(['source_sheet'], sort=False):
        if len(group) != len(specs):
            raise ValueError(f'National traditional sheet has {len(group)} rows, expected {len(specs)}')
        part = group.copy().reset_index(drop=True)
        part['activity_code'] = [spec.code for spec in specs]
        part['activity_name'] = [spec.canonical_name_ru for spec in specs]
        chunks.append(part)
    out = pd.concat(chunks, ignore_index=True)
    out['source_series'] = '01_02_A'
    out['geography_node_id'] = 'RF'
    out['geography_name'] = 'РОССИЙСКАЯ ФЕДЕРАЦИЯ'
    out['geography_kind'] = 'country_total'
    out['observation_id'] = [f'01_02_A:{i}' for i in range(len(out))]
    return out


def parse_fd_okved2(path: str | Path, as_of_date: str, policy: RoundingPolicy) -> pd.DataFrame:
    actual = Path(path)
    wb = load_workbook(actual, read_only=True, data_only=True)
    rows: list[dict[str, object]] = []
    seen_date = False
    try:
        for ws in wb.worksheets:
            title_text = normalize_text(ws.cell(1, 1).value)
            sheet_date = _iso_date(title_text)
            if sheet_date:
                seen_date = True
                if sheet_date != as_of_date:
                    raise ValueError(f'FD workbook sheet {ws.title!r} has date {sheet_date}, expected {as_of_date}')
            lowered = title_text.lower()
            if 'задолж' not in lowered:
                continue
            measure = 'overdue' if 'просроч' in lowered else 'debt'
            header_row = None
            for r in range(1, min(ws.max_row, 8) + 1):
                values = [normalize_text(ws.cell(r, c).value) for c in range(2, min(ws.max_column, 20) + 1)]
                if sum(bool(re.match(r'^[A-Z](?:\.|\s|$)', v)) or v.lower().startswith('проч') for v in values) >= 10:
                    header_row = r
                    break
            if header_row is None:
                raise ValueError(f'Cannot locate FD section header in {ws.title!r}')
            headers: dict[int, str] = {}
            for c in range(2, ws.max_column + 1):
                header = normalize_text(ws.cell(header_row, c).value)
                if not header:
                    continue
                headers[c] = 'PUBLISHED_OTHER' if header.lower().startswith('проч') else header.split('.', 1)[0].strip()
            for r in range(header_row + 1, ws.max_row + 1):
                fd_name = normalize_text(ws.cell(r, 1).value)
                if 'ФЕДЕРАЛЬНЫЙ ОКРУГ' not in fd_name.upper():
                    continue
                for c, section in headers.items():
                    value = ws.cell(r, c).value
                    if value is None:
                        continue
                    rows.append({
                        'source_series': '01_03_C',
                        'source_file_actual': actual.name,
                        'source_sha256': _sha256(actual),
                        'source_sheet': ws.title,
                        'source_row': r,
                        'source_column': c,
                        'as_of_date': as_of_date,
                        'classifier_id': 'okved2_section',
                        'activity_code': section,
                        'activity_name': normalize_text(ws.cell(header_row, c).value),
                        'geography_node_id': FD_ALIASES.get(fd_name, fd_name),
                        'geography_name': fd_name,
                        'geography_kind': 'federal_district_total',
                        'measure': measure,
                        'currency': 'total',
                        'value': float(value),
                    })
    finally:
        wb.close()
    if not seen_date:
        raise ValueError('FD workbook does not contain a recognizable reporting date')
    out = pd.DataFrame(rows)
    if len(out) != 256:
        raise ValueError(f'Expected 256 FD observations, got {len(out)}')
    out['observation_id'] = [f'01_03_C:{i}' for i in range(len(out))]
    return _canonical_records(out, policy)


def load_sors_source_grid(files: SorsSourceFiles, as_of_date: str, publication_step: float = 1.0) -> SorsSourceBundle:
    policy = RoundingPolicy(step=publication_step)
    regional, geography, atomic = parse_regional_traditional(files.regional_traditional, as_of_date, policy)
    national_old = parse_national_traditional(files.national_traditional, as_of_date, policy)
    national_new = parse_national_okved2(files.national_okved2, as_of_date, policy)
    fd = parse_fd_okved2(files.fd_okved2, as_of_date, policy)
    classes = read_okved2_classes()
    explicit = set(national_new.loc[national_new['activity_code'].str.fullmatch(r'\d{2}'), 'activity_code'])
    missing = tuple(sorted(set(classes['class_code']) - explicit))
    if len(missing) != 8:
        raise ValueError(f'Expected 8 classes in national PUBLISHED_OTHER, got {missing}')
    frames = [regional, national_old, national_new, fd]
    # Drop columns that are entirely empty inside an individual source before the
    # union. This avoids pandas' deprecated all-NA dtype inference while retaining
    # the complete canonical column set after concatenation.
    canonical = pd.concat(
        [frame.dropna(axis=1, how='all') for frame in frames],
        ignore_index=True,
        sort=False,
    )
    manifest = pd.DataFrame([
        {'source_series': '01_05_A', 'path': str(files.regional_traditional), 'sha256': _sha256(files.regional_traditional), 'rows': len(regional)},
        {'source_series': '01_02_A', 'path': str(files.national_traditional), 'sha256': _sha256(files.national_traditional), 'rows': len(national_old)},
        {'source_series': '01_02_C', 'path': str(files.national_okved2), 'sha256': _sha256(files.national_okved2), 'rows': len(national_new)},
        {'source_series': '01_03_C', 'path': str(files.fd_okved2), 'sha256': _sha256(files.fd_okved2), 'rows': len(fd)},
    ])
    return SorsSourceBundle(canonical, regional, national_old, national_new, fd, geography, atomic, classes, missing, manifest)


load_sors_sources = load_sors_source_grid
