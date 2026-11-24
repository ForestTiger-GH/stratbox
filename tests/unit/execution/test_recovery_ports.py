from dataclasses import replace

from stratbox.core.execution.contracts import EffectReceipt
from stratbox.core.execution.effects import EffectAuthority, EffectIntent
from stratbox.core.execution.recovery import (
    CheckpointRevision, RecoveryArtifact, RecoveryCheckpoint, check_state_conformance, inspect_replay,
)
from stratbox.shared.identity import ByteIdentity


class State:
    def __init__(self):
        self.value = None
        self.revision = 0
    def read_checkpoint(self, key):
        return self.value
    def commit_checkpoint(self, checkpoint, *, expected_revision):
        actual = self.value.revision if self.value else None
        if actual != expected_revision:
            return False
        self.revision += 1
        self.value = CheckpointRevision(checkpoint, str(self.revision))
        return True


class Artifacts:
    def read_artifact(self, reference, *, max_bytes):
        assert reference == 'durable:extract'
        assert max_bytes == len(b'ready')
        return b'ready'


def test_host_state_conformance_checks_create_update_stale_cas_and_replay():
    first = RecoveryCheckpoint('test-checkpoint', 'plan', 'basis')
    second = replace(first, plan_id='plan2')
    assert check_state_conformance(State(), first, second) == ()


def test_replay_preserves_surviving_output_and_requires_evidence_for_unknown_effect():
    identity = ByteIdentity.of(b'ready')
    authority = EffectAuthority()
    authority.begin_attempt('run', 'scope', 'work', 'attempt')
    effect = EffectIntent('run', 'scope', 'work', 'storage.write', 'save', 'dest', input_basis='basis', identity=identity)
    authority.commit(effect, 'attempt', lambda: (_ for _ in ()).throw(OSError()))
    checkpoint = RecoveryCheckpoint('checkpoint', 'plan', 'basis',
        (RecoveryArtifact('extract', 'durable:extract', identity, 'basis', 'extracts', 'reported'),),
        authority.snapshot())
    decision = inspect_replay(checkpoint, artifacts=Artifacts())
    assert decision.reusable_outputs == ('extract',)
    assert decision.unresolved_effects == ('save',)
    class Evidence:
        def reconcile_effect(self, record):
            return EffectReceipt('storage.write', 'confirmed', effect_id='save', identity=identity)
    reconciled = inspect_replay(checkpoint, artifacts=Artifacts(), effects=Evidence())
    assert reconciled.complete
    assert reconciled.reusable_outputs == ('extract',)
    assert inspect_replay(checkpoint, artifacts=Artifacts(), input_basis='changed').diagnostics == ('recovery.input_basis_changed',)
