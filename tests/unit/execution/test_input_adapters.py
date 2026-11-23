"""Inline, retained and collection adapters preserve exact input meaning."""

from dataclasses import dataclass, replace

import pytest

from stratbox.core.execution import ExecutionContext, OperationDefinition, run
from stratbox.core.execution.handoff import (
    HandoffError, PreparedInput, adapt_input, artifact_input, bind_request,
    collect_inputs, prepare_input, project_output, reference_output,
)
from stratbox.shared.data.operations import InputPort, OperationSemantics, OutputPort, ProcessingStage
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.materials import MaterialArtifact


VALUE = DataContract("adapters.value", role=DataRole.EXTRACTS)
VALUES = DataContract("adapters.values", role=DataRole.EXTRACTS)


@dataclass(frozen=True)
class ValuesRequest:
    values: tuple[str, ...]


CONSUMER = OperationDefinition("adapters.consume", "v1", ValuesRequest, str,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        inputs=(InputPort("items", VALUES, "values"),),
        outputs=(OutputPort("joined", DataContract("adapters.joined")),),
        summary="Join explicitly selected input values."))


def produce(text):
    definition = OperationDefinition("adapters.produce", "v1", str, str,
        processing=OperationSemantics((ProcessingStage.EXTRACT,),
            outputs=(OutputPort("value", VALUE),), summary="Prepare a value."))

    def work(value, invocation):
        invocation.use(UsedInputReceipt.for_payload(SourcePayload(value.encode(), "text/plain"), "source"))
        invocation.record(ByteIdentity.of(value.encode()))
        return value

    return run(definition, text, work)


def consume(request, *, context=None):
    def work(value, invocation):
        result = "|".join(value.values)
        invocation.record(ByteIdentity.of(result.encode()))
        return result
    return run(CONSUMER, request, work, context=context)


def test_inline_payload_has_exact_receipt_and_no_fabricated_producer():
    payload = SourcePayload(b"data", "text/plain", "source-one")
    prepared = prepare_input(payload)
    assert prepared.contract == DataContract("source.payload", role=DataRole.ORIGINALS)
    assert prepared.value is payload
    assert prepared.identity == payload.identity
    assert prepared.used_inputs == (UsedInputReceipt.for_payload(payload, "source"),)
    assert not hasattr(prepared, "producer")
    with pytest.raises(HandoffError, match="explicit_contract_required"):
        prepare_input("untyped")
    with pytest.raises(HandoffError, match="storage_confirmation_requires_projection"):
        prepare_input(payload, qualifications=frozenset({"storage.confirmed"}))


def test_artifact_wrapper_and_encoded_representation_are_explicitly_distinct():
    rep = Representation("adapters.representation", 1, "application/json", b'{"x":1}')
    artifact = MaterialArtifact(VALUE, rep)
    wrapper = prepare_input(artifact)
    assert wrapper.contract == DataContract("material.artifact")
    assert wrapper.value is artifact
    encoded = artifact_input(artifact)
    assert encoded.contract == VALUE
    assert encoded.value is rep
    assert encoded.identity == rep.identity


def test_collection_preserves_member_evidence_and_named_computation_parents():
    first, second = produce("first"), produce("second")
    selected = collect_inputs((project_output(first, "value"), project_output(second, "value")),
        contract=VALUES, element_contract=VALUE)
    bound = bind_request(CONSUMER, {"items": selected})
    result = bound.invoke(consume)
    assert result.value == "first|second"
    assert result.used_inputs == (*first.used_inputs, *second.used_inputs)
    # Parent evidence remains available without becoming a different set of
    # directly consumed arguments for an otherwise identical computation.
    assert result.computation.inputs == ()
    assert result.computation.parents == (("items.0", first.computation), ("items.1", second.computation))
    assert result.computation.computation_id == consume(bound.request).computation.computation_id
    assert result.effects == ()
    assert bound.request == ValuesRequest(("first", "second"))


def test_collections_intersect_guarantees_and_keep_partial_outcome():
    first = prepare_input("a", VALUE, coverage=frozenset({"all_cells", "all_rows"}))
    second = replace(prepare_input("b", VALUE, coverage=frozenset({"all_cells"})), outcome="partial")
    selected = collect_inputs((first, second), contract=VALUES, element_contract=VALUE)
    assert selected.coverage == frozenset({"all_cells"})
    assert selected.outcome == "partial"
    with pytest.raises(HandoffError, match="outcome_not_accepted"):
        bind_request(CONSUMER, {"items": selected})
    with pytest.raises(HandoffError, match="schema_mismatch"):
        collect_inputs((first,), contract=VALUES, element_contract=DataContract("another"))
    with pytest.raises(HandoffError, match="collection_empty"):
        collect_inputs((), contract=VALUES, element_contract=VALUE)


def test_inline_typed_values_still_need_the_declared_request_type():
    with pytest.raises(HandoffError, match="input_type_mismatch"):
        bind_request(CONSUMER, {"items": prepare_input("wrong outer type", VALUES)})
    with pytest.raises(HandoffError, match="input_type_mismatch"):
        bind_request(CONSUMER, {"items": prepare_input((12,), VALUES)})
    bound = bind_request(CONSUMER, {"items": prepare_input(("valid",), VALUES)})
    assert bound.invoke(consume).value == "valid"


def test_context_receipts_are_validated_deduplicated_and_never_replayed_as_effects():
    payload = SourcePayload(b"source")
    receipt = UsedInputReceipt.for_payload(payload, "source")
    bound = bind_request(CONSUMER, {"items": prepare_input(("a",), VALUES, receipts=(receipt,))})
    result = bound.invoke(consume, context=ExecutionContext(input_receipts=(receipt,)))
    assert result.used_inputs == (receipt,)
    assert result.effects == ()
    with pytest.raises(ValueError, match="input receipt"):
        ExecutionContext(input_receipts=(object(),))


def test_transport_evidence_does_not_change_direct_byte_computation_identity():
    payload = SourcePayload(b"same bytes", "text/plain", "example.source")
    direct_receipt = UsedInputReceipt.for_payload(payload, "semantic_input")
    inherited_receipt = UsedInputReceipt.for_payload(payload, "transport")
    dependency = None

    def work(request, invocation):
        invocation.use(direct_receipt)
        if dependency is not None:
            invocation.depend(dependency)
        invocation.record(ByteIdentity.of(b"result"))
        return "result"

    direct = run(CONSUMER, ValuesRequest(("value",)), work)
    handed_off = run(CONSUMER, ValuesRequest(("value",)), work,
        context=ExecutionContext(input_receipts=(inherited_receipt,),
                                 input_transports=(inherited_receipt,)))
    assert handed_off.computation.computation_id == direct.computation.computation_id
    assert handed_off.computation.inputs == (direct_receipt,)
    assert set(handed_off.used_inputs) == {inherited_receipt, direct_receipt}
    extra = UsedInputReceipt.for_payload(SourcePayload(b"reference"), "reference")
    qualified = run(CONSUMER, ValuesRequest(("value",)), work,
        context=ExecutionContext(input_receipts=(inherited_receipt, extra),
                                 input_transports=(inherited_receipt,)))
    assert qualified.computation.inputs == (direct_receipt,)
    assert qualified.computation.computation_id == direct.computation.computation_id
    assert extra in qualified.used_inputs
    dependency = extra
    consumed = run(CONSUMER, ValuesRequest(("value",)), work,
        context=ExecutionContext(input_receipts=(inherited_receipt, extra),
                                 input_transports=(inherited_receipt,)))
    assert consumed.computation.inputs == (direct_receipt, extra)
    assert consumed.computation.computation_id != direct.computation.computation_id


def test_result_adapter_requires_explicit_output_and_pinned_reference_resolver():
    result = produce("value")
    output = adapt_input(result, output_name="value")
    assert output == project_output(result, "value")
    assert adapt_input(output) is output
    prepared = prepare_input("local", VALUE)
    assert adapt_input(prepared) is prepared
    with pytest.raises(HandoffError, match="output_name_required"):
        adapt_input(result)
    with pytest.raises(HandoffError, match="explicit_input_required"):
        adapt_input("untyped")
    reference = reference_output(output, owner_id="retained", result_id="first")
    with pytest.raises(HandoffError, match="result_resolver_required"):
        adapt_input(reference)

    class Resolver:
        owner_id = "retained"

        def resolve(self, ref):
            return result

    assert adapt_input(reference, resolver=Resolver()) == output
    with pytest.raises(HandoffError, match="output_mismatch"):
        adapt_input(reference, resolver=Resolver(), output_name="another")
