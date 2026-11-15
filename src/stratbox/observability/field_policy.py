"""Typed allowlists for builtin observations and separately authorized projections.

Schemas validate *content*, never authenticate a user or authorize filesystem access.
"""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal
from .contracts import JournalRecord

FieldClass = Literal["public", "operational", "restricted"]


@dataclass(frozen=True, slots=True)
class AllowedField:
    name: str
    value_kind: Literal["string", "integer", "boolean", "mapping", "sequence", "optional", "scalar"]
    field_class: FieldClass = "operational"
    max_length: int | None = None

    def __post_init__(self):
        if not self.name or self.field_class not in {"public", "operational", "restricted"} or self.value_kind not in {"string", "integer", "boolean", "mapping", "sequence", "optional", "scalar"}:
            raise ValueError("Invalid field declaration")
        if self.max_length is not None and self.max_length <= 0:
            raise ValueError("Invalid field length")


@dataclass(frozen=True, slots=True)
class RecordFieldSchema:
    record_type: str
    kind: str
    fields: tuple[AllowedField, ...]
    permit_extensions: bool = False

    def __post_init__(self):
        if len({f.name for f in self.fields}) != len(self.fields):
            raise ValueError("Duplicate declared fields")

    def validate(self, payload: Mapping[str, object]) -> None:
        definitions = {f.name: f for f in self.fields}
        for name, value in payload.items():
            item = definitions.get(name)
            if item is None:
                if not self.permit_extensions:
                    raise ValueError("journal.field_not_allowed")
                continue
            expected = item.value_kind
            checks = {
                "string": lambda v: type(v) is str,
                "integer": lambda v: type(v) is int,
                "boolean": lambda v: type(v) is bool,
                "mapping": lambda v: isinstance(v, Mapping),
                "sequence": lambda v: isinstance(v, (tuple, list)),
                "optional": lambda v: True,
                "scalar": lambda v: v is None or type(v) in {str, int, bool},
            }
            if not checks[expected](value):
                raise ValueError("journal.field_type_invalid")
            if type(value) is str and item.max_length is not None and len(value) > item.max_length:
                raise ValueError("journal.field_length_limit")

    def present(self, record: JournalRecord, *, allow: frozenset[FieldClass] = frozenset({"public"})) -> dict[str, object]:
        if (record.record_type, record.kind) != (self.record_type, self.kind):
            raise ValueError("Schema does not match record")
        self.validate(record.payload)
        return {field.name: record.payload[field.name] for field in self.fields
                if field.field_class in allow and field.name in record.payload}


SCHEMAS = {
    ("result_summary", "operation.result"): RecordFieldSchema("result_summary", "operation.result", (
        AllowedField("contract_version", "integer"), AllowedField("method_version", "string"),
        AllowedField("time_basis", "string"), AllowedField("diagnostics", "sequence", "restricted"),
        AllowedField("effects", "sequence", "restricted"), AllowedField("inputs", "sequence", "restricted"),
        AllowedField("computation", "optional", "operational"),
        AllowedField("observability", "mapping", "operational"),
        AllowedField("resources_used", "sequence", "operational"),
    )),
}


# Narrow and explicit builtin schemas. A new domain can supply its own schema to
# a registry; the core does not assume every future domain shares these fields.
def _schema(kind: str, fields: tuple[tuple[str, str], ...], *, record_type: str = "domain_fact") -> RecordFieldSchema:
    return RecordFieldSchema(record_type, kind, tuple(AllowedField(name, value_kind) for name, value_kind in fields))

for _kind in ("material.stored", "effect.unknown", "effect.failed"):
    SCHEMAS[("domain_fact", _kind)] = _schema(_kind, (
        ("status", "string"), ("effect_state", "string"), ("guarantee", "string"),
        ("identity", "mapping"), ("effect_id", "string"),
    ))
for _kind in ("artifact.produced", "artifact.stored"):
    SCHEMAS[("domain_fact", _kind)] = _schema(_kind, (("status", "string"), ("identity", "mapping")))
for _kind in ("publication.discovered", "publication.unconfirmed"):
    SCHEMAS[("domain_fact", _kind)] = _schema(_kind, (
        ("confirmation", "string"), ("transition_id", "string"), ("release_id", "string"),
        ("owner_id", "string"), ("identity", "mapping"),
    ))
SCHEMAS[("domain_fact", "material.acquired")] = _schema("material.acquired", (
    ("identity", "mapping"), ("status_code", "integer"),
    ("origin_assurance", "string"), ("reused", "boolean"),
))
SCHEMAS[("domain_fact", "source.checked")] = _schema("source.checked", (
    ("version_id", "optional"), ("status", "string"),
    ("diagnostic", "optional"), ("check_id", "string"),
))
SCHEMAS[("domain_fact", "dataset.comparison_completed")] = _schema("dataset.comparison_completed", (
    ("baseline", "optional"), ("candidate", "string"),
    ("comparison_scope", "string"), ("semantic_method_version", "string"),
    ("state", "string"), ("reason", "string"), ("layers", "mapping"),
    ("changed_count", "integer"), ("coverage", "optional"),
))
for _kind in ("operation.started", "operation.stage", "operation.progress", "operation.finished"):
    SCHEMAS[("execution", _kind)] = _schema(_kind, (
        ("version", "integer"), ("kind", "string"), ("invocation_id", "string"),
        ("operation_id", "string"), ("contract_version", "integer"),
        ("method_version", "string"), ("sequence", "integer"),
        ("occurred_at_utc", "string"), ("correlation", "mapping"),
        ("stage", "optional"), ("outcome", "optional"),
        ("diagnostic_code", "optional"), ("duration_ms", "optional"),
        ("completed", "optional"), ("total", "optional"),
        ("reason_class", "optional"), ("stage_elapsed_ms", "optional"),
        ("incident_id", "optional"),
    ), record_type="execution")


class FieldSchemaRegistry:
    """Caller-owned explicit schema extensions; never a process-global registration."""
    def __init__(self, schemas=()):
        self._schemas: dict[tuple[str, str], RecordFieldSchema] = dict(SCHEMAS)
        for schema in schemas:
            self.add(schema)

    def add(self, schema: RecordFieldSchema) -> None:
        key = (schema.record_type, schema.kind)
        if key in self._schemas:
            raise ValueError("Duplicate registered field schema")
        self._schemas[key] = schema

    def validate(self, record: JournalRecord) -> None:
        schema = self._schemas.get((record.record_type, record.kind))
        if schema is None:
            raise ValueError("journal.field_schema_missing")
        schema.validate(record.payload)

    def present(self, record: JournalRecord, *, allow: frozenset[FieldClass] = frozenset({"public"})) -> dict[str, object]:
        schema = self._schemas.get((record.record_type, record.kind))
        if schema is None:
            raise ValueError("journal.field_schema_missing")
        return schema.present(record, allow=allow)


def validate_builtin_fields(record: JournalRecord) -> None:
    schema = SCHEMAS.get((record.record_type, record.kind))
    if schema:
        schema.validate(record.payload)
