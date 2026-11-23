"""Preparation scope controls qualify results independently of external delivery."""
from stratbox.core.notifications import PrepareRequest, prepare
from stratbox.core.observability import JournalReadLimits

from conftest import byte_event


def _prepare(factory, *, positions=1, pages=1):
    runtime, key, context, source, _, _ = factory()
    source.records.extend((byte_event("one", "obs-one"), byte_event("two", "obs-two")))
    result = prepare(PrepareRequest(key, JournalReadLimits(max_positions=positions),
                                    mode="catch_up", max_pages=pages), runtime=runtime, context=context)
    assert result.outcome == "succeeded", result.diagnostics
    assert result.computation is not None
    return result


def test_page_count_changes_prepared_scope_and_computation_identity(session_factory):
    first = _prepare(session_factory, pages=1)
    second = _prepare(session_factory, pages=2)
    assert first.value.prepared == 1
    assert second.value.prepared == 2
    assert first.computation.computation_id != second.computation.computation_id


def test_page_position_ceiling_is_a_semantic_partition_size(session_factory):
    first = _prepare(session_factory, positions=1)
    second = _prepare(session_factory, positions=2)
    assert first.value.checkpoint.last_offset == 1
    assert second.value.checkpoint.last_offset == 2
    assert first.computation.computation_id != second.computation.computation_id
