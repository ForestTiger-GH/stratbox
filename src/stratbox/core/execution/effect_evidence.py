"""One admission boundary for direct results and exact-effect observations.

The caller binds a provider invocation to the durable intended occurrence. A
provider need not echo its arguments, but every identifier or precondition it
does return must agree. Current bytes prove a copy postcondition; they do not
prove a conditional replacement, move, or deletion happened under its intended
preconditions. This module admits evidence, not a global exactly-once promise.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import datetime, timezone
import json

from stratbox.shared.data.materials import NamedEffectIntent, NamedMaterialReceipt
from stratbox.shared.data.values import ImmutableMaterialRef, SnapshotRef, canonical_tree, fingerprint, immutable


@dataclass(frozen=True)
class EffectEvidence:
    effect_id: str
    effect_kind: str
    provider_scope: str | None
    intent_identity: str
    outcome: str
    evidence_kind: str
    evidence_identity: str
    observed_at: datetime
    payload: object
    acknowledgement_level: str | None = None


@dataclass(frozen=True)
class EvidenceAdmission:
    outcome: str
    value: object = None
    finding: str | None = None
    evidence: EffectEvidence | None = None


def evidence_summary(evidence):
    """Retain qualification metadata without duplicating the receipt payload."""
    if evidence is None:
        return None
    if not isinstance(evidence, EffectEvidence):
        raise TypeError('effect.typed_evidence_required')
    return immutable({item.name: getattr(evidence, item.name)
                      for item in fields(evidence) if item.name != 'payload'})


_POSITIVE = frozenset({'confirmed', 'accepted', 'delivered', 'stored', 'already_present'})
_REVISION_FIELDS = frozenset({'expected_source_revision', 'expected_destination_revision'})
_REFERENCE_FIELDS = ('location', 'identity', 'provider_id', 'guarantee', 'effect_id', 'provider_scope')
_MISSING = object()


def _field(value, name):
    return value.get(name, _MISSING) if isinstance(value, Mapping) else getattr(value, name, _MISSING)


def _scope(expected):
    intent = expected.intent
    return (intent.get('provider_scope') if isinstance(intent, Mapping)
            else getattr(intent, 'provider_scope', None)) or expected.resource


def same_effect_intent(left, right):
    """Compare the semantic obligation, allowing already observed revisions.

    Immutable content can have several logical users. Its first accepted
    provenance remains on the historical receipt, outside physical identity.
    """
    if isinstance(left, ImmutableMaterialRef) and isinstance(right, ImmutableMaterialRef):
        return all(getattr(left, name) == getattr(right, name) for name in _REFERENCE_FIELDS)
    if isinstance(left, NamedEffectIntent) and isinstance(right, NamedEffectIntent):
        return all(getattr(left, item.name) == getattr(right, item.name)
            or item.name in _REVISION_FIELDS and None in (getattr(left, item.name), getattr(right, item.name))
            for item in fields(left))
    return fingerprint(left) == fingerprint(right)


def valid_intent_update(previous, updated):
    """A claimed occurrence may add observations, never change its obligation."""
    if isinstance(previous, NamedEffectIntent) and isinstance(updated, NamedEffectIntent):
        return same_effect_intent(previous, updated) and all(
            getattr(previous, name) is None or getattr(previous, name) == getattr(updated, name)
            for name in _REVISION_FIELDS)
    if isinstance(previous, Mapping) and isinstance(updated, Mapping):
        return all(key in updated and fingerprint(value) == fingerprint(updated[key])
                   for key, value in previous.items())
    return same_effect_intent(previous, updated)


def _conflict(value, expected):
    # Check all aliases independently: a matching primary alias cannot hide a
    # contradictory secondary alias, including aliases exposed as attributes.
    for names, wanted in ((('effect_id', 'intent_id'), expected.effect_id),
                          (('effect_kind', 'kind'), expected.kind)):
        for name in names:
            actual = _field(value, name)
            if actual is not _MISSING and actual != wanted:
                return 'effect.evidence_identity_conflict'
    intent = expected.intent
    scope = _scope(expected)
    for name, wanted in (('provider_scope', scope), ('resource', expected.resource),
                         ('intent_identity', fingerprint(intent)), ('intent', intent)):
        actual = _field(value, name)
        if actual is not _MISSING and fingerprint(actual) != fingerprint(wanted):
            return 'effect.evidence_intent_conflict'
    if isinstance(intent, Mapping) and expected.kind == 'notification.deliver':
        for name in ('payload', 'route'):
            actual = _field(value, name)
            if actual is not _MISSING and fingerprint(actual) != fingerprint(intent.get(name)):
                return 'effect.evidence_payload_conflict'
    if isinstance(intent, Mapping) and expected.kind in {'dataset.write', 'publication.write'}:
        for name in ('provider_id', 'destination', 'identity', 'expected_token'):
            actual = _field(value, name)
            if actual is not _MISSING and fingerprint(actual) != fingerprint(intent.get(name)):
                return 'effect.evidence_payload_conflict'
    if isinstance(intent, NamedEffectIntent):
        for name in ('destination', 'identity', 'operation', 'source', 'policy',
                     'expected_source', 'expected_destination', 'expected_source_revision',
                     'expected_destination_revision', 'source_provider_scope', 'prerequisites'):
            actual = _field(value, name)
            if actual is not _MISSING and fingerprint(actual) != fingerprint(getattr(intent, name)):
                return 'effect.evidence_precondition_conflict'
    return None


def _payload_outcome(expected, value, source):
    intent = expected.intent
    if expected.kind == 'dataset.write':
        if (not isinstance(intent, Mapping) or not isinstance(value, SnapshotRef)
                or (value.provider_id, value.provider_scope, value.identity) != (
                    intent.get('provider_id'), intent.get('provider_scope'), intent.get('identity'))
                or not isinstance(value.snapshot_id, str) or not value.snapshot_id or len(value.snapshot_id) > 8192):
            return 'conflict', 'effect.evidence_snapshot_payload_conflict', None
        return 'confirmed', None, 'identified_action_lookup' if source == 'lookup' else 'direct_result'
    if expected.kind == 'publication.write':
        token = value.get('token') if isinstance(value, Mapping) else value
        if (not isinstance(intent, Mapping) or token != intent.get('identity')
                or source == 'lookup'):
            return 'unknown', 'effect.conditional_publication_evidence_required', None
        return 'confirmed', None, 'verified_causal_transition'
    if isinstance(intent, ImmutableMaterialRef):
        if not isinstance(value, ImmutableMaterialRef) or not same_effect_intent(intent, value):
            return 'conflict', 'effect.evidence_retained_payload_conflict', None
        # A receipt for another accepted origin is not this occurrence's proof.
        if value.accepted_value_id != intent.accepted_value_id:
            return 'conflict', 'effect.evidence_retained_payload_conflict', None
        return 'confirmed', None, 'verified_current_postcondition' if source == 'lookup' else 'direct_result'
    if isinstance(intent, NamedEffectIntent):
        if not isinstance(value, NamedMaterialReceipt) or (
                value.operation, value.destination, value.identity, value.provider_scope) != (
                intent.operation, intent.destination, intent.identity, intent.provider_scope):
            return 'conflict', 'effect.evidence_named_payload_conflict', None
        if intent.operation in {'move', 'delete'} or intent.policy == 'replace_if_matches':
            guarantee = ('guarded_conditional_transition' if intent.operation in {'move', 'delete'}
                         else 'compare_and_replace_under_directory_guard')
            if value.guarantee != guarantee:
                return 'unknown', 'effect.causal_transition_evidence_required', None
            return 'confirmed', None, 'verified_causal_transition'
        if value.guarantee not in {'atomic_create', 'verified_existing_postcondition',
                                   'verified_current_postcondition', 'verified_postcondition'}:
            return 'unknown', 'effect.copy_postcondition_evidence_required', None
        return 'confirmed', None, 'verified_current_postcondition'
    if source == 'lookup':
        return 'confirmed', None, 'identified_action_lookup'
    return 'confirmed', None, 'direct_result'


def admit_evidence(expected, observed, *, source='action'):
    """Admit an observation only for the supplied durable intended occurrence.

    A direct callback without a status is its adapter's successful result. A
    lookup requires positive evidence. Negative lookup alone never proves that
    an earlier uncertain external mutation did not happen.
    """
    if source not in {'action', 'lookup'}:
        raise ValueError('effect.evidence_source_invalid')
    statuses = []
    # A wrapper is evidence about its payload, never a way to hide a lower
    # confidence or contradictory status inside that payload. Inspect every
    # supplied layer before classifying the one resulting observation.
    for _ in range(8):
        if isinstance(observed, EffectEvidence):
            if (observed.effect_id != expected.effect_id or observed.effect_kind != expected.kind
                    or observed.provider_scope != _scope(expected)
                    or observed.intent_identity != fingerprint(expected.intent)
                    or observed.evidence_identity != fingerprint(observed.payload)):
                return EvidenceAdmission('conflict', finding='effect.evidence_binding_conflict')
            statuses.append(observed.outcome)
            if observed.acknowledgement_level is not None:
                statuses.append(observed.acknowledgement_level)
            observed = observed.payload
            continue
        conflict = _conflict(observed, expected)
        if conflict:
            return EvidenceAdmission('conflict', finding=conflict)
        statuses.extend(status for status in (_field(observed, name) for name in ('status', 'confirmation'))
                        if status is not _MISSING)
        if type(observed).__name__ == 'EffectReceipt' and type(observed).__module__ == 'stratbox.core.execution.service':
            observed = observed.value
            continue
        break
    else:
        return EvidenceAdmission('unknown', finding='effect.evidence_nesting_limit')
    normalized = [('confirmed' if status in _POSITIVE else 'rejected' if status == 'rejected' else 'unknown')
                  if isinstance(status, str) else 'unknown' for status in statuses]
    if len(set(normalized)) > 1:
        return EvidenceAdmission('conflict', finding='effect.evidence_status_conflict')
    if normalized and normalized[0] != 'confirmed':
        outcome = 'rejected' if source == 'action' and normalized[0] == 'rejected' else 'unknown'
        return EvidenceAdmission(outcome, finding='effect.evidence_' + outcome)
    if not statuses and (expected.kind == 'notification.deliver' or source == 'lookup'):
        if not isinstance(observed, (ImmutableMaterialRef, SnapshotRef)):
            return EvidenceAdmission('unknown', finding='effect.positive_evidence_required')
    outcome, finding, evidence_kind = _payload_outcome(expected, observed, source)
    if outcome != 'confirmed':
        return EvidenceAdmission(outcome, finding=finding)
    try:
        raw = json.dumps(canonical_tree(observed), sort_keys=True, separators=(',', ':')).encode()
        if len(raw) > 16 * 1024 * 1024:
            return EvidenceAdmission('unknown', finding='effect.evidence_size_limit')
        payload = immutable(observed)
        evidence = EffectEvidence(expected.effect_id, expected.kind,
            _scope(expected),
            fingerprint(expected.intent), 'confirmed', evidence_kind, fingerprint(payload),
            datetime.now(timezone.utc), payload, statuses[0] if statuses else None)
    except (ValueError, TypeError, OverflowError):
        return EvidenceAdmission('unknown', finding='effect.evidence_payload_invalid')
    return EvidenceAdmission('confirmed', payload, evidence=evidence)
