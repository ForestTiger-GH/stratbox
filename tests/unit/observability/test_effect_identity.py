"""Qualified effect identity, attempt scope, partial coverage and safe digest v3."""
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from stratbox.core.execution import (
    Completion, Diagnostic, EffectKey, EffectReceipt, ExecutionContext,
    InMemorySink, OperationDefinition, run,
)
from stratbox.core.observability import (
    decode_records, effect_ref_id, effect_state_from_result,
    encode_records, fact_from_stored_bytes, project_effect_state,
    record_from_fact, record_from_result,
)
from stratbox.shared.evidence import StoredBytesReceipt, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity


TIME = datetime(2026, 11, 19, tzinfo=timezone.utc)
KEY_WRITE = EffectKey("storage.write", "shared")
KEY_HANDOFF = EffectKey("notification.handoff", "shared")
DEFINITION = OperationDefinition(
    "test.qualified_effects", "m1", str, str,
    possible_effects=frozenset({"storage.write", "notification.handoff"}),
)


def _run(states=("confirmed", "unknown"), effect_id="shared"):
    def handler(req, invocation):
        invocation.effect(EffectReceipt("storage.write", states[0], effect_id=effect_id))
        if len(states) > 1:
            invocation.effect(EffectReceipt(
                "notification.handoff", states[1], effect_id=effect_id,
                reconciliation_owner="consumer",
            ))
        return req
    return run(DEFINITION, "done", handler)


def test_mixed_kinds_same_id_are_separate_across_journal_serialization():
    result = _run()
    assert result.outcome == "unknown"
    assert effect_state_from_result(result, key=KEY_WRITE).needs_reconciliation is False
    assert effect_state_from_result(result, key=KEY_HANDOFF).needs_reconciliation is True
    summary = record_from_result(result, occurred_at_utc=TIME, observation_id="mixed")
    assert len(summary.references) == 2
    assert {ref.object_id for ref in summary.references} == {
        effect_ref_id(KEY_WRITE), effect_ref_id(KEY_HANDOFF),
    }
    decoded, = decode_records(encode_records((summary,)))
    write = project_effect_state((decoded,), KEY_WRITE)
    handoff = project_effect_state((decoded,), KEY_HANDOFF)
    assert write.states == ("confirmed",) and write.needs_reconciliation is False
    assert write.evidence_coverage == "complete"
    assert handoff.states == ("unknown",) and handoff.needs_reconciliation is True
    assert handoff.evidence_coverage == "complete"
    with pytest.raises(TypeError):
        project_effect_state((decoded,), "shared")


def test_unrelated_confirmed_attempt_does_not_close_unknown_attempt():
    first = _run(("confirmed",))
    second = _run(("unknown",))
    # Both invocations target the same kind/provider ID; their authority
    # to refer to the same physical action has not been established.
    journal = (
        record_from_result(first, occurred_at_utc=TIME, observation_id="first"),
        record_from_result(second, occurred_at_utc=TIME, observation_id="second"),
    )
    aggregate = project_effect_state(journal, KEY_WRITE)
    assert aggregate.states == ("confirmed", "unknown")
    assert aggregate.needs_reconciliation is True
    assert aggregate.evidence_coverage == "indeterminate"
    assert len(aggregate.observed_attempts) == 2
    scoped = project_effect_state(journal, KEY_WRITE, invocation_id=first.invocation_id)
    assert scoped.states == ("confirmed",)
    assert scoped.needs_reconciliation is False
    assert scoped.evidence_coverage == "complete"


def test_missing_from_truncated_effects_is_not_proof_of_absence():
    def handler(req, invocation):
        for i in range(200):
            invocation.effect(EffectReceipt(
                "storage.write", "confirmed" if i != 199 else "unknown",
                effect_id=f"key_{i}",
            ))
        return req
    result = run(DEFINITION, "ok", handler)
    target = EffectKey("storage.write", "key_199")
    assert effect_state_from_result(result, key=target).needs_reconciliation is True
    summary = record_from_result(result, occurred_at_utc=TIME)
    projected = project_effect_state((summary,), target)
    assert projected.states == ()
    assert projected.needs_reconciliation is None
    assert projected.evidence_coverage == "partial"


def test_fully_enumerated_summary_proves_local_nonobservation_only():
    summary = record_from_result(_run(("confirmed",)), occurred_at_utc=TIME)
    target = project_effect_state((summary,), KEY_HANDOFF)
    assert target.states == ()
    assert target.evidence_coverage == "not_observed"
    assert target.needs_reconciliation is None


def test_independent_storage_fact_and_summary_share_effect_reference():
    identity = ByteIdentity.of(b"data")
    material = StoredBytesReceipt("secret/path", identity, "stored", "atomic_create",
                                  "test", effect_id="shared")
    fact = fact_from_stored_bytes(material, subject_id="source", observed_at_utc=TIME)
    assert fact.payload["effect_kind"] == "storage.write"
    assert fact.references[0].object_id == effect_ref_id(KEY_WRITE)
    result = _run(("confirmed",))
    summary = record_from_result(result, occurred_at_utc=TIME)
    record = record_from_fact(fact, invocation_id=result.invocation_id,
                              operation_id=result.operation_id)
    state = project_effect_state((summary, record), KEY_WRITE,
                                 invocation_id=result.invocation_id)
    assert state.states == ("confirmed",)
    assert state.needs_reconciliation is False
    assert len(state.observed_attempts) == 1


def test_digest_changes_when_reconciliation_owner_changes():
    diagnosis = Diagnostic("domain.uncertain", reconciliation_owner="owner_a")
    result = run(DEFINITION, "ok", lambda req, invocation:
                 Completion(req, "unknown", diagnosis))
    a = record_from_result(result, occurred_at_utc=TIME)
    other = replace(result, diagnostics=(
        replace(result.diagnostics[0], reconciliation_owner="owner_b"),
    ))
    b = record_from_result(other, occurred_at_utc=TIME)
    assert a.payload["details_digest"] != b.payload["details_digest"]
    assert b.payload["diagnostics"][0]["reconciliation_owner"] == "owner_b"


@pytest.mark.parametrize("field,change", [
    ("media_type", "text/csv"), ("availability", "reference_only"),
])
def test_input_media_and_availability_are_digest_material(field, change):
    identity = ByteIdentity.of(b"input")
    receipt = UsedInputReceipt("input", identity, "text/plain", "inline")
    def handler(req, inv):
        inv.use(receipt)
        return req
    result = run(DEFINITION, "ok", handler)
    different = replace(result, used_inputs=(replace(receipt, **{field: change}),))
    a = record_from_result(result, occurred_at_utc=TIME)
    b = record_from_result(different, occurred_at_utc=TIME)
    assert a.payload["details_digest"] != b.payload["details_digest"]
    assert b.payload["inputs"][0][field] == change


def test_sensitive_input_source_and_member_do_not_enter_journal():
    source = "https://api.example.invalid/secret?token=private-value"
    secret_member = "../private/contract-amounts.csv"
    receipt = UsedInputReceipt(
        "source", ByteIdentity.of(b"hi"), "text/plain", "inline",
        source_id=source, container=ByteIdentity.of(b"archive"),
        member=secret_member,
    )
    def handler(req, invocation):
        invocation.use(receipt)
        invocation.effect(EffectReceipt(
            "storage.write", "confirmed", reference="/private/write/location",
            effect_id="shared",
        ))
        return req
    result = run(DEFINITION, "ok", handler)
    summary = record_from_result(result, occurred_at_utc=TIME)
    data = encode_records((summary,)).decode("utf-8")
    assert source not in data and "private-value" not in data
    assert secret_member not in data and "/private/write/location" not in data
    assert summary.payload["inputs"][0]["source_id_digest"] is not None
    assert summary.payload["details_digest_profile"] == "stratbox.result-details.v3"
    assert summary.payload["privacy_qualification"] == "safe_fields_only_private_locators_omitted"


def test_finish_linked_v3_schema_preserves_typed_projection_after_roundtrip():
    sink = InMemorySink()
    result = run(DEFINITION, "ok", lambda req, inv: req,
                 context=ExecutionContext(sink=sink))
    record = record_from_result(result, finished_event=sink.events[-1])
    assert record.payload["data_version"] == 3
    assert record.payload["details_digest_profile"] == "stratbox.result-details.v3"
    read, = decode_records(encode_records((record,)))
    assert read == record


def test_result_summary_v3_rejects_false_complete_coverage_and_unknown_digest_profile():
    from stratbox.core.observability.records.field_policy import validate_builtin_fields
    result = _run(("confirmed",))
    summary = record_from_result(result, occurred_at_utc=TIME)
    for change in (
        {"details_included": {"diagnostics": 0, "inputs": 0, "effects": 0}},
        {"details_counts": {"diagnostics": 0, "inputs": 0, "effects": 0}},
        {"details_coverage": "summarized"},
        {"details_digest_profile": "unqualified"},
    ):
        broken = replace(summary, payload={**summary.payload, **change})
        with pytest.raises(ValueError):
            validate_builtin_fields(broken)


def test_same_effect_key_with_conflicting_byte_identifications_requires_reconciliation():
    ident_a = ByteIdentity.of(b"version-a")
    ident_b = ByteIdentity.of(b"version-b")
    def worker(req, inv):
        inv.effect(EffectReceipt(
            "storage.write", "confirmed", effect_id="shared", identity=ident_a,
        ))
        return req
    result = run(DEFINITION, "ok", worker)
    summary = record_from_result(result, occurred_at_utc=TIME)
    material = StoredBytesReceipt(
        "private/location", ident_b, "stored", "atomic_create", "local",
        effect_id="shared",
    )
    fact = fact_from_stored_bytes(material, subject_id="dataset", observed_at_utc=TIME)
    rec = record_from_fact(fact, invocation_id=result.invocation_id)
    projected = project_effect_state((summary, rec), KEY_WRITE,
                                     invocation_id=result.invocation_id)
    assert projected.states == ("confirmed",)
    assert projected.conflicting_receipts
    assert projected.needs_reconciliation is True


def test_qualified_record_selection_uses_composite_reference_not_raw_provider_id():
    from stratbox.core.observability import RecordFilter, select_records
    result = _run()
    summary = record_from_result(result, occurred_at_utc=TIME)
    found = tuple(select_records(
        (summary,), RecordFilter(
            related_namespace="effect", related_id=effect_ref_id(KEY_HANDOFF),
        ),
    ))
    assert found == (summary,)
    assert tuple(select_records(
        (summary,), RecordFilter(
            related_namespace="effect", related_id="shared",
        ),
    )) == ()


def test_field_registry_present_rejects_unqualified_standalone_summary():
    from stratbox.core.observability import FieldSchemaRegistry
    result = _run(("confirmed",))
    record = record_from_result(result, occurred_at_utc=TIME)
    broken = replace(record, payload={
        **record.payload, "details_digest_profile": "invalid_digest_profile",
    })
    registry = FieldSchemaRegistry()
    with pytest.raises(ValueError):
        registry.present(broken, allow=frozenset({"public", "operational"}))
