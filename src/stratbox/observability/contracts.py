"""Semantic, portable facts and observation records; independent of storage."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from types import MappingProxyType
from typing import Literal, Mapping
from uuid import uuid4

from stratbox.data import ByteIdentity, canonical_manifest_bytes
from stratbox.execution.contracts import Correlation, safe_token

RecordType = Literal["execution", "domain_fact", "effect", "diagnostic", "result_summary"]
Reliability = Literal["best_effort", "durable", "required"]
WriteState = Literal["confirmed", "failed", "unknown"]


def require_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
        raise ValueError("Timestamp must have a UTC timezone")
    return value


def _json_value(value: object, depth: int = 0) -> object:
    """Copy only bounded, explicitly supported portable values (never arbitrary objects)."""
    if depth > 16:
        raise ValueError("Observation payload exceeds nesting limit")
    if value is None or isinstance(value, (bool, str)):
        if isinstance(value, str) and len(value) > 8192:
            raise ValueError("Observation field is too large")
        return value
    if type(value) is int:
        return value
    if isinstance(value, Decimal) and value.is_finite():
        return value
    if type(value) is float:
        raise TypeError("Float payloads require an explicit loss/precision policy")
    if isinstance(value, (list, tuple)):
        if len(value) > 4096:
            raise ValueError("Observation payload list too large")
        return tuple(_json_value(x, depth + 1) for x in value)
    if isinstance(value, Mapping):
        if len(value) > 4096 or any(not isinstance(k, str) or len(k) > 128 for k in value):
            raise ValueError("Invalid observation mapping")
        return {k: _json_value(v, depth + 1) for k, v in value.items()}
    raise TypeError(f"Unsupported journal payload value: {type(value).__name__}")


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, tuple):
        return tuple(_freeze(v) for v in value)
    return value


def _payload(payload: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(payload, Mapping):
        raise TypeError("Record payload must be a mapping")
    return _freeze(_json_value(payload))  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class ObjectRef:
    namespace: str
    object_id: str
    relation: str = "subject"
    version_id: str | None = None
    identity: ByteIdentity | None = None

    def __post_init__(self):
        for token in (self.namespace, self.object_id, self.relation, self.version_id):
            if token is not None:
                safe_token(token)
        if self.identity is not None and not isinstance(self.identity, ByteIdentity):
            raise ValueError("Invalid reference byte identity")


def make_fact_id(kind: str, subject: ObjectRef, semantic_identity: Mapping[str, object]) -> str:
    """The caller supplies domain-qualified identity; no label matching is inferred."""
    safe_token(kind)
    if not isinstance(subject, ObjectRef):
        raise TypeError("Subject must be an ObjectRef")
    return sha256(canonical_manifest_bytes({
        "schema": 1, "kind": kind,
        "subject": {"namespace": subject.namespace, "id": subject.object_id,
                    "version": subject.version_id, "sha256": subject.identity.sha256 if subject.identity else None},
        "semantic_identity": semantic_identity,
    })).hexdigest()


@dataclass(frozen=True, slots=True)
class DomainFact:
    kind: str
    subject: ObjectRef
    fact_id: str
    occurred_at_utc: datetime
    payload: Mapping[str, object] = field(default_factory=dict)
    observation_id: str = field(default_factory=lambda: uuid4().hex)
    observed_at_utc: datetime | None = None
    correlation: Correlation = field(default_factory=Correlation)
    references: tuple[ObjectRef, ...] = ()

    def __post_init__(self):
        for token in (self.kind, self.fact_id, self.observation_id):
            safe_token(token)
        if not isinstance(self.subject, ObjectRef) or not isinstance(self.correlation, Correlation):
            raise ValueError("Invalid fact subject or correlation")
        require_utc(self.occurred_at_utc)
        if self.observed_at_utc is not None:
            require_utc(self.observed_at_utc)
        if any(not isinstance(ref, ObjectRef) for ref in self.references):
            raise ValueError("Invalid fact references")
        object.__setattr__(self, "payload", _payload(self.payload))


@dataclass(frozen=True, slots=True)
class JournalRecord:
    record_id: str
    record_type: RecordType
    kind: str
    occurred_at_utc: datetime
    payload: Mapping[str, object]
    schema_version: int = 1
    observed_at_utc: datetime | None = None
    correlation: Correlation = field(default_factory=Correlation)
    invocation_id: str | None = None
    operation_id: str | None = None
    fact_id: str | None = None
    subject: ObjectRef | None = None
    references: tuple[ObjectRef, ...] = ()
    cause_record_ids: tuple[str, ...] = ()
    outcome: str | None = None
    sequence: int | None = None

    def __post_init__(self):
        if self.schema_version != 1 or self.record_type not in {"execution", "domain_fact", "effect", "diagnostic", "result_summary"}:
            raise ValueError("Unsupported journal schema or record type")
        for token in (self.record_id, self.kind, self.invocation_id, self.operation_id, self.fact_id, self.outcome, *self.cause_record_ids):
            if token is not None:
                safe_token(token)
        if self.record_type == "execution" and (self.invocation_id is None or self.operation_id is None or self.sequence is None):
            raise ValueError("Execution record requires invocation, operation and sequence")
        if self.record_type == "domain_fact" and (self.fact_id is None or self.subject is None):
            raise ValueError("Domain fact requires subject and stable fact ID")
        if self.sequence is not None and (type(self.sequence) is not int or not 0 < self.sequence < 2**53):
            raise ValueError("Invalid sequence")
        require_utc(self.occurred_at_utc)
        if self.observed_at_utc is not None:
            require_utc(self.observed_at_utc)
        if not isinstance(self.correlation, Correlation) or (self.subject is not None and not isinstance(self.subject, ObjectRef)):
            raise ValueError("Invalid correlation or subject")
        if any(not isinstance(ref, ObjectRef) for ref in self.references):
            raise ValueError("Invalid references")
        object.__setattr__(self, "payload", _payload(self.payload))


@dataclass(frozen=True, slots=True)
class JournalWriteReceipt:
    state: WriteState
    segment_id: str
    content_identity: ByteIdentity
    record_ids: tuple[str, ...]
    guarantee: str
    locator: str = field(repr=False)
    diagnostic_code: str | None = None
    already_present: bool = False

    def __post_init__(self):
        if self.state not in {"confirmed", "failed", "unknown"}:
            raise ValueError("Invalid journal write state")
        safe_token(self.segment_id)
        safe_token(self.guarantee)
        if self.diagnostic_code is not None:
            safe_token(self.diagnostic_code)
        if not isinstance(self.content_identity, ByteIdentity) or any(not isinstance(x, str) for x in self.record_ids):
            raise ValueError("Invalid journal write identity")


class JournalBarrierError(Exception):
    """A required journal barrier blocked the following action."""
    def __init__(self, receipt: JournalWriteReceipt):
        self.receipt = receipt
        super().__init__(receipt.diagnostic_code or "journal.registration_unconfirmed")
