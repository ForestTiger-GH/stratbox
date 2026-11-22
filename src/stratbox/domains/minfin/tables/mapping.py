"""Explicit reviewed source-cell mappings; no inferred economic axes."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from .contracts import MapRequest, MappedObservations, MetricObservation

def map_metrics(request: MapRequest) -> MappedObservations:
    if not request.bindings:
        raise ValueError("minfin.mapping_empty")
    indexed = {(c.sheet, c.row, c.column): c for sh in request.extract.sheets for c in sh.cells}
    seen = set()
    observations = []
    for binding in request.bindings:
        key = (binding.sheet, binding.row, binding.column)
        identity = (binding.metric_id, binding.period_id, binding.geography_id, binding.value_basis)
        if identity in seen:
            raise ValueError("minfin.mapping_duplicate")
        seen.add(identity)
        if not all((binding.metric_id, binding.period_id, binding.geography_id, binding.unit, binding.value_basis)):
            raise ValueError("minfin.mapping_incomplete")
        cell = indexed.get(key)
        if cell is None or cell.kind not in {"number", "formula"}:
            raise ValueError("minfin.mapping_value_unavailable")
        value = cell.cached if cell.kind == "formula" else cell.value
        try:
            parsed = Decimal(value)
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("minfin.mapping_value_invalid") from None
        if not parsed.is_finite():
            raise ValueError("minfin.mapping_value_invalid")
        observations.append(MetricObservation(binding.metric_id, binding.period_id,
                          binding.geography_id, str(parsed), binding.value_basis, binding.unit,
                          *key))
    return MappedObservations(request.extract.family_id, request.extract.source_identity, tuple(observations))
