"""Pure, conservative projections of the latest known technical and domain states.

A later *attempt* never silently replaces the last *confirmed* business version.
Competing versions remain explicit unless a caller supplies source-specific order.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from stratbox.execution import OperationResult
from stratbox.data import Comparison, PublicationReceipt, StoredBytesReceipt
from .contracts import JournalRecord
from .history import OperationHistory, build_operation_history


@dataclass(frozen=True, slots=True)
class OperationState:
    invocation_id: str
    outcome: str | None
    coverage: str
    duration_ms: int | None = None
    stage: str | None = None


def project_operation_state(records: Iterable[JournalRecord], invocation_id: str,
                            *, capture_complete: bool = False) -> OperationState:
    history = build_operation_history(records, invocation_id, capture_complete=capture_complete)
    stages = [r.payload.get("stage") for r in history.records if r.kind == "operation.stage"]
    return OperationState(invocation_id, history.outcome, history.coverage, history.duration_ms,
                          stages[-1] if stages else None)


def operation_state_from_result(result: OperationResult) -> OperationState:
    return OperationState(result.invocation_id, result.outcome,
                          "complete" if not result.observability.degraded else "indeterminate")


@dataclass(frozen=True, slots=True)
class SourceCheckState:
    source_id: str
    last_check_at_utc: str | None
    last_check_outcome: str | None
    confirmed_releases: tuple[str, ...]
    conflict: bool


@dataclass(frozen=True, slots=True)
class DatasetState:
    dataset_id: str
    compared_versions: tuple[str, ...]
    latest_comparison: str | None
    indeterminate: bool
    conflict: bool


@dataclass(frozen=True, slots=True)
class ArtifactState:
    artifact_id: str
    identity_sha256: str | None
    produced: bool
    stored_confirmed: bool
    conflicting_identity: bool


@dataclass(frozen=True, slots=True)
class EffectState:
    effect_id: str
    states: tuple[str, ...]
    needs_reconciliation: bool
    conflicting_receipts: bool


def _facts(records, kind, namespace, ident):
    return [r for r in records if r.record_type == "domain_fact" and r.kind in kind and
            r.subject is not None and r.subject.namespace == namespace and r.subject.object_id == ident]


def project_source_state(records: Iterable[JournalRecord], source_id: str) -> SourceCheckState:
    items = [r for r in records if r.record_type == "domain_fact" and r.kind in {"source.checked", "publication.discovered"}
             and ((r.subject is not None and r.subject.namespace == "source" and r.subject.object_id == source_id)
                  or any(ref.namespace == "source" and ref.object_id == source_id for ref in r.references))]
    checks = sorted((r for r in items if r.kind == "source.checked"),
                    key=lambda r: (r.observed_at_utc or r.occurred_at_utc, r.record_id))
    releases = {str(r.payload.get("release_id")) for r in items
                if r.kind == "publication.discovered" and r.payload.get("confirmation") == "confirmed"
                and r.payload.get("release_id") is not None}
    return SourceCheckState(source_id, checks[-1].occurred_at_utc.isoformat() if checks else None,
                            checks[-1].outcome if checks else None,
                            tuple(sorted(releases)), len(releases) > 1)


def project_dataset_state(records: Iterable[JournalRecord], dataset_id: str) -> DatasetState:
    items = _facts(tuple(records), {"dataset.comparison_completed", "dataset.revision_confirmed"}, "dataset", dataset_id)
    candidates = {str(r.payload["candidate"]) for r in items if r.payload.get("candidate") is not None}
    states = {str(r.payload["state"]) for r in items if r.payload.get("state") is not None}
    return DatasetState(dataset_id, tuple(sorted(candidates)), next(iter(states)) if len(states) == 1 else None,
                        "indeterminate" in states, len(candidates) > 1 or len(states) > 1)


def project_artifact_state(records: Iterable[JournalRecord], artifact_id: str) -> ArtifactState:
    items = _facts(tuple(records), {"artifact.produced", "artifact.stored"}, "artifact", artifact_id)
    ids = {r.subject.identity.sha256 for r in items if r.subject and r.subject.identity}
    confirms = [r for r in items if r.kind == "artifact.stored" and r.payload.get("status") in {"stored", "already_present", "confirmed"}]
    return ArtifactState(artifact_id, next(iter(ids)) if len(ids) == 1 else None,
                         any(r.kind == "artifact.produced" for r in items), bool(confirms), len(ids) > 1)


def project_effect_state(records: Iterable[JournalRecord], effect_id: str) -> EffectState:
    items = tuple(records)
    states = set()
    for r in items:
        if r.record_type == "result_summary":
            for receipt in r.payload.get("effects", ()):
                if isinstance(receipt, dict) and receipt.get("effect_id") == effect_id:
                    states.add(receipt.get("state"))
        elif r.record_type in {"domain_fact", "effect"} and any(
                ref.namespace == "effect" and ref.object_id == effect_id for ref in r.references):
            if r.payload.get("state"):
                states.add(r.payload["state"])
    distinct = tuple(sorted(x for x in states if isinstance(x, str)))
    return EffectState(effect_id, distinct, "unknown" in states or not states,
                       len(states & {"confirmed", "failed", "unknown"}) > 1)


def projection_rows(items: Iterable[object], fields: tuple[str, ...]) -> tuple[dict[str, object], ...]:
    """Explicit plain rows for a chosen typed projection and CSV schema."""
    return tuple({field: getattr(item, field) for field in fields} for item in items)


def source_state_from_publication(receipt: PublicationReceipt) -> SourceCheckState:
    versions = (receipt.release_id,) if receipt.confirmation == "confirmed" else ()
    return SourceCheckState(receipt.owner_id, None, None, versions, False)


def dataset_state_from_comparison(comparison: Comparison, *, dataset_id: str, candidate_id: str) -> DatasetState:
    return DatasetState(dataset_id, (candidate_id,), comparison.state, comparison.state == "indeterminate", False)


def artifact_state_from_storage(receipt: StoredBytesReceipt, *, artifact_id: str) -> ArtifactState:
    return ArtifactState(artifact_id, receipt.identity.sha256, False,
                         receipt.status in {"stored", "already_present"}, False)


def effect_state_from_result(result: OperationResult, *, effect_id: str) -> EffectState:
    states = {x.state for x in result.effects if x.effect_id == effect_id}
    return EffectState(effect_id, tuple(sorted(states)), "unknown" in states or not states, len(states) > 1)
