"""Content-only reference and distribution integrity without component editions."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import runpy
from zipfile import ZipFile
import pytest
from stratbox.shared.reference.assets import load_reference, parse_reference_manifest, ReferenceError

ROOT=Path(__file__).resolve().parents[3]


def test_packaged_references_have_direct_assets_without_version_registry():
    from importlib.resources import files
    for family in ('banks','geography','okved2'):
        package='stratbox.shared.reference.'+family
        document=json.loads(files(package).joinpath('_resources','manifest.json').read_bytes())
        assert not set(document)&{'editions','active_edition','manifest_schema_version'}
        assert document['assets']
        load_reference(package).validate_all()


def test_old_reference_release_envelope_is_rejected():
    value={'reference_id':'reference.banks','assets':[],'editions':[{}]}
    with pytest.raises(ReferenceError,match='release lifecycle'):
        parse_reference_manifest('stratbox.shared.reference.banks',value)


def test_archive_verifier_detects_missing_and_changed_package_bytes(tmp_path):
    tool=runpy.run_path(str(ROOT/'scripts/inspect_reference_wheel.py'))
    package=ROOT/'src/stratbox'
    expected=tool['inventory']()
    wheel=tmp_path/'stratbox-test.whl'
    with ZipFile(wheel,'w') as archive:
        for name in expected:
            archive.writestr('stratbox/'+name,(package/name).read_bytes())
    assert tool['inspect_archive'](wheel)['members']==len(expected)
    removed=next(name for name in expected if name.endswith('manifest.json'))
    damaged=tmp_path/'stratbox-damaged.whl'
    with ZipFile(damaged,'w') as archive:
        for name in expected:
            if name!=removed:
                archive.writestr('stratbox/'+name,(package/name).read_bytes())
    with pytest.raises(ValueError,match='archive.mismatch'):
        tool['inspect_archive'](damaged)


def test_pure_asset_manifest_rejects_traversal_and_duplicate_roles():
    from importlib.resources import files
    package='stratbox.shared.reference.banks'
    document=json.loads(files(package).joinpath('_resources','manifest.json').read_bytes())
    document['assets'][0]['path']='../outside.csv'
    with pytest.raises(ReferenceError,match='escapes'):
        parse_reference_manifest(package,document)
