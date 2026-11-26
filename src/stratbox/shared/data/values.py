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
        import struct
        return {"float_bits": struct.pack(">d", value).hex()}
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    if type(value).__module__.startswith("pandas") and type(value).__name__ in {"NAType", "NaTType"}:
        return {"missing_scalar": type(value).__name__}
    if type(value).__module__.startswith("pandas") and type(value).__name__ == "Timestamp":
        from .frame_codec import _temporal_value
        return {"pandas_timestamp": _temporal_value(value)}
    if type(value).__module__.startswith("pandas") and type(value).__name__ == "Timedelta":
        return {"pandas_timedelta_ns": str(value.value)}
    if isinstance(value, datetime):
        from .frame_codec import _temporal_value
        return {"datetime": _temporal_value(value)}
    if isinstance(value, (date, datetime, time)):
        return {"datetime" if isinstance(value, datetime) else "time" if isinstance(value, time) else "date": value.isoformat()}
    if isinstance(value, timedelta):
        return {"timedelta": (value.days, value.seconds, value.microseconds)}
    if type(value).__module__.startswith("numpy") and type(value).__name__ == "ndarray":
        if value.dtype.hasobject or value.dtype.kind not in "biufcmM": raise ValueError("codec.ndarray_dtype_not_admitted")
        return {"ndarray": {"dtype":value.dtype.str, "shape":tuple(value.shape), "bytes":value.tobytes(order="C").hex()}}
    if type(value).__module__.startswith("numpy") and hasattr(value, "item"):
        return canonical_tree(value.item())
    if type(value).__module__.startswith("pandas"):
        if type(value).__name__ in {"NAType", "NaTType"}:
            return {"missing_scalar": type(value).__name__}
        if hasattr(value, "columns") and hasattr(value, "itertuples"):
            from .frame_codec import _atom, _axis_value, _dtype_value
            return {"dataframe": {"columns": _axis_value(value.columns),
                "index": _axis_value(value.index), "dtypes": [_dtype_value(x) for x in value.dtypes],
                "rows": [[_atom(item) for item in row] for row in value.itertuples(index=False, name=None)] if len(value.columns) else [[] for _ in value.index]}}
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


def _codec_types():
    known = {cls.__module__ + ":" + cls.__qualname__: cls for cls in globals().values()
             if isinstance(cls, type) and is_dataclass(cls) and cls.__module__ == __name__}
    known[ByteIdentity.__module__ + ":" + ByteIdentity.__qualname__] = ByteIdentity
    from stratbox.shared.data import workbook_cells, source_context, assessment, coverage, journal
    from stratbox.shared import evidence
    for module in (workbook_cells, source_context, assessment, coverage, journal, evidence):
        for cls in vars(module).values():
            if isinstance(cls, type) and is_dataclass(cls) and cls.__module__ == module.__name__:
                known[cls.__module__ + ":" + cls.__qualname__] = cls
    return known


def validate_portable_tree(tree, *, admitted_types=None):
    """Reject non-replayable carrier classes before a representation is retained."""
    known = _codec_types()
    for locator, cls in dict(admitted_types or {}).items():
        if not isinstance(cls, type) or not is_dataclass(cls) or locator != cls.__module__ + ":" + cls.__qualname__:
            raise ValueError("codec.invalid_admitted_type")
        known[locator] = cls
    def visit(value):
        if isinstance(value, dict):
            if "competent_identity" in value:
                raise ValueError("codec.explicit_scientific_codec_required")
            if set(value) == {"type", "fields"} and value["type"] not in known:
                raise ValueError("codec.type_not_admitted:" + value["type"])
            for part in value.values(): visit(part)
        elif isinstance(value, (tuple, list)):
            for part in value: visit(part)
    visit(tree)
    return tree


def restore_tree(value, *, admitted_types=None):
    """Restore statically admitted values; callers may supply trusted type objects.

    Artifact contents never select imports. A domain codec can explicitly supply
    its own scientific carrier classes without making shared depend on a domain.
    """
    known = _codec_types()
    for locator, cls in dict(admitted_types or {}).items():
        if not isinstance(cls, type) or not is_dataclass(cls) or locator != cls.__module__ + ":" + cls.__qualname__:
            raise ValueError("codec.invalid_admitted_type")
        known[locator] = cls
    def decode(item):
        if not isinstance(item, dict): return item
        if set(item) == {"decimal"}: return Decimal(item["decimal"])
        if set(item) == {"decimal_infinity"}: return Decimal(item["decimal_infinity"])
        if set(item) == {"float_bits"}:
            import struct
            return struct.unpack(">d", bytes.fromhex(item["float_bits"]))[0]
        if set(item) == {"float_infinity"}: return float("inf") * item["float_infinity"]
        if set(item) == {"bytes"}: return bytes.fromhex(item["bytes"])
        if set(item) == {"tuple"}: return tuple(decode(x) for x in item["tuple"])
        if set(item) == {"set"}: return frozenset(decode(x) for x in item["set"])
        if set(item) == {"date"}: return date.fromisoformat(item["date"])
        if set(item) == {"datetime"}:
            from .frame_codec import _temporal_from
            return _temporal_from(item["datetime"], kind="datetime")
        if set(item) == {"datetime", "zone", "fold"}:
            result = datetime.fromisoformat(item["datetime"])
            if item["zone"] is not None:
                from zoneinfo import ZoneInfo
                result = result.astimezone(ZoneInfo(item["zone"]))
            return result.replace(fold=item["fold"])
        if set(item) == {"time"}: return time.fromisoformat(item["time"])
        if set(item) == {"timedelta"}: return timedelta(days=item["timedelta"][0], seconds=item["timedelta"][1], microseconds=item["timedelta"][2])
        if set(item) == {"pandas_timestamp"}:
            from .frame_codec import _temporal_from
            return _temporal_from(item["pandas_timestamp"], kind="timestamp")
        if set(item) == {"pandas_timestamp", "zone", "fold"}:
            import pandas as pd
            result = pd.Timestamp(item["pandas_timestamp"])
            if item["zone"] is not None: result = result.tz_convert(item["zone"])
            return result.replace(fold=item["fold"])
        if set(item) == {"pandas_timedelta_ns"}:
            import pandas as pd
            return pd.Timedelta(int(item["pandas_timedelta_ns"]), unit="ns")
        if set(item) == {"missing_scalar"}:
            import pandas as pd
            return pd.NA if item["missing_scalar"] == "NAType" else pd.NaT
        if set(item) == {"missing_float"} and item["missing_float"] == "nan": return float("nan")
        if set(item) == {"mapping"}: return {decode(k): decode(v) for k, v in item["mapping"]}
        if set(item) == {"ndarray"}:
            import numpy as np
            descriptor = item["ndarray"]
            if set(descriptor) != {"dtype", "shape", "bytes"}: raise ValueError("codec.ndarray_descriptor_invalid")
            dtype = np.dtype(descriptor["dtype"])
            if dtype.hasobject or dtype.kind not in "biufcmM" or any(type(n) is not int or n < 0 for n in descriptor["shape"]):
                raise ValueError("codec.ndarray_dtype_not_admitted")
            result = np.frombuffer(bytes.fromhex(descriptor["bytes"]), dtype=dtype).reshape(descriptor["shape"]).copy()
            if canonical_tree(result) != item: raise ValueError("codec.ndarray_noncanonical")
            return result
        if set(item) == {"type", "fields"}:
            cls = known.get(item["type"])
            if cls is None: raise ValueError("codec.type_not_admitted:" + str(item["type"]))
            return cls(**{key: decode(part) for key, part in item["fields"].items()})
        if set(item) == {"dataframe"}:
            import pandas as pd
            from .frame_codec import _unatom, _axis_from, _dtype_from
            frame = item["dataframe"]
            if not isinstance(frame, dict) or set(frame) != {"columns", "index", "dtypes", "rows"}:
                raise ValueError("dataframe.descriptor_invalid")
            columns, index = _axis_from(frame["columns"]), _axis_from(frame["index"])
            rows = [[_unatom(part) for part in row] for row in frame["rows"]]
            if len(frame["dtypes"]) != len(columns) or len(rows) != len(index) or any(len(row) != len(columns) for row in rows):
                raise ValueError("dataframe.geometry_mismatch")
            result = pd.DataFrame(rows, columns=columns, index=index, dtype=object)
            for position, dtype in enumerate(frame["dtypes"]):
                result.isetitem(position, result.iloc[:, position].astype(_dtype_from(dtype)))
            if canonical_tree(result) != item: raise ValueError("dataframe.noncanonical_values")
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
        from math import isfinite
        if (self.method not in {"GET", "POST", "HEAD"} or type(self.max_bytes) is not int or self.max_bytes <= 0
                or type(self.timeout) not in (int, float) or not isfinite(self.timeout) or self.timeout <= 0):
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
class ReadEvidence:
    location: str
    material_identity: ByteIdentity
    observed_at: datetime
    provider_scope: str


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
    decoded_identity: str | None = None
    encoding: str = "cp866"

    def __post_init__(self):
        object.__setattr__(self, "fields", tuple(self.fields))
        object.__setattr__(self, "records", tuple(self.records))
        self.validate_integrity()

    def validate_integrity(self):
        if self.decoded_identity is not None and self.decoded_identity != fingerprint((self.material.identity, self.fields, self.records, self.encoding)):
            raise ValueError("dbf.decoded_content_mismatch")


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


def select_dataset(dataset, rows):
    """Retain a closed row selection without carrying unselected native facts."""
    from dataclasses import replace
    rows = tuple(rows)
    if rows == dataset.rows: return dataset
    coverage = dataset.assessment.coverage
    if coverage is not None:
        from .assessment import CoverageAssessment, CoverageCoordinate
        if isinstance(coverage, CoverageAssessment):
            actual = set()
            for row in rows:
                try:
                    period = row["period"]
                    if isinstance(period, tuple): period = "/".join(map(str, period))
                    dimensions = row.get("dimensions", ())
                    if isinstance(dimensions, Mapping): dimensions = tuple(sorted((str(k), str(v)) for k,v in dimensions.items()))
                    coordinate = CoverageCoordinate(str(row["subject_namespace"]), str(row["subject"]), str(row["metric"]),
                        str(row["period_kind"]), str(period), str(row["perimeter"]), tuple(dimensions))
                    actual.add(coordinate.identity)
                except (KeyError, TypeError, ValueError):
                    pass
            coverage = replace(coverage, members=tuple(member for member in coverage.members if member in actual), observed=(), selection=None)
        else:
            coverage = None
    assessment = replace(dataset.assessment, status="partial", observed=(), coverage=coverage,
        findings=(*dataset.assessment.findings, "Selected rows do not establish the full input coverage."),
        qualifications=dataset.assessment.qualifications | frozenset({"selected_rows"}))
    return replace(dataset, rows=rows, native=None, assessment=assessment, lineage=(*dataset.lineage, dataset.identity))


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
        for name in ("periods", "values", "lineage", "source_uses"):
            object.__setattr__(self, name, tuple(getattr(self, name)))


@dataclass(frozen=True)
class AdjustmentDiagnostics:
    input_identity: str
    checks: Mapping[str, bool]
    findings: tuple[str, ...] = ()
    assessment: Assessment = Assessment()

    def __post_init__(self):
        object.__setattr__(self, "checks", immutable(self.checks))
        object.__setattr__(self, "findings", tuple(self.findings))
        if not self.checks or any(type(value) is not bool for value in self.checks.values()):
            raise ValueError("timeseries.diagnostic_checks_required")


@dataclass(frozen=True)
class TimeSeriesAdjustment:
    input_identity: str
    original: TimeSeries
    adjusted: TimeSeries
    method: str
    diagnostics: AdjustmentDiagnostics
    assessment: Assessment = Assessment()



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
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "metadata", immutable(self.metadata))


@dataclass(frozen=True)
class SnapshotRef:
    snapshot_id: str
    provider_id: str
    identity: str
    provider_scope: str | None = None


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
