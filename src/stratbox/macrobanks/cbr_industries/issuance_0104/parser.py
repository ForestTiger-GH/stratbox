"""CBR issuance XLSX parser: verified month, 26 industries and 96 geographic rows."""

from __future__ import annotations

import re
import warnings
from dataclasses import replace
from datetime import date
from hashlib import sha256

import pandas as pd
from openpyxl.utils import get_column_letter

from stratbox.base.ioapi.workbook_input import open_ooxml_workbook
from stratbox.macrobanks.cbr_industries.contracts import Cbr0105ADebtCorpValidationIssue
from stratbox.macrobanks.cbr_industries.shared_parsing import (
    _coerce_numeric_value, _non_empty_industry_headers,
    _region_names, _match_sheet_regions, _sheet_rows, _check_published_unit,
)
from stratbox.macrobanks.cbr_industries.streams import (
    STREAM_COLUMNS, optimize_cbr_0105a_debt_corp_stream_dtypes,
)
from stratbox.macrobanks.cbr_industries.regions import build_cbr_0105a_debt_corp_region_specs
from stratbox.macrobanks.cbr_industries.schema import (
    normalize_cbr_0105a_text, select_industry_headers,
)

from .contracts import IssuanceSheetSpec, ParsedIssuanceFile
from .sources import SERIES_CODE, reference_period, report_date_from_filename

_SHEETS = (
    IssuanceSheetSpec("issuance_rubles", "rubles", "В рублях", "в рублях", 1),
    IssuanceSheetSpec("issuance_foreign", "foreign_currency_and_precious_metals",
                      "В иностранной валюте и драгоценных металлах", "в инвалюте", 2),
    IssuanceSheetSpec("issuance_total", "total", "Итого", "итого", 3),
)
_MONTHS = (
    ("январь", "января"), ("февраль", "февраля"), ("март", "марта"),
    ("апрель", "апреля"), ("май", "мая"), ("июнь", "июня"),
    ("июль", "июля"), ("август", "августа"), ("сентябрь", "сентября"),
    ("октябрь", "октября"), ("ноябрь", "ноября"), ("декабрь", "декабря"),
)


def _recognize_sheet(title: object) -> IssuanceSheetSpec | None:
    text = normalize_cbr_0105a_text(title)
    words = set(text.split())
    if not {"объем", "кредитов", "юридическим", "лицам", "индивидуальным", "предпринимателям"} <= words:
        return None
    if "иностранной валюте" in text:
        if "драгоценных металлах" not in text:
            raise ValueError(f"Unrecognized currency scope: {title!r}")
        return _SHEETS[2] if "в рублях" in text else _SHEETS[1]
    if "в рублях" in text:
        return _SHEETS[0]
    return _SHEETS[2]


def _verify_reference_month(raw: object, report_date: str) -> str:
    text = normalize_cbr_0105a_text(raw)
    years = re.findall(r"(?<!\d)\d{4}(?!\d)", text)
    matches = [index for index, month_names in enumerate(_MONTHS, 1)
               if any(re.search(rf"\b{month}\b", text) for month in month_names)]
    if len(years) != 1 or len(matches) != 1:
        raise ValueError(f"Invalid issuance month in A2: {raw!r}")
    actual = f"{int(years[0]):04d}-{matches[0]:02d}"
    expected = reference_period(report_date)
    if actual != expected:
        raise ValueError(f"Issuance period {actual} does not match release {report_date}: expected {expected}")
    return actual


def _validate_stream(stream: pd.DataFrame, report_date: str) -> tuple[Cbr0105ADebtCorpValidationIssue, ...]:
    issues: list[Cbr0105ADebtCorpValidationIssue] = []
    missing = int(stream["value"].isna().sum())
    if missing:
        issues.append(Cbr0105ADebtCorpValidationIssue(
            "missing_values", "warning", "В исходной таблице есть пустые значения.", missing))
    negatives = stream["value"].dropna().lt(0)
    if negatives.any():
        issues.append(Cbr0105ADebtCorpValidationIssue(
            "negative_values", "error", "В выдачах есть отрицательные значения.", int(negatives.sum())))
    values = stream.pivot(index=["region_code", "industry_code"],
                          columns="currency_scope", values="value")
    keys = ("total", "rubles", "foreign_currency_and_precious_metals")
    if all(key in values.columns for key in keys):
        available = values[list(keys)].notna().all(axis=1)
        diff = (values[keys[0]] - values[keys[1]] - values[keys[2]]).abs()
        divergent = available & diff.gt(1.0)
        if divergent.any():
            issues.append(Cbr0105ADebtCorpValidationIssue(
                "currency_components_do_not_match_total", "warning",
                "Итого отличается от рублевой и валютной частей более чем на 1 млн руб.",
                int(divergent.sum()),
                {"report_date": report_date, "max_absolute_gap": float(diff.loc[divergent].max())},
            ))
    # The published agriculture/forestry aggregate must dominate its own
    # agriculture/services subset. Otherwise the shared APK formula would
    # create a negative forestry remainder from an invalid source identity.
    groups = stream.loc[
        stream["industry_code"].isin(("agriculture_hunting_forestry", "agriculture_hunting_services"))
    ].pivot(index=["region_code", "currency_scope"], columns="industry_code", values="value")
    parent = groups["agriculture_hunting_forestry"]
    child = groups["agriculture_hunting_services"]
    violations = parent.notna() & child.notna() & child.gt(parent)
    if violations.any():
        issues.append(Cbr0105ADebtCorpValidationIssue(
            "industry_subcomponent_exceeds_parent", "error",
            "Сельское хозяйство и услуги превышают сельское хозяйство и лесное хозяйство.",
            int(violations.sum()), {"report_date": report_date},
        ))
    return tuple(issues)


def parse_workbook(content: bytes, *, source_name: str, source_url: str | None = None,
                   source_sha256: str | None = None, checkpoint=None) -> ParsedIssuanceFile:
    report_date = report_date_from_filename(source_name)
    period = reference_period(report_date)
    digest = sha256(content).hexdigest()
    if source_sha256 is not None and source_sha256 != digest:
        raise ValueError("Source content digest mismatch")
    source_id = f"{SERIES_CODE}_{report_date.replace('-', '')}"
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Workbook contains no default style.*", category=UserWarning)
        workbook = open_ooxml_workbook(content, reset_dimensions=True)
    try:
        seen: set[str] = set()
        records: list[dict[str, object]] = []
        regions = None
        industries = None
        unmapped_headers = []
        for worksheet in workbook.worksheets:
            if checkpoint is not None:
                checkpoint()
            row_iterator = iter(worksheet.iter_rows(values_only=True))
            first = next(row_iterator, ())
            title = first[0] if first else None
            spec = _recognize_sheet(title)
            if spec is None:
                continue
            rows = _sheet_rows(row_iterator, first, checkpoint=checkpoint)
            if len(rows) < 4:
                raise ValueError(f"Issuance worksheet is too short: {worksheet.title!r}")
            if spec.code in seen:
                raise ValueError(f"Duplicate issuance indicator: {spec.code}")
            seen.add(spec.code)
            observed_period = _verify_reference_month(rows[1][0] if rows[1] else None, report_date)
            if observed_period != period:
                raise ValueError("Inconsistent issuance reference month")
            _check_published_unit(title)
            headers, current_industries, unmapped = select_industry_headers(
                _non_empty_industry_headers(rows, sheet_name=worksheet.title)
            )
            unmapped_headers.extend((worksheet.title, label) for label in unmapped)
            if industries is None:
                industries = tuple(sorted(current_industries, key=lambda item: item.order))
            region_rows, names = _region_names(rows, sheet_name=worksheet.title)
            if regions is None:
                regions = build_cbr_0105a_debt_corp_region_specs(names)
            matching_regions = _match_sheet_regions(regions, names)
            for source_row, region in zip(region_rows, matching_regions, strict=True):
                row_values = rows[source_row - 1]
                for (source_column, header), industry in zip(headers, current_industries, strict=True):
                    cell = f"{get_column_letter(source_column)}{source_row}"
                    raw = row_values[source_column - 1] if source_column - 1 < len(row_values) else None
                    value = _coerce_numeric_value(raw, coordinate=cell, sheet_name=worksheet.title)
                    records.append({
                        "series_code": SERIES_CODE, "report_date": report_date,
                        "reference_period": period,
                        "sheet_code": spec.code, "sheet_order": spec.order,
                        "measure": spec.measure, "measure_name_ru": spec.measure_name_ru,
                        "currency_scope": spec.currency_scope,
                        "currency_scope_name_ru": spec.currency_scope_name_ru,
                        "unit": "million_rubles", "unit_name_ru": "млн руб.",
                        "region_code": region.code, "region_name": region.canonical_name,
                        "region_source_name": region.source_name,
                        "region_kind": region.region_kind,
                        "federal_district_name": region.federal_district_name,
                        "region_order": region.order,
                        "industry_code": industry.code,
                        "industry_name_ru": industry.canonical_name_ru,
                        "industry_source_name": str(header),
                        "industry_parent_code": industry.parent_code,
                        "industry_hierarchy_level": industry.hierarchy_level,
                        "industry_order": industry.order, "value": value,
                        "source_id": source_id, "source_url": source_url,
                        "source_name": source_name, "source_sha256": digest,
                        "source_sheet_name": worksheet.title,
                        "source_sheet_title": str(title), "source_row": source_row,
                        "source_column": get_column_letter(source_column),
                    })
        if seen != {spec.code for spec in _SHEETS}:
            raise ValueError(f"Expected exactly three issuance indicators, found {sorted(seen)}")
        assert regions is not None and industries is not None
        stream = pd.DataFrame.from_records(records, columns=[*STREAM_COLUMNS, "reference_period"])
        issues = _validate_stream(stream, report_date)
        stream = optimize_cbr_0105a_debt_corp_stream_dtypes(stream)
        return ParsedIssuanceFile(source_id, source_name, source_url, digest, report_date,
                                  period, _SHEETS, industries, regions, issues, stream, len(stream),
                                  unmapped_headers=tuple(unmapped_headers))
    finally:
        workbook.close()
