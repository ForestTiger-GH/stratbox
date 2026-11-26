from dataclasses import replace
import pytest
from stratbox.sdk import StrategyBox
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.values import Material, ImmutableMaterialRef


def good(result, port):
    assert result.outcome == 'succeeded', result.diagnostics
    return result.output(port)


def test_exact_content_moves_between_independent_explicit_stores(tmp_path):
    source,destination = LocalFileStore(tmp_path/'source'),LocalFileStore(tmp_path/'destination')
    source.write_bytes('input',b'exact selected bytes')
    with StrategyBox(providers={'filestore':source}) as reader:
        material = good(reader.invoke('command.material.read',inputs={'location':'input'}),'material')
    with StrategyBox(providers={'filestore':destination}) as writer:
        reference = good(writer.invoke('command.artifact.commit',inputs={'material':material,'destination':'objects'}),'reference')
        replay = good(writer.invoke('command.material.read',inputs={'location':reference}),'material')
    assert replay.data == b'exact selected bytes'
    assert replay.identity == material.identity == reference.identity
    assert reference.provider_id == destination.provider_id
    assert source.read_bytes('input') == material.data


def test_missing_explicit_disk_location_never_falls_back_to_another_provider(tmp_path):
    left,right = LocalFileStore(tmp_path/'left'),LocalFileStore(tmp_path/'right')
    right.write_bytes('report',b'other store')
    with StrategyBox(providers={'filestore':left,'backup':right}) as box:
        result = box.invoke('command.material.read',inputs={'location':'report'})
        assert result.outcome == 'failed'
        assert 'material' not in result.outputs
    assert right.read_bytes('report') == b'other store'


def test_changed_expected_content_is_rejected_before_handoff(tmp_path):
    store = LocalFileStore(tmp_path)
    store.write_bytes('report',b'changed')
    reference = ImmutableMaterialRef('report',ByteIdentity.of(b'expected'))
    with StrategyBox(providers={'filestore':store}) as box:
        result = box.invoke('command.material.read',inputs={'location':reference})
        assert result.outcome == 'failed'
        assert any('identity_mismatch' in item for item in result.diagnostics)
        assert 'material' not in result.outputs


def test_unclassified_local_read_does_not_assert_a_publisher(tmp_path):
    store = LocalFileStore(tmp_path)
    store.write_bytes('product.xlsx',b'retained product')
    with StrategyBox(providers={'filestore':store}) as box:
        material = good(box.invoke('command.material.read',inputs={'location':'product.xlsx'}),'material')
    assert material.source_id is None


def test_explicit_disk_read_reobserves_disappearance_after_an_earlier_success(tmp_path):
    store=LocalFileStore(tmp_path)
    store.write_bytes('report',b'first observation')
    with StrategyBox(providers={'filestore':store}) as box:
        first=box.invoke('command.material.read',inputs={'location':'report'})
        assert first.outcome=='succeeded',first.diagnostics
        store.checked_file_path('report').unlink()
        second=box.invoke('command.material.read',inputs={'location':'report'})
        assert second.outcome=='failed'
        assert 'material' not in second.outputs
