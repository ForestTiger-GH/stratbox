"""Bounded, authorized projections and immutable handoff intent construction."""
from __future__ import annotations
from collections.abc import Mapping
from datetime import datetime
from stratbox.shared.data import ByteIdentity, canonical_manifest_bytes
from stratbox.core.observability import JournalRecord, JournalHead, JournalEntry
from stratbox.core.observability.records.contracts import require_utc
from stratbox.core.observability.records.schema import ValueRule
from stratbox.core.notifications.contracts import AccessDecision, EventPointer, NotificationIntent, Subscription
from stratbox.core.notifications.topics import NotificationTopic, Projection

MAX_ENVELOPE_BYTES = 64 * 1024
_MISSING = object()

def _utc(value: datetime) -> str:
    require_utc(value)
    return value.isoformat().removesuffix("+00:00") + "Z"


def _permitted(path: str, grants: frozenset[str]) -> bool:
    return any(path == grant or path.startswith(grant + ".") for grant in grants)


def _project_value(rule: ValueRule, value: object, path: str, grants: frozenset[str]) -> object:
    allowed = _permitted(path, grants)
    if not allowed and not any(grant.startswith(path + ".") for grant in grants):
        return _MISSING
    if rule.kind == "object" and isinstance(value, Mapping):
        projected = {}
        for field_rule in rule.fields:
            if field_rule.name not in value:
                continue
            child = _project_value(field_rule.rule, value[field_rule.name],
                                   f"{path}.{field_rule.name}", grants)
            if child is not _MISSING:
                projected[field_rule.name] = child
        return projected
    if rule.kind == "array" and isinstance(value, (list, tuple)):
        members = tuple(_project_value(rule.items, member, path, grants) for member in value)
        return members if all(member is not _MISSING for member in members) else _MISSING
    return value if allowed else _MISSING


def _projection(projection: Projection, data: Mapping[str, object], grant: AccessDecision) -> dict:
    selected = {}
    for field_rule in projection.fields:
        present = field_rule.name in data
        value = _project_value(field_rule.rule, data[field_rule.name], field_rule.name, grant.fields) if present else _MISSING
        if value is _MISSING:
            if field_rule.required:
                if present:
                    raise PermissionError("notification.projection_unavailable")
                raise ValueError("notification.projection_field_missing")
            continue
        try:
            field_rule.rule.validate(value)
        except ValueError as error:
            if str(error) == "journal.field_required":
                raise PermissionError("notification.projection_unavailable") from None
            raise
        selected[field_rule.name] = value
    return selected


def dispatch_key(
    subscription: Subscription, authority_id: str, topic_id: str, event_key_kind: str, event_key: str,
) -> str:
    spec = subscription.spec
    return ByteIdentity.of(canonical_manifest_bytes({
        "key_version": 1, "scope_id": spec.scope_id, "source_authority_id": authority_id,
        "subscription_id": spec.subscription_id, "topic_id": topic_id, "event_key_kind": event_key_kind,
        "event_key": event_key, "consumer_id": spec.route.consumer_id,
        "route_id": spec.route.route_id, "target_id": spec.route.target_id,
    })).sha256


def _metadata(record: JournalRecord, version: int, names: frozenset[str]) -> dict:
    value = {}
    if "event_ref" in names:
        value["event_ref"] = {"record_id": record.record_id, "record_type": record.record_type,
                              "kind": record.kind, "data_version": version}
    if "occurred_at_utc" in names:
        value["occurred_at_utc"] = _utc(record.occurred_at_utc)
    if "observed_at_utc" in names and record.observed_at_utc is not None:
        value["observed_at_utc"] = _utc(record.observed_at_utc)
    if "subject" in names and record.subject is not None:
        value["subject"] = {"namespace": record.subject.namespace, "object_id": record.subject.object_id,
                            "version_id": record.subject.version_id}
    if "correlation" in names:
        value["correlation"] = {key: getattr(record.correlation, key)
                                for key in ("run_id", "step_id", "attempt_id", "cause_event_id")}
    return value


def _intent(
    sub: Subscription, topic: NotificationTopic, projection: Projection, head: JournalHead,
    entry: JournalEntry, *, data: Mapping[str, object], data_version: int, grant: AccessDecision,
    now: datetime, dispatch_id: str, event_key: str, semantic: ByteIdentity,
) -> NotificationIntent:
    if grant.route_revision is None:
        raise ValueError("notification.route_revision_required")
    selected = _projection(projection, data, grant)
    reference = selected.get("artifact_ref")
    if isinstance(reference, Mapping) and reference.get("scope_id") != sub.spec.scope_id:
        raise ValueError("notification.artifact_scope_mismatch")
    metadata = _metadata(entry.record, data_version, projection.metadata & grant.metadata)
    payload = canonical_manifest_bytes({
        "envelope_version": 1, "dispatch_id": dispatch_id,
        "topic_id": topic.topic_id, "topic_version": topic.version,
        "projection_id": projection.projection_id, "projection_version": projection.version,
        "consumer_id": sub.spec.route.consumer_id, "subscription_id": sub.spec.subscription_id,
        "subscription_revision": sub.revision, **metadata, "data": selected,
    })
    if len(payload) > MAX_ENVELOPE_BYTES:
        raise ValueError("notification.projection_size_limit")
    return NotificationIntent(
        dispatch_id, sub.spec.scope_id, sub.spec.subscription_id, sub.revision, sub.spec.route,
        grant.route_revision, EventPointer(head.cursor(entry.offset), head.source_authority_id,
                                           entry.record.record_id, entry.identity, entry.evidence_ref),
        topic.event_key_kind, event_key, semantic, topic.topic_id, topic.version, projection.projection_id,
        projection.version, frozenset(selected), frozenset(metadata), grant.grant_ref, now,
        ByteIdentity.of(payload), payload,
    )
