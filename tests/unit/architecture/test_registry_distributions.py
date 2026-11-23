"""Canonical source, operation and profile bytes survive distribution packaging."""

from pathlib import Path
import runpy

import pytest


def _fixture():
    root = Path(__file__).resolve().parents[3]
    inspector = runpy.run_path(str(root / "scripts/inspect_reference_wheel.py"))
    source = inspector["REGISTRY_SOURCE"]
    members = {
        "stratbox/registry/" + path.relative_to(source).as_posix(): path.read_bytes()
        for path in source.rglob("*") if path.is_file()
        and (path.suffix in {".yaml", ".yml"} or path.name == "__init__.py")
    }
    return inspector["_verify_registry_members"], members


def test_registry_distribution_includes_every_declaration_and_package_boundary():
    verify, members = _fixture()
    result = verify(set(members), "", members.__getitem__)
    assert result["owners"] > 0
    assert result["declarations"] > result["owners"]


@pytest.mark.parametrize("kind", ["SOURCE_", "OPERATION_", "PROFILE_", "OWNER.yaml", "__init__.py"])
def test_omitted_registry_resource_is_rejected(kind):
    verify, members = _fixture()
    victim = next(name for name in members if Path(name).name.startswith(kind))
    del members[victim]
    with pytest.raises(ValueError, match="Registry distribution mismatch: missing="):
        verify(set(members), "", members.__getitem__)


def test_changed_registry_metadata_and_unexpected_declarations_are_rejected():
    verify, members = _fixture()
    victim = next(name for name in members if Path(name).name.startswith("OPERATION_"))
    original = members[victim]
    members[victim] = b"{}"
    with pytest.raises(ValueError, match="changed=\\['"):
        verify(set(members), "", members.__getitem__)
    members[victim] = original
    members["stratbox/registry/extra/sources/SOURCE_extra.yaml"] = b"{}"
    with pytest.raises(ValueError, match="extra=\\['"):
        verify(set(members), "", members.__getitem__)


def test_sdist_prefix_preserves_the_same_registry_identity():
    verify, members = _fixture()
    prefix = "stratbox-example/src/"
    archive = {prefix + name: content for name, content in members.items()}
    assert verify(set(archive), prefix, archive.__getitem__) == verify(
        set(members), "", members.__getitem__
    )
