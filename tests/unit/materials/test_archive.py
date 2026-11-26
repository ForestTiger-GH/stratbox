from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

import pytest
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material


def checked(result, port):
    assert result.outcome == 'succeeded', result.diagnostics
    return result.output(port)


def archive_bytes(names):
    stream = BytesIO()
    with ZipFile(stream, 'w', ZIP_DEFLATED) as archive:
        for name in names:
            archive.writestr(name, b'exact source')
    return stream.getvalue()


def test_archive_composes_supplied_materials_and_retains_exact_member_bytes():
    members = (Material(b'%PDF-1.7\nsource', 'application/pdf', metadata={'member':'sources/source.pdf'}),
               Material(b'exact workbook', metadata={'member':'workbook.xlsx'}),
               Material(b'selected scope', 'text/plain', metadata={'member':'scope.txt'}))
    with StrategyBox() as box:
        packed = checked(box.invoke('command.archive.pack', inputs={'members':members}), 'material')
        unpacked = checked(box.invoke('command.archive.unpack', inputs={'material':packed}), 'members')
    assert tuple((m.metadata['member'],m.data) for m in unpacked) == tuple((m.metadata['member'],m.data) for m in members)
    assert all(m.metadata['parent'] == packed.identity.sha256 for m in unpacked)
    assert packed.identity not in {member.identity for member in members}
    assert set(packed.lineage) == {member.identity for member in members}


@pytest.mark.parametrize('names', [('../unsafe',),('/absolute',),('C:/drive',),('same','SAME'),
    ('file','file/child'),('a/b','a/B'),('dir\\file',),('dir/../file',),('dir//file',)])
@pytest.mark.parametrize('mode', ['pack','unpack'])
def test_unsafe_aliases_and_file_parent_conflicts_are_rejected(names, mode):
    with StrategyBox() as box:
        if mode == 'pack':
            inputs = {'members':tuple(Material(b'data',metadata={'member':name}) for name in names)}
            result = box.invoke('command.archive.pack',inputs=inputs)
        else:
            result = box.invoke('command.archive.unpack',inputs={'material':Material(archive_bytes(names))})
        assert result.outcome != 'succeeded', (names,result.diagnostics)
        assert not result.effects


def test_unpack_rejects_symbolic_links():
    stream = BytesIO()
    with ZipFile(stream,'w') as archive:
        info = ZipInfo('link')
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        archive.writestr(info,'target')
    with StrategyBox() as box:
        result = box.invoke('command.archive.unpack',inputs={'material':Material(stream.getvalue())})
        assert result.outcome != 'succeeded'


def test_packing_null_member_name_is_rejected_before_zip_truncates_it():
    with StrategyBox() as box:
        result=box.invoke('command.archive.pack',inputs={'members':(Material(b'x',metadata={'member':'a\x00b'}),)})
    assert result.outcome!='succeeded'
