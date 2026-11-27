"""Public SDK compositions preserve historical values through retained replay."""
from dataclasses import replace
from decimal import Decimal

from stratbox.core.storage.datasets.stores import FileDatasetStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.history import RevisionPolicy
from stratbox.shared.data.selection import ObservationQuery
from stratbox.shared.data.values import SourceDataset, fingerprint


def original(issue, value, period="2026-01"):
    return SourceDataset("history.fixture", ({"period": period, "metric": "value",
        "value": Decimal(value), "source_issue": issue},), issue_id=issue)


def invoke(box, capability, **inputs):
    with box.invoke(capability, inputs=inputs) as result:
        assert result.outcome == "succeeded", result.diagnostics
        return result.output("dataset")


def test_sdk_resolve_select_encode_retain_restore_merge_and_revisit(tmp_path):
    policy = RevisionPolicy(conflicts="latest", ordered_issues=("first", "revised"),
        ordering_basis="publisher.release_order")
    with StrategyBox() as box:
        latest = invoke(box, "command.observations.resolve_revisions",
            datasets=(original("first", 1), original("revised", 2)), policy=policy)
        selected = invoke(box, "command.observations.select", dataset=latest,
            query=ObservationQuery(periods=("2026-01",)))
        with box.invoke("command.value.encode", inputs={"value": selected}) as encoded:
            assert encoded.outcome == "succeeded", encoded.diagnostics
            with box.invoke("command.value.decode", inputs={"representation": encoded.output("representation")}) as decoded:
                assert decoded.outcome == "succeeded", decoded.diagnostics
                portable = decoded.output("value")
        store = FileDatasetStore(tmp_path / "snapshots")
        reference = store.ingest(portable, destination="history", identity=fingerprint(portable))
    restored = FileDatasetStore(tmp_path / "snapshots").query(reference, None)
    assert restored.native is None
    with StrategyBox() as box:
        merged = invoke(box, "command.observations.merge", datasets=(restored, original("first", 3, "2026-02")))
        earlier = invoke(box, "command.observations.resolve_revisions", datasets=(merged,),
            policy=replace(policy, as_of="first"))
        assert [row["value"] for row in earlier.rows] == [1, 3]
        assert earlier.rows[0]["source_issue"] == "first"
        assert earlier.assessment.complete
        newest = invoke(box, "command.observations.resolve_revisions", datasets=(earlier,), policy=policy)
        assert [row["value"] for row in newest.rows] == [2, 3]
        assert newest.assessment.complete
