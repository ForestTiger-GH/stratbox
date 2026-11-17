from dataclasses import replace
from decimal import Decimal

import pytest

from stratbox.base.filestore import LocalFileStore
from stratbox.data import ByteIdentity
from stratbox.notifications import (
    AuditBatch, CheckpointUpdate, DispatchUpdate, MemoryNotificationState, PrepareRequest,
    RecordIdentity, StateMutation, flush_audit, prepare,
)
from stratbox.observability import FileJournalWriter, JournalRecord, JournalWriteReceipt

from conftest import TIME, byte_event


@pytest.mark.parametrize("field,code", (
    ("checkpoint_updates", "notification.checkpoint_duplicate"),
    ("dispatch_updates", "notification.dispatch_duplicate"),
    ("record_identities", "journal.record_identity_duplicate"),
    ("audit", "notification.audit_duplicate"),
))
def test_state_mutation_rejects_writes_to_the_same_key(session, field, code):
    runtime, key, context, source, _, _ = session
    source.records.append(byte_event())
    prepare(PrepareRequest(key), runtime=runtime, context=context)
    state = runtime.state
    row, = state.scan_dispatches(key.scope_id, key.subscription_id, limit=2)
    cursor = state.get_checkpoint(key)
    identity = RecordIdentity("publisher", "same-record", ByteIdentity.of(b"first"))
    audit = state.pending_audit(key.scope_id, limit=1)[0]
    entries = {
        "checkpoint_updates": (CheckpointUpdate(key, cursor, replace(cursor, last_offset=2)),
                               CheckpointUpdate(key, cursor, replace(cursor, last_offset=3))),
        "dispatch_updates": (DispatchUpdate(row.version, replace(row, version=2, state="cancelled")),
                             DispatchUpdate(row.version, replace(row, version=2, state="expired"))),
        "record_identities": (identity, replace(identity, identity=ByteIdentity.of(b"second"))),
        "audit": (audit, replace(audit, payload={"different": True})),
    }
    with pytest.raises(ValueError, match=code):
        StateMutation(key.scope_id, key.subscription_id, 2, **{field: entries[field]})


def test_state_command_identity_includes_exact_audit_bytes():
    state = MemoryNotificationState()
    record = JournalRecord("same-record", "diagnostic", "test.audit", TIME, {"value": Decimal("1.0")})
    first = StateMutation("scope", "subscription", None, audit=(record,))
    second = replace(first, audit=(replace(record, payload={"value": "1.0"}),))
    assert first.command_id != second.command_id
    assert state.commit(first).state == "confirmed"
    assert state.commit(second).state == "conflict"
    assert state.pending_audit("scope", limit=2) == (record,)


@pytest.mark.parametrize("mismatch", ("digest", "size", "record_ids", "segment_id"))
def test_mismatched_confirmed_receipt_keeps_the_audit_pending(session, mismatch):
    runtime, key, _, _, _, _ = session
    pending = runtime.state.pending_audit(key.scope_id, limit=10)
    batch = AuditBatch(key.scope_id, pending, "jsonl")
    identity = batch.content_identity
    changes = {
        "digest": {"content_identity": replace(identity, sha256="0" * 64)},
        "size": {"content_identity": replace(identity, size=identity.size + 1)},
        "record_ids": {"record_ids": batch.record_ids[::-1]},
        "segment_id": {"segment_id": "another-segment"},
    }

    class WrongReceiptWriter:
        format = "jsonl"

        def write_batch(self, records, *, segment_id):
            assert records == pending
            receipt = JournalWriteReceipt("confirmed", segment_id, identity, batch.record_ids,
                                          "immutable_read_back", "export")
            return replace(receipt, **changes[mismatch])

    receipt = flush_audit(runtime.state, key.scope_id, WrongReceiptWriter())
    assert (receipt.state, receipt.diagnostic_code) == ("failed", "notification.audit_receipt_mismatch")
    assert runtime.state.pending_audit(key.scope_id, limit=10) == pending


def test_old_receipt_cannot_clear_a_changed_batch(session, tmp_path):
    runtime, key, _, _, _, _ = session
    state = runtime.state
    batch = AuditBatch(key.scope_id, state.pending_audit(key.scope_id, limit=10), "jsonl")
    writer = FileJournalWriter(LocalFileStore(tmp_path), "audit", writer_id="notifications")
    receipt = writer.write_batch(batch.records, segment_id=batch.segment_id)
    with pytest.raises(ValueError, match="notification.audit_unconfirmed"):
        state.acknowledge_audit(replace(batch, scope_id="another-scope"), receipt)
    state.acknowledge_audit(batch, receipt)
    state.acknowledge_audit(batch, receipt)
    assert state.pending_audit(key.scope_id, limit=10) == ()

    first, last = batch.records
    pending = (first, replace(last, payload={**last.payload, "revision": 3}))
    command = StateMutation(key.scope_id, key.subscription_id, 2, audit=pending)
    assert state.commit(command).state == "confirmed"
    with pytest.raises(ValueError, match="notification.audit_conflict"):
        state.acknowledge_audit(batch, receipt)
    assert state.pending_audit(key.scope_id, limit=10) == pending


def test_audit_retry_reuses_the_same_confirmed_segment(session, tmp_path):
    runtime, key, _, _, _, _ = session
    state = runtime.state
    pending = state.pending_audit(key.scope_id, limit=10)
    writer = FileJournalWriter(LocalFileStore(tmp_path), "audit", writer_id="notifications")

    class LostReplyWriter:
        format = writer.format

        def write_batch(self, records, *, segment_id):
            receipt = writer.write_batch(records, segment_id=segment_id)
            return replace(receipt, state="unknown", diagnostic_code="journal.commit_unknown")

    lost = flush_audit(state, key.scope_id, LostReplyWriter())
    assert lost.state == "unknown"
    assert state.pending_audit(key.scope_id, limit=10) == pending
    recovered = flush_audit(state, key.scope_id, writer)
    assert recovered.state == "confirmed" and recovered.already_present
    assert recovered.segment_id == lost.segment_id
    assert state.pending_audit(key.scope_id, limit=10) == ()
