"""A full fact journal keeps admitted publication promises addressable."""
import pytest

from stratbox.core.execution.contracts import Correlation
from stratbox.core.observability.capture.orchestration import OrchestrationJournal
from stratbox.core.observability.journal.sources import JournalReadLimits
from stratbox.shared.identity import ByteIdentity


def accept(journal, run_id, value):
    return journal.accepted_value(Correlation(session_id="session", run_id=run_id),
        value_id="value", stage="extract", role="extracts", identity=ByteIdentity.of(value))


def test_admitted_fact_survives_full_journal_and_retries_same_identity():
    journal = OrchestrationJournal("session", max_pending_runs=1, max_records=1)
    journal.reserve_publications("first", 1)
    first = accept(journal, "first", b"A")
    journal.reserve_publications("second", 1)
    second = accept(journal, "second", b"B")
    assert journal.facts_source.pending == 1
    assert journal.health_snapshot().unpublished_transitions == 1
    assert accept(journal, "second", b"B") == second
    with pytest.raises(ValueError, match="publication_capacity"):
        journal.reserve_publications("third", 1)
    journal.release_publications("second")
    assert journal.health_snapshot().unpublished_transitions == 1
    journal.facts_source.acknowledge(1)
    assert journal.flush_transitions() == 1
    head = journal.facts_source.head(journal.facts_stream)
    page = journal.facts_source.read_page(head.cursor(1), head=head, limits=JournalReadLimits())
    assert [entry.record for entry in page.entries] == [second]
    assert second.fact_id != first.fact_id
    assert journal.health_snapshot().unpublished_transitions == 0


def test_publication_credits_are_admitted_before_execution_and_released_on_failed_run_admission():
    journal = OrchestrationJournal("session", max_pending_runs=1)
    journal.reserve_run("first", publications=1)
    with pytest.raises(ValueError):
        journal.reserve_run("second", publications=1)
    journal.release_run("first")
    journal.reserve_run("second", publications=1)
    journal.release_run("second")
    assert journal.facts_source.pending == journal.source.reserved == 0


def test_impossible_publication_claim_is_distinct_from_temporary_backpressure():
    journal = OrchestrationJournal("session", max_pending_runs=1)
    with pytest.raises(ValueError, match="publication_unsatisfiable"):
        journal.reserve_publications("too_large", 2)
    journal.reserve_publications("first", 1)
    with pytest.raises(ValueError, match="publication_capacity"):
        journal.reserve_publications("temporarily_full", 1)
