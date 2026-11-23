"""Result postconditions finalize with physical effect truth, before telemetry."""

from dataclasses import dataclass

import pytest

from stratbox.core.execution import (
    Completion, Diagnostic, EffectReceipt, ExecutionContext, InMemorySink,
    OperationDefinition, ResultAdmission, run,
)
from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.datasets.definitions import WriteSnapshotRequest
from stratbox.core.storage.datasets.operations import write_snapshot
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.identity import ByteIdentity


@dataclass(frozen=True)
class SourceValue:
    source: str


@dataclass(frozen=True)
class ExpectedSource(ResultAdmission):
    expected: str
    policy_id: str = "test.source_result"

    def assess(self, definition, value, *, phase, outcome=None):
        return (() if value.source == self.expected else
            (Diagnostic("source.output_series_mismatch"),))


@pytest.mark.parametrize("effect_state,expected", [(None, "failed"), ("confirmed", "failed"), ("unknown", "unknown")])
def test_bad_source_result_preserves_effect_receipts_and_one_truthful_finish(tmp_path, effect_state, expected):
    sink = InMemorySink()
    definition = OperationDefinition("test.source_bound", "source-check", str, SourceValue,
        possible_effects=frozenset({"storage.write"}) if effect_state else frozenset())
    destination = tmp_path / "committed.bin"
    identity = ByteIdentity.of(b"committed")

    def work(request, invocation):
        if effect_state:
            destination.write_bytes(b"committed")
            invocation.effect(EffectReceipt("storage.write", effect_state,
                str(destination), "commit", identity=identity,
                reconciliation_owner="store"))
        return SourceValue("foreign")

    result = run(definition, "request", work, context=ExecutionContext(
        sink=sink, result_admissions=(ExpectedSource("expected"),)))
    assert result.outcome == expected
    assert result.value is None
    assert result.diagnostics[0].code == "source.output_series_mismatch"
    assert result.diagnostics[0].stage == "result_admission"
    finished = [event for event in sink.events if event.kind == "operation.finished"]
    assert len(finished) == 1 and finished[0].outcome == expected
    if effect_state:
        assert result.effects[0].state == effect_state
        assert result.effects[0].identity == identity
        assert destination.read_bytes() == b"committed"
    if effect_state == "unknown":
        uncertain = next(item for item in result.diagnostics if item.code == "effect.outcome_unknown")
        assert uncertain.retry_disposition == "reconcile"
        assert uncertain.reconciliation_owner == "store"


def test_unknown_work_outcome_survives_result_rejection_without_an_effect():
    definition = OperationDefinition("test.unknown_result", "source-check", str, SourceValue)
    result = run(definition, "request", lambda request, invocation:
        Completion(SourceValue("foreign"), "unknown", "domain.outcome_unknown"),
        context=ExecutionContext(result_admissions=(ExpectedSource("expected"),)))
    assert result.outcome == "unknown" and result.value is None
    assert {item.code for item in result.diagnostics} == {
        "domain.outcome_unknown", "source.output_series_mismatch"}


def snapshot():
    from stratbox.shared.data.observations import ObservationBatch
    from stratbox.shared.data.observation_snapshots import observation_snapshot
    return observation_snapshot(ObservationBatch("test.source", 1, "issue", (), ()))


@dataclass(frozen=True)
class RejectPhase(ResultAdmission):
    phase: str
    policy_id: str = "test.phase_condition"

    def assess(self, definition, value, *, phase, outcome=None):
        return (Diagnostic("source.output_series_mismatch"),) if phase == self.phase else ()


def test_precommit_rejection_prevents_real_dataset_store_writes(tmp_path):
    store = FileDatasetStore(LocalFileStore(str(tmp_path)), "datasets", provider_id="files", scope_id="test")
    result = write_snapshot(WriteSnapshotRequest(snapshot()), store=store,
        context=ExecutionContext(result_admissions=(RejectPhase("precommit"),)))
    assert result.outcome == "failed" and result.effects == ()
    assert result.diagnostics[0].stage == "precommit_admission"
    assert not tuple(tmp_path.rglob("*"))


def test_rejected_storage_result_keeps_confirmed_real_publication(tmp_path):
    store = FileDatasetStore(LocalFileStore(str(tmp_path)), "datasets", provider_id="files", scope_id="test")
    value = snapshot()
    sink = InMemorySink()
    result = write_snapshot(WriteSnapshotRequest(value), store=store,
        context=ExecutionContext(sink=sink, result_admissions=(RejectPhase("result"),)))
    assert result.outcome == "failed" and result.value is None
    assert any(receipt.kind == "dataset.write" and receipt.state == "confirmed" for receipt in result.effects)
    assert all(receipt.state == "confirmed" for receipt in result.effects)
    reference, = store.versions(value.manifest.dataset_id)
    assert store.read_snapshot(reference) == value
    assert sink.events[-1].outcome == "failed"


def test_untrusted_callbacks_cannot_be_context_result_policies():
    with pytest.raises(ValueError, match="result.admission_policy_invalid"):
        ExecutionContext(result_admissions=(lambda value: True,))


def test_invalid_trusted_policy_decision_does_not_erase_an_effect():
    class BrokenPolicy(ResultAdmission):
        policy_id = "test.invalid_decision"
        def assess(self, definition, value, *, phase, outcome=None):
            return True

    definition = OperationDefinition("test.broken_policy", "produce", str, str,
        possible_effects=frozenset({"storage.write"}))
    def work(request, invocation):
        invocation.effect(EffectReceipt("storage.write", "confirmed", effect_id="committed"))
        return request
    sink = InMemorySink()
    result = run(definition, "value", work, context=ExecutionContext(
        sink=sink, result_admissions=(BrokenPolicy(),)))
    assert result.outcome == "failed" and result.value is None
    assert result.effects[0].state == "confirmed"
    assert result.diagnostics[0].code == "result.admission_invalid"
    assert sink.events[-1].outcome == "failed"


def test_effect_signature_preflight_refuses_unsupported_input_before_handler():
    from stratbox.shared.data.operations import InputPort, OperationSemantics, OutputPort, ProcessingStage
    from stratbox.shared.data.processing import DataContract

    @dataclass(frozen=True)
    class Request:
        value: object

    definition = OperationDefinition("test.preflight", "inspect", Request, str,
        possible_effects=frozenset({"storage.write"}),
        processing=OperationSemantics((ProcessingStage.PUBLISH,),
            inputs=(InputPort("data", DataContract("test.data"), "value"),),
            outputs=(OutputPort("result", DataContract("test.result")),),
            summary="Refuse unsupported content before external commit."))
    called = []
    result = run(definition, Request(object()), lambda request, invocation:
        called.append("effect") or "unreachable")
    assert result.outcome == "failed" and not called and not result.effects
    assert result.diagnostics[0].code == "processing.signature_unavailable"
    assert result.diagnostics[0].stage == "preflight"
