from dataclasses import replace

import pytest
from stratbox.sdk import StrategyBox
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.values import Material, EncodedProduct, SourceDataset, View
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import UsedInputReceipt


def checked(result,port):
    assert result.outcome == 'succeeded',result.diagnostics
    return result.output(port)


@pytest.mark.parametrize('kind',['original','dataset','view','product'])
def test_typed_value_retains_semantics_and_lineage_across_independent_stores(tmp_path,kind):
    original = Material(b'exact publisher source','text/csv','publisher.table')
    use = SourceUse(SourceCoordinate('publisher.table',issue_id='2026-11',asset_id='main',material_identity=original.identity),
                    'original','asserted','sha256:'+original.identity.sha256)
    lineage = (UsedInputReceipt('original',original.identity,'text/csv','reference_only','publisher.table'),)
    dataset = SourceDataset('publisher.table',({'metric':'value','value':7},),{'unit':'RUB'},'2026-11',lineage,source_uses=(use,))
    value = {'original':original,'dataset':dataset,'view':View(dataset,lineage=lineage,source_uses=(use,)),
             'product':EncodedProduct(b'workbook','application/octet-stream',lineage,source_uses=(use,))}[kind]
    left,right = LocalFileStore(tmp_path/'left'),LocalFileStore(tmp_path/'right')
    with StrategyBox(providers={'filestore':left}) as first:
        encoded = checked(first.invoke('command.value.encode',inputs={'value':value}),'representation')
        reference = checked(first.invoke('command.artifact.commit',inputs={'material':encoded,'destination':'objects'}),'reference')
        retained = checked(first.invoke('command.material.read',inputs={'location':reference}),'material')
    with StrategyBox(providers={'filestore':right}) as second:
        transferred = checked(second.invoke('command.artifact.commit',inputs={'material':retained,'destination':'copy'}),'reference')
        read = checked(second.invoke('command.material.read',inputs={'location':transferred}),'material')
        restored = checked(second.invoke('command.value.decode',inputs={'representation':read}),'value')
    assert restored == value
    assert reference.identity == transferred.identity == ByteIdentity.of(encoded.data)


def test_immutable_retry_uses_same_content_reference(tmp_path):
    store = LocalFileStore(tmp_path)
    material = Material(b'unchanged')
    with StrategyBox(providers={'filestore':store}) as box:
        first = checked(box.invoke('command.artifact.commit',inputs={'material':material,'destination':'objects'}),'reference')
        again = checked(box.invoke('command.artifact.commit',inputs={'material':material,'destination':'objects'}),'reference')
    assert first == again
    assert store.read_bytes(first.location) == material.data


def test_retained_bytes_tamper_cannot_restore_under_previous_content_identity(tmp_path):
    store = LocalFileStore(tmp_path)
    with StrategyBox(providers={'filestore':store}) as box:
        reference = checked(box.invoke('command.artifact.commit',inputs={'material':Material(b'original'),'destination':'objects'}),'reference')
        store.checked_file_path(reference.location).write_bytes(b'changed')
        rejected = box.invoke('command.material.read',inputs={'location':reference})
    assert rejected.outcome == 'failed' and 'material' not in rejected.outputs
