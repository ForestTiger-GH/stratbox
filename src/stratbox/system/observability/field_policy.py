"""Typed allowlists for builtin observations and separately authorized projections.

Schemas validate *content*, never authenticate a user or authorize filesystem access.
"""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass, replace
from .contracts import JournalRecord
from .event_schemas import BUILTIN_DATA_SCHEMAS
from .schema import FieldClass, RecordDataSchema
from typing import Literal


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
        self._data = {schema.key: schema for schema in BUILTIN_DATA_SCHEMAS}
        self._frozen = False
        for schema in schemas:
            self.add(schema)

    def add(self, schema: RecordFieldSchema | RecordDataSchema) -> None:
        if self._frozen:
            raise ValueError("journal.registry_frozen")
        if isinstance(schema, RecordDataSchema):
            if schema.key in self._data:
                raise ValueError("Duplicate registered data schema")
            self._data[schema.key] = schema
            return
        key = (schema.record_type, schema.kind)
        if key in self._schemas:
            raise ValueError("Duplicate registered field schema")
        self._schemas[key] = schema

    def freeze(self) -> FieldSchemaRegistry:
        registry = FieldSchemaRegistry()
        registry._schemas = self._schemas.copy()
        registry._data = self._data.copy()
        registry._frozen = True
        return registry

    def data_schema(self, key: tuple[str, str, int]) -> RecordDataSchema:
        if key not in self._data:
            raise ValueError("journal.unsupported_data_schema")
        return self._data[key]

    def validate(self, record: JournalRecord) -> None:
        key = (record.record_type, record.kind)
        version = record.payload.get("data_version")
        if "data_version" in record.payload:
            if type(version) is not int:
                raise ValueError("journal.unsupported_data_schema")
            if key == _SUMMARY_KEY and version == 2:
                _SUMMARY_V2.validate(record.payload)
            else:
                self.data_schema((*key, version)).validate(record)
            return
        schema = self._schemas.get(key)
        if schema is None:
            raise ValueError("journal.field_schema_missing")
        schema.validate(record.payload)

    def present(self, record: JournalRecord, *, allow: frozenset[FieldClass] = frozenset({"public"})) -> dict[str, object]:
        key = (record.record_type, record.kind)
        if "data_version" in record.payload:
            self.validate(record)
            if key == _SUMMARY_KEY and record.payload["data_version"] == 2:
                return _SUMMARY_V2.present(record, allow=allow)
            schema_v = self._data[(*key, record.payload["data_version"])]
            return {field.name: record.payload[field.name] for field in schema_v.fields
                    if field.classification in allow and field.name in record.payload}
        schema = self._schemas.get(key)
        if schema is None:
            raise ValueError("journal.field_schema_missing")
        return schema.present(record, allow=allow)

_SUMMARY_KEY = ("result_summary", "operation.result")
_SUMMARY_V2 = replace(SCHEMAS[_SUMMARY_KEY], fields=SCHEMAS[_SUMMARY_KEY].fields + (
    AllowedField("data_version", "integer"),
))
_EXPLICIT_BUILTINS = {
    (schema.record_type, schema.kind): schema for schema in BUILTIN_DATA_SCHEMAS
    if not schema.implicit_version_one
}


def validate_builtin_fields(record: JournalRecord) -> None:
    key = (record.record_type, record.kind)
    if key in _EXPLICIT_BUILTINS:
        _EXPLICIT_BUILTINS[key].validate(record)
        return
    if key == _SUMMARY_KEY and type(record.payload.get("data_version")) is int and record.payload["data_version"] == 2:
        _SUMMARY_V2.validate(record.payload)
        return
    schema = SCHEMAS.get(key)
    if schema:
        schema.validate(record.payload)
