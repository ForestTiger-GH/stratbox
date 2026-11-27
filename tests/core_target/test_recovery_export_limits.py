"""Oversized recovery exports stop before publishing partial owners."""
import pytest

from stratbox.core.notifications.state import FileNotificationState
from stratbox.core.observability.journal.stream import FileJournal
from stratbox.core.recovery import RecoveryLimits
from stratbox.core.storage.source_state import SQLiteSourceState
from stratbox.sdk import LocalProfile


@pytest.mark.parametrize('kind', ['source_state', 'notifications'])
def test_sqlite_export_rejects_physical_size_before_creating_snapshot(tmp_path, kind):
    target = tmp_path / 'snapshot.sqlite'
    owner = (SQLiteSourceState(tmp_path / 'source.sqlite') if kind == 'source_state'
             else FileNotificationState(tmp_path / 'notifications'))
    try:
        with pytest.raises(ValueError, match='checkpoint_size_limit'):
            owner.export_checkpoint(target, max_bytes=1)
        assert not target.exists()
        owner.export_checkpoint(target, max_bytes=1024**2)
        assert target.is_file() and target.stat().st_size <= 1024**2
    finally:
        if kind == 'source_state':
            owner.close()


@pytest.mark.parametrize('budget', [{'max_bytes': 1}, {'max_files': 1}, {'max_file_bytes': 1}])
def test_journal_export_budget_keeps_live_owner_usable(tmp_path, budget):
    with FileJournal(tmp_path / 'journal') as journal:
        journal.append(kind='example', run_id='before')
        with pytest.raises(ValueError, match='checkpoint_size_limit'):
            journal.export_checkpoint(tmp_path / 'too-large', **budget)
        assert not (tmp_path / 'too-large').exists()
        journal.append(kind='example', run_id='after')
        assert journal.checkpoint().tail == 2


def test_successful_append_preserves_tail_evidence_without_a_consumer_checkpoint(tmp_path):
    directory = tmp_path / 'journal'
    with FileJournal(directory, segment_size=1) as journal:
        journal.append(kind='example', run_id='first')
        journal.append(kind='example', run_id='second')
    # No consumer was registered or advanced. Physical loss of the completed
    # second append still cannot turn this into an apparently valid shorter log.
    (directory / 'facts-000000000001.jsonl').unlink()
    with pytest.raises(ValueError, match='coverage_gap'):
        FileJournal(directory)


@pytest.mark.parametrize('limits', [RecoveryLimits(max_bytes=1024), RecoveryLimits(max_files=2)])
def test_package_budget_rejects_incomplete_publication_and_releases_pause(tmp_path, limits):
    package = tmp_path / 'oversized'
    with LocalProfile(tmp_path / 'state', artifact_root=tmp_path / 'artifacts') as profile:
        with pytest.raises(ValueError, match='limit|capacity'):
            profile.export_recovery(package, limits=limits)
        assert not package.exists()
        assert not tuple(tmp_path.glob('stratbox-recovery-*'))
        assert profile.box.session.quiescent
        complete = profile.export_recovery(tmp_path / 'complete')
        assert complete['completeness'] == 'verified_at_cut'
