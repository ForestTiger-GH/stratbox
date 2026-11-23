"""Source-faithful FNS flakes and explicitly selected reported observations."""
from dataclasses import dataclass
from decimal import Decimal
import json

from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity

from ..publications.contracts import ReleaseContext


@dataclass(frozen=True, slots=True)
class JsonField:
    name: str
    kind: str
    raw_token: str

    @property
    def value(self):
        return json.loads(self.raw_token, parse_float=Decimal)


@dataclass(frozen=True, slots=True)
class JsonRecord:
    ordinal: int
    fields: tuple[JsonField, ...]

    def values(self):
        return {field.name: field.value for field in self.fields}


@dataclass(frozen=True, slots=True)
class JsonFlake:
    context: ReleaseContext
    source_identity: ByteIdentity
    records: tuple[JsonRecord, ...]
    lineage: tuple[UsedInputReceipt, ...]
    profile_id: str = "fns.sme.full-json"
    coverage: SnapshotCoverage = SnapshotCoverage("complete", "All records and all fields of the supplied JSON asset.")

    @property
    def identity(self):
        from .sme.snapshots import flake_snapshot
        return flake_snapshot(self).identity


@dataclass(frozen=True, slots=True)
class FieldDisposition:
    source_field: str
    target_field: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    code: str
    severity: str
    evidence_ref: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    profile_id: str
    source_identity: ByteIdentity
    findings: tuple[ValidationFinding, ...]

    @property
    def valid(self):
        return not any(item.severity == "error" for item in self.findings)


@dataclass(frozen=True, slots=True)
class SourceProjection:
    context: ReleaseContext
    source_identity: ByteIdentity
    batch: ObservationBatch
    profile_id: str
    coverage: SnapshotCoverage
    qualifications: tuple[str, ...]
    dispositions: tuple[FieldDisposition, ...] = ()
    details_json: str = "{}"

    @property
    def identity(self):
        from .snapshots import projection_snapshot
        return projection_snapshot(self).identity
