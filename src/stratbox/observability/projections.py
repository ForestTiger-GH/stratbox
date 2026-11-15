"""Pure qualified state projections. Chronology is not authoritative domain order."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from stratbox.execution import OperationResult
from stratbox.data import Comparison, PublicationReceipt, StoredBytesReceipt
from .contracts import JournalRecord
from .coverage import CaptureCoverage
from .history import build_operation_history
from .adapters import effect_state_from_storage_status


@dataclass(frozen=True, slots=True)
class OperationState:
    invocation_id: str
    outcome: str | None
    event_coverage: str
    duration_ms: int | None = None
    stage: str | None = None
    result_known: bool = False

    @property
    def coverage(self) -> str:
        return self.event_coverage


def project_operation_state(records: Iterable[JournalRecord], invocation_id: str, *,
                            coverage: CaptureCoverage | None = None) -> OperationState:
    history = build_operation_history(records, invocation_id, coverage=coverage)
    stages = [rec.payload.get("stage") for rec in history.records if rec.kind == "operation.stage"]
    return OperationState(invocation_id, history.outcome, history.coverage,
                          history.duration_ms, stages[-1] if stages else None,
                          result_known=history.outcome is not None)


def operation_state_from_result(result: OperationResult) -> OperationState:
    return OperationState(result.invocation_id, result.outcome, "not_collected", result_known=True)


@dataclass(frozen=True, slots=True)
class SourceCheckState:
    source_id: str
    last_check_at_utc: str | None
    last_check_outcome: str | None
    confirmed_releases: tuple[str, ...]
    conflict: bool
    current_release_id: str | None = None
    current_release_qualification: str = "indeterminate"
    indeterminate: bool = True


@dataclass(frozen=True, slots=True)
class DatasetState:
    dataset_id: str
    compared_versions: tuple[str, ...]
    latest_comparison: str | None
    indeterminate: bool
    conflict: bool
    comparison_count: int = 0


@dataclass(frozen=True, slots=True)
class ArtifactState:
    artifact_id: str
    identity_sha256: str | None
    produced: bool
    stored_confirmed: bool
    conflicting_identity: bool
    indeterminate: bool = False


@dataclass(frozen=True, slots=True)
class EffectState:
    effect_id: str
    states: tuple[str, ...]
    needs_reconciliation: bool
    conflicting_receipts: bool


def _facts(records, kinds: frozenset[str], namespace: str, ident: str):
    return [rec for rec in records if rec.record_type == "domain_fact" and rec.kind in kinds
            and rec.subject is not None and rec.subject.namespace == namespace and rec.subject.object_id == ident]


def _identity_sha(obj: object) -> str | None:
    if isinstance(obj, Mapping) and type(obj.get("sha256")) is str:
        return obj["sha256"]
    return None


def project_source_state(records: Iterable[JournalRecord], source_id: str, *,
                         resolver: Callable[[tuple[str, ...]], str | None] | None = None) -> SourceCheckState:
    items = [rec for rec in records if rec.record_type == "domain_fact"
             and rec.kind in {"source.checked", "publication.discovered"}
             and ((rec.subject is not None and rec.subject.namespace == "source" and rec.subject.object_id == source_id)
                  or any(ref.namespace == "source" and ref.object_id == source_id for ref in rec.references))]
    checks = sorted((rec for rec in items if rec.kind == "source.checked"),
                    key=lambda rec: (rec.observed_at_utc or rec.occurred_at_utc, rec.record_id))
    releases: dict[tuple[str, str], set[str]] = {}
    for rec in items:
        if rec.kind != "publication.discovered" or rec.payload.get("confirmation") != "confirmed":
            continue
        release = rec.payload.get("release_id")
        if not isinstance(release, str):
            continue
        scope = rec.payload.get("owner_id")
        key = (str(scope), release)
        ident = _identity_sha(rec.payload.get("identity")) or (rec.subject.identity.sha256 if rec.subject and rec.subject.identity else None)
        if ident:
            releases.setdefault(key, set()).add(ident)
    confirmed = tuple(sorted({release for (_, release) in releases}))
    conflict = any(len(identities) > 1 for identities in releases.values())
    current = resolver(confirmed) if resolver else None
    if current is not None and current not in confirmed:
        raise ValueError("Source resolver selected an unconfirmed release")
    last = checks[-1] if checks else None
    return SourceCheckState(source_id, (last.observed_at_utc or last.occurred_at_utc).isoformat() if last else None,
                            str(last.payload.get("status")) if last else None, confirmed, conflict, current,
                            "domain_resolver" if current else "indeterminate", current is None or conflict)


def project_dataset_state(records: Iterable[JournalRecord], dataset_id: str, *,
                          resolver: Callable[[tuple[JournalRecord, ...]], JournalRecord | None] | None = None) -> DatasetState:
    items = _facts(records, frozenset({"dataset.comparison_completed", "dataset.revision_confirmed"}), "dataset", dataset_id)
    groups: dict[tuple[object, object, object, object], set[str]] = {}
    for item in items:
        p = item.payload
        pair = (p.get("baseline"), p.get("candidate"), p.get("comparison_scope", "default"),
                p.get("semantic_method_version", "unspecified"))
        state = p.get("state")
        if isinstance(state, str):
            groups.setdefault(pair, set()).add(state)
    candidates = tuple(sorted({str(r.payload["candidate"]) for r in items if r.payload.get("candidate") is not None}))
    conflict = any(len(states) > 1 for states in groups.values())
    selected = resolver(tuple(items)) if resolver else items[0] if len(groups) == 1 and items else None
    if selected is not None and selected not in items:
        raise ValueError("Dataset resolver returned unobserved comparison")
    current = str(selected.payload["state"]) if selected and not conflict and selected.payload.get("state") else None
    uncertain = conflict or current is None or current == "indeterminate"
    return DatasetState(dataset_id, candidates, current, uncertain, conflict, len(groups))


def project_artifact_state(records: Iterable[JournalRecord], artifact_id: str, *,
                           version_id: str | None = None) -> ArtifactState:
    items = _facts(records, frozenset({"artifact.produced", "artifact.stored"}), "artifact", artifact_id)
    by_version: dict[str, set[str]] = {}
    for item in items:
        if item.subject and item.subject.identity:
            key = item.subject.version_id or "unqualified"
            by_version.setdefault(key, set()).add(item.subject.identity.sha256)
    chosen = by_version.get(version_id) if version_id is not None else (
        next(iter(by_version.values())) if len(by_version) == 1 else set())
    # Without a domain version key, different byte snapshots may be ordinary
    # revisions. They are ambiguous, not automatically competing assertions.
    conflict = (len(chosen or ()) > 1 if version_id is not None else
                any(len(values) > 1 for key, values in by_version.items() if key != "unqualified"))
    identity = next(iter(chosen)) if chosen and len(chosen) == 1 else None
    confirms = [r for r in items if r.kind == "artifact.stored" and r.payload.get("status") in {"stored", "already_present", "confirmed"}
                and (version_id is None or (r.subject and r.subject.version_id == version_id))]
    return ArtifactState(artifact_id, identity, any(r.kind == "artifact.produced" for r in items),
                         bool(confirms), conflict, identity is None and bool(by_version))


def project_effect_state(records: Iterable[JournalRecord], effect_id: str) -> EffectState:
    receipts: list[tuple[str | None, str]] = []
    for rec in records:
        c = rec.correlation
        attempt = c.attempt_id or rec.invocation_id
        if rec.record_type == "result_summary":
            effects = rec.payload.get("effects", ())
            if isinstance(effects, (tuple, list)):
                for evidence in effects:
                    if isinstance(evidence, Mapping) and evidence.get("effect_id") == effect_id and evidence.get("state") in {"confirmed", "failed", "unknown"}:
                        receipts.append((attempt, str(evidence["state"])))
        elif rec.record_type in {"domain_fact", "effect"} and rec.kind in {"material.stored", "effect.unknown", "effect.failed", "effect.confirmed"}:
            is_related = any(ref.namespace == "effect" and ref.object_id == effect_id for ref in rec.references)
            if not is_related and rec.kind in {"material.stored", "effect.unknown", "effect.failed"}:
                is_related = rec.payload.get("effect_id") == effect_id  # explicit historical storage evidence only
            if is_related:
                state = rec.payload.get("effect_state", rec.payload.get("state"))
                if state is None and rec.payload.get("status") in {"stored", "already_present", "failed", "unknown"}:
                    state = effect_state_from_storage_status(str(rec.payload["status"]))
                if state in {"confirmed", "failed", "unknown"}:
                    receipts.append((attempt, str(state)))
    distinct = tuple(sorted({state for _, state in receipts}))
    grouped: dict[str, set[str]] = {}
    for attempt, state in receipts:
        if attempt is not None:
            grouped.setdefault(attempt, set()).add(state)
    conflict = any("confirmed" in states and "failed" in states for states in grouped.values())
    return EffectState(effect_id, distinct, conflict or "confirmed" not in distinct and (not distinct or "unknown" in distinct), conflict)


def projection_rows(items: Iterable[object], fields: tuple[str, ...], *,
                    max_rows: int = 100_000) -> tuple[dict[str, object], ...]:
    if len(set(fields)) != len(fields):
        raise ValueError("Duplicate projection fields")
    rows = []
    for n, item in enumerate(items, 1):
        if n > max_rows:
            raise ValueError("journal.projection_limit")
        rows.append({name: getattr(item, name) for name in fields})
    return tuple(rows)


def source_state_from_publication(receipt: PublicationReceipt) -> SourceCheckState:
    versions = (receipt.release_id,) if receipt.confirmation == "confirmed" else ()
    return SourceCheckState(receipt.owner_id, None, None, versions, False)


def dataset_state_from_comparison(comparison: Comparison, *, dataset_id: str, candidate_id: str) -> DatasetState:
    return DatasetState(dataset_id, (candidate_id,), comparison.state,
                        comparison.state == "indeterminate", False, 1)


def artifact_state_from_storage(receipt: StoredBytesReceipt, *, artifact_id: str) -> ArtifactState:
    return ArtifactState(artifact_id, receipt.identity.sha256, False,
                         receipt.status in {"stored", "already_present"}, False)


def effect_state_from_result(result: OperationResult, *, effect_id: str) -> EffectState:
    states = {item.state for item in result.effects if item.effect_id == effect_id}
    return EffectState(effect_id, tuple(sorted(states)), not states or "unknown" in states and "confirmed" not in states,
                       "confirmed" in states and "failed" in states)
