"""Direct and retained inputs share schema, outcome and lineage admission."""

from dataclasses import dataclass, replace

import pytest

from stratbox.core.execution import (
    Completion, EffectReceipt, InputPort, OperationDefinition, OperationSemantics,
    OutputPort, ProcessingStage, run,
)
from stratbox.core.execution.handoff import (
    HandoffError, ResultReference, bind_request, project_output,
    reference_output, resolve_output,
)
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.evidence import MaterialReference, SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity


CONTRACT = DataContract("test.flake.json", 1, DataRole.EXTRACTS)


@dataclass(frozen=True)
class Produce:
    data: bytes


@dataclass(frozen=True)
class Consume:
    representation: Representation
    label: str = "value"


PRODUCER = OperationDefinition("test.serialize", 1, "serialize-1", Produce, Representation,
    partial_allowed=True, processing=OperationSemantics(
        (ProcessingStage.RENDER,), outputs=(OutputPort("flake", CONTRACT,
            outcomes=frozenset({"succeeded", "partial"}), coverage=frozenset({"all_cells"})),),
        summary="Serialize a typed test extract."))
CONSUMER = OperationDefinition("test.consume", 1, "consume-1", Consume, str,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        inputs=(InputPort("source", CONTRACT, "representation", coverage=frozenset({"all_cells"})),),
        parameters=("label",), outputs=(OutputPort("text", DataContract("test.text", role=DataRole.PRODUCTS)),),
        summary="Consume a complete typed extract."))


def produce(data=b'{"value":5}', *, outcome="succeeded"):
    def work(req, inv):
        rep = Representation("test.flake", 1, "application/json", req.data)
        return rep if outcome == "succeeded" else Completion(rep, outcome, "test.incomplete")
    return run(PRODUCER, Produce(data), work)


def consume(request, *, context=None):
    def work(req, inv):
        inv.use(UsedInputReceipt.for_payload(SourcePayload(req.representation.data, "application/json"), "source"))
        inv.record(ByteIdentity.of(req.representation.data), parameters={"label": req.label})
        return req.label
    return run(CONSUMER, request, work, context=context)


def test_direct_handoff_binds_typed_request_and_keeps_parent_computation():
    original = produce()
    projected = project_output(original, "flake")
    bound = bind_request(CONSUMER, {"source": projected}, parameters={"label": "retained"})
    assert bound.request == Consume(original.value, "retained")
    result = bound.invoke(consume)
    assert result.outcome == "succeeded"
    assert result.value == "retained"
    assert result.computation.parents == (("source", original.computation),)
    assert bound.inputs[0][1].used_inputs == original.used_inputs
    assert bound.inputs[0][1].effects == original.effects
    direct = consume(bound.request)
    assert direct.computation.computation_id == result.computation.computation_id


class Results:
    owner_id = "retained"

    def __init__(self, result):
        self.result = result

    def resolve(self, reference):
        assert reference.result_id == "result-1"
        return self.result


def test_retained_reference_roundtrip_uses_same_admission_as_live_result():
    result = produce()
    output = project_output(result, "flake")
    reference = reference_output(output, owner_id="retained", result_id="result-1")
    portable = ResultReference.from_dict(reference.to_dict())
    restored = resolve_output(portable, Results(result))
    assert restored == output
    before = bind_request(CONSUMER, {"source": output}).invoke(consume)
    after = bind_request(CONSUMER, {"source": restored}).invoke(consume)
    assert after.value == before.value
    assert after.computation == before.computation


@pytest.mark.parametrize("case,code", [
    ("owner", "handoff.result_owner_mismatch"),
    ("invocation", "handoff.result_mismatch"),
    ("identity", "handoff.identity_mismatch"),
    ("unpinned", "handoff.identity_required"),
])
def test_reference_cannot_switch_authority_result_or_content(case, code):
    result = produce()
    reference = reference_output(project_output(result, "flake"), owner_id="retained", result_id="result-1")
    if case == "owner":
        reference = replace(reference, owner_id="different")
    elif case == "invocation":
        reference = replace(reference, invocation_id="another-invocation")
    elif case == "identity":
        reference = replace(reference, identity=ByteIdentity.of(b"different"))
    else:
        reference = replace(reference, identity=None)
    with pytest.raises(HandoffError, match=code):
        resolve_output(reference, Results(result))


def test_partial_result_requires_consumer_admission_and_no_failed_result_is_projected():
    partial = project_output(produce(outcome="partial"), "flake")
    with pytest.raises(HandoffError, match="outcome_not_accepted"):
        bind_request(CONSUMER, {"source": partial})
    admitted = replace(CONSUMER, processing=replace(CONSUMER.processing, inputs=(
        replace(CONSUMER.processing.inputs[0], outcomes=frozenset({"partial"})),)))
    assert bind_request(admitted, {"source": partial}).request.representation == partial.value
    for outcome in ("failed", "unknown"):
        with pytest.raises(HandoffError, match="outcome_not_accepted"):
            project_output(produce(outcome=outcome), "flake")


@pytest.mark.parametrize("case,code", [
    ("role", "processing.schema_mismatch"),
    ("edition", "processing.schema_mismatch"),
    ("coverage", "processing.coverage_missing"),
    ("qualification", "processing.qualification_missing"),
    ("missing", "handoff.input_required"),
    ("parameter", "handoff.parameter_unknown"),
    ("type", "handoff.input_type_mismatch"),
])
def test_request_binding_checks_semantics_before_consumer_execution(case, code):
    output = project_output(produce(), "flake")
    definition, bindings, parameters = CONSUMER, {"source": output}, {}
    if case == "role":
        bindings["source"] = replace(output, contract=replace(CONTRACT, role=DataRole.PRODUCTS))
    elif case == "edition":
        bindings["source"] = replace(output, contract=replace(CONTRACT, version=2))
    elif case == "coverage":
        bindings["source"] = replace(output, coverage=frozenset())
    elif case == "qualification":
        definition = replace(definition, processing=replace(definition.processing, inputs=(
            replace(definition.processing.inputs[0], qualifications=frozenset({"complete"})),)))
    elif case == "missing":
        bindings = {}
    elif case == "parameter":
        parameters = {"representation": output.value}
    else:
        bindings["source"] = replace(output, value="untyped")
    with pytest.raises(HandoffError, match=code):
        bind_request(definition, bindings, parameters=parameters)


def test_storage_qualification_requires_actual_matching_effect():
    identity = ByteIdentity.of(b"original")
    material = MaterialReference("object.xlsx", "store", identity, "application/octet-stream")
    definition = OperationDefinition("test.save", 1, "save-1", int, MaterialReference,
        possible_effects=frozenset({"storage.write"}), processing=OperationSemantics(
            (ProcessingStage.PRESERVE,), outputs=(OutputPort("material",
                DataContract("source.material_reference", role=DataRole.ORIGINALS),
                qualifications=frozenset({"storage.confirmed"})),), summary="Store an original."))
    result = run(definition, 1, lambda req, inv: material)
    with pytest.raises(HandoffError, match="storage_confirmation_missing"):
        project_output(result, "material")
    def stored(req, inv):
        inv.effect(EffectReceipt("storage.write", "confirmed", "object.xlsx", identity=identity))
        return material
    confirmed = run(definition, 1, stored)
    assert project_output(confirmed, "material").value is material

    def read_back(req, inv):
        inv.use(UsedInputReceipt("original", identity, "application/octet-stream", "reference_only"))
        return material

    # Merely observing the source input does not confirm a writing operation.
    with pytest.raises(HandoffError, match="storage_confirmation_missing"):
        project_output(run(definition, 1, read_back), "material")
    reader = replace(definition, operation_id="test.read", possible_effects=frozenset())
    assert project_output(run(reader, 1, read_back), "material").value is material


def test_paths_project_dataclass_fields_and_never_properties():
    @dataclass(frozen=True)
    class Value:
        actual: str

        @property
        def secret(self):
            pytest.fail("A property was evaluated")

    definition = OperationDefinition("test.project", 1, "v1", int, Value,
        processing=OperationSemantics((ProcessingStage.VIEW,), outputs=(
            OutputPort("value", DataContract("test.value"), "secret"),), summary="Project a value."))
    with pytest.raises(HandoffError, match="path_unavailable"):
        project_output(run(definition, 1, lambda req, inv: Value("value")), "value")


def test_portable_reference_rejects_extra_fields_and_boolean_size():
    ref = reference_output(project_output(produce(), "flake"), owner_id="retained", result_id="result-1")
    invalid = ref.to_dict()
    invalid["python_class"] = "arbitrary.module"
    with pytest.raises(HandoffError, match="reference_invalid"):
        ResultReference.from_dict(invalid)
    invalid = ref.to_dict()
    invalid["identity"]["size"] = True
    with pytest.raises(HandoffError, match="reference_invalid"):
        ResultReference.from_dict(invalid)
