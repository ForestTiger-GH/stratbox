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
        for name in ("identity.py", "evidence.py"):
            archive.writestr(f"stratbox/shared/{name}", b"# fixture")
        archive.writestr("stratbox/shared/data/datasets.py", b"# fixture")
        archive.writestr("stratbox/shared/reference/assets.py", b"# fixture")
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
