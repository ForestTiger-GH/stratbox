"""Immutable source evidence and semantic values shared by all action protocols.

These values describe actual content and qualifications. They carry no component
release counters and do not select publishers, providers or executable routes.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping
import json

from stratbox.shared.identity import ByteIdentity


def immutable(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: immutable(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(immutable(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(immutable(item) for item in value)
    return value


def canonical_tree(value):
    if value is None or type(value) in {str, int, bool}:
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("identity.nonfinite")
        return {"decimal": str(value)}
    if isinstance(value, float):
        if not __import__("math").isfinite(value):
            raise ValueError("identity.nonfinite")
        return {"float": value.hex()}
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    if isinstance(value, (date, datetime)):
        return {type(value).__name__: value.isoformat()}
    if isinstance(value, Mapping):
        if all(isinstance(key, str) for key in value):
            return {key: canonical_tree(item) for key, item in sorted(value.items())}
        pairs = [(canonical_tree(key), canonical_tree(item)) for key, item in value.items()]
        return {"mapping": sorted(pairs, key=lambda pair: json.dumps(pair[0], sort_keys=True))}
    if isinstance(value, (tuple, list)):
        return {"tuple": [canonical_tree(item) for item in value]}
    if isinstance(value, (set, frozenset)):
        return {"set": sorted((canonical_tree(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))}
    custom = getattr(value, "fingerprint", None)
    if isinstance(custom, str):
        return {"competent_identity": custom, "type": type(value).__module__ + ":" + type(value).__qualname__}
    if is_dataclass(value):
        return {"type": type(value).__module__ + ":" + type(value).__qualname__,
                "fields": {item.name: canonical_tree(getattr(value, item.name)) for item in fields(value)}}
    raise ValueError("identity.opaque_value")


def fingerprint(value):
    return sha256(json.dumps(canonical_tree(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Assessment:
    status: str = "complete"
    findings: tuple[str, ...] = ()
    expected: tuple[str, ...] = ()
    observed: tuple[str, ...] = ()
    qualifications: frozenset[str] = frozenset()

    @property
    def complete(self):
        return self.status == "complete" and set(self.expected) <= set(self.observed)


@dataclass(frozen=True)
class Material:
    data: bytes
    media_type: str = "application/octet-stream"
    source_id: str | None = None
    charset: str | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)
    lineage: tuple[object, ...] = ()

    def __post_init__(self):
        if not isinstance(self.data, bytes):
            raise TypeError("material.bytes_required")
        object.__setattr__(self, "metadata", immutable(self.metadata))

    @property
    def identity(self):
        return ByteIdentity.of(self.data)


@dataclass(frozen=True)
class RequestSpec:
    url: str
    method: str = "GET"
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes | None = None
    form: Mapping[str, str] | None = None
    max_bytes: int = 16 * 1024 * 1024
    timeout: float = 60
    source_id: str | None = None
    observation_id: str | None = None
    freshness: str = "observation"
    read_only: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        if self.method not in {"GET", "POST", "HEAD"} or self.max_bytes <= 0 or self.timeout <= 0:
            raise ValueError("request.invalid")
        if self.body is not None and self.form is not None:
            raise ValueError("request.ambiguous_body")
        object.__setattr__(self, "headers", immutable(self.headers))
        object.__setattr__(self, "form", immutable(self.form) if self.form is not None else None)
        object.__setattr__(self, "metadata", immutable(self.metadata))


@dataclass(frozen=True)
class FetchEvidence:
    request_identity: str
    observed_at: datetime
    status_code: int
    material_identity: ByteIdentity | None
    headers: Mapping[str, str] = field(default_factory=dict)
    observation_id: str = ""

    def __post_init__(self):
        object.__setattr__(self, "headers", immutable(self.headers))


@dataclass(frozen=True)
class SourceClaim:
    source_id: str
    issue_id: str = ""
    asset_id: str = "main"
    attribution: str = "asserted"


@dataclass(frozen=True)
class IdentifiedMaterial:
    material: Material
    claim: SourceClaim
    assessment: Assessment = Assessment()

    @property
    def source_id(self):
        return self.claim.source_id

    @property
    def identity(self):
        return self.material.identity


@dataclass(frozen=True)
class PublicationAsset:
    source_id: str
    issue_id: str
    asset_id: str
    locator: str
    format: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "metadata", immutable(self.metadata))


@dataclass(frozen=True)
class PublicationListing:
    domain_id: str
    entries: tuple[PublicationAsset, ...]
    assessment: Assessment = Assessment()
    lineage: tuple[object, ...] = ()


@dataclass(frozen=True)
class AssetSelection:
    entries: tuple[PublicationAsset, ...]
    assessment: Assessment = Assessment()


@dataclass(frozen=True)
class UpdateAssessment:
    status: str
    basis: str
    findings: tuple[str, ...] = ()
    predecessor: str | None = None
    candidate: str | None = None


@dataclass(frozen=True)
class WorkbookEvidence:
    material: Material
    workbook: object
    assessment: Assessment = Assessment()


@dataclass(frozen=True)
class JsonEvidence:
    material: Material
    value: object
    assessment: Assessment = Assessment()
    tokens: Mapping[tuple[object, ...], str] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "value", immutable(self.value))
        object.__setattr__(self, "tokens", immutable(self.tokens))


@dataclass(frozen=True)
class DbfEvidence:
    material: Material
    fields: tuple[object, ...]
    records: tuple[object, ...]
    assessment: Assessment = Assessment()


@dataclass(frozen=True)
class DocumentEvidence:
    material: Material
    document: object
    assessment: Assessment = Assessment()


@dataclass(frozen=True)
class TableEvidenceSet:
    tables: tuple[object, ...]
    material: Material | None = None
    source_id: str | None = None
    issue_id: str = ""
    assessment: Assessment = Assessment()
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "metadata", immutable(self.metadata))


@dataclass(frozen=True)
class SourceDataset:
    source_id: str
    rows: tuple[Mapping[str, object], ...]
    semantics: Mapping[str, object] = field(default_factory=dict)
    issue_id: str = ""
    lineage: tuple[object, ...] = ()
    assessment: Assessment = Assessment()
    native: object = None

    def __post_init__(self):
        object.__setattr__(self, "rows", tuple(immutable(row) for row in self.rows))
        object.__setattr__(self, "semantics", immutable(self.semantics))

    @property
    def identity(self):
        return fingerprint(self)


@dataclass(frozen=True)
class IntegratedDataset(SourceDataset):
    pass


@dataclass(frozen=True)
class DerivedDataset(SourceDataset):
    pass


@dataclass(frozen=True)
class TimeSeries:
    coordinates: Mapping[str, object]
    periods: tuple[object, ...]
    values: tuple[object, ...]
    unit: str
    frequency: str
    measure_kind: str
    lineage: tuple[object, ...] = ()
    assessment: Assessment = Assessment()

    def __post_init__(self):
        if len(self.periods) != len(self.values) or len(set(self.periods)) != len(self.periods):
            raise ValueError("timeseries.invalid_periods")
        object.__setattr__(self, "coordinates", immutable(self.coordinates))


@dataclass(frozen=True)
class View:
    value: object
    settings: Mapping[str, object] = field(default_factory=dict)
    lineage: tuple[object, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "settings", immutable(self.settings))


@dataclass(frozen=True)
class EncodedProduct:
    data: bytes
    media_type: str
    lineage: tuple[object, ...] = ()
    descriptor: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "descriptor", immutable(self.descriptor))

    @property
    def identity(self):
        return ByteIdentity.of(self.data)


@dataclass(frozen=True)
class ImmutableMaterialRef:
    location: str
    identity: ByteIdentity
    provider_id: str = "filestore"
    lineage: tuple[object, ...] = ()
    guarantee: str = "immutable_content"


@dataclass(frozen=True)
class SnapshotRef:
    snapshot_id: str
    provider_id: str
    identity: str


@dataclass(frozen=True)
class ConvertedMaterial:
    material: Material
    original_identity: ByteIdentity
    provider_id: str
    assessment: Assessment = Assessment()


@dataclass(frozen=True)
class FormulaSpec:
    expression: str
    operands: Mapping[str, str]
    output_metric: str
    unit: str
    group_by: tuple[str, ...] = ("period", "subject", "perimeter")

    def __post_init__(self):
        object.__setattr__(self, "operands", immutable(self.operands))


@dataclass(frozen=True)
class DocumentBlock:
    ordinal: int
    kind: str
    text: str = ""
    page: int | None = None
    rows: tuple[tuple[str, ...], ...] = ()
    locator: str = ""


@dataclass(frozen=True)
class DocumentStructure:
    format: str
    blocks: tuple[DocumentBlock, ...]
    source_identity: ByteIdentity
    assessment: Assessment = Assessment()
