"""Integrate admitted rows; mixed-unit tables require row-level semantics."""
from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from urllib.parse import quote

from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.evidence import UsedInputReceipt
from ..tables.flake_codec import serialize_flake, validate_flake
from ..tables.contracts import SerializeFlakeRequest
from .contracts import IntegrateRequest, RowBinding

_KINDS = {"stock": "stock", "ytd": "flow", "annual": "flow", "period_flow": "flow", "ratio": "ratio", "index": "index", "count": "count"}
_BUDGET_PERIMETERS = {
    "minfin.fedbud": "russian_federal_budget", "minfin.conbud": "russian_consolidated_budget",
    "minfin.subbud": "russian_regional_budgets",
}


def economic_period(period_id: str, frequency: str, basis: str) -> PeriodRef:
    if frequency == "annual" and re.fullmatch(r"(?:19|20|21)\d{2}", period_id):
        year, month, first = int(period_id), 12, 1
    elif frequency == "quarterly" and re.fullmatch(r"(?:19|20|21)\d{2}-Q[1-4]", period_id):
        year, month = int(period_id[:4]), int(period_id[-1]) * 3
        first = month - 2
    elif frequency == "monthly" and re.fullmatch(r"(?:19|20|21)\d{2}-(?:0[1-9]|1[0-2])", period_id):
        year, month = map(int, period_id.split("-"))
        first = month
    else:
        raise ValueError("minfin.integration.period_invalid")
    end = date(year, month, monthrange(year, month)[1])
    if basis == "stock":
        return PeriodRef("as_of", as_of=end)
    if basis in {"ytd", "annual", "period_flow", "ratio", "index", "count"}:
        if basis == "annual" and frequency != "annual":
            raise ValueError("minfin.integration.period_basis_mismatch")
        return PeriodRef("interval", start=date(year, 1 if basis in {"ytd", "annual"} else first, 1), end=end)
    raise ValueError("minfin.integration.basis_invalid")


def reviewed_bindings(flake) -> tuple[RowBinding, ...]:
    if flake.family_id in _BUDGET_PERIMETERS:
        specs = (("1", "budget.revenue", "Доходы, всего"),
                 ("2", "budget.expenditure", "Расходы, всего"),
                 ("3", "budget.balance", "Дефицит (-)/Профицит (+)"))
        perimeter, basis = _BUDGET_PERIMETERS[flake.family_id], flake.value_basis
    elif flake.source_id == "minfin.nwf.flows":
        specs = (("2", "nwf.total", "Объем на конец периода"),
                 ("5", "nwf.other_assets", "Размещено в иные разрешенные активы на конец периода"))
        perimeter, basis = "russian_national_wealth_fund", "stock"
    else:
        raise ValueError("minfin.integration.bindings_required")
    bindings = []
    for code, metric_id, prefix in specs:
        rows = [row for row in flake.rows if row.code.rstrip(".") == code]
        if len(rows) != 1 or not rows[0].indicator.casefold().startswith(prefix.casefold()):
            raise ValueError("minfin.integration.reviewed_layout_mismatch")
        bindings.append(RowBinding(code, MetricRef(metric_id, "RUB", _KINDS[basis], "1", Decimal("1e9")),
                                   SubjectRef("geography", "RU"), perimeter, basis))
    return tuple(bindings)


def numeric_value(raw: str | None):
    if raw is None:
        return None, "missing"
    token = raw.strip()
    if not token:
        return None, "blank"
    if token in {"-", "—", "–"}:
        return None, "dash"
    normalized = token.replace("\u00a0", "").replace("\u202f", "").replace(" ", "").replace(",", ".")
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?", normalized):
        raise ValueError("minfin.integration.numeric_value_invalid")
    try:
        value = Decimal(normalized)
    except InvalidOperation:
        raise ValueError("minfin.integration.numeric_value_invalid") from None
    if not value.is_finite():
        raise ValueError("minfin.integration.numeric_value_invalid")
    return value, "reported"


def integrate(request: IntegrateRequest) -> ObservationBatch:
    flake = request.flake
    validate_flake(flake)
    if not request.dataset_id or not request.release_id:
        raise ValueError("minfin.integration.identity_required")
    bindings = request.bindings or reviewed_bindings(flake)
    if not isinstance(bindings, tuple) or not bindings or len({x.code.rstrip(".") for x in bindings}) != len(bindings):
        raise ValueError("minfin.integration.bindings_invalid")
    observations = []
    keys = set()
    for binding in bindings:
        if (not isinstance(binding, RowBinding) or not binding.perimeter or
                binding.metric.definition_version is None or binding.metric.scale is None or
                _KINDS.get(binding.value_basis) != binding.metric.quantity_kind or
                not binding.subject.namespace or not binding.subject.id):
            raise ValueError("minfin.integration.semantics_required")
        rows = [row for row in flake.rows if row.code.rstrip(".") == binding.code.rstrip(".")]
        if len(rows) != 1:
            raise ValueError("minfin.integration.row_ambiguous")
        row = rows[0]
        if row.unit is not None and (row.unit != binding.metric.unit or Decimal(row.scale) != binding.metric.scale):
            raise ValueError("minfin.integration.unit_mismatch")
        if row.unit is None and flake.unit_hint == "billion_rub" and (
                binding.metric.unit != "RUB" or binding.metric.scale != Decimal("1e9")):
            raise ValueError("minfin.integration.unit_mismatch")
        if row.value_basis is not None and row.value_basis != binding.value_basis:
            raise ValueError("minfin.integration.basis_mismatch")
        periods = dict(binding.periods)
        if (not isinstance(binding.periods, tuple) or len(periods) != len(binding.periods)
                or periods and set(periods) != {column.period_id for column in flake.columns}
                or any(not isinstance(period, PeriodRef) or period.kind == "capture" for period in periods.values())
                or binding.value_basis in {"ratio", "index", "count"} and not periods):
            raise ValueError("minfin.integration.explicit_periods_required")
        dimensions = (*binding.dimensions, ("value_basis", binding.value_basis), ("source_series", flake.source_id))
        for column, raw in zip(flake.columns, row.values):
            period = periods.get(column.period_id) or economic_period(column.period_id, flake.frequency, binding.value_basis)
            if (binding.metric.quantity_kind == "stock" and period.kind != "as_of"
                    or binding.metric.quantity_kind == "flow" and period.kind != "interval"):
                raise ValueError("minfin.integration.period_basis_mismatch")
            key = (binding.subject, binding.metric, period, dimensions, binding.perimeter)
            if key in keys:
                raise ValueError("minfin.integration.duplicate_semantic_key")
            keys.add(key)
            value, status = numeric_value(raw)
            evidence = f"sha256:{flake.original_identity.sha256}#sheet={quote(flake.sheet_name, safe='')}&row={row.source_row}&column={column.source_column}"
            if flake.publication is not None:
                evidence += "&issue=" + quote(flake.publication.issue_id, safe="") + "&asset=" + quote(flake.publication.asset_id, safe="")
            observations.append(Observation(binding.subject, binding.metric, period, dimensions,
                                            binding.perimeter, value, status, evidence, raw))
    representation = serialize_flake(SerializeFlakeRequest(flake))
    lineage = (UsedInputReceipt("flake", representation.identity, representation.media_type, "inline", flake.source_id),
               UsedInputReceipt("original", flake.original_identity, "application/octet-stream", "reference_only", flake.source_id))
    return ObservationBatch(request.dataset_id, 1, request.release_id, tuple(observations), lineage)
