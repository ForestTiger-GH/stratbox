"""Source context survives exact handoff, retained data and source selectors."""
from dataclasses import dataclass, replace
from datetime import date
from io import BytesIO

import pytest

from stratbox.core.execution import HandoffError, prepare_input, project_output
from stratbox.core.execution.value_context import value_context
from stratbox.operations import operation_catalog
from stratbox.shared.data.processing import DataContract
from stratbox.shared.evidence import SourcePayload


@pytest.fixture
def payload():
    from openpyxl import Workbook
    workbook = Workbook()
    workbook.active.append(["Metric", "Value"])
    workbook.active.append(["Loans", 27])
    stream = BytesIO()
    workbook.save(stream)
    return SourcePayload(stream.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _snapshot(catalog, payload, series_id="cbr.corporate_lending.corp_debt_c"):
    source = catalog.bind_source(series_id, format="xlsx")
    original = source.bind("cbr.publications.identify",
        inputs={"material": prepare_input(payload)},
        parameters={"issue_id": "2026-10", "format": "xlsx"}).invoke()
    assert original.outcome == "succeeded", original.diagnostics
    extracted = source.bind("cbr.tables.extract",
        inputs={"original": project_output(original, "original")}).invoke()
    assert extracted.outcome == "succeeded", extracted.diagnostics
    result = source.bind("cbr.tables.flake_snapshot",
        inputs={"flake": project_output(extracted, "flake")}).invoke()
    assert result.outcome == "succeeded", result.diagnostics
    return source, result


def test_exact_cbr_selection_can_feed_acquisition_regardless_of_stage_projection():
    catalog = operation_catalog()
    source = catalog.bind_source("cbr.corporate_lending.corp_debt_a", format="xlsx")
    discovered = source.bind("cbr.publications.discover").invoke()
    assert discovered.outcome == "succeeded", discovered.diagnostics
    selected = source.bind("cbr.publications.select",
        inputs={"inventory": project_output(discovered, "inventory")}).invoke()
    assert selected.outcome == "succeeded", selected.diagnostics
    projected = source.bind("cbr.publications.acquire",
        inputs={"asset": project_output(selected, "asset")},
        parameters={"issue_id": "2026-10"})
    prepared = source.bind("cbr.publications.acquire",
        inputs={"asset": prepare_input(selected.value, DataContract("cbr.publications.asset"))},
        parameters={"issue_id": "2026-10"})
    assert projected.request == prepared.request


@pytest.mark.parametrize("projected", [True, False])
def test_foreign_source_snapshot_is_rejected_before_replay(payload, projected):
    catalog = operation_catalog()
    _, result = _snapshot(catalog, payload)
    incoming = (project_output(result, "snapshot") if projected else
        prepare_input(result.value, DataContract("dataset.snapshot")))
    assert value_context(result.value).source_ids == ("cbr.corporate_lending.corp_debt_c",)
    wrong = catalog.bind_source("cbr.corporate_lending.corp_debt_a", format="xlsx")
    with pytest.raises(HandoffError, match="source.input_series_mismatch"):
        wrong.bind("cbr.tables.read_flake_snapshot", inputs={"snapshot": incoming})


def test_projected_and_prepared_retained_input_have_same_computation(payload):
    catalog = operation_catalog()
    source, result = _snapshot(catalog, payload)
    projected = source.bind("cbr.tables.read_flake_snapshot",
        inputs={"snapshot": project_output(result, "snapshot")}).invoke()
    prepared = source.bind("cbr.tables.read_flake_snapshot", inputs={
        "snapshot": prepare_input(result.value, DataContract("dataset.snapshot"))}).invoke()
    assert projected.outcome == prepared.outcome == "succeeded"
    assert projected.value == prepared.value
    assert projected.computation.computation_id == prepared.computation.computation_id


def test_frank_rg_selector_is_fixed_by_its_declared_identity_parameter(payload):
    from stratbox.domains.frank_rg.publications.contracts import ReportPeriod
    source = operation_catalog().bind_source("frg.regional.issuance", format="xlsx")
    with pytest.raises(HandoffError, match="source.parameter_conflict"):
        source.bind("frg.capture", inputs={"payload": prepare_input(payload)},
            parameters={"source_id": "frg.regional.issuance_cards",
                        "period": ReportPeriod(date(2026, 10, 1)), "format": "xlsx"})
    bound = source.bind("frg.capture", inputs={"payload": prepare_input(payload)},
        parameters={"period": ReportPeriod(date(2026, 10, 1)), "format": "xlsx"})
    assert bound.request.source_id == source.source.series_id
    result = bound.invoke()
    assert result.outcome == "succeeded", result.diagnostics
    assert value_context(result.value).source_ids == (source.source.series_id,)


def test_source_bound_call_checks_actual_output_context(payload, monkeypatch):
    from stratbox.domains.frank_rg.publications.contracts import ReportPeriod
    catalog = operation_catalog()
    parameters = {"period": ReportPeriod(date(2026, 10, 1)), "format": "xlsx"}
    wrong = catalog.bind_source("frg.regional.issuance_cards", format="xlsx").bind(
        "frg.capture", inputs={"payload": prepare_input(payload)}, parameters=parameters).invoke()
    assert wrong.outcome == "succeeded", wrong.diagnostics
    call = catalog.bind_source("frg.regional.issuance", format="xlsx").bind(
        "frg.capture", inputs={"payload": prepare_input(payload)}, parameters=parameters)
    from stratbox.core.execution import run
    monkeypatch.setattr(type(catalog), "resolve", lambda self, operation_id:
        (call.definition, lambda request, context=None: run(call.definition, request,
            lambda req, invocation: wrong.value, context=context), None))
    rejected = call.invoke()
    assert rejected.outcome == "failed"
    assert rejected.value is None
    assert any(item.code == "source.output_series_mismatch" for item in rejected.diagnostics)


def test_auxiliary_source_admission_is_scoped_to_input_and_preserves_primary_output(payload, monkeypatch):
    catalog = operation_catalog()
    _, snapshot = _snapshot(catalog, payload)
    foreign = catalog.bind_source("cbr.corporate_lending.corp_debt_a", format="xlsx")
    original_binding = next(item for item in foreign.source.operations
        if item.operation_id == "cbr.tables.read_flake_snapshot")

    def with_auxiliary(input_name):
        binding = replace(original_binding, auxiliary_sources=((input_name,
            ("cbr.corporate_lending.corp_debt_c",)),))
        from stratbox.domains.registry.catalog import SourceCatalog
        card = replace(foreign.source, operations=(binding,))
        source_catalog = SourceCatalog(tuple(card if source.series_id == card.series_id else source
            for source in catalog.source_catalog().sources), catalog)
        monkeypatch.setattr(type(catalog), "source_catalog", lambda self: source_catalog)
        return replace(foreign, source=card)

    with pytest.raises(HandoffError, match="source.input_series_mismatch"):
        with_auxiliary("other_input").bind("cbr.tables.read_flake_snapshot",
            inputs={"snapshot": project_output(snapshot, "snapshot")})
    admitted = with_auxiliary("snapshot").bind("cbr.tables.read_flake_snapshot",
        inputs={"snapshot": project_output(snapshot, "snapshot")})
    # A permitted supporting source never becomes the primary output source.
    rejected = admitted.invoke()
    assert rejected.outcome == "failed"
    assert any(item.code == "source.output_series_mismatch" for item in rejected.diagnostics)


def test_source_bound_storage_requires_context_and_generic_storage_accepts_unqualified_snapshot():
    from stratbox.core.storage.datasets.memory import MemoryDatasetStore
    from stratbox.shared.data.snapshots import (
        ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable,
    )
    table = TypedTable(TableSchema(DataContract("external.unqualified"),
        (ColumnSchema("value", ScalarType.INTEGER),)), ((27,),))
    snapshot = DatasetSnapshot.build("caller-selected", "capture", DataContract("external.snapshot"),
        (("values", table),), coverage=SnapshotCoverage("complete"))
    incoming = prepare_input(snapshot, DataContract("dataset.snapshot"))
    catalog = operation_catalog()
    source = catalog.bind_source("cbr.corporate_lending.corp_debt_a", format="xlsx")
    with pytest.raises(HandoffError, match="source.input_context_missing"):
        source.bind("dataset.write_snapshot", inputs={"snapshot": incoming})
    store = MemoryDatasetStore(provider_id="test", scope_id="context")
    generic = catalog.bind("dataset.write_snapshot", inputs={"snapshot": incoming}).invoke(store=store)
    assert generic.outcome == "succeeded", generic.diagnostics
    assert store.read_snapshot(generic.value.reference) == snapshot


def test_source_bound_storage_admits_qualified_prepared_value_before_commit(payload):
    from stratbox.core.execution import ExecutionContext, InMemorySink
    from stratbox.core.storage.datasets.memory import MemoryDatasetStore
    catalog = operation_catalog()
    source, result = _snapshot(catalog, payload)
    store = MemoryDatasetStore(provider_id="test", scope_id="qualified")
    sink = InMemorySink()
    written = source.bind("dataset.write_snapshot", inputs={
        "snapshot": project_output(result, "snapshot")}).invoke(
            store=store, context=ExecutionContext(sink=sink))
    assert written.outcome == "succeeded", written.diagnostics
    assert any(effect.kind == "dataset.write" and effect.state == "confirmed" for effect in written.effects)
    assert store.read_snapshot(written.value.reference) == result.value
    assert sink.events[-1].outcome == "succeeded"


def test_known_issue_changed_by_preparation_is_rejected_before_writer(payload, monkeypatch):
    from stratbox.core.execution import ExecutionContext, InMemorySink, run
    from stratbox.core.storage.datasets.memory import MemoryDatasetStore
    from stratbox.shared.data.snapshots import DatasetSnapshot, TypedTable
    catalog = operation_catalog()
    source, encoded = _snapshot(catalog, payload)
    snapshot = encoded.value
    metadata = snapshot.table("metadata")
    wrong_row = (*metadata.rows[0][:1], "2026-09", *metadata.rows[0][2:])
    wrong = DatasetSnapshot.build(snapshot.manifest.dataset_id, "wrong-issue", snapshot.manifest.contract,
        tuple((name, TypedTable(metadata.schema, (wrong_row,)) if name == "metadata" else table)
              for name, table in snapshot.tables), coverage=snapshot.manifest.coverage,
        inputs=snapshot.manifest.inputs)
    call = source.bind("dataset.write_snapshot", inputs={"snapshot": project_output(encoded, "snapshot")})

    class CountedStore(MemoryDatasetStore):
        calls = 0
        def write_snapshot(self, value, **options):
            self.calls += 1
            return super().write_snapshot(value, **options)

    store = CountedStore(provider_id="test", scope_id="before-commit")
    def prepare_wrong_issue(request, *, context=None, store=None):
        def work(req, invocation):
            invocation.admit_prepared(wrong)
            return store.write_snapshot(wrong)
        return run(call.definition, request, work, context=context, providers={"dataset_writer": store})
    monkeypatch.setattr(type(catalog), "resolve", lambda self, operation_id:
        (call.definition, prepare_wrong_issue, None))
    sink = InMemorySink()
    result = call.invoke(store=store, context=ExecutionContext(sink=sink))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "source.output_issue_mismatch"
    assert result.diagnostics[0].stage == "precommit_admission"
    assert store.calls == 0 and not result.effects
    assert sink.events[-1].outcome == "failed"


def test_undeclared_field_names_and_transport_labels_are_not_source_claims():
    @dataclass(frozen=True)
    class ExternalRecord:
        series_id: str
        source_id: str
    assert not value_context(ExternalRecord("foreign", "also_foreign")).source_ids
    assert not value_context(SourcePayload(b"x", "text/plain", "transport-label")).source_ids
