"""Optional composition of real operation results with typed business evidence.

This is an explicit post-processing operation, not another execution engine.
No source, download, storage or economic computation is re-executed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from stratbox.data import AcquiredSource, ByteIdentity, Comparison
from stratbox.execution import OperationResult
from .adapters import (fact_from_acquisition, fact_from_comparison, fact_from_stored_bytes,
                       record_from_fact, record_from_result)
from .contracts import DomainFact, JournalRecord, ObjectRef, make_fact_id, require_utc


class RecordCapture(Protocol):
    def capture(self, record: JournalRecord) -> bool: ...


@dataclass(frozen=True, slots=True)
class CaptureReport:
    produced: int
    accepted: int
    rejected: int


def fact_for_source_check(*, source_id: str, checked_at_utc: datetime, status: str,
                          version_id: str | None = None, diagnostic_code: str | None = None) -> DomainFact:
    """Check attempts are distinct observations, even when they find no change."""
    subject = ObjectRef("source", source_id)
    identity = {"version_id": version_id, "status": status, "diagnostic": diagnostic_code}
    return DomainFact("source.checked", subject, make_fact_id("source.checked", subject, identity),
                      require_utc(checked_at_utc), identity)


def fact_for_artifact(*, artifact_id: str, identity: ByteIdentity,
                      occurred_at_utc: datetime, stored: bool = False,
                      receipt_status: str | None = None) -> DomainFact:
    kind = "artifact.stored" if stored else "artifact.produced"
    if stored and receipt_status not in {"stored", "already_present", "confirmed"}:
        raise ValueError("Artifact storage confirmation required")
    subject = ObjectRef("artifact", artifact_id, identity=identity)
    payload = {"identity": {"sha256": identity.sha256, "size": identity.size},
               "status": receipt_status if stored else "produced"}
    return DomainFact(kind, subject, make_fact_id(kind, subject, payload),
                      require_utc(occurred_at_utc), payload)


def capture_operation_result(result: OperationResult, recorder: RecordCapture, *,
                             occurred_at_utc: datetime | None = None,
                             dataset_id: str | None = None,
                             baseline_id: str | None = None,
                             candidate_id: str | None = None) -> CaptureReport:
    """Capture a summary and established evidence for known core result classes.

    A comparison requires explicit dataset/release identity from the caller.
    Unknown result types produce only the portable result summary.
    """
    instant = require_utc(occurred_at_utc or datetime.now(timezone.utc))
    records = [record_from_result(result, occurred_at_utc=instant)]
    value = result.value
    if isinstance(value, AcquiredSource):
        records.append(record_from_fact(fact_from_acquisition(value.receipt),
                                        invocation_id=result.invocation_id,
                                        operation_id=result.operation_id))
    if isinstance(value, Comparison):
        if dataset_id and candidate_id:
            fact = fact_from_comparison(value, dataset_id=dataset_id, baseline_id=baseline_id,
                                        candidate_id=candidate_id, occurred_at_utc=instant)
            records.append(record_from_fact(fact, invocation_id=result.invocation_id,
                                            operation_id=result.operation_id))
    # StoredOriginal is created by execution.originals; load its type lazily.
    if value is not None and hasattr(value, "storage") and hasattr(value, "material"):
        from stratbox.execution.originals import StoredOriginal
        if isinstance(value, StoredOriginal):
            if value.acquisition is not None:
                records.append(record_from_fact(fact_from_acquisition(value.acquisition),
                                                invocation_id=result.invocation_id,
                                                operation_id=result.operation_id))
            source_id = (value.material.source_id if value.material else None) or (
                value.acquisition.source_id if value.acquisition else None)
            if source_id is not None:
                records.append(record_from_fact(fact_from_stored_bytes(
                    value.storage, subject_id=source_id, observed_at_utc=instant),
                    invocation_id=result.invocation_id, operation_id=result.operation_id))
    accepted = sum(bool(recorder.capture(x)) for x in records)
    return CaptureReport(len(records), accepted, len(records) - accepted)
