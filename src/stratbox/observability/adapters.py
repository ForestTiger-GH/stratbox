"""Pure adapters for existing execution, evidence and domain evidence contracts."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Mapping

from stratbox.data import (AcquisitionReceipt, ByteIdentity, Comparison, PublicationReceipt,
                           StoredBytesReceipt, canonical_manifest_bytes)
from stratbox.execution import ExecutionEvent, OperationResult
from stratbox.execution.contracts import Correlation
from .contracts import DomainFact, JournalRecord, ObjectRef, make_fact_id, require_utc


def _id(kind: str, identity: str) -> str:
    return sha256(f"journal:v1:{kind}:{identity}".encode("utf-8")).hexdigest()


def record_from_execution_event(event: ExecutionEvent) -> JournalRecord:
    payload = json.loads(event.to_json())
    return JournalRecord(
        _id("execution", event.event_id), "execution", event.kind, event.occurred_at_utc,
        payload, correlation=event.correlation, invocation_id=event.invocation_id,
        operation_id=event.operation_id, outcome=event.outcome, sequence=event.sequence,
    )


def record_from_fact(fact: DomainFact, *, operation_id: str | None = None,
                     invocation_id: str | None = None) -> JournalRecord:
    return JournalRecord(
        _id("fact_observation", fact.observation_id), "domain_fact", fact.kind,
        fact.occurred_at_utc, fact.payload, observed_at_utc=fact.observed_at_utc,
        correlation=fact.correlation, invocation_id=invocation_id, operation_id=operation_id,
        fact_id=fact.fact_id, subject=fact.subject, references=fact.references,
    )


def _byte(value: ByteIdentity | None) -> dict[str, object] | None:
    return {"sha256": value.sha256, "size": value.size} if value is not None else None


def record_from_result(result: OperationResult, *, occurred_at_utc: datetime | None = None,
                       correlation: Correlation | None = None) -> JournalRecord:
    """Summarize receipts without embedding the computed value or incidental locators."""
    instant = require_utc(occurred_at_utc or datetime.now(timezone.utc))
    data = {
        "contract_version": result.definition.contract_version,
        "method_version": result.definition.method_version,
        "diagnostics": [{"code": d.code, "stage": d.stage, "component": d.component,
                         "reason_class": d.reason_class, "retry_disposition": d.retry_disposition,
                         "evidence_ref": d.evidence_ref, "incident_id": d.incident_id}
                        for d in result.diagnostics],
        "inputs": [{"role": r.role, "source_id": r.source_id, "identity": _byte(r.identity),
                    "version": _byte(r.version), "container": _byte(r.container), "member": r.member}
                   for r in result.used_inputs],
        "effects": [{"kind": r.kind, "state": r.state, "effect_id": r.effect_id,
                     "stage": r.stage, "identity": _byte(r.identity),
                     "guarantee": r.guarantee, "reconciliation_owner": r.reconciliation_owner}
                    for r in result.effects],
        "computation": ({"id": _byte(result.computation.computation_id),
                         "output": _byte(result.computation.output),
                         "dataset_id": result.computation.version.dataset_id,
                         "release_id": result.computation.version.release_id,
                         "method_version": result.computation.version.method_version}
                        if result.computation is not None else None),
        "observability": {"emitted": result.observability.emitted, "dropped": result.observability.dropped,
                          "incidents_dropped": result.observability.incidents_dropped,
                          "degraded": result.observability.degraded},
        "resources_used": [{"resource": str(resource), "count": count} for resource, count in result.resources_used],
    }
    refs = tuple(ObjectRef("effect", x.effect_id, "receipt", identity=x.identity)
                 for x in result.effects if x.effect_id is not None)
    return JournalRecord(
        _id("result_observation", f"{result.invocation_id}:{instant.isoformat()}"), "result_summary", "operation.result",
        instant, data, correlation=correlation or Correlation(),
        invocation_id=result.invocation_id, operation_id=result.operation_id,
        references=refs, outcome=result.outcome,
    )


def fact_from_acquisition(receipt: AcquisitionReceipt, *, correlation: Correlation | None = None) -> DomainFact:
    subject = ObjectRef("source", receipt.source_id, "subject", identity=receipt.identity)
    return DomainFact(
        "material.acquired", subject,
        make_fact_id("material.acquired", subject, {"bytes": receipt.identity.sha256}),
        receipt.observed_at_utc, {"identity": _byte(receipt.identity), "status_code": receipt.status_code,
                                  "origin_assurance": receipt.origin_assurance, "reused": receipt.reused},
        correlation=correlation or Correlation(),
    )


def fact_from_stored_bytes(receipt: StoredBytesReceipt, *, subject_id: str,
                           observed_at_utc: datetime, correlation: Correlation | None = None) -> DomainFact:
    """Only confirmed storage is called stored; other states remain qualified effects."""
    kind = "material.stored" if receipt.status in {"stored", "already_present"} else "effect.unknown" if receipt.status == "unknown" else "effect.failed"
    subject = ObjectRef("material", subject_id, "subject", identity=receipt.identity)
    return DomainFact(kind, subject,
        make_fact_id(kind, subject, {"effect_id": receipt.effect_id or receipt.identity.sha256, "status": receipt.status}),
        require_utc(observed_at_utc), {"status": receipt.status, "guarantee": receipt.guarantee,
                                       "identity": _byte(receipt.identity), "effect_id": receipt.effect_id},
        correlation=correlation or Correlation())


def fact_from_publication(receipt: PublicationReceipt, *, occurred_at_utc: datetime,
                          correlation: Correlation | None = None) -> DomainFact:
    kind = "publication.discovered" if receipt.confirmation == "confirmed" else "publication.unconfirmed"
    subject = ObjectRef("publication", receipt.release_id, "subject", identity=receipt.identity)
    return DomainFact(kind, subject,
        make_fact_id(kind, subject, {"owner_id": receipt.owner_id,
                                    "destination_id": receipt.destination_id, "transition_id": receipt.transition_id}),
        require_utc(occurred_at_utc), {"confirmation": receipt.confirmation,
                                       "transition_id": receipt.transition_id, "release_id": receipt.release_id,
                                       "owner_id": receipt.owner_id, "identity": _byte(receipt.identity)},
        correlation=correlation or Correlation(),
        references=(ObjectRef("source", receipt.owner_id, "publisher"),))


def fact_from_comparison(comparison: Comparison, *, dataset_id: str, baseline_id: str | None,
                         candidate_id: str, occurred_at_utc: datetime,
                         correlation: Correlation | None = None) -> DomainFact:
    subject = ObjectRef("dataset", dataset_id)
    kind = "dataset.comparison_completed"
    identity = {"baseline": baseline_id, "candidate": candidate_id,
                "state": comparison.state, "reason": comparison.reason,
                "layers": {"original": comparison.layers.original, "facts": comparison.layers.facts,
                           "structure": comparison.layers.structure, "method": comparison.layers.method,
                           "representation": comparison.layers.representation}}
    return DomainFact(kind, subject, make_fact_id(kind, subject, identity), require_utc(occurred_at_utc),
        {**identity, "changed_count": comparison.changed_count,
         "coverage": ({"common_observations": comparison.coverage.common_observations,
                       "baseline_observations": comparison.coverage.baseline_observations,
                       "candidate_observations": comparison.coverage.candidate_observations,
                       "scope": comparison.coverage.scope} if comparison.coverage else None)},
        correlation=correlation or Correlation(),
        references=tuple(ObjectRef("dataset_release", item, relation)
                         for relation, item in (("baseline", baseline_id), ("candidate", candidate_id)) if item))
