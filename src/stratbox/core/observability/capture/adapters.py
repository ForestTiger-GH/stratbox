"""Pure adapters from competent core receipts to immutable, minimal observations."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import uuid4

from stratbox.shared.evidence import AcquisitionReceipt, PublicationReceipt, StoredBytesReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.data.comparison import Comparison
from stratbox.core.execution import EffectKey, ExecutionEvent, OperationResult
from stratbox.core.execution.contracts import Correlation
from stratbox.core.observability.records.contracts import DomainFact, JournalRecord, ObjectRef, make_fact_id, require_utc
from stratbox.core.observability.records.field_policy import validate_builtin_fields
from stratbox.core.observability.records.effect_refs import effect_reference


def _id(kind: str, identity: str) -> str:
    return sha256(f"journal:v1:{kind}:{identity}".encode("utf-8")).hexdigest()


def _byte(value: ByteIdentity | None) -> dict[str, object] | None:
    return {"sha256": value.sha256, "size": value.size} if value is not None else None


def effect_state_from_storage_status(status: str) -> str:
    if status in {"stored", "already_present"}:
        return "confirmed"
    if status in {"failed", "unknown"}:
        return status
    raise ValueError("Invalid storage status")


def record_from_execution_event(event: ExecutionEvent) -> JournalRecord:
    record = JournalRecord(
        _id("execution", event.event_id), "execution", event.kind, event.occurred_at_utc,
        json.loads(event.to_json()), correlation=event.correlation,
        invocation_id=event.invocation_id, operation_id=event.operation_id,
        outcome=event.outcome, sequence=event.sequence,
    )
    validate_builtin_fields(record)
    return record


def record_from_fact(fact: DomainFact, *, operation_id: str | None = None,
                     invocation_id: str | None = None) -> JournalRecord:
    record = JournalRecord(
        _id("fact_observation", fact.observation_id), "domain_fact", fact.kind,
        fact.occurred_at_utc, fact.payload, observed_at_utc=fact.observed_at_utc,
        correlation=fact.correlation, invocation_id=invocation_id, operation_id=operation_id,
        fact_id=fact.fact_id, subject=fact.subject, references=fact.references,
    )
    validate_builtin_fields(record)
    return record


_RESULT_DETAIL_LIMIT = 128


def _diagnostic_detail(item) -> dict[str, object]:
    return {
        "code": item.code, "stage": item.stage, "component": item.component,
        "reason_class": item.reason_class, "retry_disposition": item.retry_disposition,
        "evidence_ref": item.evidence_ref, "incident_id": item.incident_id,
    }


def _input_detail(item) -> dict[str, object]:
    return {
        "role": item.role, "source_id": item.source_id, "identity": _byte(item.identity),
        "version": _byte(item.version), "container": _byte(item.container),
    }


def _effect_detail(item) -> dict[str, object]:
    return {
        "kind": item.kind, "state": item.state, "effect_id": item.effect_id,
        "stage": item.stage, "identity": _byte(item.identity),
        "guarantee": item.guarantee, "reconciliation_owner": item.reconciliation_owner,
    }


def _details_metadata(result: OperationResult) -> tuple[str, dict[str, object]]:
    """Stable digest of complete safe projections, never private locators."""
    digest = sha256()
    streams = (
        ("diagnostics", result.diagnostics, _diagnostic_detail),
        ("inputs", result.used_inputs, _input_detail),
        ("effects", result.effects, _effect_detail),
    )
    for name, entries, project in streams:
        for index, item in enumerate(entries):
            serialized = canonical_manifest_bytes({
                "stream": name, "position": index, "receipt": project(item),
            })
            digest.update(len(serialized).to_bytes(8, "big"))
            digest.update(serialized)
    states = Counter(effect.state for effect in result.effects)
    kinds = Counter(effect.kind for effect in result.effects)
    names = sorted(kinds)
    return digest.hexdigest(), {
        "diagnostics": len(result.diagnostics),
        "inputs": len(result.used_inputs),
        "effects": len(result.effects),
        "confirmed": states["confirmed"],
        "failed": states["failed"],
        "unknown": states["unknown"],
        "effect_kinds": {name: kinds[name] for name in names[:32]},
        "other_effect_kinds": len(names) - min(len(names), 32),
    }


def record_from_result(result: OperationResult, *, occurred_at_utc: datetime | None = None,
                       finished_event: ExecutionEvent | None = None,
                       observation_id: str | None = None,
                       correlation: Correlation | None = None) -> JournalRecord:
    """Build one *observation* or a canonical finish-linked summary.

    `occurred_at_utc` without `finished_event` is the time *observed*, not an
    inferred execution-finish timestamp. A canonical summary requires the actual
    final event. Neither representation embeds computation values or locators.
    """
    cause_ids: tuple[str, ...] = ()
    if finished_event is not None:
        if (finished_event.kind != "operation.finished" or finished_event.invocation_id != result.invocation_id
                or finished_event.operation_id != result.operation_id or finished_event.outcome != result.outcome
                or finished_event.contract_version != result.definition.contract_version
                or finished_event.method_version != result.definition.method_version
                or (correlation is not None and correlation != finished_event.correlation)):
            raise ValueError("Finish event does not match result")
        if occurred_at_utc is not None and occurred_at_utc != finished_event.occurred_at_utc:
            raise ValueError("Finish event timestamp mismatch")
        instant = require_utc(finished_event.occurred_at_utc)
        finished_id = record_from_execution_event(finished_event).record_id
        record_id = _id("result_final_linked", finished_id)
        correlation, cause_ids = finished_event.correlation, (finished_id,)
        time_basis = "producer_finished_event"
        if observation_id is not None:
            raise ValueError("Canonical summary cannot have observation ID")
    else:
        instant = require_utc(occurred_at_utc or datetime.now(timezone.utc))
        stamp = observation_id or uuid4().hex
        from stratbox.core.execution.contracts import safe_token
        safe_token(stamp)
        record_id = _id("result_observation", f"{result.invocation_id}:{stamp}")
        time_basis = "observation"
    digest, counts = _details_metadata(result)
    computation = (
        {"id": _byte(result.computation.computation_id),
         "output": _byte(result.computation.output),
         "dataset_id": result.computation.version.dataset_id,
         "release_id": result.computation.version.release_id,
         "method_version": result.computation.version.method_version}
        if result.computation is not None else None
    )
    metadata = {
        "contract_version": result.definition.contract_version,
        "method_version": result.definition.method_version,
        "time_basis": time_basis,
        "details_digest": digest,
        "details_counts": counts,
        "computation": computation,
        "observability": {
            "emitted": result.observability.emitted,
            "dropped": result.observability.dropped,
            "incidents_dropped": result.observability.incidents_dropped,
            "timing_degraded": result.observability.timing_degraded,
            "degraded": result.observability.degraded,
        },
        "resources_used": [{"resource": str(resource), "count": count}
                           for resource, count in result.resources_used],
    }
    if finished_event is not None:
        metadata["data_version"] = 2

    # A single bounded record cannot convey all receipts of a massive run.
    # Count and hash the entire safe projection, and explicitly label coverage.
    limit = _RESULT_DETAIL_LIMIT
    while True:
        included = {
            "diagnostics": min(len(result.diagnostics), limit),
            "inputs": min(len(result.used_inputs), limit),
            "effects": min(len(result.effects), limit),
        }
        complete = all(included[key] == counts[key] for key in included)
        data = {
            **metadata,
            "diagnostics": [_diagnostic_detail(item) for item in result.diagnostics[:limit]],
            "inputs": [_input_detail(item) for item in result.used_inputs[:limit]],
            "effects": [_effect_detail(item) for item in result.effects[:limit]],
            "details_included": included,
            "details_coverage": "complete" if complete else "summarized",
        }
        refs = tuple(
            effect_reference(item.key, identity=item.identity)
            for item in result.effects[:limit] if item.key is not None
        )
        try:
            rec = JournalRecord(
                record_id, "result_summary", "operation.result", instant, data,
                observed_at_utc=instant if time_basis == "observation" else None,
                correlation=correlation or Correlation(), invocation_id=result.invocation_id,
                operation_id=result.operation_id, references=refs, outcome=result.outcome,
                cause_record_ids=cause_ids,
            )
            validate_builtin_fields(rec)
            return rec
        except ValueError as error:
            if limit == 0 or not str(error).startswith((
                "journal.payload_", "journal.field_length_limit",
            )):
                raise
            limit //= 2


def fact_from_acquisition(receipt: AcquisitionReceipt, *, correlation: Correlation | None = None) -> DomainFact:
    subject = ObjectRef("source", receipt.source_id, "subject", identity=receipt.identity)
    return DomainFact("material.acquired", subject,
                      make_fact_id("material.acquired", subject, {"bytes": receipt.identity.sha256}),
                      receipt.observed_at_utc,
                      {"identity": _byte(receipt.identity), "status_code": receipt.status_code,
                       "origin_assurance": receipt.origin_assurance, "reused": receipt.reused},
                      correlation=correlation or Correlation())


def fact_from_stored_bytes(receipt: StoredBytesReceipt, *, subject_id: str,
                           observed_at_utc: datetime, correlation: Correlation | None = None) -> DomainFact:
    state = effect_state_from_storage_status(receipt.status)
    kind = "material.stored" if state == "confirmed" else "effect.unknown" if state == "unknown" else "effect.failed"
    subject = ObjectRef("material", subject_id, identity=receipt.identity)
    effect_kind = "storage.write"
    payload = {"status": receipt.status, "effect_state": state,
               "effect_kind": effect_kind,
               "guarantee": receipt.guarantee, "identity": _byte(receipt.identity)}
    if receipt.effect_id is not None:
        payload["effect_id"] = receipt.effect_id
    refs = (
        effect_reference(EffectKey(effect_kind, receipt.effect_id), identity=receipt.identity),
    ) if receipt.effect_id is not None else ()
    return DomainFact(kind, subject,
                      make_fact_id(kind, subject, {"effect_kind": effect_kind, "effect_id": receipt.effect_id,
                                                   "status": receipt.status, "guarantee": receipt.guarantee}),
                      require_utc(observed_at_utc), payload,
                      references=refs, correlation=correlation or Correlation())


def fact_from_publication(receipt: PublicationReceipt, *, occurred_at_utc: datetime,
                          correlation: Correlation | None = None) -> DomainFact:
    kind = "publication.discovered" if receipt.confirmation == "confirmed" else "publication.unconfirmed"
    subject = ObjectRef("publication", receipt.release_id, identity=receipt.identity)
    return DomainFact(kind, subject,
                      make_fact_id(kind, subject, {"owner_id": receipt.owner_id,
                                                       "destination_id": receipt.destination_id,
                                                       "transition_id": receipt.transition_id}),
                      require_utc(occurred_at_utc),
                      {"confirmation": receipt.confirmation, "transition_id": receipt.transition_id,
                       "release_id": receipt.release_id, "owner_id": receipt.owner_id,
                       "identity": _byte(receipt.identity)},
                      references=(ObjectRef("source", receipt.owner_id, "publisher"),),
                      correlation=correlation or Correlation())


def fact_from_comparison(comparison: Comparison, *, dataset_id: str, baseline_id: str | None,
                         candidate_id: str, occurred_at_utc: datetime,
                         scope_id: str = "default", method_version: str = "unspecified",
                         correlation: Correlation | None = None) -> DomainFact:
    subject = ObjectRef("dataset", dataset_id)
    identity = {"baseline": baseline_id, "candidate": candidate_id,
                "comparison_scope": scope_id, "semantic_method_version": method_version,
                "state": comparison.state, "reason": comparison.reason,
                "layers": {"original": comparison.layers.original, "facts": comparison.layers.facts,
                           "structure": comparison.layers.structure, "method": comparison.layers.method,
                           "representation": comparison.layers.representation}}
    return DomainFact("dataset.comparison_completed", subject,
                      make_fact_id("dataset.comparison_completed", subject, identity),
                      require_utc(occurred_at_utc),
                      {**identity, "changed_count": comparison.changed_count,
                       "coverage": ({"common_observations": comparison.coverage.common_observations,
                                     "baseline_observations": comparison.coverage.baseline_observations,
                                     "candidate_observations": comparison.coverage.candidate_observations,
                                     "scope": comparison.coverage.scope} if comparison.coverage else None)},
                      references=tuple(ObjectRef("dataset_release", item, relation)
                                       for relation, item in (("baseline", baseline_id), ("candidate", candidate_id)) if item),
                      correlation=correlation or Correlation())
