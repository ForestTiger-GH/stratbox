"""Accepted outputs and completion are separate retained journal facts."""
import pytest
from dataclasses import replace

from stratbox.core.execution.contracts import Correlation, EffectReceipt
from stratbox.core.observability.capture.orchestration import OrchestrationJournal
from stratbox.core.observability.journal.sources import JournalReadLimits
from stratbox.core.observability.records.field_policy import validate_builtin_fields
from stratbox.shared.identity import ByteIdentity


def records(journal):
    head = journal.facts_source.head(journal.facts_stream)
    page = journal.facts_source.read_page(head.cursor(head.first_retained - 1), head=head,
        limits=JournalReadLimits())
    return tuple(entry.record for entry in page.entries)


@pytest.mark.parametrize("kind", ("command", "operation", "scenario", "cascade"))
def test_technical_named_output_and_completion_have_exact_logical_coordinates(kind):
    with_journal = OrchestrationJournal("capabilities")
    correlation = Correlation(session_id="capabilities", run_id="first", workflow_scope_id="scope")
    coordinates = dict(capability_id="example." + kind, capability_kind=kind,
                       scope_id="root/items:2/" + kind)
    accepted = with_journal.accepted_value(correlation, value_id="output.version", stage="technical",
        role=None, identity=ByteIdentity.of(b"7"), output_name="answer", **coordinates)
    finished = with_journal.capability_finished(correlation, outcome="failed", **coordinates)
    assert accepted.kind == "value.accepted" and finished.kind == "capability.finished"
    assert accepted.payload["output_name"] == "answer"
    assert accepted.payload["role"] is None
    assert finished.payload["outcome"] == "failed"
    assert all(record.payload["scope_id"] == coordinates["scope_id"] for record in records(with_journal))
    assert with_journal.capability_finished(correlation, outcome="failed", **coordinates) == finished
    assert len(records(with_journal)) == 2
    with_journal.close()


def test_opaque_accepted_output_has_occurrence_identity_without_fabricated_content_digest():
    journal = OrchestrationJournal("opaque")
    correlation = Correlation(session_id="opaque", run_id="run")
    fact = journal.accepted_value(correlation, value_id="accepted.occurrence", stage="opaque.command",
        role=None, identity=None, identity_status="unavailable", acceptance_id="logical.acceptance",
        capability_id="opaque.command", capability_kind="command", scope_id="opaque.command", output_name="value")
    validate_builtin_fields(fact)
    assert fact.payload["identity"] is None and fact.subject.identity is None
    assert fact.payload["identity_status"] == "unavailable"
    assert fact.payload["acceptance_id"] == "logical.acceptance"
    with pytest.raises(ValueError, match="identity_status_mismatch"):
        journal.accepted_value(correlation, value_id="bad", stage="opaque.command", role=None,
            identity=None, identity_status="available")
    with pytest.raises(ValueError, match="identity_status_mismatch"):
        validate_builtin_fields(replace(fact, payload={**fact.payload, "identity_status": "available"}))
    with pytest.raises(ValueError, match="coordinates_incomplete"):
        validate_builtin_fields(replace(fact, payload={**fact.payload, "output_name": None}))
    journal.close()


def test_each_invocation_has_its_own_completion_even_when_result_and_target_are_equal():
    journal = OrchestrationJournal("runs")
    coordinates = dict(capability_id="example.scenario", capability_kind="scenario", scope_id="root/scenario")
    first = journal.capability_finished(Correlation(session_id="runs", run_id="first"),
        outcome="succeeded", **coordinates)
    second = journal.capability_finished(Correlation(session_id="runs", run_id="second"),
        outcome="succeeded", **coordinates)
    assert first.fact_id != second.fact_id
    assert first.payload["completion_id"] != second.payload["completion_id"]
    assert len(records(journal)) == 2
    journal.close()


def test_full_journal_retains_completion_until_explicit_acknowledgement():
    journal = OrchestrationJournal("bounded", max_pending_runs=1)
    coordinates = dict(capability_id="example.scenario", capability_kind="scenario", scope_id="root/scenario")
    journal.capability_finished(Correlation(session_id="bounded", run_id="first"), outcome="skipped", **coordinates)
    final = journal.capability_finished(Correlation(session_id="bounded", run_id="second"), outcome="cancelled", **coordinates)
    assert journal.health_snapshot().unpublished_transitions == 1
    journal.release_publications("second")
    assert journal.health_snapshot().unpublished_transitions == 1
    journal.facts_source.acknowledge(1)
    assert journal.flush_transitions() == 1
    assert records(journal) == (final,)
    journal.close()


def test_saved_effect_carries_producer_coordinates_without_private_destination():
    journal = OrchestrationJournal("effects")
    fact = journal.confirmed_effect(Correlation(session_id="effects", run_id="run"),
        EffectReceipt("storage.write", "confirmed", effect_id="write", reference="/private/location.csv"),
        capability_id="example.save", capability_kind="command", scope_id="root/scenario/save")
    assert fact.payload["capability_id"] == "example.save"
    assert fact.payload["scope_id"] == "root/scenario/save"
    assert "/private" not in str(fact.payload)
    assert fact.payload["output_name"] is None
    journal.close()
