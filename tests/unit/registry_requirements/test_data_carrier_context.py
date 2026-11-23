"""Selected data carriers preserve source coordinates without broadening scope."""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from stratbox.core.execution.handoff import prepare_input, project_output
from stratbox.core.registry import operation_catalog
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity

SOURCE = "minfin.fedbud.annex3.monthly"


def _mapped_request():
    from stratbox.domains.minfin.tables.contracts import Cell, Sheet, TableExtract, MapRequest, MetricBinding
    from stratbox.domains.minfin.publications.context import PublicationContext
    payload = SourcePayload(b"original published workbook")
    publication = PublicationContext(SOURCE, "document-42", "annex3", date(2026, 11, 15))
    extract = TableExtract("minfin.fedbud", SOURCE, payload.identity, "xlsx",
        (Sheet("Budget", 1, 1, (Cell("Budget", 1, 1, "number", "1.2300"),)),), publication=publication)
    binding = MetricBinding("Budget", 1, 1, "budget.revenue", "2026-10", "ytd", "RUB_bn")
    return MapRequest(extract, (binding,))


def test_actual_mapped_values_keep_series_material_release_and_separate_economic_period():
    from stratbox.core.execution.value_context import value_context
    request = _mapped_request()
    catalog = operation_catalog()
    call = catalog.bind_source(SOURCE, format="xlsx").bind("minfin.map_observations",
        inputs={"extract": prepare_input(request.extract, DataContract("minfin.source_cells", 2, DataRole.EXTRACTS))},
        parameters={"bindings": request.bindings})
    result = call.invoke()
    assert result.outcome == "succeeded", result.diagnostics
    use, = result.value.source_uses
    assert use.coordinate.source_id == SOURCE
    assert use.coordinate.family_id == "minfin.fedbud"
    assert use.coordinate.source_group_id == "fiscal_statistics"
    assert use.coordinate.material_identity == request.extract.source_identity
    assert use.coordinate.issue_id == "document-42"
    assert result.value.observations[0].period_id == "2026-10"
    assert result.value.observations[0].value == "1.2300"
    assert value_context(result.value).source_ids == (SOURCE,)
    assert project_output(result, "observations").source_context.source_ids == (SOURCE,)


def test_mapping_refuses_conflicting_source_context_and_keeps_family_inventory_unqualified():
    from stratbox.domains.minfin.tables.mapping import map_metrics
    request = _mapped_request()
    bad = replace(request.extract, source_id="minfin.conbud.monthly")
    with pytest.raises(ValueError, match="minfin.mapping_source_unregistered"):
        map_metrics(replace(request, extract=bad))
    inventory = replace(request.extract, source_id="minfin.fedbud.attachments", publication=None)
    value = map_metrics(replace(request, extract=inventory))
    assert value.source_uses[0].coordinate.source_id is None
    assert value.source_uses[0].coordinate.family_id == "minfin.fedbud"


def _batch_snapshot():
    from stratbox.shared.data.observations import ObservationBatch, Observation, MetricRef, PeriodRef, SubjectRef
    from stratbox.shared.data.observation_snapshots import observation_snapshot
    use = SourceUse(SourceCoordinate(SOURCE, "minfin.fedbud", "fiscal_statistics", "document-42",
                    material_identity=ByteIdentity.of(b"published source")), "published", "declared")
    record = Observation(SubjectRef("geography", "RU"), MetricRef("revenue", "RUB"),
        PeriodRef("interval", start=date(2026, 1, 1), end=date(2026, 10, 31)), (), "federal_budget", Decimal("1.23"), "reported", "fixture")
    return observation_snapshot(ObservationBatch("example", 1, "release", (record,), (), (use,))), use


def test_query_projection_keeps_qualified_source_and_uses_its_own_projection_contract():
    from stratbox.core.storage.datasets.operations import query_snapshot
    from stratbox.core.storage.datasets.definitions import QuerySnapshotRequest
    from stratbox.shared.data.query import TableQuery
    snapshot, use = _batch_snapshot()
    result = query_snapshot(QuerySnapshotRequest(snapshot, TableQuery("observations", columns=("metric_id", "decimal_value"))))
    assert result.outcome == "succeeded", result.diagnostics
    assert result.value.table.rows == (("revenue", Decimal("1.23")),)
    assert result.value.table.schema.contract.schema_id == "dataset.table_projection"
    assert result.value.source_contract == snapshot.table("observations").schema.contract
    assert result.value.source_uses == (use,)
    assert result.value.source_context_qualification == "snapshot_single_coordinate"
    assert project_output(result, "preview").source_context.source_ids == (SOURCE,)


def test_query_does_not_read_discarded_tables_or_attach_unrelated_metadata():
    from stratbox.core.storage.datasets.operations import query_snapshot
    from stratbox.core.storage.datasets.definitions import QuerySnapshotRequest
    from stratbox.shared.data.query import TableQuery
    from stratbox.shared.data.snapshots import DatasetSnapshot, TypedTable, TableSchema, ColumnSchema, ScalarType, SnapshotCoverage
    snapshot, _ = _batch_snapshot()
    unrelated = TypedTable(TableSchema(DataContract("example.unrelated"), (ColumnSchema("value", ScalarType.INTEGER),)), ((99,),))
    discarded = TypedTable(TableSchema(DataContract("example.discarded"), (ColumnSchema("value", ScalarType.INTEGER),)), ((1,),))
    class UnreadRows(tuple):
        def __iter__(self):
            raise AssertionError("Discarded rows were read")
    object.__setattr__(discarded, "rows", UnreadRows(discarded.rows))
    combined = DatasetSnapshot.build("composite", "v1", DataContract("example.composite"),
        (("metadata", snapshot.table("metadata")), ("unrelated", unrelated), ("discarded", discarded)),
        coverage=SnapshotCoverage("partial", "Only the selected component is consumed."))
    result = query_snapshot(QuerySnapshotRequest(combined, TableQuery("unrelated")))
    assert result.outcome == "succeeded", result.diagnostics
    assert result.value.source_uses == ()
    assert result.value.source_context_qualification == "unqualified"
