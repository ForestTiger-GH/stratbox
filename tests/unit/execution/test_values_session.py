"""Command acceptance and returned result lifetime use the actual coordinator."""
import pytest

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import (
    Call, CommandDefinition, GraphBody, InputRef, OperationDefinition,
    OutputRef, PortContract, ScenarioDefinition,
)
from stratbox.composition import prepare_invocation
from stratbox.core.execution.session import ExecutionSession, ExecutionSettings
from stratbox.sdk.bootstrap import CapabilityRuntimeCatalog
from stratbox.shared.data.processing import DataContract

_consumer_calls = []
BYTES = PortContract(DataContract("test.owned-bytes"), bytes)
NUMBER = PortContract(DataContract("test.owned-count"), int)


def blob(values, invocation):
    return b"owned" * 50


def count(values, invocation):
    _consumer_calls.append(len(values["data"]))
    return len(values["data"])


def mutable(values, invocation):
    return {"rows": [1, 2]}


def runtime():
    definitions = (
        CommandDefinition("owned.blob.command", __name__ + ":blob", outputs={"value": BYTES}),
        CommandDefinition("owned.count.command", __name__ + ":count", inputs={"data": BYTES}, outputs={"value": NUMBER}),
        OperationDefinition("owned.blob", GraphBody((Call("blob", "owned.blob.command"),),
            {"value": OutputRef("blob")}), outputs={"value": BYTES}),
        OperationDefinition("owned.count", GraphBody((Call("count", "owned.count.command", {"data": InputRef("data")}),),
            {"value": OutputRef("count")}), inputs={"data": BYTES}, outputs={"value": NUMBER}),
        ScenarioDefinition("owned.chain", GraphBody((Call("blob", "owned.blob"),
            Call("count", "owned.count", {"data": OutputRef("blob")})), {"value": OutputRef("count")}),
            outputs={"value": NUMBER}),
    )
    snapshot = CatalogSnapshot(definitions)
    return snapshot, CapabilityRuntimeCatalog(snapshot)


def test_rejected_staging_candidate_is_not_exposed_to_downstream_consumer():
    _consumer_calls.clear()
    snapshot, catalog = runtime()
    settings = ExecutionSettings(max_workers=1, staging_bytes=100, retained_bytes=4096)
    with ExecutionSession(catalog, settings=settings) as session:
        result = session.run(prepare_invocation("owned.chain", snapshot, catalog))
        assert result.outcome == "failed"
        assert "resource.staging_bytes" in result.diagnostics
        assert not _consumer_calls
        assert not result.outputs
        assert session.ledger.snapshot().occupied.get("staging_bytes", 0) == 0
        result.close()


def test_result_and_reader_keep_capacity_after_run_and_session_close():
    snapshot, catalog = runtime()
    session = ExecutionSession(catalog, settings=ExecutionSettings(max_workers=1))
    result = session.run(prepare_invocation("owned.blob.command", snapshot, catalog))
    assert result.outcome == "succeeded"
    assert session.ledger.snapshot().occupied["retained_bytes"] >= 250
    lease = result.read("value")
    session.close()
    result.close()
    assert lease.value == b"owned" * 50
    assert session.ledger.snapshot().occupied["retained_bytes"] >= 250
    lease.close()
    assert session.ledger.snapshot().occupied["retained_bytes"] == 0
    with pytest.raises(RuntimeError, match="result.closed"):
        result.output("value")


def test_public_result_views_and_leases_preserve_independent_mutable_consumers():
    command = CommandDefinition("owned.mutable", __name__ + ":mutable",
        outputs={"value": PortContract(DataContract("test.mutable"), dict)})
    snapshot = CatalogSnapshot((command,))
    catalog = CapabilityRuntimeCatalog(snapshot)
    with ExecutionSession(catalog) as session:
        result = session.run(prepare_invocation(command.capability_id, snapshot, catalog))
        assert result.outcome == "succeeded"
        result.outputs["value"].value["rows"].append(3)
        next(iter(result.results.values())).value["rows"].append(4)
        next(iter(result.attempts.values()))[0].value["rows"].append(5)
        next(iter(result.scope_outputs.values()))["value"]["rows"].append(6)
        with result.read("value") as leased:
            leased["rows"].append(7)
            assert result.output("value") == {"rows": [1, 2]}
        assert result.output("value") == {"rows": [1, 2]}
        result.close()
        assert session.ledger.snapshot().occupied["retained_bytes"] == 0
