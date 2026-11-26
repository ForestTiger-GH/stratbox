"""Qualified byte carriers and physical inspection, independent of providers."""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from typing import Mapping

from stratbox.shared.identity import ByteIdentity
from .values import immutable, fingerprint


@dataclass(frozen=True)
class StagedMaterialRef:
    """An immutable complete object borrowed from a session-owned result."""
    stage_id: str
    provider_scope: str
    session_id: str
    identity: ByteIdentity
    media_type: str = "application/octet-stream"
    source_id: str | None = None
    charset: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)
    lineage: tuple[object, ...] = ()
    source_uses: tuple[object, ...] = ()

    def __post_init__(self):
        if not all(isinstance(x, str) and x for x in (self.stage_id, self.provider_scope, self.session_id)):
            raise ValueError("stage.identity_required")
        if not isinstance(self.identity, ByteIdentity):
            raise TypeError("stage.byte_identity_required")
        object.__setattr__(self, "metadata", immutable(self.metadata))
        object.__setattr__(self, "lineage", immutable(self.lineage))
        object.__setattr__(self, "source_uses", immutable(self.source_uses))


@dataclass(frozen=True)
class MaterialInspection:
    material_identity: ByteIdentity
    format: str
    media_type: str = "application/octet-stream"
    provider_scope: str | None = None
    qualifications: frozenset[str] = frozenset()
    findings: tuple[str, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.material_identity, ByteIdentity) or not self.format:
            raise ValueError("inspection.identity_and_format_required")
        object.__setattr__(self, "qualifications", frozenset(self.qualifications))
        object.__setattr__(self, "findings", tuple(self.findings))
        object.__setattr__(self, "metadata", immutable(self.metadata))

    @property
    def identity(self):
        return self.material_identity


_CONTROL_HEADERS = frozenset({
    "if-match", "if-none-match", "if-modified-since", "if-unmodified-since",
    "if-range", "cache-control", "pragma",
})


def representation_identity(request, *, vary=()):
    """Bind a retained representation without conditional/attempt controls."""
    names = tuple(sorted({str(name).strip().lower() for name in vary}))
    if "*" in names:
        raise ValueError("http.vary_not_reusable")
    headers = {str(k).lower(): str(v) for k, v in request.headers.items()
               if str(k).lower() not in _CONTROL_HEADERS}
    # Conservatively retain every supplied representation field, as well as
    # absent Vary fields. The resulting digest contains no exposed credential.
    return fingerprint((request.method, request.url, request.body, request.form,
                        request.read_only, request.metadata.get("access_scope"),
                        headers, tuple((name, headers.get(name)) for name in names)))


@dataclass(frozen=True)
class RetainedRepresentation:
    reference: object
    representation_identity: str
    validators: Mapping[str, str]
    observed_at: datetime
    vary: tuple[str, ...] = ()
    request_identity: str = ""
    assurance: str = "provider_validated"
    evidence: object | None = None

    def __post_init__(self):
        from .values import ImmutableMaterialRef
        if not isinstance(self.reference, ImmutableMaterialRef):
            raise TypeError("http.retained_reference_required")
        if not self.representation_identity or self.observed_at.tzinfo is None:
            raise ValueError("http.retained_basis_required")
        allowed = {"etag", "last-modified"}
        validators = {str(k).lower(): str(v) for k, v in self.validators.items()}
        if set(validators) - allowed:
            raise ValueError("http.validator_field_not_admitted")
        object.__setattr__(self, "validators", immutable(validators))
        object.__setattr__(self, "vary", tuple(str(x).lower() for x in self.vary))


@dataclass(frozen=True)
class NamedEffectIntent:
    """Durable postconditions for a provider-qualified mutable transition."""
    operation: str
    provider_scope: str
    destination: str
    identity: ByteIdentity | None = None
    source: str | None = None
    expected_source: ByteIdentity | None = None
    expected_destination: ByteIdentity | None = None
    policy: str = "create_only"
    retained_ancestor: object = None
    source_provider_scope: str | None = None
    expected_source_revision: str | None = None
    expected_destination_revision: str | None = None
    prerequisites: tuple[object, ...] = ()

    def __post_init__(self):
        if self.operation not in {"copy", "move", "delete"} or self.policy not in {"create_only", "replace_if_matches"}:
            raise ValueError("storage.invalid_named_intent")
        if not self.provider_scope or not self.destination:
            raise ValueError("storage.named_intent_scope_required")
        object.__setattr__(self, "prerequisites", immutable(self.prerequisites))
        for name in ("identity", "expected_source", "expected_destination"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, ByteIdentity):
                raise ValueError("storage.named_intent_identity_required")
        if self.operation == "copy" and self.identity is None:
            raise ValueError("storage.named_intent_identity_required")
        if self.operation in {"move", "delete"} and (not self.source or self.expected_source is None):
            raise ValueError("storage.named_intent_source_required")


@dataclass(frozen=True)
class NamedMaterialReceipt:
    destination: str
    identity: ByteIdentity | None
    provider_scope: str
    operation: str = "copy"
    status: str = "confirmed"
    guarantee: str = "verified_postcondition"


def staged_references(value):
    """Visit bounded graph containers without traversing scientific buffers."""
    seen, found = set(), {}
    def visit(item):
        if id(item) in seen:
            return
        seen.add(id(item))
        if isinstance(item, StagedMaterialRef):
            key = (item.session_id, item.stage_id)
            previous = found.get(key)
            if previous is not None and previous != item:
                raise ValueError("stage.conflicting_descriptor")
            found[key] = item
        elif isinstance(item, Mapping):
            for part in item.values():
                visit(part)
        elif isinstance(item, (tuple, list, set, frozenset)):
            for part in item:
                visit(part)
        elif is_dataclass(item) and not isinstance(item, type):
            for descriptor in fields(item):
                visit(getattr(item, descriptor.name))
    visit(value)
    return tuple(found.values())


PORTABLE_TYPES = (MaterialInspection, RetainedRepresentation, NamedEffectIntent,
                  NamedMaterialReceipt)
