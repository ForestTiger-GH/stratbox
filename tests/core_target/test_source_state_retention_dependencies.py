"""Cross-owner retention keeps live scientific witnesses and exact horizons."""
import pytest

from stratbox.core.observability.journal.stream import MemoryJournal
from stratbox.core.observability.projections.source_state import SourceStateIndex
from stratbox.core.storage.source_state import SQLiteSourceState, SourceStateRetention
from stratbox.shared.data.values import Assessment, ByteIdentity, ImmutableMaterialRef, SnapshotRef


def accepted(journal, capability, accepted_id, *, source="s", basis="validator", certificate_ids=(),
             dependencies=(), reference=None, output="dataset"):
    return journal.append(kind="output.accepted", run_id="fixture", command_id=capability, output_name=output,
        data={"accepted_value_id": accepted_id, "value_identity": accepted_id + "-content",
            "source_id": source, "issue_id": "issue", "processing_basis": (basis,),
            "output_disposition": "accepted", "output_role": "data", "assessment": Assessment(),
            "certificate_ids": certificate_ids, "certificate_dependencies": dependencies,
            "persistent": reference is not None, "retained_reference": reference})


def maintain(store, journal, disposition="discard", *, through=None):
    for _ in range(20):
        report = store.maintain(stream_id=journal.stream_id, policy=SourceStateRetention(
            journal.checkpoint().tail if through is None else through, disposition,
            limit=2, retire_persistent=True))
        if not report.has_more:
            return
    raise AssertionError("finite fixture maintenance failed to terminate")


@pytest.mark.parametrize("archive_first", (False, True))
def test_current_retained_history_keeps_its_original_validation_witness(tmp_path, archive_first):
    journal = MemoryJournal()
    accepted(journal, "command.observations.validate", "old-validator", certificate_ids=("original-certificate",))
    reference = SnapshotRef("history", "datasets.files", "history-content", "fixture")
    accepted(journal, "command.observations.resolve_revisions", "history", basis="history",
        dependencies=("original-certificate",), reference=reference)
    accepted(journal, "command.observations.validate", "new-validator", certificate_ids=("new-certificate",))
    with SQLiteSourceState(tmp_path / "state.sqlite") as store:
        SourceStateIndex(store).advance(journal)
        if archive_first:
            maintain(store, journal, "archive")
        maintain(store, journal)
        current = store.read(("s",), stream_id=journal.stream_id)
        assert any(value.accepted_value_id == "history" and value.persistent for value in current.outputs)
        assert not any(value.accepted_value_id == "old-validator" for value in
            store.read(("s",), stream_id=journal.stream_id, view="history").outputs)
        assert store.has_validation_certificate("original-certificate")
        assert store.has_validation_certificate("new-certificate")


def test_referenced_certificate_does_not_create_its_own_authority(tmp_path):
    journal = MemoryJournal()
    accepted(journal, "command.observations.resolve_revisions", "history", basis="history",
        dependencies=("unadmitted-certificate",))
    with SQLiteSourceState(tmp_path / "state.sqlite") as store:
        SourceStateIndex(store).advance(journal)
        maintain(store, journal)
        assert not store.has_validation_certificate("unadmitted-certificate")


def test_discard_horizon_does_not_remove_a_later_retention_link(tmp_path):
    journal = MemoryJournal()
    reference = ImmutableMaterialRef("objects/value", ByteIdentity.of(b"value"),
        accepted_value_id="later-encoded-value", effect_id="effect", provider_scope="fixture")
    accepted(journal, "command.artifact.commit", "receipt", source=None, basis="retention",
        reference=reference, output="reference")
    with SQLiteSourceState(tmp_path / "state.sqlite") as store:
        SourceStateIndex(store).advance(journal)
        assert tuple(store.retained_references()) == (reference,)
        maintain(store, journal, through=0)
        assert tuple(store.retained_references()) == (reference,)


def maintain_policy(store, stream_id, policy):
    reports = []
    for _ in range(100):
        report = store.maintain(stream_id=stream_id, policy=policy)
        assert report.retired_current + report.records + report.authority + report.retention_links <= policy.limit
        reports.append(report)
        if not report.has_more:
            return reports
    raise AssertionError("bounded retirement did not converge")


def test_changing_content_is_bounded_under_explicit_host_basis_retirement(tmp_path):
    journal = MemoryJournal()
    previous = None
    with SQLiteSourceState(tmp_path / "state.sqlite", max_records=4) as store:
        index = SourceStateIndex(store)
        for number in range(40):
            identity = f"revision-{number}"
            accepted(journal, "command.observations.resolve_revisions", identity, basis=f"body-{number}",
                reference=SnapshotRef(identity, "datasets.files", identity + "-content", "fixture"))
            index.advance(journal)
            policy = SourceStateRetention(journal.checkpoint().tail, "discard", 1, retire_persistent=True,
                retire_current_accepted_ids=() if previous is None else (previous,))
            reports = maintain_policy(store, journal.stream_id, policy)
            assert sum(report.retired_current for report in reports) == int(previous is not None)
            current = store.read(("s",), stream_id=journal.stream_id)
            assert current.complete and [value.accepted_value_id for value in current.outputs] == [identity]
            assert store.storage_usage()["hot_records"] == 1
            assert store.storage_usage()["archive_records"] == 0
            previous = identity
        assert not store.read(("s",), stream_id=journal.stream_id, view="history").complete


def test_explicit_retirement_preserves_pinned_unselected_and_future_current_bases(tmp_path):
    journal = MemoryJournal()
    for identity in ("unselected", "obsolete", "pinned", "after-horizon"):
        accepted(journal, "command.observations.resolve_revisions", identity, basis=identity)
    journal.append(kind="source.observed", run_id="observation", data={"source_id": "s", "issue_id": "issue",
        "observation_id": "latest-source", "evidence_identity": "source-evidence"})
    with SQLiteSourceState(tmp_path / "state.sqlite") as store:
        SourceStateIndex(store).advance(journal)
        reports = maintain_policy(store, journal.stream_id, SourceStateRetention(3, "discard", 1,
            retire_persistent=True, protected_accepted_ids=("pinned",),
            retire_current_accepted_ids=("obsolete", "pinned", "after-horizon", "latest-source")))
        current = store.read(("s",), stream_id=journal.stream_id)
        assert {value.accepted_value_id for value in current.outputs} == {"unselected", "pinned", "after-horizon"}
        assert [value.observation_id for value in current.observations] == ["latest-source"]
        assert sum(report.retired_current for report in reports) == 1


def test_retirement_pointer_work_consumes_the_same_page_budget(tmp_path):
    journal = MemoryJournal()
    for identity in ("one", "two", "three"):
        accepted(journal, "command.observations.resolve_revisions", identity, basis=identity)
    with SQLiteSourceState(tmp_path / "state.sqlite") as store:
        SourceStateIndex(store).advance(journal)
        policy = SourceStateRetention(3, "archive", 1, retire_current_accepted_ids=("one", "two", "three"))
        first = store.maintain(stream_id=journal.stream_id, policy=policy)
        assert first.retired_current == 1 and first.records == 0 and first.has_more
        reports = maintain_policy(store, journal.stream_id, policy)
        assert first.retired_current + sum(report.retired_current for report in reports) == 3
        assert not store.read(("s",), stream_id=journal.stream_id).outputs
        history = store.read(("s",), stream_id=journal.stream_id, view="history")
        assert history.complete and len(history.outputs) == 3


def test_archive_failure_rolls_back_explicit_pointer_retirements(tmp_path):
    journal = MemoryJournal()
    for identity in ("one", "two"):
        accepted(journal, "command.observations.resolve_revisions", identity, basis=identity)
    with SQLiteSourceState(tmp_path / "state.sqlite", max_archive_records=1) as store:
        SourceStateIndex(store).advance(journal)
        policy = SourceStateRetention(2, "archive", 4, retire_current_accepted_ids=("one", "two"))
        with pytest.raises(ValueError, match="archive_capacity_exhausted"):
            store.maintain(stream_id=journal.stream_id, policy=policy)
        assert {value.accepted_value_id for value in store.read(("s",), stream_id=journal.stream_id).outputs} == {"one", "two"}
        assert store.storage_usage()["archive_records"] == 0


def test_recovery_metadata_preserves_every_source_state_limit(tmp_path):
    limits = {"max_records": 23, "max_bytes": 100003, "max_record_bytes": 1009,
        "max_archive_records": 47, "max_archive_bytes": 200003}
    with SQLiteSourceState(tmp_path / "state.sqlite", **limits) as store:
        assert store.recovery_metadata()["limits"] == limits
