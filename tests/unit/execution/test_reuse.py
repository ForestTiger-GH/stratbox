"""A matching key is reusable only with qualified, available, admitted content."""
from dataclasses import replace

from stratbox.core.execution import Completion, Diagnostic, EffectReceipt, OperationDefinition, run
from stratbox.core.execution.reuse import assess_reuse
from stratbox.shared.data.operations import OperationSemantics, OutputPort, ProcessingStage
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.representation import Representation
from stratbox.shared.identity import ByteIdentity


def result():
    definition = OperationDefinition("fixture.encode", "encode", bytes, Representation,
        processing=OperationSemantics((ProcessingStage.RENDER,),
            outputs=(OutputPort("output", DataContract("fixture.encoded"),
                qualifications=frozenset({"complete"})),), summary="Encode a supplied value."))
    def work(value, invocation):
        return Representation("fixture", 1, "application/octet-stream", value)
    return run(definition, b"material", work)


def test_qualified_accessible_content_requires_receiving_owner_admission():
    candidate = result()
    admitted = assess_reuse(candidate, expected_computation=candidate.computation.computation_id,
        output_name="output", required_qualifications=frozenset({"complete"}),
        receiving_owner=lambda material: isinstance(material, Representation))
    assert admitted.eligible
    denied = assess_reuse(candidate, expected_computation=candidate.computation.computation_id,
        output_name="output", receiving_owner=lambda material: False)
    assert not denied.eligible and denied.reasons == ("reuse.owner_rejected",)


def test_hash_without_actual_readable_material_and_failed_source_result_cannot_be_reused():
    candidate = result()
    unavailable = assess_reuse(candidate, expected_computation=candidate.computation.computation_id,
        output_name="output", receiving_owner=lambda material: True,
        resolve_material=lambda identity: identity)
    assert not unavailable.eligible and unavailable.reasons == ("reuse.material_unresolved",)
    failed = replace(candidate, outcome="failed", value=None, diagnostics=(Diagnostic("source.output_series_mismatch"),))
    assert not assess_reuse(failed, expected_computation=candidate.computation.computation_id,
        output_name="output", receiving_owner=lambda material: True).eligible


def test_old_or_different_computation_and_missing_qualification_are_rejected():
    candidate = result()
    mismatch = assess_reuse(candidate, expected_computation=ByteIdentity.of(b"different computation"),
        output_name="output", receiving_owner=lambda material: True)
    assert not mismatch.eligible and "reuse.computation_mismatch" in mismatch.reasons
    unqualified = assess_reuse(candidate, expected_computation=candidate.computation.computation_id,
        output_name="output", required_qualifications=frozenset({"interpreted"}),
        receiving_owner=lambda material: True)
    assert not unqualified.eligible and unqualified.reasons == ("reuse.qualification_missing",)


def test_confirmed_partition_from_partial_run_requires_a_partial_accepting_output_port():
    definition = OperationDefinition("fixture.partition", "partition", bytes, Representation,
        partial_allowed=True, possible_effects=frozenset({"storage.write"}),
        processing=OperationSemantics((ProcessingStage.PUBLISH,), outputs=(
            OutputPort("confirmed_partition", DataContract("fixture.partition"),
                outcomes=frozenset({"succeeded", "partial"}), qualifications=frozenset({"storage.confirmed"})),
            OutputPort("complete_result", DataContract("fixture.partition"),
                qualifications=frozenset({"storage.confirmed"}))), summary="Publish independent admitted partitions."))
    def work(value, invocation):
        material = Representation("fixture.partition", 1, "application/octet-stream", value)
        invocation.effect(EffectReceipt("storage.write", "confirmed", effect_id="partition-one", identity=material.identity))
        return Completion(material, "partial", "fixture.remaining_partitions")
    candidate = run(definition, b"confirmed partition", work)
    assert candidate.outcome == "partial", candidate.diagnostics
    admitted = assess_reuse(candidate, expected_computation=candidate.computation.computation_id,
        output_name="confirmed_partition", required_qualifications=frozenset({"storage.confirmed"}),
        receiving_owner=lambda material: isinstance(material, Representation))
    assert admitted.eligible
    blocked = assess_reuse(candidate, expected_computation=candidate.computation.computation_id,
        output_name="complete_result", receiving_owner=lambda material: True)
    assert not blocked.eligible and blocked.reasons == ("processing.outcome_not_accepted",)
