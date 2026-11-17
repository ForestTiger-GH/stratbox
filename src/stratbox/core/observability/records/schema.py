"""Closed versioned payload schemas for admissible journal data and projections."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
import re
from types import MappingProxyType
from typing import Literal

from stratbox.core.execution.contracts import safe_token

from stratbox.core.observability.records.contracts import JournalRecord

FieldClass = Literal["public", "operational", "restricted"]
_DIGEST = re.compile(r"[0-9a-f]{64}", re.ASCII)
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", re.ASCII)
_SAFE_INT = 2**53 - 1
_KINDS = {"text", "token", "hash", "date", "decimal", "integer", "boolean", "object", "array"}


@dataclass(frozen=True, slots=True)
class ValueRule:
    kind: str
    nullable: bool = False
    max_length: int = 256
    minimum: int = -_SAFE_INT
    maximum: int = _SAFE_INT
    choices: tuple[str, ...] = ()
    fields: tuple[FieldRule, ...] = ()
    items: ValueRule | None = None

    def __post_init__(self) -> None:
        if self.kind not in _KINDS or type(self.max_length) is not int or not 1 <= self.max_length <= 8192:
            raise ValueError("journal.rule_invalid")
        if (type(self.minimum) is not int or type(self.maximum) is not int
                or not -_SAFE_INT <= self.minimum <= self.maximum <= _SAFE_INT):
            raise ValueError("journal.rule_range_invalid")
        if (self.kind != "object" and self.fields) or (self.kind == "array") != (self.items is not None):
            raise ValueError("journal.rule_shape_invalid")
        if (not isinstance(self.fields, tuple) or len(self.fields) > 128
                or len({field.name for field in self.fields}) != len(self.fields)
                or not isinstance(self.choices, tuple) or len(self.choices) > 128):
            raise ValueError("journal.rule_fields_invalid")
        if self.choices and (self.kind not in {"token", "text"} or any(
            type(choice) is not str or len(choice) > self.max_length for choice in self.choices
        )):
            raise ValueError("journal.rule_choices_invalid")

    def validate(self, value: object, *, depth: int = 0) -> None:
        if depth > 16:
            raise ValueError("journal.field_depth_limit")
        if value is None and self.nullable:
            return
        kind = self.kind
        if kind == "object":
            if not isinstance(value, Mapping) or len(value) > len(self.fields):
                raise ValueError("journal.field_type_invalid")
            fields = {field.name: field for field in self.fields}
            if value.keys() - fields.keys():
                raise ValueError("journal.field_not_allowed")
            for field in self.fields:
                if field.name in value:
                    field.rule.validate(value[field.name], depth=depth + 1)
                elif field.required:
                    raise ValueError("journal.field_required")
            return
        if kind == "array":
            if not isinstance(value, (tuple, list)) or len(value) > self.max_length:
                raise ValueError("journal.field_type_invalid")
            for member in value:
                self.items.validate(member, depth=depth + 1)
            return
        if kind == "boolean":
            if type(value) is not bool:
                raise ValueError("journal.field_type_invalid")
            return
        if kind == "integer":
            if type(value) is not int or not self.minimum <= value <= self.maximum:
                raise ValueError("journal.field_type_invalid")
            return
        if type(value) is not str or len(value) > self.max_length:
            raise ValueError("journal.field_type_invalid")
        if self.choices and value not in self.choices:
            raise ValueError("journal.field_value_invalid")
        try:
            if kind == "token":
                safe_token(value)
            elif kind == "hash" and not _DIGEST.fullmatch(value):
                raise ValueError
            elif kind == "date" and date.fromisoformat(value).isoformat() != value:
                raise ValueError
            elif kind == "decimal" and not _DECIMAL.fullmatch(value):
                raise ValueError
        except ValueError:
            raise ValueError("journal.field_value_invalid") from None


@dataclass(frozen=True, slots=True)
class FieldRule:
    name: str
    rule: ValueRule
    required: bool = True
    classification: FieldClass = "operational"

    def __post_init__(self) -> None:
        safe_token(self.name)
        if not isinstance(self.rule, ValueRule) or type(self.required) is not bool:
            raise ValueError("journal.field_rule_invalid")
        if self.classification not in {"public", "operational", "restricted"}:
            raise ValueError("journal.field_class_invalid")


@dataclass(frozen=True, slots=True)
class RecordDataSchema:
    record_type: str
    kind: str
    version: int
    fields: tuple[FieldRule, ...]
    implicit_version_one: bool = False

    def __post_init__(self) -> None:
        safe_token(self.record_type)
        safe_token(self.kind)
        if type(self.version) is not int or not 1 <= self.version <= _SAFE_INT:
            raise ValueError("journal.data_version_invalid")
        if self.implicit_version_one and self.version != 1:
            raise ValueError("journal.data_version_invalid")
        if any(f.name == "data_version" for f in self.fields):
            raise ValueError("journal.field_not_allowed")
        ValueRule("object", fields=self.fields)

    @property
    def key(self) -> tuple[str, str, int]:
        return self.record_type, self.kind, self.version

    def validate(self, record: JournalRecord) -> Mapping[str, object]:
        version = record.payload.get("data_version", 1 if self.implicit_version_one else None)
        if type(version) is not int or (record.record_type, record.kind, version) != self.key:
            raise ValueError("journal.unsupported_data_schema")
        data = {key: value for key, value in record.payload.items() if key != "data_version"}
        ValueRule("object", fields=self.fields).validate(data)
        return MappingProxyType(data)
