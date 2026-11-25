"""Generic stage edges retain concrete schemas and enforce semantic restrictions."""
from dataclasses import replace

import pytest

from stratbox.capabilities.catalog import CatalogContribution, CatalogSnapshot
from stratbox.capabilities.manifest import catalog_snapshot
from stratbox.capabilities.model import (AcceptanceContract, CommandDefinition, OperationDefinition, ScenarioDefinition, GraphBody, Call,
    InputRef, OutputRef, PortContract)
from stratbox.core.execution.handoff import PreparedInput
from stratbox.core.storage.datasets import MemoryDatasetStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.assessment import ValueEvidence
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import DatasetSnapshot, ColumnSchema, ScalarType, TableSchema, TypedTable, SnapshotCoverage


def supplied_value(request, invocation):
    return request["value"]


def optional_none(request, invocation):
    return {"data": 7, "preview": None}


def partial_value(request, invocation):
    from stratbox.core.execution.runner import Completion
    return Completion(7, "partial", "test.partial")


def test_source_specific_snapshot_flows_through_generic_ingestion_without_schema_loss():
    source_schema = DataContract("test.source.snapshot", 3, DataRole.EXTRACTS)
    table = TypedTable(TableSchema(DataContract("test.source.rows", 2, DataRole.EXTRACTS),
        (ColumnSchema("source_value", ScalarType.TEXT),)), (("withheld",),))
    source = DatasetSnapshot.build("test.source", "2026-01", source_schema, (("rows", table),),
        coverage=SnapshotCoverage("partial", "One retained publisher table."))
    typed = PortContract(source_schema, DatasetSnapshot)
    producer = CommandDefinition("test.source_snapshot", __name__ + ":supplied_value",
        inputs={"value": typed}, outputs={"value": typed})
    source_operation = OperationDefinition("test.source_snapshot_operation", GraphBody((
        Call("source", producer.id, {"value": source}),
    ), {"value": OutputRef("source")}), outputs={"value": typed})
    from stratbox.capabilities.commands.stages import DATASET_REFERENCE
    scenario = ScenarioDefinition("test.ingest_specific", GraphBody((
        Call("source", source_operation.id),
        Call("ingest", "ingest.observations", {"value": OutputRef("source")}),
    ), {"reference": OutputRef("ingest")}), outputs={"reference": DATASET_REFERENCE},
        effects=frozenset({"dataset.write"}))
    catalog = catalog_snapshot().overlay(CatalogContribution(definitions=(producer, source_operation, scenario)))
    store = MemoryDatasetStore(provider_id="test", scope_id="specific")
    with StrategyBox(capabilities=catalog, providers={"dataset_writer": store, "dataset_reader": store}) as box:
        result = box.invoke(scenario.id, timeout=5)
        assert result.outcome == "succeeded", result.diagnostics
        reference = result.output("reference")
        assert reference.identity == source.identity
        restored = box.invoke("query.dataset", inputs={"reference": reference}, timeout=5)
        assert restored.outcome == "succeeded", restored.diagnostics
        assert restored.output("value") == source
        assert restored.output("value").manifest.contract == source_schema
        # The same wildcard also admits an explicitly qualified retained input.
        direct = box.invoke("ingest.observations", inputs={"value": PreparedInput(source_schema, source)}, timeout=5)
        assert direct.outcome == "succeeded", direct.diagnostics
        assert direct.output("value").identity == source.identity


def test_wildcard_preserves_qualification_and_outcome_requirements():
    schema = DataContract("test.source.native", 4, DataRole.EXTRACTS)
    evidence = ValueEvidence(frozenset({"test.validated"}))
    value = Representation("test.native", 1, "text/plain", b"native", "utf-8", evidence)
    generic_input = PortContract(value_type=Representation, qualifications=frozenset({"test.validated"}))
    command = CommandDefinition("test.generic_consumer", __name__ + ":supplied_value",
        inputs={"value": generic_input}, outputs={"value": PortContract(schema, Representation)})
    with StrategyBox(capabilities=CatalogSnapshot(definitions=(command,))) as box:
        accepted = PreparedInput(schema, value, qualifications=frozenset({"test.validated"}))
        result = box.invoke(command.id, inputs={"value": accepted}, timeout=5)
        assert result.outcome == "succeeded" and result.output("value") == value
        unqualified = PreparedInput(schema, value)
        with pytest.raises(ValueError, match="qualification"):
            box.invoke(command.id, inputs={"value": unqualified}, timeout=5)
        partial = replace(accepted, outcome="partial")
        with pytest.raises(ValueError, match="outcome"):
            box.invoke(command.id, inputs={"value": partial}, timeout=5)


def test_retained_value_assessments_survive_a_fresh_direct_invocation():
    schema = DataContract("test.retained.native", 2, DataRole.EXTRACTS)
    value = Representation("test.native", 1, "text/plain", b"native", "utf-8",
        ValueEvidence(frozenset({"test.validated"})))
    command = CommandDefinition("test.retained_consumer", __name__ + ":supplied_value",
        inputs={"value": PortContract(schema, Representation, qualifications=frozenset({"test.validated"}))},
        outputs={"value": PortContract(schema, Representation)})
    with StrategyBox(capabilities=CatalogSnapshot(definitions=(command,))) as box:
        result = box.invoke(command.id, inputs={"value": value}, timeout=5)
        assert result.outcome == "succeeded" and result.output("value") == value


def test_explicit_none_in_optional_success_output_is_absent():
    command = CommandDefinition("test.optional_none", __name__ + ":optional_none", outputs={
        "data": PortContract(DataContract("test.data"), int),
        "preview": PortContract(DataContract("test.preview"), str, required=False)})
    with StrategyBox(capabilities=CatalogSnapshot(definitions=(command,))) as box:
        result = box.invoke(command.id, timeout=5)
        assert result.outcome == "succeeded", result.diagnostics
        assert result.output("data") == 7 and "preview" not in result.outputs


def test_partial_command_value_cannot_escape_success_only_operation_output():
    schema = DataContract("test.partial.data")
    producer = CommandDefinition("test.partial_value", __name__ + ":partial_value",
        outputs={"value": PortContract(schema, int, outcomes=frozenset({"succeeded", "partial"}))},
        acceptance=AcceptanceContract(partial_allowed=True))
    operation = OperationDefinition("test.success_only", GraphBody((Call("work", producer.id),),
        {"data": OutputRef("work")}), outputs={"data": PortContract(schema, int)},
        acceptance=AcceptanceContract(partial_allowed=True))
    with StrategyBox(capabilities=CatalogSnapshot(definitions=(producer, operation))) as box:
        result = box.invoke(operation.id, timeout=5)
        assert "data" not in result.outputs
        assert next(iter(result.results.values())).outcome == "partial"


def test_operation_input_schema_is_enforced_before_a_wildcard_child():
    source_schema, other_schema = DataContract("test.expected.input"), DataContract("test.other.input")
    result_schema = DataContract("test.result")
    command = CommandDefinition("test.wildcard_echo", __name__ + ":supplied_value",
        inputs={"value": PortContract(value_type=int)}, outputs={"value": PortContract(result_schema, int)})
    operation = OperationDefinition("test.typed_operation", GraphBody((
        Call("work", command.id, {"value": InputRef("value")}),
    ), {"value": OutputRef("work")}), inputs={"value": PortContract(source_schema, int)},
        outputs=command.outputs)
    with StrategyBox(capabilities=CatalogSnapshot(definitions=(command, operation))) as box:
        valid = box.invoke(operation.id, inputs={"value": PreparedInput(source_schema, 7)}, timeout=5)
        assert valid.outcome == "succeeded" and valid.output("value") == 7
        with pytest.raises(ValueError, match="schema"):
            box.invoke(operation.id, inputs={"value": PreparedInput(other_schema, 7)}, timeout=5)
