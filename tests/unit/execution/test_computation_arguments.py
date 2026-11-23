"""Exact consumed values and semantic parameters qualify every computation."""

from dataclasses import dataclass, replace
from datetime import date
import json

from stratbox.core.execution import ExecutionContext, OperationDefinition, run
from stratbox.shared.data.observations import (
    MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef,
)
from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot
from stratbox.shared.data.operations import InputPort, OperationSemantics, OutputPort, ProcessingStage
from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity


@dataclass(frozen=True)
class Request:
    values: tuple[str, ...]
    factor: int = 2


DEFINITION = OperationDefinition("arguments.consume", "consume", Request, str,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        inputs=(InputPort("items", DataContract("arguments.values"), "values"),),
        parameters=("factor",), outputs=(OutputPort("result", DataContract("arguments.result")),),
        summary="Consume the exact ordered collection with an applied factor."))


def consume(request, *, context=None, explicit_record=True):
    def work(req, invocation):
        if explicit_record:
            # A handler may report incomplete or incorrectly repeated metadata.
            # The executor still captures actual arguments and request defaults.
            invocation.record(ByteIdentity.of(b"same output"))
        return "same output"
    return run(DEFINITION, request, work, context=context)


def test_inputs_preserve_order_multiplicity_and_values_without_handler_bookkeeping():
    cases = (Request(("a",)), Request(("a", "a")), Request(("a", "b")), Request(("b", "a")))
    results = tuple(consume(request) for request in cases)
    assert all(result.outcome == "succeeded" for result in results)
    assert len({result.computation.computation_id for result in results}) == len(cases)
    assert len({result.computation.output for result in results}) == 1


def test_actual_parameters_defaults_and_arguments_are_saved_in_manifest():
    implicit = consume(Request(("a",)))
    explicit = consume(Request(("a",), factor=2))
    changed = consume(Request(("a",), factor=3))
    assert implicit.computation.computation_id == explicit.computation.computation_id
    assert implicit.computation.computation_id != changed.computation.computation_id
    manifest = json.loads(implicit.computation.version.manifest)
    assert manifest["parameters"] == {"factor": 2}
    assert manifest["arguments"]["items"]["contract"]["schema_id"] == "arguments.values"
    assert manifest["arguments"]["items"]["identity"]["sha256"]


def test_declared_output_gets_computation_even_when_handler_omits_record():
    first = consume(Request(("a",)), explicit_record=False)
    changed = consume(Request(("b",)), explicit_record=False)
    assert first.computation is not None
    assert first.computation.computation_id != changed.computation.computation_id


def batch(value):
    receipt = UsedInputReceipt.for_payload(SourcePayload(b"same original"), "source")
    return ObservationBatch("cbr.service_network.offices", 1, "2026-11-01", (
        Observation(SubjectRef("territory", "RU"), MetricRef("offices", "unit", "count"),
            PeriodRef("as_of", as_of=date(2026, 11, 1)), (), "all", value,
            "reported", "same-source"),), (receipt,))


def test_cbr_observation_snapshot_key_tracks_consumed_values_and_dataset_revision():
    from stratbox.domains.cbr.operations.service_network.observation_definitions import SnapshotOfficeObservationsRequest
    from stratbox.domains.cbr.operations.service_network.observation_operations import snapshot_observations

    def snapshot(value, revision="retained"):
        result = snapshot_observations(SnapshotOfficeObservationsRequest(value, "offices", revision))
        assert result.outcome == "succeeded", result.diagnostics
        return result

    first = snapshot(batch(1))
    changed = snapshot(batch(2))
    revision = snapshot(batch(1), "another-release")
    restored = observations_from_snapshot(observation_snapshot(batch(1)))
    replay = snapshot(restored)
    assert first.computation.computation_id != changed.computation.computation_id
    assert first.computation.computation_id != revision.computation.computation_id
    assert first.computation.computation_id == replay.computation.computation_id


def test_independent_dependency_editions_survive_identical_payload_bytes():
    identity = ByteIdentity.of(b"identical bytes")
    direct = UsedInputReceipt("source", identity, "application/json", "inline", "example")

    def perform(revision):
        dependency = UsedInputReceipt("reference", identity, "application/json", "inline", "example",
            version=ByteIdentity.of(revision))
        def work(req, invocation):
            invocation.use(direct)
            invocation.depend(dependency)
            invocation.record(ByteIdentity.of(b"output"))
            return "same output"
        return run(DEFINITION, Request(("a",)), work,
            context=ExecutionContext(input_receipts=(dependency,)))

    before, after = perform(b"edition-a"), perform(b"edition-b")
    assert len(before.computation.inputs) == 2
    assert before.computation.computation_id != after.computation.computation_id


def test_unused_environment_reference_does_not_qualify_a_computation():
    dependency = UsedInputReceipt("unused_reference", ByteIdentity.of(b"reference"),
        "application/json", "reference_only", version=ByteIdentity.of(b"reference-definition"))
    direct = consume(Request(("a",)))
    supplied = consume(Request(("a",)), context=ExecutionContext(input_receipts=(dependency,)))
    assert supplied.computation.computation_id == direct.computation.computation_id
    assert dependency in supplied.used_inputs
    assert dependency not in supplied.computation.inputs


def test_payload_interpretation_qualifies_identical_bytes_without_handler_receipts():
    definition = OperationDefinition("arguments.payload", "interpret", SourcePayload, str,
        processing=OperationSemantics((ProcessingStage.EXTRACT,),
            inputs=(InputPort("payload", DataContract("arguments.payload")),),
            outputs=(OutputPort("result", DataContract("arguments.result")),),
            summary="Interpret exact bytes under their declared source and encoding."))
    cases = (SourcePayload(b"same", "text/plain", "one", charset="utf-8"),
             SourcePayload(b"same", "text/plain", "two", charset="utf-8"),
             SourcePayload(b"same", "application/json", "one", charset="utf-8"),
             SourcePayload(b"same", "text/plain", "one", charset="utf-16"))
    results = tuple(run(definition, request, lambda req, invocation: "constant") for request in cases)
    assert all(result.outcome == "succeeded" for result in results)
    assert len({result.computation.computation_id for result in results}) == len(cases)
    assert len({request.identity for request in cases}) == 1


def test_encoded_schema_and_media_qualify_byte_identical_representations():
    definition = OperationDefinition("arguments.representation", "read", Representation, str,
        processing=OperationSemantics((ProcessingStage.EXTRACT,),
            inputs=(InputPort("representation", DataContract("arguments.representation")),),
            outputs=(OutputPort("result", DataContract("arguments.result")),),
            summary="Read a representation using its schema, media and encoding."))
    cases = (Representation("rows", 1, "text/csv", b"same", encoding="utf-8"),
             Representation("columns", 1, "text/csv", b"same", encoding="utf-8"),
             Representation("rows", 2, "text/csv", b"same", encoding="utf-8"),
             Representation("rows", 1, "text/plain", b"same", encoding="utf-8"))
    results = tuple(run(definition, request, lambda req, invocation: "constant") for request in cases)
    assert all(result.outcome == "succeeded" for result in results)
    assert len({result.computation.computation_id for result in results}) == len(cases)


@dataclass(frozen=True)
class TracedValue:
    values: tuple[str, ...]
    evidence: ComputationReceipt | None = None


def test_parent_execution_history_never_changes_the_same_consumed_content():
    previous = consume(Request(("previous",))).computation
    parent = consume(Request(("parent",))).computation
    with_history = replace(previous, parents=(("upstream", parent),))
    definition = OperationDefinition("arguments.traced", "consume", TracedValue, str,
        processing=OperationSemantics((ProcessingStage.CALCULATE,),
            inputs=(InputPort("value", DataContract("arguments.traced")),),
            outputs=(OutputPort("result", DataContract("arguments.result")),),
            summary="Compute from supplied content independently of execution ancestry."))
    def evaluate(value):
        result = run(definition, value, lambda req, invocation: "constant")
        assert result.outcome == "succeeded", result.diagnostics
        return result.computation.computation_id
    assert evaluate(TracedValue(("a",))) == evaluate(TracedValue(("a",), previous))
    assert evaluate(TracedValue(("a",), previous)) == evaluate(TracedValue(("a",), with_history))
    assert evaluate(TracedValue(("a",), previous)) != evaluate(TracedValue(("b",), previous))
