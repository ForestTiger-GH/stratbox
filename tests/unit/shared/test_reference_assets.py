"""Packaged reference editions are deterministic and checked before decoding."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from importlib import resources

import pytest

from stratbox.shared.identity import ByteIdentity
from stratbox.shared.reference.assets import ReferenceError, load_reference


@pytest.mark.parametrize("package,count", [
    ("stratbox.shared.reference.banks", 4),
    ("stratbox.shared.reference.okved2", 3),
    ("stratbox.shared.reference.geography", 1),
])
def test_complete_packaged_reference_and_deterministic_snapshot(package, count):
    bundle = load_reference(package)
    assert len(bundle.edition.assets) == count
    assert bundle.snapshot_identity == load_reference(package, edition_id=bundle.edition.edition_id).snapshot_identity
    assert bundle.edition.published_at is None
    bundle.validate_all()
    for asset in bundle.edition.assets:
        data = bundle.read(asset.role)
        assert len(data) == asset.identity.size
        assert sha256(data).hexdigest() == asset.identity.sha256


def test_used_reference_asset_receipt_includes_edition_identity():
    bundle = load_reference("stratbox.shared.reference.banks")
    inputs = []
    bundle.read("aliases", inputs=inputs)
    assert len(inputs) == 1
    assert inputs[0].role == "aliases"
    assert inputs[0].version == bundle.snapshot_identity
    assert inputs[0].identity == bundle.asset("aliases").identity
    assert inputs[0].source_id.startswith("reference.banks:")


def test_reference_corruption_is_not_silently_swallowed():
    bundle = load_reference("stratbox.shared.reference.banks")
    original = bundle.asset("aliases")
    bogus = replace(original, identity=ByteIdentity("0" * 64, original.identity.size))
    corrupted_edition = replace(bundle.edition, assets=tuple(
        bogus if asset.role == "aliases" else asset for asset in bundle.edition.assets))
    corrupted = replace(bundle, edition=corrupted_edition)
    with pytest.raises(ReferenceError, match="integrity mismatch"):
        corrupted.read("aliases")
    with pytest.raises(ReferenceError, match="Undeclared"):
        bundle.read("nonexistent")


def test_invalid_explicit_edition_is_rejected():
    with pytest.raises(ReferenceError, match="edition"):
        load_reference("stratbox.shared.reference.okved2", edition_id="unknown-edition")


def test_reference_root_does_not_resolve_external_package():
    with pytest.raises(ReferenceError, match="owned reference"):
        load_reference("os.path")


def test_reference_snapshot_includes_semantically_relevant_edition_metadata():
    from stratbox.shared.identity import canonical_manifest_bytes
    bundle = load_reference("stratbox.shared.reference.banks")
    manifest = bundle.edition
    assert manifest.source_url is None
    assert manifest.effective_from is None
    assert bundle.snapshot_identity == load_reference("stratbox.shared.reference.banks").snapshot_identity
    assert ByteIdentity.of(canonical_manifest_bytes({"published_at": None})) != (
        ByteIdentity.of(canonical_manifest_bytes({"published_at": "2026-11-18"}))
    )
