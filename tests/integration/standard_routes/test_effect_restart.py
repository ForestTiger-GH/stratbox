"""An uncertain immutable write survives service restart without a second mutation."""
from contextlib import contextmanager
from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material


class LostAcknowledgement(LocalFileStore):
    calls=0
    @contextmanager
    def stage_content(self, directory):
        owner = type(self)
        with super().stage_content(directory) as stage:
            class Lost:
                stream = stage.stream
                def location(self, identity):
                    return stage.location(identity)
                def commit(self, identity, **kwargs):
                    owner.calls += 1
                    result = stage.commit(identity, **kwargs)
                    if owner.calls == 1:
                        raise OSError('write committed; response lost')
                    return result
            yield Lost()


def test_lost_save_acknowledgement_reconciles_after_restart_without_resend(tmp_path):
    LostAcknowledgement.calls=0
    original=Material(b'exact original content')
    def providers():
        return {'filestore':LostAcknowledgement(str(tmp_path/'files')),
                'effect_state':FileEffectState(tmp_path/'effects')}
    with StrategyBox(providers=providers()) as box:
        first=box.invoke('command.artifact.commit',inputs={'material':original,'destination':'objects'})
        assert first.outcome=='unknown',first.diagnostics
        effect,=first.effects.values()
        assert effect.status=='unknown'
        first.close()
    with StrategyBox(providers=providers()) as box:
        retry=box.invoke('command.artifact.commit',inputs={'material':original,'destination':'objects'})
        assert retry.outcome=='unknown',retry.diagnostics
        assert LostAcknowledgement.calls==1
        recovered=box.invoke('command.artifact.reconcile',inputs={'effect':effect})
        assert recovered.outcome=='succeeded',recovered.diagnostics
        assert box.session.lookup_effect(effect.effect_id).status=='confirmed'
        assert LostAcknowledgement.calls==1
