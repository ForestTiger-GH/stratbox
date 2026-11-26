from dataclasses import replace
import json

import pytest
from stratbox.sdk import StrategyBox
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.values import Material, SourceClaim, ImmutableMaterialRef, EncodedProduct
from stratbox.shared.identity import ByteIdentity


def test_raw_material_requires_an_explicit_publisher_claim():
    with StrategyBox() as box:
        result = box.invoke('command.material.identify',inputs={'material':Material(b'exact')})
    assert result.outcome == 'failed'
    assert any('claim_required' in code for code in result.diagnostics)


def test_conflicting_publisher_claim_is_rejected_before_handoff():
    with StrategyBox() as box:
        result = box.invoke('command.material.identify',inputs={'material':Material(b'exact',source_id='publisher.a'),
            'claim':SourceClaim('publisher.b')})
    assert result.outcome == 'failed' and 'material' not in result.outputs


def test_asserted_claim_is_preserved_without_promotion_to_remote_authentication():
    with StrategyBox() as box:
        result = box.invoke('command.material.identify',inputs={'material':Material(b'exact'),
            'claim':SourceClaim('publisher.a','2026-11','main','asserted')})
        assert result.outcome == 'succeeded',result.diagnostics
        identified = result.output('material')
        assert identified.claim.attribution == 'asserted'
        assert 'source.asserted' in identified.assessment.qualifications
        assert identified.material.identity == ByteIdentity.of(b'exact')


def test_encoded_data_cannot_select_an_arbitrary_python_import():
    value = {'type':'subprocess:Popen','fields':{'args':{'tuple':['false']}}}
    with StrategyBox() as box:
        result = box.invoke('command.value.decode',inputs={'representation':json.dumps(value).encode()})
    assert result.outcome == 'failed' and 'value' not in result.outputs


def test_lost_write_ack_stays_unknown_and_has_no_accepted_reference(tmp_path):
    class LostAck(LocalFileStore):
        def create_immutable(self,location,data):
            super().create_immutable(location,data)
            raise ConnectionError('synthetic lost acknowledgement')
    store = LostAck(tmp_path)
    with StrategyBox(providers={'filestore':store}) as box:
        result = box.invoke('command.artifact.commit',inputs={'material':Material(b'exact'),'destination':'objects'})
        assert result.outcome == 'unknown',result.diagnostics
        assert 'reference' not in result.outputs
        assert any(effect.status == 'unknown' for effect in result.effects.values())
    assert store.read_bytes('objects/'+ByteIdentity.of(b'exact').sha256) == b'exact'


def test_release_requires_runtime_confirmed_retention_and_rechecks_current_bytes(tmp_path):
    store = LocalFileStore(tmp_path)
    with StrategyBox(providers={'filestore':store}) as box:
        fabricated = ImmutableMaterialRef('objects/not-written',ByteIdentity.of(b'x'))
        rejected = box.invoke('command.release.assemble',inputs={'members':(fabricated,)})
        assert rejected.outcome == 'failed'
        encoded = box.invoke('command.value.encode',inputs={'value':Material(b'exact')}).output('representation')
        retained = box.invoke('command.artifact.commit',inputs={'material':encoded,'destination':'objects'})
        assert retained.outcome == 'succeeded',retained.diagnostics
        reference = retained.output('reference')
        assembled = box.invoke('command.release.assemble',inputs={'members':(reference,)})
        assert assembled.outcome == 'succeeded',assembled.diagnostics
        store.checked_file_path(reference.location).write_bytes(b'changed')
        tampered = box.invoke('command.release.assemble',inputs={'members':(reference,)})
        assert tampered.outcome == 'failed'
