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


def test_independently_pinned_historical_reference_bytes():
    # Golden vectors recorded from the original Git blobs before the shared refactor.
    # These must NOT be rewritten to follow manifest changes.
    golden = {
        "banks": {
            "official_xlsx": ("8af8c25cd4c809a28c415bd9a531cc0ef0b90e534124a17bbef0c8463ac657f6", 142625),
            "aliases": ("25e0e6114e56d5f8b485442d930f07e281e5002309d928e33f9dcf789026a13f", 622),
            "default_selection": ("dbd4ed1be2ff03f8e2eaa44a06a4e31473941861b93e38860259cbf1ee41bb50", 1382),
            "legacy_selection": ("3e4fb049f49370367872840a113750a2cc97c64149d46d6d3320a0cc37f94309", 330),
        },
        "okved2": {
            "data": ("b9b05bb8d7edc6315d899978fe22ae46f4103ad7300625645d3ef8c9b8d4a280", 259822),
            "meta": ("f62a642ed56d40e99a57d5c355326e911c091232e4d7d5948b5999500129fa40", 6804),
            "structure": ("62d9de91ece8ef0b5901a5024726da9c661dfdca708e7e3229802a6581691dfa", 726),
        },
    }
    for family, roles in golden.items():
        bundle = load_reference("stratbox.shared.reference." + family,
                                edition_id="bundled-original-2026-11")
        for role, (digest, size) in roles.items():
            data = bundle.read(role)
            assert sha256(data).hexdigest() == digest
            assert len(data) == size


def test_pure_manifest_validation_rejects_duplicate_and_missing_roles():
    from copy import deepcopy
    import json
    from stratbox.shared.reference.assets import parse_reference_manifest
    package = "stratbox.shared.reference.banks"
    original = resources.files(package).joinpath("_resources", "manifest.json").read_bytes()
    data = json.loads(original)
    active, editions = parse_reference_manifest(package, original)
    assert active == editions[0].edition_id
    duplicate = deepcopy(data)
    duplicate["editions"].append(deepcopy(duplicate["editions"][0]))
    with pytest.raises(ReferenceError, match="duplicate"):
        parse_reference_manifest(package, duplicate)
    incomplete = deepcopy(data)
    incomplete["editions"][0]["assets"] = incomplete["editions"][0]["assets"][:1]
    with pytest.raises(ReferenceError, match="Incomplete"):
        parse_reference_manifest(package, incomplete)
    collision = deepcopy(data)
    collision["editions"][0]["assets"][1]["path"] = collision["editions"][0]["assets"][0]["path"]
    with pytest.raises(ReferenceError, match="Duplicate"):
        parse_reference_manifest(package, collision)
