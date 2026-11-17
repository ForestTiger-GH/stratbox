"""Immutable lifecycle observations coupled to state transitions."""
from datetime import datetime

from stratbox.shared.data import ByteIdentity, canonical_manifest_bytes
from stratbox.core.execution import Correlation
from stratbox.core.observability import DomainFact, JournalRecord, ObjectRef, make_fact_id, record_from_fact


def audit_record(
    kind: str, scope_id: str, object_id: str, now: datetime, *,
    details: dict, correlation: Correlation | None = None, cause: str | None = None,
) -> JournalRecord:
    from dataclasses import replace

    subject = ObjectRef("notification", object_id)
    data = {"data_version": 1, "scope_id": scope_id, **details}
    fact_id = make_fact_id(kind, subject, data)
    observation_id = ByteIdentity.of(canonical_manifest_bytes({
        "fact_id": fact_id, "time": now, "cause": cause,
    })).sha256
    record = record_from_fact(DomainFact(
        kind, subject, fact_id, now, data, observation_id=observation_id,
        observed_at_utc=now, correlation=correlation or Correlation(),
    ))
    return replace(record, cause_record_ids=(cause,)) if cause is not None else record

from dataclasses import replace
from stratbox.core.observability.journal.ports import RecordWriter
from stratbox.core.observability.journal.contracts import JournalWriteReceipt
from stratbox.core.notifications.state.contracts import AuditBatch, NotificationStateStore

def flush_audit(
    state: NotificationStateStore, scope_id: str, writer: RecordWriter, *, limit: int = 200,
) -> JournalWriteReceipt | None:
    records = state.pending_audit(scope_id, limit=limit)
    if not records:
        return None
    batch = AuditBatch(scope_id, records, writer.format)
    receipt = writer.write_batch(batch.records, segment_id=batch.segment_id)
    if not isinstance(receipt, JournalWriteReceipt):
        raise ValueError("journal.write_receipt_invalid")
    if receipt.state == "confirmed":
        if not batch.is_confirmed_by(receipt):
            return replace(receipt, state="failed", diagnostic_code="notification.audit_receipt_mismatch",
                           already_present=False)
        state.acknowledge_audit(batch, receipt)
    return receipt

