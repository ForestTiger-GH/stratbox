"""Series-local corporate observations, independent of integration and SORS.

All admitted source periods and missing cells remain available. Source category
labels are preserved; shared identities and model constraints are assigned by
the integration owner.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import re
from typing import TYPE_CHECKING

from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake
from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity

if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True, slots=True)
class CorporateObservationProfile:
    series_id: str
    publisher_code: str
    layout: str
    row_dimension: str
    quantity_kind: str
    portfolio_scope: str
    version: int = 1


_PREFIX = "cbr.corporate_lending."
PROFILES = tuple(CorporateObservationProfile(_PREFIX + key, code, layout, dimension, kind, scope)
    for key, code, layout, dimension, kind, scope in (
        ("corp_new_loans_a", "01_01_A", "history", "activity", "flow", "CORPORATE_TOTAL"),
        ("corp_new_loans_c", "01_01_C", "history", "activity", "flow", "CORPORATE_TOTAL"),
        ("corp_debt_a", "01_02_A", "history", "activity", "stock", "CORPORATE_TOTAL"),
        ("corp_debt_c", "01_02_C", "history", "activity", "stock", "CORPORATE_TOTAL"),
        ("sme_debt", "01_11", "history", "portfolio", "stock", "SME"),
        ("sme_debt_activity", "01_11_F", "history", "activity", "stock", "SME"),
        ("sme_ie_debt_activity", "01_11_I", "history", "activity", "stock", "SME_IE"),
        ("sme_debt_subj_f", "01_13_F", "history", "geography", "stock", "SME"),
        ("sme_debt_subj_i", "01_13_I", "history", "geography", "stock", "SME_IE"),
        ("corp_debt_subj", "01_05_D", "history", "geography", "stock", "CORPORATE_TOTAL"),
        ("sme_by_activity", "01_10_F", "history", "activity", "flow", "SME"),
        ("fd_okved2", "01_03_C", "district", "geography_activity", "mixed", "CORPORATE_TOTAL"),
        ("sme_fd_okved2", "01_12_A", "district", "geography_activity", "mixed", "SME"),
    ))
_PROFILES = {item.series_id: item for item in PROFILES}
_DATE = re.compile(r"(?<!\d)(\d{2})[./](\d{2})[./](\d{4})(?!\d)")
_COLUMNS = ("series_id", "publisher_code", "issue_id", "period", "period_basis", "period_raw", "quantity_kind", "portfolio_scope",
            "sheet", "sheet_title", "row", "column", "coordinate", "row_dimension", "row_label", "row_label_raw", "unit",
            "activity_raw", "geography_raw", "measure", "currency", "value", "raw_token", "cell_kind",
            "status", "formula", "number_format")


@dataclass(frozen=True)
class CorporateSourceDataset:
    series_id: str
    issue_id: str
    source_identity: ByteIdentity
    profile_id: str
    profile_version: int
    observations: pd.DataFrame
    available_periods: tuple[str, ...]
    selected_periods: tuple[str, ...]
    diagnostics: tuple[tuple[str, str], ...]
    coverage: SnapshotCoverage
    lineage: tuple[UsedInputReceipt, ...] = ()
    evidence: ComputationReceipt | None = None
    asset_id: str = "main"


def normalize_text(value):
    text = str(value if value is not None else "").replace("\xa0", " ").replace("ё", "е").replace("Ё", "Е")
    return re.sub(r"\s+", " ", text.replace("–", "-").replace("—", "-")).strip()


def source_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, Decimal)) and not isinstance(value, bool) and 1 <= value <= 100000:
        return (datetime(1899, 12, 30) + timedelta(days=float(value))).date().isoformat()
    text = str(value if value is not None else "")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return date.fromisoformat(text).isoformat()
    match = _DATE.search(text)
    if match:
        day, month, year = map(int, match.groups())
        return date(year, month, day).isoformat()
    return None


_MONTHS = {name: index for index, names in enumerate((
    ("январь", "января"), ("февраль", "февраля"), ("март", "марта"),
    ("апрель", "апреля"), ("май", "мая"), ("июнь", "июня"),
    ("июль", "июля"), ("август", "августа"), ("сентябрь", "сентября"),
    ("октябрь", "октября"), ("ноябрь", "ноября"), ("декабрь", "декабря"),
), start=1) for name in names}


def source_period(value, quantity_kind):
    if quantity_kind == "stock":
        return source_date(value)
    text = normalize_text(value).lower()
    match = re.search(r"(?<![а-я])([а-я]+)\s+(\d{4})(?!\d)", text)
    if match and match.group(1) in _MONTHS:
        return f"{int(match.group(2)):04d}-{_MONTHS[match.group(1)]:02d}"
    if re.fullmatch(r"\d{4}-\d{2}", text):
        date.fromisoformat(text + "-01")
        return text
    day = source_date(value)
    return day[:7] if day else None


def valid_period(value, quantity_kind):
    if not isinstance(value, str):
        return False
    if quantity_kind == "mixed":
        return valid_period(value, "stock") or valid_period(value, "flow")
    try:
        return source_period(value, quantity_kind) == value
    except ValueError:
        return False


def sheet_semantics(title, *, quantity_kind="stock"):
    value = normalize_text(title).lower()
    measure = "issuance" if quantity_kind == "flow" or "объем кредитов" in value and "задолж" not in value else "overdue" if "просроч" in value else "debt"
    currency = "fx" if "инвалют" in value or "иностран" in value else "rub" if "в рублях" in value else "total"
    if "в рублях" in value and ("инвалют" in value or "иностран" in value):
        currency = "total"
    return measure, currency


def cell_number(cell):
    if cell is None or cell.value is None:
        return None, "formula_unresolved" if cell is not None and cell.formula is not None else "blank"
    if isinstance(cell.value, (int, Decimal)) and not isinstance(cell.value, bool):
        return cell.value, "formula_cached" if cell.formula is not None else "numeric"
    text = str(cell.value).strip()
    if not text:
        return None, "blank"
    if text in {"-", "—", "–", "...", "…", "х", "x"}:
        return None, "marker"
    try:
        value = Decimal(text.replace("\xa0", "").replace(" ", "").replace(",", "."))
        if value.is_finite():
            return value, "numeric_text"
    except InvalidOperation:
        pass
    return None, "unparsed"


def extract_observations(flake: WorkbookFlake, *, periods=None, checkpoint=None, budget=None):
    import pandas as pd
    if not isinstance(flake, WorkbookFlake) or flake.series_id not in _PROFILES:
        raise ValueError("cbr.corporate.source_profile_unsupported")
    profile = _PROFILES[flake.series_id]
    if periods is not None and (not isinstance(periods, tuple) or not periods or len(set(periods)) != len(periods)
            or any(not valid_period(day, profile.quantity_kind) for day in periods)):
        raise ValueError("cbr.corporate.period_selection_invalid")
    selected = set(periods) if periods else None
    records, diagnostics, available = [], [], set()
    for sheet in flake.sheets:
        if checkpoint is not None:
            checkpoint()
        cells = {(cell.row, cell.column): cell for cell in sheet.cells}
        at = lambda row, column: cells.get((row, column))
        val = lambda row, column: at(row, column).value if at(row, column) is not None else None
        title = normalize_text(val(1, 1)) or sheet.name
        measure, currency = sheet_semantics(title, quantity_kind=profile.quantity_kind)
        positions = []
        if profile.layout == "history":
            date_columns = [(column, source_period(val(2, column), profile.quantity_kind)) for column in range(2, sheet.columns + 1)]
            date_columns = [(column, day) for column, day in date_columns if day is not None]
            if not date_columns:
                diagnostics.append((sheet.name, "date_header_unrecognized"))
                continue
            if len({day for _, day in date_columns}) != len(date_columns):
                raise ValueError("cbr.corporate.duplicate_date_column")
            available.update(day for _, day in date_columns)
            row_stop = min(sheet.rows, 4) if profile.row_dimension == "portfolio" else sheet.rows
            for row in range(3, row_stop + 1):
                label = normalize_text(val(row, 1))
                if not label:
                    continue
                for column, day in date_columns:
                    if selected is None or day in selected:
                        positions.append((row, column, day, label,
                            label if profile.row_dimension == "activity" else "",
                            label if profile.row_dimension == "geography" else ""))
        else:
            day = source_period(title, "flow" if measure == "issuance" else "stock")
            if day is None:
                diagnostics.append((sheet.name, "reference_date_unrecognized"))
                continue
            available.add(day)
            if selected is not None and day not in selected:
                continue
            header = next((row for row in range(1, min(sheet.rows, 8) + 1)
                if sum(bool(re.match(r"^[A-Z](?:\.|\s|$)", normalize_text(val(row, column))))
                       or normalize_text(val(row, column)).lower().startswith("проч")
                       for column in range(2, min(sheet.columns, 20) + 1)) >= 10), None)
            if header is None:
                diagnostics.append((sheet.name, "activity_header_unrecognized"))
                continue
            if "задолж" not in title.lower():
                measure = "issuance" if any(word in title.lower() for word in ("объем", "предоставлен")) else "unknown"
            for row in range(header + 1, sheet.rows + 1):
                geography = normalize_text(val(row, 1))
                if "ФЕДЕРАЛЬНЫЙ ОКРУГ" not in geography.upper():
                    continue
                for column in range(2, sheet.columns + 1):
                    activity = normalize_text(val(header, column))
                    if activity:
                        positions.append((row, column, day, geography, activity, geography))
        for row, column, day, label, activity, geography in positions:
            cell = at(row, column)
            value, status = cell_number(cell)
            scope = "SME_IE" if profile.row_dimension == "portfolio" and row == 4 else profile.portfolio_scope
            coordinate = cell.coordinate if cell is not None else _coordinate(row, column)
            records.append((flake.series_id, profile.publisher_code, flake.issue_id, day,
                "reference_month" if measure == "issuance" else "as_of", val(2, column) if profile.layout == "history" else title,
                "flow" if measure == "issuance" else "stock", scope,
                sheet.name, title, row, column, coordinate, profile.row_dimension, label, val(row, 1), "million_rubles", activity, geography,
                measure, currency, value, cell.raw_token if cell else None, cell.kind if cell else "blank", status,
                cell.formula if cell else None, cell.number_format if cell else "General"))
    if selected is not None and not selected <= available:
        raise ValueError("cbr.corporate.period_missing")
    if not records:
        raise ValueError("cbr.corporate.observations_empty")
    if budget is not None:
        budget.check("cells", len(records) * len(_COLUMNS))
    selected_periods = tuple(sorted(selected if selected is not None else available))
    return CorporateSourceDataset(flake.series_id, flake.issue_id, flake.source_identity,
        "cbr.corporate.observations." + profile.publisher_code.lower(), profile.version,
        pd.DataFrame(records, columns=_COLUMNS, dtype=object), tuple(sorted(available)), selected_periods,
        tuple(diagnostics), SnapshotCoverage("partial" if diagnostics or selected is not None else "complete",
            "Recognized source observation grids; complete original context remains in the source workbook flake."),
        flake.lineage, asset_id=flake.asset_id)


def _coordinate(row, column):
    label = ""
    while column:
        column, digit = divmod(column - 1, 26)
        label = chr(65 + digit) + label
    return label + str(row)
