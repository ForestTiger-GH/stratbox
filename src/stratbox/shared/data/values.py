"""Immutable source evidence and semantic values shared by all action protocols.

These values describe actual content and qualifications. They carry no component
release counters and do not select publishers, providers or executable routes.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime, time, timedelta
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
        if value.is_infinite(): return {"decimal_infinity": str(value)}
        if not value.is_finite(): raise ValueError("identity.decimal_nan")
        return {"decimal": str(value)}
    if isinstance(value, float):
        if __import__("math").isnan(value):
            return {"missing_float": "nan"}
        if __import__("math").isinf(value):
            return {"float_infinity": 1 if value > 0 else -1}
        return {"float": value.hex()}
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    if type(value).__module__.startswith("pandas") and type(value).__name__ in {"NAType", "NaTType"}:
        return {"missing_scalar": type(value).__name__}
    if type(value).__module__.startswith("pandas") and type(value).__name__ == "Timestamp":
        return {"pandas_timestamp": value.isoformat()}
    if isinstance(value, (date, datetime, time)):
        return {"datetime" if isinstance(value, datetime) else "time" if isinstance(value, time) else "date": value.isoformat()}
    if isinstance(value, timedelta):
        return {"timedelta": (value.days, value.seconds, value.microseconds)}
    if type(value).__module__.startswith("numpy") and hasattr(value, "item"):
        return canonical_tree(value.item())
    if type(value).__module__.startswith("pandas"):
        if type(value).__name__ in {"NAType", "NaTType"}:
            return {"missing_scalar": type(value).__name__}
        if hasattr(value, "columns") and hasattr(value, "itertuples"):
            from .frame_codec import _atom, _axis_value, _dtype_value
            return {"dataframe": {"columns": _axis_value(value.columns),
                "index": _axis_value(value.index), "dtypes": [_dtype_value(x) for x in value.dtypes],
                "rows": [[_atom(item) for item in row] for row in value.itertuples(index=False, name=None)]}}
        if hasattr(value, "isoformat"):
            return {"timestamp": value.isoformat()}
    if isinstance(value, Mapping):
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


def restore_tree(value, *, admitted_types=None):
    """Restore statically admitted values; callers may supply trusted type objects.

    Artifact contents never select imports. A domain codec can explicitly supply
    its own scientific carrier classes without making shared depend on a domain.
    """
    known = {cls.__module__ + ":" + cls.__qualname__: cls for cls in globals().values()
             if isinstance(cls, type) and is_dataclass(cls) and cls.__module__ == __name__}
    known[ByteIdentity.__module__ + ":" + ByteIdentity.__qualname__] = ByteIdentity
    from stratbox.shared.data import workbook_cells, source_context, assessment, coverage
    from stratbox.shared import evidence
    for module in (workbook_cells, source_context, assessment, coverage, evidence):
        for cls in vars(module).values():
            if isinstance(cls, type) and is_dataclass(cls) and cls.__module__ == module.__name__:
                known[cls.__module__ + ":" + cls.__qualname__] = cls
    for locator, cls in dict(admitted_types or {}).items():
        if not isinstance(cls, type) or not is_dataclass(cls) or locator != cls.__module__ + ":" + cls.__qualname__:
            raise ValueError("codec.invalid_admitted_type")
        known[locator] = cls
    def decode(item):
        if not isinstance(item, dict): return item
        if set(item) == {"decimal"}: return Decimal(item["decimal"])
        if set(item) == {"decimal_infinity"}: return Decimal(item["decimal_infinity"])
        if set(item) == {"float"}: return float.fromhex(item["float"])
        if set(item) == {"float_infinity"}: return float("inf") * item["float_infinity"]
        if set(item) == {"bytes"}: return bytes.fromhex(item["bytes"])
        if set(item) == {"tuple"}: return tuple(decode(x) for x in item["tuple"])
        if set(item) == {"set"}: return frozenset(decode(x) for x in item["set"])
        if set(item) == {"date"}: return date.fromisoformat(item["date"])
        if set(item) == {"datetime"}: return datetime.fromisoformat(item["datetime"])
        if set(item) == {"time"}: return time.fromisoformat(item["time"])
        if set(item) == {"timedelta"}: return timedelta(days=item["timedelta"][0], seconds=item["timedelta"][1], microseconds=item["timedelta"][2])
        if set(item) == {"pandas_timestamp"}:
            import pandas as pd
            return pd.Timestamp(item["pandas_timestamp"])
        if set(item) == {"missing_scalar"}:
            import pandas as pd
            return pd.NA if item["missing_scalar"] == "NAType" else pd.NaT
        if set(item) == {"missing_float"} and item["missing_float"] == "nan": return float("nan")
        if set(item) == {"mapping"}: return {decode(k): decode(v) for k, v in item["mapping"]}
        if set(item) == {"type", "fields"}:
            cls = known.get(item["type"])
            if cls is None: raise ValueError("codec.type_not_admitted:" + str(item["type"]))
            return cls(**{key: decode(part) for key, part in item["fields"].items()})
        if set(item) == {"dataframe"}:
            import pandas as pd
            from .frame_codec import _unatom, _axis_from, _dtype_from
            frame = item["dataframe"]
            columns, index = _axis_from(frame["columns"]), _axis_from(frame["index"])
            rows = [[_unatom(part) for part in row] for row in frame["rows"]]
            result = pd.DataFrame(rows, columns=columns, index=index, dtype=object)
            for position, dtype in enumerate(frame["dtypes"]):
                result.isetitem(position, result.iloc[:, position].astype(_dtype_from(dtype)))
            return result
        raise ValueError("codec.envelope_not_admitted")
    return decode(value)


@dataclass(frozen=True)
class Assessment:
    status: str = "complete"
    findings: tuple[str, ...] = ()
    expected: tuple[str, ...] = ()
    observed: tuple[str, ...] = ()
    qualifications: frozenset[str] = frozenset()
    coverage: object | None = None

    def __post_init__(self):
        for name in ("findings", "expected", "observed"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        object.__setattr__(self, "qualifications", frozenset(self.qualifications))

    @property
    def complete(self):
        return (self.status == "complete" and set(self.expected) <= set(self.observed)
                and (self.coverage is None or getattr(self.coverage, "status", None) == "complete"))


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
    effective_locator: str | None = None
    observed_origin_assurance: str = "provider_reported"
    transport_assurance: str | None = None
    route_id: str | None = None
    actual_target_identity: str | None = None
    logical_target_identity: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "headers", immutable(self.headers))


def request_identity(request):
    """Identity of an observed HTTP request, independent of logical source use."""
    return fingerprint((request.method, request.url, request.headers, request.body, request.form,
        request.max_bytes, request.timeout, request.read_only, request.metadata.get("access_scope")))


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
    evidence: object = None


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
class DBFField:
    name: str
    field_type: str
    length: int
    decimals: int
    offset: int


@dataclass(frozen=True)
class DBFRecord:
    ordinal: int
    deleted: bool
    values: tuple[str, ...]


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
    source_uses: tuple[object, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "rows", tuple(immutable(row) for row in self.rows))
        object.__setattr__(self, "semantics", immutable(self.semantics))
        from stratbox.shared.data.source_context import SourceUse
        if any(not isinstance(item, SourceUse) for item in self.source_uses):
            raise TypeError("source.typed_uses_required")
        object.__setattr__(self, "source_uses", tuple(self.source_uses))

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
    source_uses: tuple[object, ...] = ()

    def __post_init__(self):
        if len(self.periods) != len(self.values) or len(set(self.periods)) != len(self.periods):
            raise ValueError("timeseries.invalid_periods")
        object.__setattr__(self, "coordinates", immutable(self.coordinates))


@dataclass(frozen=True)
class View:
    value: object
    settings: Mapping[str, object] = field(default_factory=dict)
    lineage: tuple[object, ...] = ()
    source_uses: tuple[object, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "settings", immutable(self.settings))


@dataclass(frozen=True)
class EncodedProduct:
    data: bytes
    media_type: str
    lineage: tuple[object, ...] = ()
    descriptor: Mapping[str, object] = field(default_factory=dict)
    source_uses: tuple[object, ...] = ()

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
    accepted_value_id: str | None = None
    effect_id: str | None = None
    provider_scope: str | None = None
    source_uses: tuple[object, ...] = ()


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
