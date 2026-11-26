"""An uncertain immutable write survives service restart without a second mutation."""
from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material


class LostAcknowledgement(LocalFileStore):
    calls=0
    def create_immutable(self,location,data):
        type(self).calls+=1
        result=super().create_immutable(location,data)
        if type(self).calls==1: raise OSError('write committed; response lost')
        return result


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
