"""Series-local corporate observations, independent of integration and SORS.

All admitted source periods and missing cells remain available. Source category
labels are preserved; shared identities and model constraints are assigned by
the integration owner.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import re
from typing import TYPE_CHECKING

from stratbox.shared.data.coverage import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity

if TYPE_CHECKING:
    import pandas as pd


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
    observations: pd.DataFrame
    available_periods: tuple[str, ...]
    selected_periods: tuple[str, ...]
    diagnostics: tuple[tuple[str, str], ...]
    coverage: SnapshotCoverage
    lineage: tuple[UsedInputReceipt, ...] = ()
    evidence: object | None = None
    asset_id: str = "main"

    @property
    def source_uses(self):
        from stratbox.domains.cbr.common.provenance import source_use
        return (source_use(self.series_id, self.issue_id, self.source_identity, asset_id=self.asset_id),)


def _context_identity(value):
    from stratbox.shared.data.values import fingerprint
    return fingerprint((value.series_id, value.issue_id, value.source_identity,
        value.asset_id, value.available_periods, value.selected_periods,
        value.diagnostics, value.coverage, value.lineage))


def validate_source_dataset(value):
    from stratbox.shared.data.tables import table_identity
    if (not isinstance(value, CorporateSourceDataset) or value.evidence is None
            or value.evidence.output != table_identity((("observations", value.observations),))
            or value.evidence.context_identity != _context_identity(value)):
        raise ValueError("cbr.corporate.observation_identity_mismatch")
    return value


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


def extract_observations(flake, settings, *, periods=None, checkpoint=None, budget=None):
    import pandas as pd
    if settings is None or not hasattr(flake, "sheets"):
        raise ValueError("cbr.corporate.source_settings_required")
    if periods is not None and (not isinstance(periods, tuple) or not periods or len(set(periods)) != len(periods)
            or any(not valid_period(day, settings.quantity_kind) for day in periods)):
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
        measure, currency = sheet_semantics(title, quantity_kind=settings.quantity_kind)
        positions = []
        if settings.layout == "history":
            date_columns = [(column, source_period(val(2, column), settings.quantity_kind)) for column in range(2, sheet.columns + 1)]
            date_columns = [(column, day) for column, day in date_columns if day is not None]
            if not date_columns:
                diagnostics.append((sheet.name, "date_header_unrecognized"))
                continue
            if len({day for _, day in date_columns}) != len(date_columns):
                raise ValueError("cbr.corporate.duplicate_date_column")
            available.update(day for _, day in date_columns)
            row_stop = min(sheet.rows, 4) if settings.row_dimension == "portfolio" else sheet.rows
            for row in range(3, row_stop + 1):
                label = normalize_text(val(row, 1))
                if not label:
                    continue
                for column, day in date_columns:
                    if selected is None or day in selected:
                        positions.append((row, column, day, label,
                            label if settings.row_dimension == "activity" else "",
                            label if settings.row_dimension == "geography" else ""))
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
            scope = "SME_IE" if settings.row_dimension == "portfolio" and row == 4 else settings.portfolio_scope
            coordinate = cell.coordinate if cell is not None else _coordinate(row, column)
            records.append((flake.series_id, settings.publisher_code, flake.issue_id, day,
                "reference_month" if measure == "issuance" else "as_of", val(2, column) if settings.layout == "history" else title,
                "flow" if measure == "issuance" else "stock", scope,
                sheet.name, title, row, column, coordinate, settings.row_dimension, label, val(row, 1), "million_rubles", activity, geography,
                measure, currency, value, cell.raw_token if cell else None, cell.kind if cell else "blank", status,
                cell.formula if cell else None, cell.number_format if cell else "General"))
    if selected is not None and not selected <= available:
        raise ValueError("cbr.corporate.period_missing")
    if not records:
        raise ValueError("cbr.corporate.observations_empty")
    if budget is not None:
        budget.check("cells", len(records) * len(_COLUMNS))
    selected_periods = tuple(sorted(selected if selected is not None else available))
    value = CorporateSourceDataset(flake.series_id, flake.issue_id, flake.source_identity,
        pd.DataFrame(records, columns=_COLUMNS, dtype=object), tuple(sorted(available)), selected_periods,
        tuple(diagnostics), SnapshotCoverage("partial" if diagnostics or selected is not None else "complete",
            "Recognized source observation grids; complete original context remains in the source workbook flake."),
        flake.lineage, asset_id=flake.asset_id)
    from stratbox.shared.data.tables import table_identity
    from stratbox.domains.cbr.common.contracts import SourceContentEvidence
    return replace(value, evidence=SourceContentEvidence(
        table_identity((("observations", value.observations),)), value.lineage, _context_identity(value)))


def _coordinate(row, column):
    label = ""
    while column:
        column, digit = divmod(column - 1, 26)
        label = chr(65 + digit) + label
    return label + str(row)
