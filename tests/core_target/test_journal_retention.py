"""Contiguous evidence survives bounded retention, interruption and slow readers."""
from dataclasses import replace
from pathlib import Path
import json

import pytest

from stratbox.core.observability.journal import FileJournal, MemoryJournal, JournalPage
from stratbox.shared.data.values import fingerprint


def append(journal, count, *, start=0):
    return tuple(journal.append(kind='test.fact', run_id='A' if index % 2 else 'B',
        data={'value': index, 'statuses': {index: 'succeeded'}}) for index in range(start, start + count))


@pytest.mark.parametrize('capacity', [True, False, 0, -1, 1.5])
def test_memory_capacity_is_a_positive_integer(capacity):
    with pytest.raises(ValueError, match='journal.invalid_capacity'):
        MemoryJournal(capacity)


def test_memory_backpressure_requires_every_registered_consumer_and_keeps_sequence():
    journal = MemoryJournal(capacity=3)
    journal.register_consumer('fast'); journal.register_consumer('slow')
    append(journal, 3)
    with pytest.raises(RuntimeError, match='capacity_exhausted'):
        append(journal, 1)
    page = journal.read_page()
    journal.acknowledge('fast', page)
    with pytest.raises(ValueError, match='consumer_lagging'):
        journal.prune(3)
    with pytest.raises(ValueError, match='consumer_lagging'):
        journal.unregister_consumer('slow')
    journal.acknowledge('slow', page)
    journal.prune(3)
    assert journal.append(kind='continued', run_id='A').sequence == 4
    assert journal.checkpoint().tail == 4
    with pytest.raises(ValueError, match='cursor_expired'):
        journal.read_page(after=0)
    assert [fact.sequence for fact in journal.read(after=3)] == [4]


def test_prefix_is_never_removed_without_a_consumer_checkpoint():
    journal = MemoryJournal()
    append(journal, 1)
    with pytest.raises(ValueError, match='consumer_checkpoint_required'):
        journal.prune(1)
    assert journal.read()[0].sequence == 1


def test_filtered_pages_certify_scanned_positions_even_without_selected_events():
    journal = MemoryJournal()
    append(journal, 6)
    page = journal.read_page(run_id='A', limit=1, scan_limit=1)
    assert page.scanned_through == 1 and page.facts == () and page.has_more
    next_page = journal.read_page(after=1, run_id='A', limit=1, scan_limit=4)
    assert next_page.scanned_through == 2 and [fact.sequence for fact in next_page.facts] == [2]
    assert next_page.filters == {'run_id': 'A'}
    with pytest.raises(ValueError, match='page_coverage_gap'):
        replace(page, filters={})
    with pytest.raises(ValueError, match='page_filter_conflict'):
        replace(next_page, filters={'run_id': 'B'})
    with pytest.raises(ValueError, match='page_filter_invalid'):
        replace(next_page, filters={'unknown': 'A'})


def test_consumer_rejects_gaps_other_streams_and_changed_fact_content():
    journal = MemoryJournal()
    journal.register_consumer('reader')
    append(journal, 3)
    with pytest.raises(ValueError, match='consumer_coverage_gap'):
        journal.acknowledge('reader', journal.read_page(after=1))
    other = MemoryJournal(); append(other, 1)
    with pytest.raises(ValueError, match='stream_identity_conflict'):
        journal.acknowledge('reader', other.read_page())
    page = journal.read_page(limit=2)
    forged = replace(page, facts=(replace(page.facts[0], data={'forged': True}), page.facts[1]))
    with pytest.raises(ValueError, match='consumer_page_conflict'):
        journal.acknowledge('reader', forged)
    assert journal.checkpoint().consumers['reader'] == 0
    assert journal.acknowledge('reader', page) == 2
    assert journal.acknowledge('reader', page) == 2


def test_journal_detaches_and_deeply_freezes_nested_metadata_and_integer_keys(tmp_path):
    original = {'nested': {'rows': [1, {'number': 2}]}, 'statuses': {0: 'succeeded'}}
    for journal in (MemoryJournal(), FileJournal(tmp_path)):
        fact = journal.append(kind='map.completed', run_id='run', data=original)
        before = fingerprint(fact)
        original['nested']['rows'][1]['number'] = 100
        with pytest.raises(TypeError):
            fact.data['nested']['rows'][1]['number'] = 200
        with pytest.raises(TypeError):
            journal.read()[0].data['statuses'][0] = 'failed'
        assert fingerprint(journal.read()[0]) == before
        original['nested']['rows'][1]['number'] = 2
        if isinstance(journal, FileJournal):
            journal.close()
            reader = FileJournal(tmp_path)
            assert fingerprint(reader.read()[0]) == before
            reader.close()


def test_cold_archive_is_readable_to_lagging_consumers_after_restart(tmp_path):
    with FileJournal(tmp_path, segment_size=2) as journal:
        journal.register_consumer('fast'); journal.register_consumer('slow')
        append(journal, 5)
        journal.acknowledge('fast', journal.read_page())
        checkpoint = journal.archive(4, max_segments=1)
        assert checkpoint.archived_through == 2
        assert journal.archive(4).archived_through == 4
        assert [fact.sequence for fact in journal.read()] == [1, 2, 3, 4, 5]
        with pytest.raises(ValueError, match='consumer_lagging'):
            journal.prune(4)
    with FileJournal(tmp_path) as reopened:
        assert reopened.segment_size == 2
        assert reopened.checkpoint().consumers == {'fast': 5, 'slow': 0}
        reopened.acknowledge('slow', reopened.read_page())
        assert reopened.prune(4).retained_after == 4
        assert reopened.append(kind='continued', run_id='A').sequence == 6
    with FileJournal(tmp_path) as reopened:
        assert [fact.sequence for fact in reopened.read(after=4)] == [5, 6]
        with pytest.raises(ValueError, match='cursor_expired'):
            reopened.read_page()


def test_cold_coverage_gap_is_not_reported_as_an_empty_page(tmp_path):
    with FileJournal(tmp_path, segment_size=1) as journal:
        journal.register_consumer('slow')
        append(journal, 2)
        journal.archive(2)
    cold = next((tmp_path / 'archive').rglob('facts-000000000000.jsonl'))
    cold.unlink()
    with FileJournal(tmp_path) as reopened:
        with pytest.raises(ValueError, match='coverage_gap'):
            reopened.read_page()
        assert reopened.checkpoint().consumers['slow'] == 0


def test_only_one_writer_owns_the_stream_and_stale_observer_can_refresh(tmp_path):
    writer = FileJournal(tmp_path, segment_size=2)
    reader = FileJournal(tmp_path)
    append(writer, 1)
    assert reader.read() == ()
    assert reader.refresh().tail == 1
    assert reader.segment_size == 2 and len(reader.read()) == 1
    with pytest.raises(RuntimeError, match='writer_already_owned'):
        append(reader, 1)
    append(writer, 1, start=1)
    writer.close()
    with pytest.raises(RuntimeError, match='writer_state_stale_reopen_required'):
        append(reader, 1)
    reader.refresh()
    assert reader.append(kind='next', run_id='A').sequence == 3
    reader.close()


def test_archive_rename_before_checkpoint_is_recovered_without_losing_facts(tmp_path, monkeypatch):
    journal = FileJournal(tmp_path, segment_size=2)
    append(journal, 4)
    save = journal._save_checkpoint
    monkeypatch.setattr(journal, '_save_checkpoint', lambda: (_ for _ in ()).throw(OSError('interrupted checkpoint')))
    with pytest.raises(OSError, match='interrupted checkpoint'):
        journal.archive(2)
    monkeypatch.setattr(journal, '_save_checkpoint', save)
    journal.close()
    with FileJournal(tmp_path) as reopened:
        assert [fact.sequence for fact in reopened.read()] == [1, 2, 3, 4]
        assert reopened.archive(4).archived_through == 4


def test_pruned_checkpoint_precedes_delete_and_cleanup_resumes_after_unlink_failure(tmp_path, monkeypatch):
    journal = FileJournal(tmp_path, segment_size=1)
    journal.register_consumer('reader')
    append(journal, 3)
    journal.acknowledge('reader', journal.read_page())
    original = Path.unlink
    failed = False
    def interrupted(path, *args, **kwargs):
        nonlocal failed
        if path.name == 'facts-000000000000.jsonl' and not failed:
            failed = True
            raise OSError('interrupted unlink')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'unlink', interrupted)
    with pytest.raises(OSError, match='interrupted unlink'):
        journal.prune(3)
    assert json.loads((tmp_path / 'retention.json').read_bytes())['retained_after'] == 3
    assert (tmp_path / 'facts-000000000000.jsonl').exists()
    journal.close()
    with FileJournal(tmp_path) as reopened:
        reopened.prune(3, max_segments=1)
        assert not (tmp_path / 'facts-000000000000.jsonl').exists()
        assert (tmp_path / 'facts-000000000001.jsonl').exists()
        reopened.cleanup_pruned()
        assert not tuple(tmp_path.glob('facts-*.jsonl'))
        assert reopened.append(kind='next', run_id='A').sequence == 4


def test_failed_floor_checkpoint_never_authorizes_physical_deletion(tmp_path, monkeypatch):
    with FileJournal(tmp_path, segment_size=1) as journal:
        journal.register_consumer('reader'); append(journal, 1)
        journal.acknowledge('reader', journal.read_page())
        save = journal._save_checkpoint
        monkeypatch.setattr(journal, '_save_checkpoint', lambda: (_ for _ in ()).throw(OSError('checkpoint failed')))
        with pytest.raises(OSError): journal.prune(1)
        assert journal.checkpoint().retained_after == 0
        monkeypatch.setattr(journal, '_save_checkpoint', save)
        journal.cleanup_pruned()
        assert [fact.sequence for fact in journal.read()] == [1]


@pytest.mark.parametrize('kwargs', [{'limit': True}, {'limit': 10001}, {'scan_limit': 0}, {'scan_limit': 100001}, {'after': True}])
def test_pages_reject_invalid_or_unbounded_limits(kwargs):
    with pytest.raises(ValueError):
        MemoryJournal().read_page(**kwargs)


def test_memory_byte_quota_is_charged_before_append_and_reclaimed_after_safe_prune():
    journal = MemoryJournal(capacity=100, max_record_bytes=1000, max_bytes=700)
    journal.register_consumer('reader')
    first = journal.append(kind='bounded', run_id='run', data={'value': 'x' * 200})
    with pytest.raises(RuntimeError, match='byte_capacity_exhausted'):
        journal.append(kind='bounded', run_id='run', data={'value': 'x' * 200})
    assert journal.checkpoint().tail == 1
    journal.acknowledge('reader', journal.read_page())
    journal.prune(1)
    assert journal._bytes == 0
    assert journal.append(kind='bounded', run_id='run', data={'value': 'x' * 200}).sequence == 2
    with pytest.raises(ValueError, match='record_limit'):
        journal.append(kind='large', run_id='run', data={'value': 'x' * 10000})
    assert journal.checkpoint().tail == 2


@pytest.mark.parametrize('durable', [False, True])
def test_tuple_read_never_hides_an_unfinished_filtered_scan(tmp_path, durable):
    journal = FileJournal(tmp_path, segment_size=2) if durable else MemoryJournal()
    try:
        append(journal, 6)
        with pytest.raises(ValueError, match='journal.scan_limit'):
            journal.read(run_id='absent', limit=1, scan_limit=3)
        with pytest.raises(ValueError, match='journal.scan_limit'):
            journal.read(run_id='A', limit=2, scan_limit=3)
        page = journal.read_page(run_id='A', limit=2, scan_limit=3)
        assert [fact.sequence for fact in page.facts] == [2]
        assert page.scanned_through == 3 and page.has_more
        assert [fact.sequence for fact in journal.read(run_id='A', limit=1, scan_limit=3)] == [2]
        assert journal.read(after=3, run_id='absent', limit=1, scan_limit=3) == ()
    finally:
        if durable: journal.close()
