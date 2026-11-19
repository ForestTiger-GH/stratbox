"""Publisher-neutral original-byte comparison and registry execution."""

from dataclasses import replace

import pytest

from stratbox.shared.identity import ByteIdentity
from stratbox.core.operations.source.version_comparison import (
    CompareOriginalVersionsRequest, OriginalVersion, compare_original_versions,
)
from stratbox.domains.registry import operation_catalog


def _version(content: bytes, *, parent=None, source_id="original.demo.issue.asset"):
    return OriginalVersion(source_id, ByteIdentity.of(content), parent)


def _value(request):
    result = compare_original_versions(request)
    assert result.outcome == "succeeded"
    return result.value


def test_first_seen_and_new_release_are_different():
    candidate = _version(b"one")
    observed = _value(CompareOriginalVersionsRequest(candidate, "confirmed_absent"))
    assert observed.state == "first_seen"
    assert observed.old_identity is None
    published = _value(CompareOriginalVersionsRequest(
        candidate, "confirmed_absent", prior_inventory_identity="f" * 64))
    assert published.state == "new_release"
    assert published.transition_id != observed.transition_id


def test_revision_unchanged_and_unavailable():
    candidate = _version(b"two")
    baseline = _version(b"one")
    revised = _value(CompareOriginalVersionsRequest(candidate, "available", baseline))
    assert revised.state == "revised" and revised.old_identity == baseline.identity
    assert revised.transition_id
    same = _value(CompareOriginalVersionsRequest(baseline, "available", baseline))
    assert same.state == "unchanged" and same.transition_id is None
    unknown = _value(CompareOriginalVersionsRequest(candidate, "unavailable"))
    assert unknown.state == "indeterminate" and unknown.transition_id is None


def test_a_b_a_b_transitions_are_unique_and_retry_is_stable():
    a, b = _version(b"A"), _version(b"B")
    ab = _value(CompareOriginalVersionsRequest(b, "available", a))
    assert ab.transition_id == _value(CompareOriginalVersionsRequest(b, "available", a)).transition_id
    ba = _value(CompareOriginalVersionsRequest(a, "available", replace(b, transition_id=ab.transition_id)))
    ab2 = _value(CompareOriginalVersionsRequest(b, "available", replace(a, transition_id=ba.transition_id)))
    assert ab2.transition_id != ab.transition_id


def test_cross_asset_compare_is_invalid():
    with pytest.raises(ValueError):
        CompareOriginalVersionsRequest(_version(b"A"), "available", _version(b"A", source_id="other"))


def test_public_source_receive_to_store_handler_is_registered():
    catalog = operation_catalog()
    definition, handler, _ = catalog.resolve("source.receive_to_store", 1)
    assert definition.operation_id == "source.receive_to_store"
    assert handler.__name__ == "receive_to_store"
    definition, handler, _ = catalog.resolve("source.compare_original_versions", 1)
    assert handler.__name__ == "compare_original_versions"
