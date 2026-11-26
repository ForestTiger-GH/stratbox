"""Семантический парсер книг Банка России ``01_05_A_Debt_corp``."""

from __future__ import annotations

import re
import warnings
from datetime import date, datetime

import pandas as pd
from openpyxl.utils import get_column_letter

from stratbox.core.formats.spreadsheets.workbook_input import open_ooxml_workbook
from stratbox.shared.identity import ByteIdentity
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.contracts import IndustrySelection
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.contracts import IndustryValidationIssue as Cbr0105ADebtCorpValidationIssue
from stratbox.domains.cbr.methods.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.geography import build_cbr_0105a_debt_corp_region_specs
from stratbox.domains.cbr.methods.publications.corporate_lending.debt_rules import CBR_0105A_DEBT_CORP_SERIES_CODE
from stratbox.domains.cbr.methods.tables.corporate_lending.debt.schema import CBR_0105A_DEBT_CORP_SHEET_SPECS
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.schema import CBR_0105A_DEBT_CORP_UNIT
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.schema import CBR_0105A_DEBT_CORP_UNIT_NAME_RU
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.schema import clean_cbr_0105a_source_label
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.schema import normalize_industry_text
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.schema import select_industry_headers
from stratbox.domains.cbr.methods.tables.corporate_lending.debt.schema import resolve_cbr_0105a_debt_corp_sheet_spec
from stratbox.domains.cbr.methods.publications.corporate_lending.debt_rules import report_date_from_cbr_0105a_filename
from stratbox.domains.cbr.methods.tables.corporate_lending.debt.selection import resolve_industry_codes
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.streams import STREAM_COLUMNS
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.streams import concat_industry_streams
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.streams import optimize_industry_stream_dtypes
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.parsing import _coerce_numeric_value
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.parsing import _non_empty_industry_headers
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.parsing import _region_names
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.parsing import _match_sheet_regions
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.parsing import _sheet_rows
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.parsing import _check_published_unit


_REPORT_DATE_RE = re.compile(r"(?<!\d)(\d{2})[./](\d{2})[./](\d{4})(?!\d)")
def _report_date_from_cell(value: object) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value or "").replace("\xa0", " ")
    match = _REPORT_DATE_RE.search(text)
    if not match:
        raise ValueError(f"01_05_A_Debt_corp report date is not found in row 2: {value!r}")
    return date(int(match.group(3)), int(match.group(2)), int(match.group(1))).isoformat()


def _build_validation_issues(
    df_stream: pd.DataFrame,
    *,
    report_date: str,
    source_name: str,
) -> tuple[Cbr0105ADebtCorpValidationIssue, ...]:
    issues: list[Cbr0105ADebtCorpValidationIssue] = []
    missing_count = int(df_stream["value"].isna().sum())
    if missing_count:
        issues.append(
            Cbr0105ADebtCorpValidationIssue(
                code="missing_values",
                severity="warning",
                message="В опубликованной таблице присутствуют пустые значения.",
                count=missing_count,
                details={"report_date": report_date, "source_name": source_name},
            )
        )

    negative_mask = df_stream["value"].notna() & (df_stream["value"] < 0)
    negative_count = int(negative_mask.sum())
    if negative_count:
        issues.append(
            Cbr0105ADebtCorpValidationIssue(
                code="negative_values",
                severity="error",
                message="В остатках задолженности присутствуют отрицательные значения.",
                count=negative_count,
                details={
                    "report_date": report_date,
                    "source_name": source_name,
                    "minimum_value": float(df_stream.loc[negative_mask, "value"].min()),
                },
            )
        )

    pivot = df_stream.pivot_table(
        index=["region_code", "industry_code"],
        columns=["measure", "currency_scope"],
        values="value",
        aggfunc="first",
        dropna=False,
        observed=False,
    )
    for scope in ("rubles", "foreign_currency_and_precious_metals", "total"):
        debt_key = ("debt", scope)
        overdue_key = ("overdue_debt", scope)
        if debt_key not in pivot.columns or overdue_key not in pivot.columns:
            continue
        mask = (
            pivot[overdue_key].notna()
            & pivot[debt_key].notna()
            & (pivot[overdue_key] > pivot[debt_key])
        )
        count = int(mask.sum())
        if count:
            max_excess = float((pivot.loc[mask, overdue_key] - pivot.loc[mask, debt_key]).max())
            issues.append(
                Cbr0105ADebtCorpValidationIssue(
                    code="overdue_exceeds_debt",
                    severity="error",
                    message="Просроченная задолженность превышает общую задолженность.",
                    count=count,
                    details={
                        "report_date": report_date,
                        "source_name": source_name,
                        "currency_scope": scope,
                        "max_excess": max_excess,
                    },
                )
            )

    for measure in ("debt", "overdue_debt"):
        total_key = (measure, "total")
        rubles_key = (measure, "rubles")
        foreign_key = (measure, "foreign_currency_and_precious_metals")
        if not all(key in pivot.columns for key in (total_key, rubles_key, foreign_key)):
            continue
        complete = pivot[[total_key, rubles_key, foreign_key]].notna().all(axis=1)
        gap = (pivot[total_key] - pivot[rubles_key] - pivot[foreign_key]).abs()
        mask = complete & (gap > 1.0)
        count = int(mask.sum())
        if count:
            issues.append(
                Cbr0105ADebtCorpValidationIssue(
                    code="currency_components_do_not_match_total",
                    severity="warning",
                    message=(
                        "Итого расходится с суммой рублевой и валютной частей "
                        "более чем на 1 млн руб."
                    ),
                    count=count,
                    details={
                        "report_date": report_date,
                        "source_name": source_name,
                        "measure": measure,
                        "max_absolute_gap": float(gap.loc[mask].max()),
                    },
                )
            )
    return tuple(issues)


def parse_cbr_0105a_debt_corp_excel_bytes(
    file_bytes: bytes | ByteIdentity,
    *,
    source_name: str,
    source_id: str | None = None,
    source_url: str | None = None,
    source_sha256: str | None = None,
    checkpoint=None,
    selection: IndustrySelection = IndustrySelection(),
    decoded=None,
) -> ParsedCbr0105ADebtCorpFile:
    """Interpret one buffered or decoded original with its exact byte identity."""
    selected_codes = resolve_industry_codes(selection)
    selected_set = set(selected_codes) if selected_codes is not None else None
    filename_date = report_date_from_cbr_0105a_filename(source_name)
    source_identifier = source_id or (
        f"{CBR_0105A_DEBT_CORP_SERIES_CODE}_{filename_date.replace('-', '')}"
    )
    if isinstance(file_bytes, ByteIdentity) and decoded is None:
        raise ValueError("cbr.industry_decoded_workbook_required")
    identity = file_bytes if isinstance(file_bytes, ByteIdentity) else ByteIdentity.of(file_bytes)
    digest = identity.sha256
    if source_sha256 is not None and source_sha256 != digest:
        raise ValueError("Source workbook digest mismatch")

    workbook = None
    if decoded is None:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="Workbook contains no default style.*",
                category=UserWarning,
            )
            workbook = open_ooxml_workbook(file_bytes, reset_dimensions=True)
        sheets = tuple((worksheet.title, worksheet.iter_rows(values_only=True)) for worksheet in workbook.worksheets)
    else:
        from stratbox.domains.cbr.methods.tables.decoded_workbooks import decoded_sheets
        sheets = decoded_sheets(decoded, file_bytes, checkpoint=checkpoint)
    try:
        if not sheets:
            raise ValueError("01_05_A_Debt_corp workbook has no worksheets")

        records: list[dict[str, object]] = []
        validation_rows: list[tuple] | None = [] if selected_set is not None else None
        seen_sheet_codes: set[str] = set()
        parsed_sheet_specs = []
        common_regions = None
        industries = None
        unmapped_headers = []

        for sheet_name, source_rows in sheets:
            if checkpoint is not None:
                checkpoint()
            rows = iter(source_rows)
            first = next(rows, ())
            sheet_title = first[0] if first else None
            sheet_spec = resolve_cbr_0105a_debt_corp_sheet_spec(sheet_title, allow_unrelated=True)
            if sheet_spec is None:
                continue
            sheet_rows = _sheet_rows(rows, first, checkpoint=checkpoint)
            if len(sheet_rows) < 4:
                raise ValueError(f"01_05_A_Debt_corp sheet is too short: {sheet_name!r}")
            if sheet_spec.code in seen_sheet_codes:
                raise ValueError(
                    "Duplicate semantic sheet in 01_05_A_Debt_corp workbook: "
                    f"code={sheet_spec.code!r}, sheet={sheet_name!r}"
                )
            seen_sheet_codes.add(sheet_spec.code)
            parsed_sheet_specs.append(sheet_spec)

            sheet_date = _report_date_from_cell(sheet_rows[1][0] if sheet_rows[1] else None)
            if sheet_date != filename_date:
                raise ValueError(
                    "01_05_A_Debt_corp date mismatch between filename and sheet: "
                    f"source_name={source_name!r}, filename_date={filename_date}, "
                    f"sheet={sheet_name!r}, sheet_date={sheet_date}"
                )

            _check_published_unit(sheet_title)
            header_cells, current_industries, unmapped = select_industry_headers(
                _non_empty_industry_headers(sheet_rows, sheet_name=sheet_name)
            )
            unmapped_headers.extend((sheet_name, label) for label in unmapped)
            if industries is None:
                industries = tuple(sorted(current_industries, key=lambda item: item.order))

            region_rows, region_names = _region_names(sheet_rows, sheet_name=sheet_name)
            if common_regions is None:
                common_regions = build_cbr_0105a_debt_corp_region_specs(region_names)
            matching_regions = _match_sheet_regions(common_regions, region_names)
            for source_row, region in zip(region_rows, matching_regions, strict=True):
                for (source_column, source_header), industry in zip(
                    header_cells,
                    current_industries,
                    strict=True,
                ):
                    coordinate = f"{get_column_letter(source_column)}{source_row}"
                    row_values = sheet_rows[source_row - 1]
                    raw_value = (
                        row_values[source_column - 1]
                        if source_column - 1 < len(row_values)
                        else None
                    )
                    value = _coerce_numeric_value(
                        raw_value,
                        coordinate=coordinate,
                        sheet_name=sheet_name,
                    )
                    if validation_rows is not None:
                        validation_rows.append((region.code, industry.code, sheet_spec.measure,
                                                sheet_spec.currency_scope, value))
                    if selected_set is not None and industry.code not in selected_set:
                        continue
                    records.append(
                        {
                            "series_code": CBR_0105A_DEBT_CORP_SERIES_CODE,
                            "report_date": filename_date,
                            "sheet_code": sheet_spec.code,
                            "sheet_order": sheet_spec.order,
                            "measure": sheet_spec.measure,
                            "measure_name_ru": sheet_spec.measure_name_ru,
                            "currency_scope": sheet_spec.currency_scope,
                            "currency_scope_name_ru": sheet_spec.currency_scope_name_ru,
                            "unit": CBR_0105A_DEBT_CORP_UNIT,
                            "unit_name_ru": CBR_0105A_DEBT_CORP_UNIT_NAME_RU,
                            "region_code": region.code,
                            "region_name": region.canonical_name,
                            "region_source_name": region.source_name,
                            "region_kind": region.region_kind,
                            "federal_district_name": region.federal_district_name,
                            "region_order": region.order,
                            "industry_code": industry.code,
                            "industry_name_ru": industry.canonical_name_ru,
                            "industry_source_name": clean_cbr_0105a_source_label(source_header),
                            "industry_parent_code": industry.parent_code,
                            "industry_hierarchy_level": industry.hierarchy_level,
                            "industry_order": industry.order,
                            "value": value,
                            "source_id": source_identifier,
                            "source_url": source_url,
                            "source_name": source_name,
                            "source_sha256": digest,
                            "source_sheet_name": sheet_name,
                            "source_sheet_title": str(sheet_title or "").strip(),
                            "source_row": source_row,
                            "source_column": get_column_letter(source_column),
                        }
                    )

        expected_sheet_codes = {spec.code for spec in CBR_0105A_DEBT_CORP_SHEET_SPECS}
        if seen_sheet_codes != expected_sheet_codes:
            raise ValueError(
                "01_05_A_Debt_corp workbook must contain six semantic sheets: "
                f"missing={sorted(expected_sheet_codes - seen_sheet_codes)}, "
                f"unexpected={sorted(seen_sheet_codes - expected_sheet_codes)}"
            )
        assert industries is not None and common_regions is not None

        df_stream = pd.DataFrame.from_records(records, columns=STREAM_COLUMNS)
        df_stream = optimize_industry_stream_dtypes(df_stream)
        key_columns = [
            "report_date",
            "measure",
            "currency_scope",
            "region_code",
            "industry_code",
        ]
        checked = (df_stream if validation_rows is None else pd.DataFrame.from_records(
            validation_rows, columns=["region_code", "industry_code", "measure", "currency_scope", "value"]
        ))
        duplicate_columns = ["region_code", "industry_code", "measure", "currency_scope"]
        duplicate_count = int(checked.duplicated(duplicate_columns, keep=False).sum())
        if duplicate_count:
            raise ValueError(
                "Duplicate observations in 01_05_A_Debt_corp stream: "
                f"duplicate_rows={duplicate_count}"
            )

        df_stream = df_stream.sort_values(
            ["report_date", "sheet_order", "region_order", "industry_order"],
            kind="stable",
        ).reset_index(drop=True)
        validation_issues = _build_validation_issues(
            checked,
            report_date=filename_date,
            source_name=source_name,
        )

        return ParsedCbr0105ADebtCorpFile(
            source_id=source_identifier,
            source_name=source_name,
            source_url=source_url,
            source_sha256=digest,
            report_date=filename_date,
            sheets=tuple(sorted(parsed_sheet_specs, key=lambda item: item.order)),
            industries=industries,
            regions=common_regions,
            validation_issues=validation_issues,
            df_stream=df_stream,
            rows_stream=int(len(df_stream)),
            unmapped_headers=tuple(unmapped_headers),
            selection=selection,
        )
    finally:
        if workbook is not None:
            workbook.close()
