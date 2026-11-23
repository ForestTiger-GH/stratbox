"""A malformed dependent branch cannot terminate independent admitted runs."""
from dataclasses import dataclass

from stratbox.composition import (
    Condition, InputRef, MapStep, OperationStep, PlanOutputRef,
    ScenarioDefinition, compile_workflow,
)
from stratbox.core.execution import OperationDefinition, OperationSemantics, OutputPort, ProcessingStage, run
from stratbox.core.execution.session import ExecutionSession, ExecutionSettings
from stratbox.operations.catalog import OperationCatalog, OperationRef
from stratbox.shared.data.processing import DataContract
from stratbox.shared.evidence import SourcePayload


@dataclass(frozen=True)
class Request:
    value: int = 1


DEFINITION = OperationDefinition("test.admission", "test.admission", Request, int,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        parameters=("value",), outputs=(OutputPort("value", DataContract("test.number")),),
        summary="Exercise graph admission without external effects."))


def operation(request, *, context=None):
    return run(DEFINITION, request, lambda req, inv: req.value, context=context)


def catalog():
    return OperationCatalog((OperationRef("test.admission", __name__ + ":operation", definition=DEFINITION),))


def independent():
    return ScenarioDefinition("independent", (OperationStep("value", "test.admission", parameters={"value": 7}),),
                              {"answer": PlanOutputRef("value")})


def test_skipped_parameter_producer_blocks_dependent_without_stopping_coordinator():
    definition = ScenarioDefinition("conditional", (
        OperationStep("condition", "test.admission"),
        OperationStep("skipped", "test.admission", condition=Condition("condition", port="value", equals=2)),
        OperationStep("dependent", "test.admission", parameters={"value": PlanOutputRef("skipped")}),
    ))
    operations = catalog()
    with ExecutionSession(operations, settings=ExecutionSettings(max_workers=1)) as session:
        conditional = session.submit(compile_workflow(definition, operations))
        other = session.submit(compile_workflow(independent(), operations))
        result = conditional.result(5)
        assert result.outcome == "failed"
        assert next(task for task in result.tasks if task.task_id.endswith("dependent")).state in {"failed", "blocked"}
        assert other.result(5).output("answer") == 7


def test_impossible_dynamic_resource_fails_item_without_stopping_other_run():
    body = ScenarioDefinition("body", (
        OperationStep("large", "test.admission", parameters={"value": InputRef("item")}, resources={"worker": 99}),
    ), {"value": PlanOutputRef("large")}, {"item": None})
    definition = ScenarioDefinition("mapped", (MapStep("items", body, (1,)),))
    operations = catalog()
    with ExecutionSession(operations, settings=ExecutionSettings(max_workers=1)) as session:
        large = session.submit(compile_workflow(definition, operations))
        small = session.submit(compile_workflow(independent(), operations))
        assert large.result(5).outcome == "failed"
        assert small.result(5).output("answer") == 7


@dataclass(frozen=True)
class BlobRequest:
    size: int


@dataclass(frozen=True)
class SummaryRequest:
    data: SourcePayload


BLOB = DataContract("test.blob")
NUMBER = DataContract("test.number")
BLOBS = OperationDefinition("test.blob", "test.blob", BlobRequest, SourcePayload,
    processing=OperationSemantics((ProcessingStage.CALCULATE,), parameters=("size",),
        outputs=(OutputPort("value", BLOB),), summary="Produce a bounded temporary blob."))
from stratbox.core.execution import InputPort
SUMMARIZE = OperationDefinition("test.summarize", "test.summarize", SummaryRequest, int,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        inputs=(InputPort("blob", BLOB, "data"),), outputs=(OutputPort("value", NUMBER),),
        summary="Summarize temporary bytes into a small result."))


def blob(request, *, context=None):
    return run(BLOBS, request, lambda req, inv: SourcePayload(b"x" * req.size, "application/octet-stream"), context=context)


def summarize(request, *, context=None):
    return run(SUMMARIZE, request, lambda req, inv: len(req.data.data), context=context)


def test_map_releases_intermediate_storage_after_last_local_consumer():
    from stratbox.composition import CollectSpec, CollectStep
    operations = OperationCatalog((
        OperationRef("test.blob", __name__ + ":blob", definition=BLOBS),
        OperationRef("test.summarize", __name__ + ":summarize", definition=SUMMARIZE),
    ))
    body = ScenarioDefinition("body", (
        OperationStep("blob", "test.blob", parameters={"size": InputRef("item")}),
        OperationStep("summary", "test.summarize", inputs={"blob": PlanOutputRef("blob")}),
    ), {"value": PlanOutputRef("summary")}, {"item": None})
    definition = ScenarioDefinition("stream", (
        MapStep("items", body, (4096, 4096, 4096), window=1),
        CollectStep("join", CollectSpec((PlanOutputRef("items"),), DataContract("test.numbers"), NUMBER)),
    ), {"values": PlanOutputRef("join")})
    with ExecutionSession(operations, settings=ExecutionSettings(max_workers=1, map_window=1, retained_bytes=5000)) as session:
        result = session.submit(compile_workflow(definition, operations)).result(5)
        assert result.outcome == "succeeded"
        assert result.output("values") == (4096, 4096, 4096)
        assert session.ledger.snapshot().peak["retained_bytes"] <= 5000
        # Releasing runtime capacity does not forge a successful empty result.
        assert result.results["stream/items/0/blob"].value.data == b"x" * 4096


RAW_BYTES = OperationDefinition("test.raw_bytes", "test.raw_bytes", BlobRequest, bytes,
    processing=OperationSemantics((ProcessingStage.CALCULATE,), parameters=("size",),
        outputs=(OutputPort("value", BLOB),), summary="Return raw bytes for physical retention accounting."))


def raw_bytes(request, *, context=None):
    return run(RAW_BYTES, request, lambda req, inv: b"x" * req.size, context=context)


def test_retention_quota_measures_raw_payload_not_its_digest_descriptor():
    operations = OperationCatalog((OperationRef("test.raw_bytes", __name__ + ":raw_bytes", definition=RAW_BYTES),))
    definition = ScenarioDefinition("raw", (OperationStep("blob", "test.raw_bytes", parameters={"size": 4096}),),
                                    {"value": PlanOutputRef("blob")})
    with ExecutionSession(operations, settings=ExecutionSettings(retained_bytes=1024)) as session:
        result = session.submit(compile_workflow(definition, operations)).result(5)
        assert result.outcome == "failed"
        assert any(d.code == "resource.retained_bytes" for r in result.results.values() for d in r.diagnostics)
