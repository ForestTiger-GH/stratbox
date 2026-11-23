"""Source coordinates retain their pairing and govern qualified result admission."""
from dataclasses import replace

import pytest

from stratbox.core.execution import ExecutionContext, OperationDefinition, run
from stratbox.core.execution.calls import SourceResultAdmission
from stratbox.core.execution.value_context import value_context, validate_value_context_links
from stratbox.core.registry import operation_catalog
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.operations import OperationSemantics, OutputPort, ProcessingStage
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.snapshots import DatasetSnapshot, SnapshotCoverage
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse, ValueContext
from stratbox.shared.source_publications import SourceAssetIdentity


PRIMARY = "cbr.corporate_lending.corp_debt_a"
AUXILIARY = "frg.regional.issuance"


def test_repeated_source_uses_preserve_source_issue_edition_and_collection_position():
    values = (
        SourceUse(SourceCoordinate("example.a", source_group_id="loans", issue_id="2026-09",
            layout_edition="alpha"), "before"),
        SourceUse(SourceCoordinate("example.b", source_group_id="deposits", issue_id="2026-10",
            layout_edition="beta"), "after"),
    )
    context = value_context(values)
    assert context.uses == values
    assert [(use.coordinate.source_id, use.coordinate.issue_id, use.coordinate.layout_edition,
             use.coordinate.source_group_id, use.input_role) for use in context.uses] == [
        ("example.a", "2026-09", "alpha", "loans", "before"),
        ("example.b", "2026-10", "beta", "deposits", "after")]
    asset = SourceAssetIdentity(PRIMARY, "2026-09", "main")
    repeated = value_context((asset, asset)).uses
    assert len(repeated) == 2
    assert repeated[0].input_role != repeated[1].input_role


def test_two_releases_and_two_source_groups_remain_distinct_after_snapshot_roundtrip():
    uses = (
        SourceUse(SourceCoordinate("example.a", source_group_id="stock", issue_id="2026-09"), "before"),
        SourceUse(SourceCoordinate("example.a", source_group_id="flow", issue_id="2026-10"), "after"),
    )
    batch = ObservationBatch("example", 1, "capture", (), (), uses)
    snapshot = observation_snapshot(batch)
    assert value_context(batch) == value_context(snapshot) == ValueContext(uses)
    partial = DatasetSnapshot(snapshot.manifest, (("metadata", snapshot.table("metadata")),))
    assert not partial.complete
    assert value_context(partial) == ValueContext(uses)


def _admit(value, policy, *, scope="source", auxiliary_sources=()):
    definition = OperationDefinition("context.result", "result", str, type(value),
        processing=OperationSemantics((ProcessingStage.VALIDATE,), outputs=(OutputPort("value", DataContract("context.value"),
            source_policy=policy),), summary="Admit a source-qualified result."))
    sources = operation_catalog().source_catalog()
    primary = sources.source(PRIMARY)
    admission = SourceResultAdmission(definition, PRIMARY, primary.family_id, sources,
        auxiliary_sources=auxiliary_sources, context_scope=scope)
    return run(definition, "request", lambda request, invocation: value,
        context=ExecutionContext(result_admissions=(admission,)))


@pytest.mark.parametrize("policy, outcome", [
    ("primary_source_required", "failed"),
    ("source_optional", "succeeded"),
    ("source_inapplicable", "succeeded"),
])
def test_output_policy_explicitly_controls_sourceless_retained_result(policy, outcome):
    snapshot = DatasetSnapshot.build("unqualified", "capture", DataContract("external.unqualified"),
        (), coverage=SnapshotCoverage("unknown"))
    result = _admit(snapshot, policy)
    assert result.outcome == outcome, result.diagnostics
    if outcome == "failed":
        assert result.value is None
        assert result.diagnostics[0].code == "source.output_context_missing"


def test_technical_control_value_requires_an_explicit_source_inapplicable_policy():
    assert _admit("ready", "source_inapplicable").outcome == "succeeded"
    rejected = _admit("ready", "primary_source_required")
    assert rejected.outcome == "failed"
    assert rejected.diagnostics[0].code == "source.output_context_missing"


def test_cross_family_support_is_permitted_only_in_its_named_role():
    primary = SourceUse(SourceCoordinate(PRIMARY), "primary")
    reference = SourceUse(SourceCoordinate(AUXILIARY), "reference")
    permitted = (("reference", (AUXILIARY,)),)
    accepted = _admit((primary, reference), "source_collection", auxiliary_sources=permitted)
    assert accepted.outcome == "succeeded", accepted.diagnostics
    rejected = _admit((primary, replace(reference, input_role="unrelated")), "source_collection",
        auxiliary_sources=permitted)
    assert rejected.outcome == "failed"
    assert rejected.diagnostics[0].code == "source.auxiliary_role_mismatch"


def test_family_scope_rejects_mixed_families_even_when_expected_family_is_present():
    value = (SourceUse(SourceCoordinate(PRIMARY)), SourceUse(SourceCoordinate(AUXILIARY)))
    result = _admit(value, "source_collection", scope="family")
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "source.output_group_mismatch"


def test_context_adapter_unknown_dataclass_field_fails_static_validation(monkeypatch):
    from stratbox.core.execution import value_context as public_reader
    from importlib import import_module
    module = import_module(public_reader.__module__)
    monkeypatch.setattr(module, "_adapters", lambda: {"types": {
        "stratbox.shared.source_publications.SourceAssetIdentity": {
            "uses": [{"source": "unknown_field"}]}}, "tables": {}})
    with pytest.raises(ValueError, match="registry.value_context_path_invalid"):
        validate_value_context_links()


def test_contextless_dataframe_collection_has_a_normal_rejection():
    import pandas as pd
    result = _admit(pd.DataFrame({"value": [27]}), "source_collection")
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "source.output_context_missing"


def test_adapter_exception_message_cannot_create_an_invalid_diagnostic(monkeypatch):
    import pandas as pd
    from importlib import import_module
    module = import_module("stratbox.core.execution.value_context")
    original = module.value_context
    output = pd.DataFrame({"value": [27]})
    def read(value, contract=None):
        if value is output:
            raise ValueError("Unqualified field text with spaces and unexpected details")
        return original(value, contract)
    monkeypatch.setattr(module, "value_context", read)
    result = _admit(output, "source_optional")
    assert result.outcome == "failed" and result.value is None
    assert result.diagnostics[0].code == "source.output_context_invalid"


def test_context_adapter_unknown_table_column_fails_static_validation(monkeypatch):
    from importlib import import_module
    module = import_module("stratbox.core.execution.value_context")
    from stratbox.shared.data.workbooks import _META
    monkeypatch.setattr(module, "_adapters", lambda: {"types": {}, "tables": {
        _META.contract: {"schema_ref": "stratbox.shared.data.workbooks:_META",
            "uses": [{"source": "missing_column"}]}}})
    with pytest.raises(ValueError, match="registry.value_context_column_invalid"):
        validate_value_context_links()


def test_new_metadata_edition_does_not_reuse_an_older_context_adapter():
    from stratbox.core.execution import HandoffError, prepare_input
    from stratbox.domains.cbr.tables.statistics.snapshots import _META
    from stratbox.shared.data.snapshots import TypedTable
    from stratbox.shared.identity import ByteIdentity
    schema = replace(_META, contract=replace(_META.contract, version=_META.contract.version + 1))
    identity = ByteIdentity.of(b"original")
    table = TypedTable(schema, ((PRIMARY, "2026-09", identity.sha256,
        identity.size, "profile", 1, "main"),))
    snapshot = DatasetSnapshot.build("source", "capture", DataContract("external.snapshot"),
        (("metadata", table),), coverage=SnapshotCoverage("complete"))
    assert value_context(snapshot).source_ids == ()
    source = operation_catalog().bind_source(PRIMARY, format="xlsx")
    with pytest.raises(HandoffError, match="source.context_schema_mismatch"):
        source.bind("dataset.write_snapshot", inputs={
            "snapshot": prepare_input(snapshot, DataContract("dataset.snapshot"))})
