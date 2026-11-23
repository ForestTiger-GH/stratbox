"""Explicit post-processing of qualified core results; no business work is rerun."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Protocol

from stratbox.shared.evidence import AcquiredSource
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.comparison import Comparison
from stratbox.core.execution import Correlation, ExecutionEvent, OperationResult
from stratbox.core.observability.capture.adapters import (fact_from_acquisition, fact_from_comparison, fact_from_stored_bytes,
                       record_from_fact, record_from_result)
from stratbox.core.observability.records.contracts import DomainFact, JournalRecord, ObjectRef, make_fact_id, require_utc
from stratbox.core.observability.capture.sinks import CaptureDisposition


class RecordCapture(Protocol):
    def capture(self, record: JournalRecord) -> bool: ...


@dataclass(frozen=True, slots=True)
class CaptureReport:
    produced: int
    accepted: int
    policy_filtered: int
    rejected_capacity: int
    failed_capture: int
    unknown_capture: int

    @property
    def rejected(self) -> int:
        return self.produced - self.accepted


def fact_for_source_check(*, source_id: str, checked_at_utc: datetime, status: str,
                          version_id: str | None = None, diagnostic_code: str | None = None,
                          check_id: str | None = None) -> DomainFact:
    """Stable assertion identity; every check is a separate observation.

    Explicit check_id can identify the individual check where required; it does
    not silently turn one stable fact into a new release on every polling run.
    """
    subject = ObjectRef("source", source_id)
    identity = {"version_id": version_id, "status": status, "diagnostic": diagnostic_code}
    if check_id is not None:
        identity["check_id"] = check_id
    return DomainFact("source.checked", subject,
                      make_fact_id("source.checked", subject, identity),
                      require_utc(checked_at_utc), identity)


def fact_for_artifact(*, artifact_id: str, identity: ByteIdentity,
                      occurred_at_utc: datetime, stored: bool = False,
                      receipt_status: str | None = None, version_id: str | None = None) -> DomainFact:
    kind = "artifact.stored" if stored else "artifact.produced"
    if stored and receipt_status not in {"stored", "already_present", "confirmed"}:
        raise ValueError("Artifact storage confirmation required")
    subject = ObjectRef("artifact", artifact_id, version_id=version_id, identity=identity)
    payload = {"identity": {"sha256": identity.sha256, "size": identity.size},
               "status": receipt_status if stored else "produced"}
    return DomainFact(kind, subject, make_fact_id(kind, subject, payload),
                      require_utc(occurred_at_utc), payload)


def capture_operation_result(result: OperationResult, recorder: RecordCapture, *,
                             occurred_at_utc: datetime | None = None,
                             finished_event: ExecutionEvent | None = None,
                             correlation: Correlation | None = None,
                             dataset_id: str | None = None,
                             baseline_id: str | None = None,
                             candidate_id: str | None = None) -> CaptureReport:
    if finished_event is None and occurred_at_utc is None:
        find_finished = getattr(recorder, "finished_event", None)
        if callable(find_finished):
            finished_event = find_finished(result.invocation_id)
    if finished_event is not None and occurred_at_utc is None:
        occurred_at_utc = finished_event.occurred_at_utc
    instant = require_utc(occurred_at_utc or datetime.now(timezone.utc))
    records = [record_from_result(result, occurred_at_utc=instant, finished_event=finished_event,
                                  correlation=correlation)]
    value = result.value
    # Neutral retained processing values have portable content identities. Emit
    # artifact evidence without copying their data or source locators to logs.
    from stratbox.shared.data.snapshots import DatasetSnapshot
    from stratbox.shared.data.workbooks import WorkbookExtract
    from stratbox.shared.data.documents import DocumentExtract
    from stratbox.shared.data.views import ObservationView
    if result.outcome in {"succeeded", "partial"} and isinstance(value, (
            DatasetSnapshot, WorkbookExtract, DocumentExtract, ObservationView)):
        identity = value.identity
        records.append(record_from_fact(fact_for_artifact(artifact_id=identity.sha256,
            identity=identity, occurred_at_utc=instant), invocation_id=result.invocation_id,
            operation_id=result.operation_id))
    # Publisher-domain operations may wrap the neutral source receipt with
    # release/asset context. Project the same underlying evidence only once.
    nested = getattr(value, "source", None) if value is not None else None
    acquired = value if isinstance(value, AcquiredSource) else nested
    if isinstance(acquired, AcquiredSource):
        records.append(record_from_fact(fact_from_acquisition(acquired.receipt),
                                        invocation_id=result.invocation_id, operation_id=result.operation_id))
    if isinstance(value, Comparison) and dataset_id and candidate_id:
        records.append(record_from_fact(fact_from_comparison(value, dataset_id=dataset_id,
                                                             baseline_id=baseline_id, candidate_id=candidate_id,
                                                             occurred_at_utc=instant),
                                        invocation_id=result.invocation_id, operation_id=result.operation_id))
    from stratbox.core.operations.source.originals import StoredOriginal
    stored = value if isinstance(value, StoredOriginal) else nested
    if isinstance(stored, StoredOriginal):
        if stored.acquisition is not None:
            records.append(record_from_fact(fact_from_acquisition(stored.acquisition),
                                            invocation_id=result.invocation_id, operation_id=result.operation_id))
        source_id = (stored.material.source_id if stored.material else None) or (
            stored.acquisition.source_id if stored.acquisition else None)
        if source_id is not None:
            records.append(record_from_fact(fact_from_stored_bytes(stored.storage, subject_id=source_id,
                                                                    observed_at_utc=instant),
                                            invocation_id=result.invocation_id, operation_id=result.operation_id))
    summary = records[0]
    records[1:] = [
        replace(record, correlation=summary.correlation, cause_record_ids=(summary.record_id,))
        for record in records[1:]
    ]
    accepted = filtered = capacity = failed = unknown = 0
    for rec in records:
        classifier = getattr(recorder, "capture_disposition", None)
        try:
            disposition = classifier(rec) if callable(classifier) else (
                CaptureDisposition("accepted", "journal.accepted") if recorder.capture(rec) else
                CaptureDisposition("unknown", "journal.capture_unqualified"))
        except Exception:
            disposition = CaptureDisposition("failed", "journal.capture_failed")
        if disposition.state == "accepted":
            accepted += 1
        elif disposition.state == "filtered":
            filtered += 1
        elif disposition.state == "dropped":
            capacity += 1
        elif disposition.state == "failed":
            failed += 1
        else:
            unknown += 1
    return CaptureReport(len(records), accepted, filtered, capacity, failed, unknown)
