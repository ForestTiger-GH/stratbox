"""Immutable lifecycle observations coupled to state transitions."""
from datetime import datetime

from stratbox.data import ByteIdentity, canonical_manifest_bytes
from stratbox.execution import Correlation
from stratbox.observability import DomainFact, JournalRecord, ObjectRef, make_fact_id, record_from_fact


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
