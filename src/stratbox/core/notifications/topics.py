"""Topics expose closed projections of existing journal data schemas."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Literal

from stratbox.shared.identifiers import safe_token
from stratbox.core.observability import FieldRule, FieldSchemaRegistry, JournalRecord, RecordDataSchema
from stratbox.core.observability.records.event_schemas import (
    MATERIAL_STORED, OPERATION_FINISHED, PUBLICATION_COMMITTED, SOURCE_BYTES_CHANGED, SOURCE_ORIGINAL_COMMITTED, RUN_FINISHED, VALUE_ACCEPTED, EFFECT_CONFIRMED,
)
from stratbox.core.observability.records.schema import ValueRule

from stratbox.core.notifications.contracts import FilterCondition, SubscriptionSpec

SchemaKey = tuple[str, str, int]
Data = Mapping[str, object]
Predicate = Callable[[JournalRecord, Data], bool]
METADATA = frozenset({"event_ref", "occurred_at_utc", "observed_at_utc", "subject", "correlation"})


@dataclass(frozen=True, slots=True)
class Projection:
    projection_id: str
    version: int
    fields: tuple[FieldRule, ...]
    metadata: frozenset[str] = frozenset({"event_ref", "occurred_at_utc"})

    def __post_init__(self) -> None:
        safe_token(self.projection_id)
        if type(self.version) is not int or self.version < 1:
            raise ValueError("notification.projection_version_invalid")
        if not isinstance(self.metadata, frozenset) or not self.metadata <= METADATA:
            raise ValueError("notification.metadata_invalid")
        ValueRule("object", fields=self.fields)


@dataclass(frozen=True, slots=True)
class NotificationTopic:
    topic_id: str
    version: int
    schemas: tuple[SchemaKey, ...]
    projections: tuple[Projection, ...]
    event_key_kind: Literal["record", "fact", "transition", "effect"] = "record"
    semantic_fields: tuple[str, ...] = ()
    filter_fields: frozenset[str] = frozenset()
    eligible: Predicate | None = None
    source_authorities: frozenset[str] | None = None
    explicit_opt_in: tuple[str, str] | None = None

    def __post_init__(self) -> None:
        safe_token(self.topic_id)
        if type(self.version) is not int or self.version < 1:
            raise ValueError("notification.topic_version_invalid")
        if self.topic_id.startswith(("notification.", "notifications.", "subscription.")):
            raise ValueError("notification.service_event_forbidden")
        if (not isinstance(self.schemas, tuple) or not self.schemas or len(set(self.schemas)) != len(self.schemas)
                or not isinstance(self.projections, tuple) or not self.projections
                or len({(p.projection_id, p.version) for p in self.projections}) != len(self.projections)
                or self.event_key_kind not in {"record", "fact", "transition", "effect"}
                or not isinstance(self.filter_fields, frozenset) or not isinstance(self.semantic_fields, tuple)
                or (self.eligible is not None and not callable(self.eligible))):
            raise ValueError("notification.topic_invalid")
        if self.source_authorities is not None:
            if not isinstance(self.source_authorities, frozenset) or not self.source_authorities:
                raise ValueError("notification.topic_invalid")
            for source in self.source_authorities:
                safe_token(source)

    def in_scope(self, source_authority_id: str) -> bool:
        return self.source_authorities is None or source_authority_id in self.source_authorities

    def event_key(self, record: JournalRecord, data: Data) -> str:
        if self.event_key_kind == "record":
            return record.record_id
        if self.event_key_kind == "fact":
            return safe_token(record.fact_id)
        return safe_token(data.get(self.event_key_kind + "_id"))

    def permits_mode(self, data: Data, filters: tuple[FilterCondition, ...]) -> bool:
        if self.explicit_opt_in is None:
            return True
        name, value = self.explicit_opt_in
        return data.get(name) != value or any(
            condition.field == name and condition.operator in {"eq", "in"} and value in condition.values
            for condition in filters
        )


def is_service_event(record: JournalRecord) -> bool:
    return (record.record_type == "orchestration" and record.payload.get("service") is True) or record.kind.startswith(("notification.", "notifications.", "subscription.")) or (
        record.operation_id is not None and record.operation_id.startswith("notifications.")
    )


def _compatible(projected: ValueRule, source: ValueRule) -> bool:
    if projected.kind != source.kind:
        return False
    if projected.kind == "array":
        return _compatible(projected.items, source.items)
    if projected.kind != "object":
        return True
    definitions = {field.name: field.rule for field in source.fields}
    return all(field.name in definitions and _compatible(field.rule, definitions[field.name])
               for field in projected.fields)


class TopicCatalog:
    def __init__(self, registry: FieldSchemaRegistry, topics: Iterable[NotificationTopic]):
        self._registry = registry.freeze()
        index: dict[tuple[str, int], NotificationTopic] = {}
        for topic in topics:
            if len(index) >= 4096:
                raise ValueError("notification.topic_limit")
            key = topic.topic_id, topic.version
            if key in index:
                raise ValueError("notification.topic_duplicate")
            for schema_key in topic.schemas:
                record_type, kind, _ = schema_key
                if kind.startswith(("notification.", "notifications.", "subscription.")):
                    raise ValueError("notification.service_event_forbidden")
                schema = self._registry.data_schema(schema_key)
                fields = {field.name: field.rule for field in schema.fields}
                required = set(topic.semantic_fields) | topic.filter_fields
                if topic.event_key_kind in {"transition", "effect"}:
                    required.add(topic.event_key_kind + "_id")
                if not required <= fields.keys() or (topic.event_key_kind == "fact" and record_type != "domain_fact"):
                    raise ValueError("notification.topic_field_invalid")
                if topic.explicit_opt_in is not None and topic.explicit_opt_in[0] not in topic.filter_fields:
                    raise ValueError("notification.topic_field_invalid")
                for profile in topic.projections:
                    if any(f.name not in fields or not _compatible(f.rule, fields[f.name]) for f in profile.fields):
                        raise ValueError("notification.projection_field_invalid")
            index[key] = topic
        self._topics = MappingProxyType(index)

    def definitions(self) -> tuple[NotificationTopic, ...]:
        """List registered definitions for the host that owns this catalog."""
        return tuple(self._topics.values())

    def resolve(self, spec: SubscriptionSpec) -> tuple[NotificationTopic, Projection]:
        topic = self._topics.get((spec.topic_id, spec.topic_version))
        if topic is None:
            raise ValueError("notification.topic_unknown")
        projection = next((p for p in topic.projections if (p.projection_id, p.version) ==
                           (spec.projection_id, spec.projection_version)), None)
        if projection is None:
            raise ValueError("notification.projection_unknown")
        fields = {f.name: f.rule for f in projection.fields}
        for condition in spec.filters:
            rule = fields.get(condition.field)
            if condition.field not in topic.filter_fields or rule is None or rule.kind in {"object", "array"}:
                raise ValueError("subscription.filter_invalid")
            try:
                for value in condition.values:
                    rule.validate(value)
            except ValueError:
                raise ValueError("subscription.filter_invalid") from None
        return topic, projection

    def input_schema(self, topic: NotificationTopic, record: JournalRecord) -> RecordDataSchema:
        version = record.payload.get("data_version", 1)
        key = record.record_type, record.kind, version
        if type(version) is not int or key not in topic.schemas:
            raise ValueError("journal.unsupported_data_schema")
        return self._registry.data_schema(key)


def match_conditions(conditions: tuple[FilterCondition, ...], data: Data) -> bool:
    for condition in conditions:
        if condition.field not in data:
            return False
        if condition.operator == "exists":
            continue
        value = data[condition.field]
        if not any(type(value) is type(operand) and value == operand for operand in condition.values):
            return False
    return True


def _finished(record: JournalRecord, data: Data) -> bool:
    stamp = datetime.fromisoformat(data["occurred_at_utc"].removesuffix("Z") + (
        "+00:00" if data["occurred_at_utc"].endswith("Z") else ""
    ))
    if (record.invocation_id, record.operation_id, record.sequence, record.outcome,
            record.occurred_at_utc) != (
        data["invocation_id"], data["operation_id"], data["sequence"], data["outcome"], stamp
    ):
        raise ValueError("journal.execution_envelope_mismatch")
    expected_correlation = {key: getattr(record.correlation, key) for key in data["correlation"]}
    if expected_correlation != data["correlation"]:
        raise ValueError("journal.execution_envelope_mismatch")
    return True


def _run_finished(record: JournalRecord, data: Data) -> bool:
    if (record.correlation.run_id != data["run_id"]
            or record.correlation.plan_id != data["plan_id"]
            or record.outcome != data["outcome"]
            or record.record_id != data["transition_id"]
            or data["producer_id"] != record.correlation.session_id
            or data["outcome"] not in {"succeeded", "partial", "failed", "cancelled", "unknown"}):
        raise ValueError("journal.run_envelope_mismatch")
    return not data["service"]


def _run_failed(record: JournalRecord, data: Data) -> bool:
    return _run_finished(record, data) and data["outcome"] == "failed"


def _failed(record: JournalRecord, data: Data) -> bool:
    return _finished(record, data) and record.outcome == "failed"


def _stored(record: JournalRecord, data: Data) -> bool:
    if data["status"] != "stored" or not data.get("effect_id"):
        return False
    if (record.subject.identity is None or record.subject.identity.sha256 != data["identity"]["sha256"]
            or record.subject.identity.size != data["identity"]["size"]):
        raise ValueError("journal.storage_identity_mismatch")
    return True


def _bytes_changed(record: JournalRecord, data: Data) -> bool:
    if record.subject.object_id != data["source_id"]:
        raise ValueError("journal.source_identity_mismatch")
    return data["old_sha256"] != data["new_sha256"]


def _accepted_value(record: JournalRecord, data: Data) -> bool:
    if (record.subject is None or record.subject.namespace != "value"
            or record.subject.object_id != data["value_id"]
            or record.subject.identity is None
            or record.subject.identity.sha256 != data["identity"]["sha256"]
            or record.subject.identity.size != data["identity"]["size"]):
        raise ValueError("journal.acceptance_identity_mismatch")
    return True


def _confirmed_effect(record: JournalRecord, data: Data) -> bool:
    if (record.subject is None or record.subject.namespace != "effect"
            or record.subject.object_id != data["effect_id"]
            or record.correlation.effect_id != data["effect_id"]):
        raise ValueError("journal.effect_identity_mismatch")
    identity = record.subject.identity
    if data["identity"] != (dict(sha256=identity.sha256, size=identity.size) if identity is not None else None):
        raise ValueError("journal.effect_identity_mismatch")
    return not data["effect_kind"].startswith(("notification.", "notifications."))


def _original_committed(record: JournalRecord, data: Data) -> bool:
    from stratbox.shared.source_publications import SourceAssetIdentity
    try:
        expected = SourceAssetIdentity(data["series_id"], data["issue_id"], data["asset_id"])
    except ValueError:
        raise ValueError("journal.original_asset_invalid") from None
    if expected.source_id != data["source_id"]:
        raise ValueError("journal.original_asset_identity_mismatch")
    artifact = data["artifact_ref"]
    if (artifact["scope_id"] != data["destination_id"]
            or artifact["sha256"] != data["current_sha256"]
            or artifact["size_bytes"] != data["size_bytes"]):
        raise ValueError("journal.original_artifact_mismatch")
    if record.subject is None or record.subject.namespace != "source":
        raise ValueError("journal.original_subject_missing")
    if record.subject.object_id != data["source_id"] or (
        record.subject.identity is None
        or record.subject.identity.sha256 != data["current_sha256"]
        or record.subject.identity.size != data["size_bytes"]
    ):
        raise ValueError("journal.original_identity_mismatch")
    if data["change"] == "revised" and (
        data["previous_sha256"] is None or data["previous_sha256"] == data["current_sha256"]
    ):
        raise ValueError("journal.original_transition_invalid")
    if data["change"] != "revised" and data["previous_sha256"] is not None:
        raise ValueError("journal.original_transition_invalid")
    if data["change"] == "revised" and data["previous_transition_id"] is None:
        raise ValueError("journal.original_transition_chain_missing")
    if data["change"] != "revised" and data["previous_transition_id"] is not None:
        raise ValueError("journal.original_transition_invalid")
    # Onboarding is recorded as provenance, not sent as a fresh-release alert.
    return data["change"] != "first_seen"


def _project(
    schema: RecordDataSchema, name: str, *fields: str, metadata: frozenset[str] | None = None,
) -> Projection:
    available = {field.name: field for field in schema.fields}
    picked = tuple(available[name] for name in fields)
    return Projection(name, 1, picked) if metadata is None else Projection(name, 1, picked, metadata)


_operation = _project(OPERATION_FINISHED, "operation_summary", "operation_id", "outcome",
                      "duration_ms", "diagnostic_code")
_run_summary = _project(RUN_FINISHED, "run_summary", "run_id", "plan_id", "outcome",
                        "counters", "completed", "total", "reason")
_builtin_topics = (
    NotificationTopic("effect.confirmed", 1, (EFFECT_CONFIRMED.key,), (
        _project(EFFECT_CONFIRMED, "confirmed_effect", *(field.name for field in EFFECT_CONFIRMED.fields)),
    ), "fact", ("effect_id", "effect_kind", "identity", "destination_id", "guarantee"),
       frozenset({"effect_kind", "destination_id", "guarantee", "stage"}), _confirmed_effect),
    NotificationTopic("value.accepted", 1, (VALUE_ACCEPTED.key,), (
        _project(VALUE_ACCEPTED, "accepted_value", *(field.name for field in VALUE_ACCEPTED.fields)),
    ), "fact", ("value_id", "stage", "role", "identity", "acceptance_id"),
       frozenset({"stage", "role", "source_id", "qualification", "complete"}), _accepted_value),
    NotificationTopic("run.completed", 1, (RUN_FINISHED.key,), (_run_summary,),
                      "transition", ("run_id", "plan_id", "outcome", "counters"),
                      frozenset({"run_id", "plan_id", "outcome"}), _run_finished),
    NotificationTopic("run.failed", 1, (RUN_FINISHED.key,), (_run_summary,),
                      "transition", ("run_id", "plan_id", "outcome", "counters"),
                      frozenset({"run_id", "plan_id", "outcome"}), _run_failed),
    NotificationTopic("operation.completed", 1, (OPERATION_FINISHED.key,), (_operation,),
                      filter_fields=frozenset({"operation_id", "outcome"}), eligible=_finished),
    NotificationTopic("operation.failed", 1, (OPERATION_FINISHED.key,), (_operation,),
                      filter_fields=frozenset({"operation_id", "outcome"}), eligible=_failed),
    NotificationTopic("material.stored", 1, (MATERIAL_STORED.key,), (
        _project(MATERIAL_STORED, "stored_material", "status", "identity",
                 metadata=frozenset({"event_ref", "occurred_at_utc", "subject"})),
    ), "effect", ("status", "identity"), frozenset({"status"}), _stored),
    NotificationTopic("source.bytes_changed", 1, (SOURCE_BYTES_CHANGED.key,), (
        _project(SOURCE_BYTES_CHANGED, "bytes_change_public", *(field.name for field in SOURCE_BYTES_CHANGED.fields)),
    ), "transition", ("source_id", "old_sha256", "new_sha256", "size_bytes"),
       frozenset({"source_id"}), _bytes_changed),
    NotificationTopic("source.original_version_committed", 1, (SOURCE_ORIGINAL_COMMITTED.key,), (
        _project(SOURCE_ORIGINAL_COMMITTED, "original_version_public", *(f.name for f in SOURCE_ORIGINAL_COMMITTED.fields)),
    ), "transition", ("source_id", "series_id", "issue_id", "asset_id",
                       "current_sha256", "change", "mode", "publication_proof_ref"),
       frozenset({"source_id", "series_id", "change", "mode"}), _original_committed,
       explicit_opt_in=("mode", "backfill")),
    NotificationTopic("publication.committed", 1, (PUBLICATION_COMMITTED.key,), (
        _project(PUBLICATION_COMMITTED, "publication_summary", *(field.name for field in PUBLICATION_COMMITTED.fields)),
    ), "transition", ("series_id", "reference_date", "change", "mode", "artifact_ref"),
       frozenset({"series_id", "change", "mode", "reference_date"}), explicit_opt_in=("mode", "backfill")),
)


def build_catalog(
    registry: FieldSchemaRegistry | None = None, topics: Iterable[NotificationTopic] = (),
) -> TopicCatalog:
    return TopicCatalog(registry if registry is not None else FieldSchemaRegistry(), (*_builtin_topics, *topics))
