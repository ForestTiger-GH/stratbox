"""Explicit reviewed source-cell mappings; no inferred economic axes."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from .contracts import MapRequest, MappedObservations, MetricObservation
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse

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
    from ..publications.catalog import family
    source = request.extract
    declared = family(source.family_id)
    series = next((item for item in declared.series if item.source_id == source.source_id), None)
    if series is None and source.source_id != declared.default_source_id:
        raise ValueError("minfin.mapping_source_unregistered")
    if source.publication is not None and source.publication.series_id != source.source_id:
        raise ValueError("minfin.mapping_source_context_mismatch")
    # Attachment inventories have family context; they do not acquire a
    # fabricated atomic-series identity through a manual cell mapping.
    source_id = source.source_id if series is not None else None
    from stratbox.domains.registry.declarations import source_cards
    card = next((card for card in source_cards("minfin") if card.series_id == source_id), None)
    group_id = card.source_groups[0].group_id if card is not None and len(card.source_groups) == 1 else None
    publication = source.publication
    use = SourceUse(SourceCoordinate(source_id, source.family_id, group_id,
        issue_id=publication.issue_id if publication else None,
        asset_id=publication.asset_id if publication else None,
        material_identity=source.source_identity), "source_cells", "explicit_cell_mapping")
    return MappedObservations(source.family_id, source.source_identity, tuple(observations), (use,))
