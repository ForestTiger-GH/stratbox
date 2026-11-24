"""Durable host ports and evidence-based replay of pinned accepted outputs.

The library supplies contracts and conformance checks. The host supplies
persistent state, artifacts and competent external-effect reconciliation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from stratbox.core.execution.contracts import EffectReceipt
from stratbox.core.execution.effects import EffectRecord
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.identifiers import safe_token


@dataclass(frozen=True, slots=True)
class RecoveryArtifact:
    name: str
    reference: str
    identity: ByteIdentity
    input_basis: str
    role: str
    qualification: str

    def __post_init__(self):
        for token in (self.name, self.input_basis, self.role, self.qualification):
            safe_token(token)
        if not isinstance(self.reference, str) or not self.reference:
            raise ValueError("recovery.artifact_reference_invalid")
        if not isinstance(self.identity, ByteIdentity):
            raise ValueError("recovery.artifact_identity_invalid")


@dataclass(frozen=True, slots=True)
class RecoveryCheckpoint:
    checkpoint_id: str
    plan_id: str
    input_basis: str
    artifacts: tuple[RecoveryArtifact, ...] = ()
    effects: tuple[EffectRecord, ...] = ()

    def __post_init__(self):
        for token in (self.checkpoint_id, self.plan_id, self.input_basis):
            safe_token(token)
        if (not isinstance(self.artifacts, tuple)
                or any(not isinstance(value, RecoveryArtifact) or value.input_basis != self.input_basis
                       for value in self.artifacts)
                or len({value.name for value in self.artifacts}) != len(self.artifacts)):
            raise ValueError("recovery.artifact_basis_invalid")
        if (not isinstance(self.effects, tuple)
                or any(not isinstance(value, EffectRecord) for value in self.effects)
                or len({value.intent.key for value in self.effects}) != len(self.effects)
                or any(value.intent.input_basis not in {None, self.input_basis} for value in self.effects)):
            raise ValueError("recovery.effect_basis_invalid")


@dataclass(frozen=True, slots=True)
class CheckpointRevision:
    checkpoint: RecoveryCheckpoint
    revision: str


class RecoveryStatePort(Protocol):
    """Host atomic checkpoint commit; false means a known revision conflict."""

    def read_checkpoint(self, checkpoint_id: str) -> CheckpointRevision | None: ...
    def commit_checkpoint(self, checkpoint: RecoveryCheckpoint, *, expected_revision: str | None) -> bool: ...


class RecoveryArtifactPort(Protocol):
    def read_artifact(self, reference: str, *, max_bytes: int) -> bytes: ...


class RecoveryEffectPort(Protocol):
    def reconcile_effect(self, record: EffectRecord) -> EffectReceipt | None: ...


@dataclass(frozen=True, slots=True)
class ReplayDecision:
    reusable_outputs: tuple[str, ...]
    effects: tuple[EffectReceipt, ...]
    unresolved_effects: tuple[str, ...]
    diagnostics: tuple[str, ...]

    @property
    def complete(self):
        return (not self.unresolved_effects and not self.diagnostics
                and all(receipt.state == "confirmed" for receipt in self.effects))


def inspect_replay(checkpoint: RecoveryCheckpoint, *, artifacts: RecoveryArtifactPort,
                   effects: RecoveryEffectPort | None = None, input_basis: str | None = None) -> ReplayDecision:
    """Verify survivors without recomputing or repeating uncertain effects."""
    if input_basis is not None and input_basis != checkpoint.input_basis:
        return ReplayDecision((), (), (), ("recovery.input_basis_changed",))
    reusable, receipts, unresolved, diagnostics = [], [], [], []
    for artifact in checkpoint.artifacts:
        try:
            payload = artifacts.read_artifact(artifact.reference, max_bytes=artifact.identity.size)
            if type(payload) is not bytes or ByteIdentity.of(payload) != artifact.identity:
                raise ValueError("recovery.artifact_changed")
        except Exception:
            diagnostics.append("recovery.artifact_unavailable:" + artifact.name)
        else:
            reusable.append(artifact.name)
    for record in checkpoint.effects:
        receipt = record.receipt
        if receipt.state == "unknown" and effects is not None:
            try:
                candidate = effects.reconcile_effect(record)
            except Exception:
                candidate = None
            if candidate is not None:
                if (not isinstance(candidate, EffectReceipt) or candidate.kind != record.intent.kind
                        or candidate.effect_id != record.intent.effect_id
                        or candidate.identity not in {None, record.intent.identity}):
                    diagnostics.append("recovery.effect_evidence_mismatch:" + record.intent.effect_id)
                else:
                    receipt = candidate
        receipts.append(receipt)
        if receipt.state == "unknown":
            unresolved.append(record.intent.effect_id)
    return ReplayDecision(tuple(reusable), tuple(receipts), tuple(unresolved), tuple(diagnostics))


def check_state_conformance(store: RecoveryStatePort, first: RecoveryCheckpoint,
                            second: RecoveryCheckpoint) -> tuple[str, ...]:
    """Exercise create, CAS and replay in a caller-owned test namespace.

    Passing checks establishes atomic state-port behavior for this execution.
    Crash persistence and artifact durability require separate host evidence.
    """
    if first.checkpoint_id != second.checkpoint_id or first == second:
        raise ValueError("recovery.conformance_examples_invalid")
    failures = []
    if store.read_checkpoint(first.checkpoint_id) is not None:
        raise ValueError("recovery.conformance_namespace_not_empty")
    if store.commit_checkpoint(first, expected_revision=None) is not True:
        return ("recovery.create_rejected",)
    created = store.read_checkpoint(first.checkpoint_id)
    if created is None or created.checkpoint != first or not created.revision:
        return ("recovery.create_readback_failed",)
    if store.commit_checkpoint(second, expected_revision=None) is not False:
        failures.append("recovery.create_conflict_not_enforced")
    if store.commit_checkpoint(second, expected_revision=created.revision) is not True:
        failures.append("recovery.compare_and_swap_failed")
    updated = store.read_checkpoint(first.checkpoint_id)
    if updated is None or updated.checkpoint != second or updated.revision == created.revision:
        failures.append("recovery.update_readback_failed")
    if store.commit_checkpoint(first, expected_revision=created.revision) is not False:
        failures.append("recovery.stale_revision_accepted")
    if store.read_checkpoint(first.checkpoint_id) != updated:
        failures.append("recovery.stale_write_changed_current")
    return tuple(failures)
