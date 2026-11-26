"""Delivered code and scientific resources must retain exact source bytes."""
from pathlib import Path
import runpy
from zipfile import ZipFile
import pytest

ROOT=Path(__file__).resolve().parents[3]


def tool(): return runpy.run_path(str(ROOT/'scripts/inspect_reference_wheel.py'))


def write_archive(path,source,inventory,*,missing=(),changed=(),extra=None):
    with ZipFile(path,'w') as archive:
        for name in inventory:
            if name not in missing:
                data=(source/name).read_bytes()
                archive.writestr('stratbox/'+name,data+b'\nchanged' if name in changed else data)
        for name,data in (extra or {}).items(): archive.writestr('stratbox/'+name,data)


@pytest.mark.parametrize('mutation',('missing','changed','extra','bytecode'))
def test_executable_mutation_is_rejected(tmp_path,mutation):
    check=tool();source=ROOT/'src/stratbox';inventory=check['inventory']()
    victim='core/execution/service.py'
    options={'missing':(victim,)} if mutation=='missing' else {'changed':(victim,)} if mutation=='changed' else {
        'extra':{'undeclared.py' if mutation=='extra' else '__pycache__/undeclared.pyc':b'executable'}}
    archive=tmp_path/'stratbox-test.whl'
    write_archive(archive,source,inventory,**options)
    with pytest.raises(ValueError,match='archive.mismatch'):check['inspect_archive'](archive)


def test_future_binary_asset_is_admitted_and_cache_excluded(tmp_path):
    check=tool();source=tmp_path/'source';source.mkdir()
    (source/'__init__.py').write_text('')
    (source/'new-model.parquet').write_bytes(b'binary scientific artifact')
    (source/'.cache').mkdir();(source/'.cache'/'ignored').write_bytes(b'cache')
    inventory=check['inventory'](source)
    assert set(inventory)=={'__init__.py','new-model.parquet'}
    archive=tmp_path/'stratbox-test.whl'
    write_archive(archive,source,inventory)
    assert check['inspect_archive'](archive,source=source)['members']==2
    write_archive(archive,source,inventory,missing=('new-model.parquet',))
    with pytest.raises(ValueError,match='archive.mismatch'):check['inspect_archive'](archive,source=source)
