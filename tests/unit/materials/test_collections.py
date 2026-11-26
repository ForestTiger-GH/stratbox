from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

import pytest
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material, Assessment
from stratbox.shared.data.coverage import SnapshotCoverage, CoverageDimension
from stratbox.shared.identity import ByteIdentity


def good(result, port):
    assert result.outcome == 'succeeded',result.diagnostics
    return result.output(port)


def test_explicit_partial_collection_metadata_and_content_identities_replay():
    value = {'members':({'name':'source.csv','role':'source','identity':ByteIdentity.of(b'original')},
                        {'name':'view.xlsx','role':'product','identity':ByteIdentity.of(b'workbook')}),
        'assessment':Assessment('partial',expected=('source','missing','view'),observed=('source','view'),
            coverage=SnapshotCoverage('partial','Selected publications',(
                CoverageDimension('source',requested=('source','missing','view'),output=('source','view'),missing=('missing',)),)))}
    with StrategyBox() as box:
        encoded = good(box.invoke('command.value.encode',inputs={'value':value}),'representation')
        replayed = good(box.invoke('command.value.decode',inputs={'representation':encoded}),'value')
    assert replayed == value
    assert not replayed['assessment'].complete
    assert replayed['members'][0]['identity'] != replayed['members'][1]['identity']


def test_nested_archive_supports_more_than_five_hundred_explicit_members():
    members = tuple(Material(str(i).encode(),metadata={'member':f'2026/101/table-{i}.csv'}) for i in range(501))
    with StrategyBox() as box:
        packed = good(box.invoke('command.archive.pack',inputs={'members':members},parameters={'max_members':501}),'material')
        unpacked = good(box.invoke('command.archive.unpack',inputs={'material':packed},parameters={'max_members':501}),'members')
    assert len(unpacked) == 501 and unpacked[-1].data == b'500'
    assert unpacked[-1].metadata['member'] == '2026/101/table-500.csv'


@pytest.mark.parametrize('parameters', [{'max_members':1},{'max_unpacked_bytes':3}])
def test_archive_member_and_expansion_limits_apply_before_selection(parameters):
    stream = BytesIO()
    with ZipFile(stream,'w',ZIP_DEFLATED) as archive:
        archive.writestr('first',b'a'*10000)
        archive.writestr('second',b'b'*10000)
    with StrategyBox() as box:
        result = box.invoke('command.archive.unpack',inputs={'material':Material(stream.getvalue())},
            parameters={**parameters,'names':('first',)})
    assert result.outcome == 'failed'
    assert 'members' not in result.outputs


def test_archive_packing_has_an_exact_output_byte_limit():
    members = (Material(b'payload',metadata={'member':'a'}),)
    with StrategyBox() as box:
        result = box.invoke('command.archive.pack',inputs={'members':members},parameters={'max_bytes':1})
    assert result.outcome == 'failed' and 'material' not in result.outputs
