"""Journal retention and pages remain bounded as execution history grows."""
import pytest
from stratbox.core.observability.journal import MemoryJournal, FileJournal


def test_memory_journal_backpressure_preserves_retained_truth():
    journal=MemoryJournal(capacity=3)
    for index in range(3):journal.append(kind='diagnostic',run_id=str(index))
    with pytest.raises(RuntimeError,match='capacity_exhausted'):
        journal.append(kind='diagnostic',run_id='overflow')
    assert [fact.sequence for fact in journal.read(limit=3)]==[1,2,3]


def test_segmented_pages_have_exact_cursor_without_allocating_history(tmp_path):
    journal=FileJournal(tmp_path,segment_size=10)
    for index in range(51):journal.append(kind='diagnostic',run_id=str(index))
    assert len(list(tmp_path.glob('facts-*.jsonl')))==6
    assert [fact.sequence for fact in journal.read(after=37,limit=3)]==[38,39,40]
    assert [fact.sequence for fact in journal.read(after=49,limit=3)]==[50,51]


def test_missing_segment_is_not_silently_treated_as_complete_history(tmp_path):
    journal=FileJournal(tmp_path,segment_size=2)
    for index in range(5):journal.append(kind='diagnostic',run_id=str(index))
    sorted(tmp_path.glob('facts-*.jsonl'))[1].unlink()
    with pytest.raises(ValueError,match='coverage_gap'):
        journal.read(limit=100)


def test_invalid_or_unbounded_page_request_is_rejected(tmp_path):
    journal=FileJournal(tmp_path)
    for limit in (0,-1,10001):
        with pytest.raises(ValueError,match='invalid_page'):journal.read(limit=limit)


def test_filtered_history_has_a_real_scan_budget(tmp_path):
    journal=FileJournal(tmp_path,segment_size=2)
    for index in range(7):journal.append(kind='diagnostic',run_id='present')
    with pytest.raises(ValueError,match='scan_limit'):
        journal.read(run_id='absent',limit=1,scan_limit=3)


def test_huge_corrupt_sequence_is_rejected_before_history_expansion(tmp_path):
    import json
    journal=FileJournal(tmp_path,segment_size=2)
    journal.append(kind='diagnostic',run_id='one')
    path=next(tmp_path.glob('facts-*.jsonl'))
    record=json.loads(path.read_bytes())
    record['sequence']=2**53-1
    path.write_text(json.dumps(record)+'\n')
    with pytest.raises(ValueError,match='sequence_conflict'):
        FileJournal(tmp_path,segment_size=2)
