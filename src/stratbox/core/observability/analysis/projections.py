"""Pure qualified state projections. Chronology is not authoritative domain order."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

from stratbox.core.execution import EffectKey, OperationResult
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.evidence import PublicationReceipt, StoredBytesReceipt
from stratbox.core.observability.records.contracts import JournalRecord
from stratbox.core.observability.assessment.coverage import CaptureCoverage
from stratbox.core.observability.analysis.history import build_operation_history
from stratbox.core.observability.capture.adapters import effect_state_from_storage_status
from stratbox.core.observability.records.effect_refs import effect_ref_id


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
    observed_byte_versions: int = 0
    revision_relation: str = "indeterminate"
    last_success_at_utc: str | None = None
    failed_checks: int = 0


@dataclass(frozen=True, slots=True)
class PublicationObservation:
    owner_id: str
    release_id: str
    sha256: str
    observed_at_utc: str | None


@dataclass(frozen=True, slots=True)
class RevisionResolution:
    relation: str  # same | supersedes | competing | indeterminate
    authority: str = "domain_resolver"

    def __post_init__(self):
        if self.relation not in {"same", "supersedes", "competing", "indeterminate"}:
            raise ValueError("journal.revision_relation_invalid")
        if self.authority != "domain_resolver":
            raise ValueError("journal.revision_authority_invalid")


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
    key: EffectKey
    states: tuple[str, ...]
    needs_reconciliation: bool | None
    conflicting_receipts: bool
    evidence_coverage: Literal["complete", "partial", "not_observed", "indeterminate"]
    observed_attempts: tuple[str, ...] = ()


def _facts(records, kinds: frozenset[str], namespace: str, ident: str):
    return [rec for rec in records if rec.record_type == "domain_fact" and rec.kind in kinds
            and rec.subject is not None and rec.subject.namespace == namespace and rec.subject.object_id == ident]


def _identity_sha(obj: object) -> str | None:
    if isinstance(obj, Mapping) and type(obj.get("sha256")) is str:
        return obj["sha256"]
    return None


def project_source_state(records: Iterable[JournalRecord], source_id: str, *,
                         resolver: Callable[[tuple[str, ...]], str | None] | None = None,
                         revision_resolver: Callable[[tuple[PublicationObservation, ...]], RevisionResolution] | None = None,
                         max_records: int = 100_000) -> SourceCheckState:
    if type(max_records) is not int or not 1 <= max_records <= 1_000_000:
        raise ValueError("journal.projection_limit")
    items = []
    for number, rec in enumerate(records, 1):
        if number > max_records:
            raise ValueError("journal.projection_limit")
        if (rec.record_type == "domain_fact" and rec.kind in {"source.checked", "publication.discovered"}
                and ((rec.subject is not None and rec.subject.namespace == "source" and rec.subject.object_id == source_id)
                     or any(ref.namespace == "source" and ref.object_id == source_id for ref in rec.references))):
            items.append(rec)
    checks = sorted((rec for rec in items if rec.kind == "source.checked"),
                    key=lambda rec: (rec.observed_at_utc or rec.occurred_at_utc, rec.record_id))
    releases: dict[tuple[str, str], set[str]] = {}
    observations: list[PublicationObservation] = []
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
            observations.append(PublicationObservation(str(scope), release, ident,
                (rec.observed_at_utc or rec.occurred_at_utc).isoformat()))
    confirmed = tuple(sorted({release for (_, release) in releases}))
    ambiguous_revision = any(len(identities) > 1 for identities in releases.values())
    relation = "indeterminate" if ambiguous_revision else "same" if releases else "indeterminate"
    if revision_resolver is not None and observations:
        resolved = revision_resolver(tuple(observations))
        if not isinstance(resolved, RevisionResolution):
            raise ValueError("journal.revision_resolution_invalid")
        relation = resolved.relation
    conflict = relation == "competing"
    current = resolver(confirmed) if resolver else None
    if current is not None and current not in confirmed:
        raise ValueError("Source resolver selected an unconfirmed release")
    last = checks[-1] if checks else None
    success = next((rec for rec in reversed(checks)
                    if rec.payload.get("status") in ("succeeded", "unchanged", "changed")), None)
    failed = sum(rec.payload.get("status") in ("failed", "unknown", "unavailable") for rec in checks)
    return SourceCheckState(source_id, (last.observed_at_utc or last.occurred_at_utc).isoformat() if last else None,
                            str(last.payload.get("status")) if last else None, confirmed, conflict, current,
                            "domain_resolver" if current else "indeterminate", current is None or conflict or relation == "indeterminate",
                            sum(len(values) for values in releases.values()), relation,
                            (success.observed_at_utc or success.occurred_at_utc).isoformat() if success else None, failed)


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
    selected = [rec for rec in items if rec.subject is not None and rec.subject.version_id == version_id] \
        if version_id is not None else items
    by_version: dict[str | None, set[str]] = {}
    for item in selected:
        if item.subject and item.subject.identity:
            by_version.setdefault(item.subject.version_id, set()).add(item.subject.identity.sha256)
    if version_id is not None:
        chosen = by_version.get(version_id, set())
        conflict = len(chosen) > 1
    elif len(by_version) == 1:
        chosen = next(iter(by_version.values()))
        # Unknown revision identity may mean a sequence of ordinary snapshots.
        conflict = len(chosen) > 1 and None not in by_version
    else:
        chosen = set()
        conflict = False
    identity = next(iter(chosen)) if len(chosen) == 1 else None
    produced = any(rec.kind == "artifact.produced" for rec in selected)
    confirmed = any(rec.kind == "artifact.stored" and
                    rec.payload.get("status") in {"stored", "already_present", "confirmed"}
                    for rec in selected)
    return ArtifactState(artifact_id, identity, produced, confirmed, conflict,
                         not selected or identity is None)


def _qualified_effect_state(
    key: EffectKey, observations: list[tuple[str, str]], *,
    partial: bool, scope_observed: bool, single_invocation: bool,
) -> EffectState:
    grouped: dict[str, set[str]] = {}
    for attempt, state in observations:
        grouped.setdefault(attempt, set()).add(state)
    states = tuple(sorted({state for _, state in observations}))
    attempts = tuple(sorted(grouped))
    conflict = any(
        "confirmed" in values and "failed" in values
        for values in grouped.values()
    )
    if not states:
        return EffectState(
            key, (), None, False,
            "partial" if partial else "not_observed" if scope_observed else "indeterminate",
        )
    uncertain_attempt = not single_invocation and len(grouped) > 1
    coverage = "partial" if partial else "indeterminate" if uncertain_attempt else "complete"
    if conflict or "unknown" in states:
        reconciliation: bool | None = True
    elif partial or uncertain_attempt:
        # Another (possibly truncated) attempt cannot close a different
        # attempt without qualified provider-owned equivalence.
        reconciliation = None
    else:
        reconciliation = False
    return EffectState(key, states, reconciliation, conflict, coverage, attempts)


def project_effect_state(
    records: Iterable[JournalRecord], key: EffectKey, *,
    invocation_id: str | None = None,
) -> EffectState:
    """Qualified, attempt-aware and prefix-coverage-aware effect projection.

    A positive observation is evidence of an observed state, not a claim that
    the physical effect is globally unique across invocation attempts.
    """
    if not isinstance(key, EffectKey):
        raise TypeError("Use a kind-qualified EffectKey")
    ref_id = effect_ref_id(key)
    observations: list[tuple[str, str]] = []
    partial = False
    saw_scope = False
    for rec in records:
        if invocation_id is not None and rec.invocation_id != invocation_id:
            continue
        attempt = rec.invocation_id or rec.correlation.attempt_id or "unspecified"
        if rec.record_type == "result_summary" and rec.kind == "operation.result":
            saw_scope = True
            effects = rec.payload.get("effects")
            counts = rec.payload.get("details_counts")
            included = rec.payload.get("details_included")
            if not isinstance(effects, (tuple, list)):
                partial = True
                continue
            expected = counts.get("effects") if isinstance(counts, Mapping) else None
            shown = included.get("effects") if isinstance(included, Mapping) else None
            if type(expected) is not int or type(shown) is not int or (
                expected < len(effects) or shown != len(effects) or expected != shown
            ):
                partial = True
            for item in effects:
                if not isinstance(item, Mapping):
                    partial = True
                    continue
                if (item.get("kind") == key.kind and item.get("effect_id") == key.effect_id
                        and item.get("state") in {"confirmed", "failed", "unknown"}):
                    observations.append((attempt, str(item["state"])))
        elif rec.record_type in {"domain_fact", "effect"} and rec.kind in {
            "material.stored", "effect.unknown", "effect.failed", "effect.confirmed",
        }:
            related = any(
                ref.namespace == "effect" and ref.object_id == ref_id
                for ref in rec.references
            )
            tagged = (rec.payload.get("effect_kind") == key.kind
                      and rec.payload.get("effect_id") == key.effect_id)
            if not related and not tagged:
                continue
            saw_scope = True
            if (rec.payload.get("effect_kind") is not None
                    and not tagged):
                partial = True  # Internally contradictory identity labels.
                continue
            state = rec.payload.get("effect_state", rec.payload.get("state"))
            if state is None and rec.payload.get("status") in {
                "stored", "already_present", "failed", "unknown",
            }:
                state = effect_state_from_storage_status(str(rec.payload["status"]))
            if state in {"confirmed", "failed", "unknown"}:
                observations.append((attempt, str(state)))
            else:
                partial = True
    return _qualified_effect_state(
        key, observations, partial=partial, scope_observed=saw_scope,
        single_invocation=invocation_id is not None,
    )


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


def effect_state_from_result(
    result: OperationResult, *, key: EffectKey,
) -> EffectState:
    if not isinstance(key, EffectKey):
        raise TypeError("Use a kind-qualified EffectKey")
    observations = [(result.invocation_id, effect.state)
                    for effect in result.effects if effect.key == key]
    return _qualified_effect_state(
        key, observations, partial=False, scope_observed=True,
        single_invocation=True,
    )
