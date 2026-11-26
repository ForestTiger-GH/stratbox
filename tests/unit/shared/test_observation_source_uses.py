"""Relational input coordinates retain publisher and issue attribution."""
from dataclasses import replace
import pytest
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse, ValueContext, source_use_value, source_use_from
from stratbox.shared.data.values import fingerprint
from stratbox.shared.identity import ByteIdentity


def test_distinct_source_issue_roles_remain_related_after_replay():
    uses = (SourceUse(SourceCoordinate("publisher.a", source_group_id="table", issue_id="issue-x",
        material_identity=ByteIdentity.of(b"a")), "before", "domain_validated"),
        SourceUse(SourceCoordinate("publisher.b", source_group_id="table", issue_id="issue-y",
        material_identity=ByteIdentity.of(b"b")), "after", "domain_validated"))
    restored = tuple(source_use_from(source_use_value(use)) for use in uses)
    assert restored == uses
    assert [(u.input_role, u.coordinate.source_id, u.coordinate.issue_id) for u in restored] == [
        ("before", "publisher.a", "issue-x"), ("after", "publisher.b", "issue-y")]
    assert fingerprint(uses) != fingerprint(uses[::-1])
    assert ValueContext(restored).source_ids == ("publisher.a", "publisher.b")


def test_untyped_source_uses_cannot_be_admitted():
    with pytest.raises(ValueError, match="source.context"):
        ValueContext(({"source_id":"publisher.a"},))
    with pytest.raises(ValueError, match="source.use_encoding"):
        source_use_from({"coordinate": {"source_id": "publisher.a"}})
