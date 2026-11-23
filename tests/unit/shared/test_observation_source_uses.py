"""Relational source coordinates survive observation retention unchanged."""
from dataclasses import replace
import json
import pytest
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.identity import ByteIdentity


def test_distinct_source_issue_roles_remain_related_after_replay():
    uses = (SourceUse(SourceCoordinate("publisher.a", source_group_id="table", issue_id="issue-x",
        material_identity=ByteIdentity.of(b"a")), "before", "domain_validated"),
        SourceUse(SourceCoordinate("publisher.b", source_group_id="table", issue_id="issue-y",
        material_identity=ByteIdentity.of(b"b")), "after", "domain_validated"))
    value = ObservationBatch("caller.dataset", 1, "caller.release", (), (), uses)
    restored = observations_from_snapshot(observation_snapshot(value))
    assert restored.source_uses == uses
    assert [(u.input_role, u.coordinate.source_id, u.coordinate.issue_id) for u in restored.source_uses] == [
        ("before", "publisher.a", "issue-x"), ("after", "publisher.b", "issue-y")]
    assert observation_snapshot(value).identity != observation_snapshot(replace(value, source_uses=uses[::-1])).identity


def test_batch_rejects_untyped_source_uses():
    with pytest.raises(ValueError, match="source_uses"):
        ObservationBatch("dataset", 1, "release", (), (), ({"source_id":"publisher.a"},))
