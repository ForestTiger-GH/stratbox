"""Existing unindexed effect evidence cannot silently authorize a fresh action."""
import pytest

from stratbox.core.execution.effect_state import FileEffectState


@pytest.mark.parametrize('location', ['ab/receipt.json', 'archive/ab/acknowledgement'])
def test_unindexed_evidence_is_rejected_before_creating_empty_state(tmp_path, location):
    evidence = tmp_path / location
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b'unindexed external effect evidence')
    with pytest.raises(ValueError, match='unindexed_evidence'):
        FileEffectState(tmp_path)
    assert not (tmp_path / 'effects.sqlite').exists()
    assert evidence.read_bytes() == b'unindexed external effect evidence'
