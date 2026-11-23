"""Exercise offline maintenance and ZIP-level resource admission without network IO."""

from __future__ import annotations

from hashlib import sha256
from importlib import resources
import json
from pathlib import Path
import runpy
from zipfile import ZipFile

import pytest

from stratbox.shared.reference.assets import load_reference

_ROOT = Path(__file__).resolve().parents[3]


def _tool(name: str):
    return runpy.run_path(str(_ROOT / "scripts" / name))


def _domain_materials():
    """Supply complete domain and registry resources to archive fixtures."""
    package = _ROOT / "src/stratbox"
    for path in sorted(package.rglob("*")):
        if path.is_file() and (path.suffix in {".py", ".pyi"} or path.name == "py.typed"):
            yield "stratbox/" + path.relative_to(package).as_posix(), path.read_bytes()
    source = _ROOT / "src/stratbox/domains"
    asset = _tool("inspect_reference_wheel.py")["_domain_asset"]
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source).as_posix()
        if path.is_file() and asset(relative):
            yield "stratbox/domains/" + relative, path.read_bytes()
    registry = package / "operations" / "specifications"
    for path in sorted(registry.rglob("*")):
        if path.is_file() and path.suffix in {".yaml", ".yml"}:
            yield "stratbox/operations/specifications/" + path.relative_to(registry).as_posix(), path.read_bytes()


def test_reference_edition_verifier_covers_all_bundled_editions(capsys):
    verify = _tool("reference_editions.py")["verify"]
    verify("all")
    captured = capsys.readouterr().out
    assert "OK  banks:" in captured
    assert "OK  okved2:" in captured
    assert "OK  geography:" in captured
    assert captured.count("snapshot") == 3


def test_stage_edition_never_overwrites_historical_material(tmp_path):
    stage = _tool("reference_editions.py")["stage"]
    package = "stratbox.shared.reference.banks"
    source = resources.files(package).joinpath("_resources")
    original = load_reference(package)
    base = tmp_path / "src/stratbox/shared/reference/banks/_resources"
    base.mkdir(parents=True)
    for asset in original.edition.assets:
        location = base.joinpath(*asset.path.split("/"))
        location.parent.mkdir(parents=True, exist_ok=True)
        location.write_bytes(original.read(asset.role))
    manifest = source.joinpath("manifest.json").read_bytes()
    (base / "manifest.json").write_bytes(manifest)
    fresh = base / "aliases" / "2026-12-new.csv"
    fresh.write_bytes(original.read("aliases"))
    stage.__globals__["_manifest_path"] = lambda _family: base / "manifest.json"
    stage("banks", "reviewed-2026-12", ["aliases=aliases/2026-12-new.csv"],
          activate=True, publisher="test-procedure", source_url=None, published_at=None,
          effective_from=None, effective_to=None)
    revised = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    assert revised["active_edition"] == "reviewed-2026-12"
    assert len(revised["editions"]) == 2
    old = revised["editions"][0]
    new = revised["editions"][1]
    assert old["edition_id"] == original.edition.edition_id
    assert new["assets"][1]["path"] == "aliases/2026-12-new.csv"
    assert new["assets"][1]["sha256"] == sha256(fresh.read_bytes()).hexdigest()
    assert old["assets"][1]["path"] != new["assets"][1]["path"]
    with pytest.raises(ValueError, match="already exists"):
        stage("banks", "reviewed-2026-12", [], activate=False,
              publisher=None, source_url=None, published_at=None,
              effective_from=None, effective_to=None)


def test_zip_validator_checks_bytes_and_rejects_missing_assets(tmp_path):
    check = _tool("inspect_reference_wheel.py")["verify_wheel"]
    wheel = tmp_path / "stratbox-0.0-py3-none-any.whl"
    families = ("banks", "okved2", "geography")
    with ZipFile(wheel, "w") as archive:
        for name, raw in _domain_materials():
            archive.writestr(name, raw)
        for family in families:
            package = f"stratbox.shared.reference.{family}"
            bundled = resources.files(package).joinpath("_resources")
            archive.writestr(
                f"stratbox/shared/reference/{family}/_resources/manifest.json",
                bundled.joinpath("manifest.json").read_bytes())
            ref = load_reference(package)
            for asset in ref.edition.assets:
                archive.writestr(
                    f"stratbox/shared/reference/{family}/_resources/{asset.path}",
                    ref.read(asset.role))
    result = check(str(wheel))
    assert result["result"] == "verified"
    assert result["asset_occurrences"] == {"banks": 4, "okved2": 3, "geography": 1}
    with ZipFile(wheel, "a") as archive:
        archive.writestr("stratbox/shared/data/identity.py", b"# should be absent")
    with pytest.raises(ValueError, match="obsolete shared paths"):
        check(str(wheel))


def _stage_fixture(tmp_path):
    from stratbox.shared.reference.assets import load_reference
    package = "stratbox.shared.reference.banks"
    bundle = load_reference(package)
    base = tmp_path / "src/stratbox/shared/reference/banks/_resources"
    base.mkdir(parents=True)
    for asset in bundle.edition.assets:
        target = base.joinpath(*asset.path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bundle.read(asset.role))
    manifest = resources.files(package).joinpath("_resources", "manifest.json").read_bytes()
    (base / "manifest.json").write_bytes(manifest)
    return base, bundle


def test_stage_rejects_duplicate_new_paths_without_writing_manifest(tmp_path):
    stage = _tool("reference_editions.py")["stage"]
    base, bundle = _stage_fixture(tmp_path)
    new = base / "aliases" / "same.csv"
    new.write_bytes(bundle.read("aliases"))
    stage.__globals__["_manifest_path"] = lambda family: base / "manifest.json"
    original = (base / "manifest.json").read_bytes()
    with pytest.raises(ValueError, match="share one path"):
        stage("banks", "new-2026", [
            "aliases=aliases/same.csv", "legacy_selection=aliases/same.csv"
        ], activate=True, publisher=None, source_url=None,
          published_at=None, effective_from=None, effective_to=None)
    assert (base / "manifest.json").read_bytes() == original


def test_stage_rejects_corrupted_inactive_historical_edition(tmp_path):
    from copy import deepcopy
    from stratbox.shared.reference.assets import ReferenceError
    stage = _tool("reference_editions.py")["stage"]
    base, bundle = _stage_fixture(tmp_path)
    path = base / "manifest.json"
    manifest = json.loads(path.read_bytes())
    historical = deepcopy(manifest["editions"][0])
    historical["edition_id"] = "historical-2026"
    historical["assets"][0]["sha256"] = "0" * 64
    manifest["editions"].insert(0, historical)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    stage.__globals__["_manifest_path"] = lambda family: path
    original = path.read_bytes()
    with pytest.raises(ReferenceError, match="corrupted"):
        stage("banks", "next-2026", [], activate=True, publisher=None,
              source_url=None, published_at=None, effective_from=None,
              effective_to=None)
    assert path.read_bytes() == original


def test_wheel_duplicate_zip_members_rejected(tmp_path):
    check = _tool("inspect_reference_wheel.py")["verify_wheel"]
    wheel = tmp_path / "example.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr("stratbox/shared/identity.py", "a")
        archive.writestr("stratbox/shared/identity.py", "b")
    with pytest.raises(ValueError, match="duplicate"):
        check(str(wheel))


def test_sdist_validator_checks_all_declared_resource_materials(tmp_path):
    import io
    import tarfile
    check = _tool("inspect_reference_wheel.py")["verify_sdist"]
    sdist = tmp_path / "stratbox-0.16.0.tar.gz"
    root = "stratbox-0.16.0/src/"
    with tarfile.open(sdist, "w:gz") as archive:
        def add(name, raw):
            entry = tarfile.TarInfo(root + name)
            entry.size = len(raw)
            archive.addfile(entry, io.BytesIO(raw))
        for name, raw in _domain_materials():
            add(name, raw)
        for family in ("banks", "okved2", "geography"):
            package = "stratbox.shared.reference." + family
            source = resources.files(package).joinpath("_resources")
            add(f"stratbox/shared/reference/{family}/_resources/manifest.json",
                source.joinpath("manifest.json").read_bytes())
            for asset in load_reference(package).edition.assets:
                add(f"stratbox/shared/reference/{family}/_resources/{asset.path}",
                    load_reference(package).read(asset.role))
    result = check(str(sdist))
    assert result["result"] == "verified"
    assert result["asset_occurrences"] == {"banks": 4, "okved2": 3, "geography": 1}
