"""Budget-table period-column interpretation for the canonical extraction slot."""
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation
import re

from stratbox.core.execution.contracts import OperationFailure
from stratbox.core.capabilities.tables import CellSelection
from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.evidence import UsedInputReceipt
from .profiles import table_profile
from .periods import normalize_period


def interpret_budget(request, invocation):
    selected = request["table"]
    profile = request.get("profile", {})
    if not isinstance(selected, CellSelection):
        raise OperationFailure("minfin.selection_required")
    shape = table_profile(profile.get("table_profile", "minfin.budget_table"))
    header = profile.get("header_row", 0)
    if type(header) is not int or not 0 <= header < min(len(selected.rows), shape.max_header_rows):
        raise OperationFailure("minfin.header_invalid")
    period_columns = []
    for column in range(shape.first_period_column - 1, len(selected.rows[header])):
        cell = selected.rows[header][column]
        if cell is None or cell.value in (None, ""):
            continue
        try:
            period_id = normalize_period(str(cell.value), "monthly")
        except ValueError:
            raise OperationFailure("minfin.period.unrecognized_header") from None
        year, month = map(int, period_id.split("-"))
        period_columns.append((column, PeriodRef("interval", start=date(year, 1, 1),
            end=date(year, month, monthrange(year, month)[1]))))
    if len(period_columns) < shape.minimum_periods:
        raise OperationFailure("minfin.flake.period_header_unsupported")
    observations = []
    for row in selected.rows[header + 1:]:
        invocation.check_cancelled()
        code, label = row[shape.code_column - 1], row[shape.indicator_column - 1]
        if code is None or not re.fullmatch(shape.code_pattern, str(code.value)):
            continue
        if label is None or not isinstance(label.value, str) or not label.value:
            raise OperationFailure("minfin.indicator_missing")
        for column, period in period_columns:
            cell = row[column]
            value, status = None, "missing" if cell is None else "blank"
            if cell is not None and cell.value not in (None, ""):
                if str(cell.value) in {"-", "—"}:
                    status = "dash"
                else:
                    try:
                        value = Decimal(str(cell.value).replace(" ", "").replace(",", "."))
                        if not value.is_finite(): raise InvalidOperation()
                    except (ValueError, InvalidOperation):
                        raise OperationFailure("minfin.number_invalid") from None
                    status = "reported"
            observations.append(Observation(SubjectRef("country", "RU"),
                MetricRef("budget." + str(code.value).rstrip("."), "RUB", "flow", shape.method_version, Decimal("1000000000")),
                period, (("indicator", label.value),), profile.get("perimeter", "federal_budget"), value, status,
                f"{selected.source_identity.sha256}:{selected.sheet}:{cell.coordinate if cell else 'absent'}",
                cell.raw_token if cell else None))
    if not observations:
        raise OperationFailure("minfin.observations_missing")
    return ObservationBatch(profile.get("dataset_id", "minfin.budget"), 1, profile["release_id"],
        tuple(observations), (UsedInputReceipt("source", selected.source_identity,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only"),))
