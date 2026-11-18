"""Portable semantic observations, bounded immutable payloads and qualified receipts."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from types import MappingProxyType
from typing import Literal
from uuid import uuid4

from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.core.execution.contracts import Correlation, safe_token

RecordType = Literal["execution", "domain_fact", "effect", "diagnostic", "result_summary"]
WriteState = Literal["confirmed", "failed", "unknown"]
MAX_ENCODED_BYTES = 2 * 1024 * 1024


def require_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
        raise ValueError("Timestamp must have a UTC timezone")
    return value


@dataclass(frozen=True, slots=True)
class PayloadLimits:
    max_depth: int = 16
    max_nodes: int = 8192
    max_string_length: int = 8192
    max_items_per_container: int = 4096
    max_encoded_bytes: int = MAX_ENCODED_BYTES
    max_numeric_digits: int = 1024

    def __post_init__(self) -> None:
        if any(type(x) is not int or x < 1 for x in (
                self.max_depth, self.max_nodes, self.max_string_length,
                self.max_items_per_container, self.max_encoded_bytes, self.max_numeric_digits)):
            raise ValueError("Payload limits must be positive integers")
        if self.max_depth > 64 or self.max_nodes > 100_000 or self.max_encoded_bytes > 16 * MAX_ENCODED_BYTES:
            raise ValueError("Unsafe payload limits")


DEFAULT_PAYLOAD_LIMITS = PayloadLimits()
_RESERVED_TAGS = frozenset({"$stratbox_decimal", "$stratbox_integer"})


def _payload(payload: Mapping[str, object], *, limits: PayloadLimits = DEFAULT_PAYLOAD_LIMITS) -> Mapping[str, object]:
    """Freeze a scalar-only snapshot and bound the *whole* graph, not each subtree."""
    if not isinstance(payload, Mapping):
        raise TypeError("Record payload must be a mapping")
    nodes = 0
    estimate = 0
    stack: set[int] = set()

    def walk(value: object, depth: int) -> object:
        nonlocal nodes, estimate
        nodes += 1
        if nodes > limits.max_nodes or depth > limits.max_depth:
            raise ValueError("journal.payload_node_or_depth_limit")
        if value is None or type(value) is bool:
            estimate += 8
            result = value
        elif type(value) is str:
            if len(value) > limits.max_string_length:
                raise ValueError("journal.payload_string_limit")
            estimate += len(value.encode("utf-8")) * 6 + 2
            result = value
        elif type(value) is int or isinstance(value, Decimal):
            if isinstance(value, Decimal) and not value.is_finite():
                raise ValueError("Non-finite Decimal")
            try:
                as_text = str(value)
            except ValueError:
                raise ValueError("journal.payload_numeric_limit") from None
            if len(as_text) > limits.max_numeric_digits:
                raise ValueError("journal.payload_numeric_limit")
            estimate += len(as_text) + 64
            result = value
        elif isinstance(value, (tuple, list, Mapping)):
            ident = id(value)
            if ident in stack:
                raise ValueError("journal.payload_cycle")
            if len(value) > limits.max_items_per_container:
                raise ValueError("journal.payload_container_limit")
            stack.add(ident)
            try:
                if isinstance(value, Mapping):
                    if any(type(k) is not str or len(k) > 128 for k in value):
                        raise ValueError("Invalid journal field name")
                    # A one-field object with a codec tag must be unambiguous.
                    # Other payload mappings may contain the same text as a key.
                    if len(value) == 1 and next(iter(value)) in _RESERVED_TAGS:
                        raise ValueError("journal.reserved_tag_mapping")
                    result = MappingProxyType({k: walk(v, depth + 1) for k, v in value.items()})
                    estimate += sum(len(k.encode("utf-8")) * 6 + 4 for k in value)
                else:
                    result = tuple(walk(v, depth + 1) for v in value)
                    estimate += len(value) + 2
            finally:
                stack.remove(ident)
        else:
            raise TypeError("Unsupported journal payload value")
        if estimate > limits.max_encoded_bytes:
            raise ValueError("journal.payload_byte_limit")
        return result
    frozen = walk(payload, 0)
    return frozen  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class ObjectRef:
    namespace: str
    object_id: str
    relation: str = "subject"
    version_id: str | None = None
    identity: ByteIdentity | None = None

    def __post_init__(self) -> None:
        for x in (self.namespace, self.object_id, self.relation, self.version_id):
            if x is not None:
                safe_token(x)
        if self.identity is not None and not isinstance(self.identity, ByteIdentity):
            raise ValueError("Invalid reference byte identity")


def make_fact_id(kind: str, subject: ObjectRef, semantic_identity: Mapping[str, object]) -> str:
    safe_token(kind)
    if not isinstance(subject, ObjectRef):
        raise TypeError("Subject must be an ObjectRef")
    bounded_identity = _payload(semantic_identity)
    def thaw(value):
        if isinstance(value, Mapping):
            return {key: thaw(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return [thaw(item) for item in value]
        return value
    return sha256(canonical_manifest_bytes({
        "schema": 1, "kind": kind,
        "subject": {"namespace": subject.namespace, "id": subject.object_id,
                    "version": subject.version_id, "sha256": subject.identity.sha256 if subject.identity else None},
        "semantic_identity": thaw(bounded_identity),
    })).hexdigest()


@dataclass(frozen=True, slots=True)
class OriginClaim:
    producer_id: str
    producer_role: str
    generation_id: str
    config_fingerprint: str | None = None
    claimed_at_utc: datetime | None = None
    authority_level: Literal["claimed"] = "claimed"

    def __post_init__(self) -> None:
        for x in (self.producer_id, self.producer_role, self.generation_id, self.config_fingerprint):
            if x is not None:
                safe_token(x)
        if self.claimed_at_utc is not None:
            require_utc(self.claimed_at_utc)
        if self.authority_level != "claimed":
            raise ValueError("Producer claims cannot self-attest authority")


@dataclass(frozen=True, slots=True)
class OriginAttestation:
    claim_id: str
    attestor_id: str
    binding_kind: str
    accepted_at_utc: datetime
    qualification: Literal["verified_binding", "rejected", "unknown"]

    def __post_init__(self) -> None:
        for x in (self.claim_id, self.attestor_id, self.binding_kind):
            safe_token(x)
        require_utc(self.accepted_at_utc)
        if self.qualification not in {"verified_binding", "rejected", "unknown"}:
            raise ValueError("Invalid attestation qualification")


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

    def __post_init__(self) -> None:
        for value in (self.kind, self.fact_id, self.observation_id):
            safe_token(value)
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

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.record_type not in {"execution", "domain_fact", "effect", "diagnostic", "result_summary"}:
            raise ValueError("Unsupported journal schema or record type")
        for value in (self.record_id, self.kind, self.invocation_id, self.operation_id,
                      self.fact_id, self.outcome, *self.cause_record_ids):
            if value is not None:
                safe_token(value)
        if self.record_type == "execution" and (self.invocation_id is None or self.operation_id is None or self.sequence is None):
            raise ValueError("Execution records require invocation, operation and sequence")
        if self.record_type == "domain_fact" and (self.fact_id is None or self.subject is None):
            raise ValueError("Domain facts require a subject and fact ID")
        if self.sequence is not None and (type(self.sequence) is not int or not 0 < self.sequence < 2**53):
            raise ValueError("Invalid sequence")
        require_utc(self.occurred_at_utc)
        if self.observed_at_utc is not None:
            require_utc(self.observed_at_utc)
        if not isinstance(self.correlation, Correlation):
            raise ValueError("Invalid correlation")
        if self.subject is not None and not isinstance(self.subject, ObjectRef):
            raise ValueError("Invalid subject")
        if any(not isinstance(ref, ObjectRef) for ref in self.references):
            raise ValueError("Invalid references")
        object.__setattr__(self, "payload", _payload(self.payload))


