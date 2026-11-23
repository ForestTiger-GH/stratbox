"""Actual journal/state consumption distinguishes preparation computations."""

from dataclasses import replace

from stratbox.core.notifications import (
    ConsumerBinding, FilterCondition, NotificationRoute, PrepareRequest, SourceBinding,
    SubscriptionChange, amend_checkpoint, configure_subscription, prepare,
)
from stratbox.core.observability import JournalReadLimits, StreamKey

from conftest import byte_event


def complete(session):
    runtime, key, context, _, _, _ = session
    result = prepare(PrepareRequest(key, JournalReadLimits(max_positions=10)), runtime=runtime, context=context)
    assert result.outcome == "succeeded", result.diagnostics
    assert result.computation is not None and result.computation.inputs
    return result


def test_one_and_two_actual_journal_records_have_different_keys(session_factory):
    sessions = [session_factory(), session_factory()]
    for count, session in enumerate(sessions, 1):
        session[3].records.extend(byte_event(f"event-{i}", f"obs-{i}") for i in range(count))
    first, second = map(complete, sessions)
    assert (first.value.prepared, second.value.prepared) == (1, 2)
    assert first.computation.computation_id != second.computation.computation_id
    assert {item.role for item in second.computation.inputs} >= {
        "notification.subscription", "notification.journal_head",
        "notification.checkpoint", "notification.journal_page",
    }


def test_changed_record_bytes_with_same_head_and_count_change_key(session_factory):
    left, right = session_factory(), session_factory()
    left[3].records.append(byte_event("one", "obs-one", new="b"))
    right[3].records.append(byte_event("one", "obs-one", new="c"))
    first, second = complete(left), complete(right)
    assert first.value == second.value
    pages = lambda result: tuple(item.identity for item in result.computation.inputs
                                 if item.role == "notification.journal_page")
    assert pages(first) != pages(second)
    assert first.computation.computation_id != second.computation.computation_id


def test_selected_subscription_content_qualifies_preparation(session_factory):
    left, right = session_factory(), session_factory()
    runtime, _, context, _, _, spec = right
    filtered = replace(spec, filters=(FilterCondition("source_id", "eq", ("other",)),))
    configure_subscription(SubscriptionChange("update", filtered, 2), runtime=runtime, context=context)
    for session in (left, right):
        session[3].records.append(byte_event())
    first, second = complete(left), complete(right)
    assert (first.value.prepared, second.value.prepared) == (1, 0)
    assert first.computation.computation_id != second.computation.computation_id


def test_starting_cursor_qualifies_the_consumed_partition(session_factory):
    left, right = session_factory(), session_factory()
    for session in (left, right):
        session[3].records.extend((byte_event("one", "obs-one"), byte_event("two", "obs-two")))
    runtime, key, context, source, _, _ = right
    amend_checkpoint(key, expected=runtime.state.get_checkpoint(key), head_ref=source.head(key.stream).head_ref,
        last_offset=1, reason_code="test.explicit_cut", evidence_ref="test.approved_cut", action="rebase",
        runtime=runtime, context=context)
    first, second = complete(left), complete(right)
    assert (first.value.prepared, second.value.prepared) == (2, 1)
    assert first.computation.computation_id != second.computation.computation_id


def test_actual_authority_fields_affect_preparation_without_hashing_provider(session_factory):
    left, right = session_factory(), session_factory()
    for session in (left, right):
        session[3].records.append(byte_event())
    right[0].authority.fields -= {"new_sha256"}
    first, second = complete(left), complete(right)
    assert (first.value.prepared, second.value.prepared) == (1, 0)
    assert first.computation.computation_id != second.computation.computation_id


def test_unused_runtime_objects_leave_computation_unchanged(session_factory):
    left, right = session_factory(), session_factory()
    for session in (left, right):
        session[3].records.append(byte_event())

    class UnusedSource:
        def head(self, *args):
            raise AssertionError("An unrelated provider must remain unused")
        def read_page(self, *args, **kwargs):
            raise AssertionError("An unrelated provider must remain unused")

    runtime, key, context, _, _, _ = right
    decorated = replace(runtime,
        sources=(*runtime.sources, SourceBinding(StreamKey("public", "unused", "main"),
            "unused", "local_snapshot", UnusedSource())),
        consumers=(*runtime.consumers, ConsumerBinding("public",
            NotificationRoute("unread", "unused", "nobody"), "in_process", object())))
    runtime.authority.unrelated_configuration = object()
    baseline = complete(left)
    changed = prepare(PrepareRequest(key, JournalReadLimits(max_positions=10)),
        runtime=decorated, context=context)
    assert changed.outcome == "succeeded", changed.diagnostics
    assert changed.value == baseline.value
    assert changed.computation.computation_id == baseline.computation.computation_id
