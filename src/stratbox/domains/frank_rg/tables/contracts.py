"""Supplied semantic profiles bind exact bytes, coordinates and economic meaning."""
from dataclasses import dataclass
from typing import Literal

from stratbox.shared.data.observations import MetricRef, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.workbooks import WorkbookExtract
from stratbox.shared.identity import ByteIdentity
from ..publications.contracts import AcquiredReport


@dataclass(frozen=True, slots=True)
class ExtractRequest:
    report: AcquiredReport


@dataclass(frozen=True, slots=True)
class ExtractSnapshotRequest:
    extract: WorkbookExtract
    dataset_id: str | None = None
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReadExtractRequest:
    snapshot: DatasetSnapshot


@dataclass(frozen=True, slots=True)
class ValidateExtractRequest:
    extract: WorkbookExtract


@dataclass(frozen=True, slots=True)
class ExtractValidation:
    source_id: str
    sheets: int
    cells: int
    formulas_without_cache: int
    qualifications: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompareExtractRequest:
    before: WorkbookExtract
    after: WorkbookExtract


@dataclass(frozen=True, slots=True)
class ReadableRequest:
    extract: WorkbookExtract


@dataclass(frozen=True, slots=True)
class CellBinding:
    sheet: str
    row: int
    column: int
    subject: SubjectRef
    metric: MetricRef
    period: PeriodRef
    perimeter: str
    dimensions: tuple[tuple[str, str], ...] = ()
    decimal_separator: Literal[".", ","] = "."
    missing_tokens: tuple[tuple[str, str], ...] = (("", "blank"), ("-", "dash"), ("—", "dash"))


@dataclass(frozen=True, slots=True)
class SemanticProfile:
    source_id: str
    profile_id: str
    version: int
    original_identity: ByteIdentity
    bindings: tuple[CellBinding, ...]


@dataclass(frozen=True, slots=True)
class BuildFlakeRequest:
    extract: WorkbookExtract
    profile: SemanticProfile


@dataclass(frozen=True, slots=True)
class SemanticFlake:
    series_id: str
    issue_id: str
    asset_id: str
    original_identity: ByteIdentity
    extract_identity: ByteIdentity
    profile_id: str
    profile_version: int
    profile_identity: ByteIdentity
    batch: ObservationBatch
    qualifications: tuple[str, ...] = ("caller_supplied_byte_bound_semantics",)


@dataclass(frozen=True, slots=True)
class FlakeSnapshotRequest:
    flake: SemanticFlake
    dataset_id: str | None = None
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReadFlakeRequest:
    snapshot: DatasetSnapshot
