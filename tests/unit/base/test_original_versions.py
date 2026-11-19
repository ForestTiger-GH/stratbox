"""Publisher-neutral original comparison with qualified prior-absence evidence."""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from stratbox.shared.identity import ByteIdentity
from stratbox.shared.source_publications import (
    SourceAssetIdentity, QualifiedInventory, InventoryAbsenceEvidence,
)
from stratbox.core.operations.source.version_comparison import (
    CompareOriginalVersionsRequest, OriginalVersion, compare_original_versions,
)
from stratbox.domains.registry import operation_catalog


def _candidate(asset: SourceAssetIdentity, content: bytes):
    return OriginalVersion(asset.source_id, ByteIdentity.of(content))


def _version(request):
    result = compare_original_versions(request)
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def inventory(known=(), *, series="rosstat.test", floor="2026-01"):
    return QualifiedInventory(
        series, "recent_listing", "tested-profile", "tested-version",
        datetime(2026, 11, 19, tzinfo=timezone.utc), ByteIdentity.of(b"<a>snapshot</a>"),
        tuple(known), "trusted-owner-revision-1",
        issue_lower_bound=floor,
    )


def test_initial_has_silent_distinct_transition():
    key = SourceAssetIdentity("rosstat.test", "2026-08", "workbook")
    first = _version(CompareOriginalVersionsRequest(_candidate(key, b"A"), "initial"))
    assert first.state == "first_seen"
    assert first.transition_id and first.old_identity is None
    assert first.transition_id == _version(
        CompareOriginalVersionsRequest(_candidate(key, b"A"), "initial")
    ).transition_id


def test_proven_absence_distinguishes_new_issue_from_extra_asset():
    main = SourceAssetIdentity("rosstat.test", "2026-08", "main_workbook")
    additional = SourceAssetIdentity("rosstat.test", "2026-08", "appendix_1")
    future = SourceAssetIdentity("rosstat.test", "2026-09", "main_workbook")
    verified = inventory((main,))
    added = _version(CompareOriginalVersionsRequest(
        _candidate(additional, b"A"), "absent_proven",
        absence=InventoryAbsenceEvidence(additional, verified),
    ))
    fresh = _version(CompareOriginalVersionsRequest(
        _candidate(future, b"A"), "absent_proven",
        absence=InventoryAbsenceEvidence(future, verified),
    ))
    assert added.state == "new_asset"
    assert fresh.state == "new_release"
    assert added.transition_id != fresh.transition_id


def test_wrong_inventory_and_existing_asset_cannot_prove_absence():
    key = SourceAssetIdentity("rosstat.test", "2026-08", "main")
    with pytest.raises(ValueError):
        InventoryAbsenceEvidence(key, inventory((key,)))
    with pytest.raises(ValueError):
        InventoryAbsenceEvidence(key, inventory(series="rosstat.other"))
    with pytest.raises(ValueError):
        InventoryAbsenceEvidence(key, inventory(floor="2027-01"))
    with pytest.raises(ValueError):
        CompareOriginalVersionsRequest(_candidate(key, b"A"), "absent_proven")
    with pytest.raises(ValueError):
        CompareOriginalVersionsRequest(_candidate(key, b"A"), "absent_proven", absence="f" * 64)


def test_a_b_a_b_chain_needs_confirmed_parent_and_retry_is_idempotent():
    key = SourceAssetIdentity("rosstat.test", "2026-08", "main")
    a, b = _candidate(key, b"A"), _candidate(key, b"B")
    first = _version(CompareOriginalVersionsRequest(a, "initial"))
    with pytest.raises(ValueError):
        CompareOriginalVersionsRequest(b, "available", a)
    ab = _version(CompareOriginalVersionsRequest(
        b, "available", replace(a, transition_id=first.transition_id),
    ))
    assert ab.state == "revised"
    assert ab.transition_id == _version(CompareOriginalVersionsRequest(
        b, "available", replace(a, transition_id=first.transition_id),
    )).transition_id
    ba = _version(CompareOriginalVersionsRequest(
        a, "available", replace(b, transition_id=ab.transition_id),
    ))
    ab_again = _version(CompareOriginalVersionsRequest(
        b, "available", replace(a, transition_id=ba.transition_id),
    ))
    assert len({ab.transition_id, ba.transition_id, ab_again.transition_id}) == 3


def test_unchanged_and_unavailable():
    key = SourceAssetIdentity("rosstat.test", "2026-08", "main")
    a = _candidate(key, b"A")
    prior = replace(a, transition_id="f" * 64)
    assert _version(CompareOriginalVersionsRequest(a, "available", prior)).state == "unchanged"
    result = _version(CompareOriginalVersionsRequest(a, "unavailable"))
    assert result.state == "indeterminate" and result.transition_id is None


def test_cross_asset_compare_rejected_and_keys_stable():
    asset_a = SourceAssetIdentity("rosstat.test", "2026-08", "report")
    asset_b = SourceAssetIdentity("rosstat.test", "2026-08", "tables")
    assert asset_a.source_id != asset_b.source_id
    with pytest.raises(ValueError):
        CompareOriginalVersionsRequest(
            _candidate(asset_a, b"A"), "available",
            replace(_candidate(asset_b, b"A"), transition_id="a" * 64),
        )


def test_public_source_receive_to_store_handler_and_comparator_registered():
    catalog = operation_catalog()
    definition, handler, _ = catalog.resolve("source.receive_to_store", 1)
    assert definition.operation_id == "source.receive_to_store"
    assert handler.__name__ == "receive_to_store"
    definition, handler, _ = catalog.resolve("source.compare_original_versions", 1)
    assert handler.__name__ == "compare_original_versions"
