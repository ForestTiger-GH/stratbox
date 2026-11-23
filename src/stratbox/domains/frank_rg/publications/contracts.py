"""Transport-independent report identities and caller-owned delivery inputs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Literal

from stratbox.core.storage.filestore import FileVersion
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity


@dataclass(frozen=True, slots=True)
class ProfileRefs:
    discovery: str
    identification: str
    selection: str
    naming: str


@dataclass(frozen=True, slots=True)
class SourceSeries:
    source_id: str
    slot: str
    title: str
    periodicity: Literal["snapshot", "month_week"]
    kind: Literal["workbook"] = "workbook"


@dataclass(frozen=True, slots=True)
class SourceFamily:
    family_id: str
    title: str
    profiles: ProfileRefs
    series: tuple[SourceSeries, ...]
    publisher_id: str = "frank_rg"

    def source(self, source_id: str) -> SourceSeries:
        for item in self.series:
            if item.source_id == source_id:
                return item
        raise ValueError("frg.registry.unknown_source")

    def slot(self, slot: str) -> SourceSeries:
        for item in self.series:
            if item.slot == slot:
                return item
        raise ValueError("frg.registry.unknown_slot")


@dataclass(frozen=True, slots=True)
class ReportPeriod:
    """A supplier snapshot date or a numbered week within a calendar month."""
    snapshot_date: date
    week_no: int | None = None

    def __post_init__(self):
        if type(self.snapshot_date) is not date:
            raise ValueError("frg.period.invalid_date")
        if self.week_no is not None and (
            type(self.week_no) is not int or not 1 <= self.week_no <= 6
            or self.snapshot_date.day != 1
        ):
            raise ValueError("frg.period.invalid_month_week")

    @property
    def text(self) -> str:
        if self.week_no is None:
            return self.snapshot_date.isoformat()
        return f"{self.snapshot_date:%Y-%m} week {self.week_no}"

    @property
    def issue_id(self) -> str:
        return self.snapshot_date.isoformat() if self.week_no is None else f"{self.snapshot_date:%Y-%m}-week-{self.week_no}"

    @property
    def rank(self) -> tuple[date, int]:
        return self.snapshot_date, self.week_no or 0


@dataclass(frozen=True, slots=True)
class FileEntry:
    path: str
    filename: str
    size_bytes: int | None = None
    mtime: float | None = None

    def __post_init__(self):
        if not isinstance(self.path, str) or not self.path or "\x00" in self.path:
            raise ValueError("frg.entry.path_invalid")
        if (not isinstance(self.filename, str) or not self.filename
                or self.filename != self.path.replace("\\", "/").rsplit("/", 1)[-1]
                or self.filename in {".", ".."} or "\x00" in self.filename):
            raise ValueError("frg.entry.filename_mismatch")
        if self.size_bytes is not None and (type(self.size_bytes) is not int or self.size_bytes < 0):
            raise ValueError("frg.entry.size_invalid")
        if self.mtime is not None and (type(self.mtime) not in (int, float) or not isfinite(self.mtime)):
            raise ValueError("frg.entry.mtime_invalid")


@dataclass(frozen=True, slots=True)
class DiscoveryRequest:
    directory: str
    recursive: bool = False
    family_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SourceIndex:
    directory: str
    entries: tuple[FileEntry, ...]
    identity: ByteIdentity
    family_ids: tuple[str, ...] = ()
    recursive: bool = False
    inventory_coverage: Literal["unknown"] = "unknown"


@dataclass(frozen=True, slots=True)
class Asset:
    """Observed path and name are evidence, never the logical source ID."""
    entry: FileEntry
    family_id: str | None
    source_id: str | None
    slot: str | None
    format: str
    period: ReportPeriod | None
    recognition: Literal["supplier", "canonical", "unclassified", "conflicted"]
    valid: bool
    diagnostic: str


@dataclass(frozen=True, slots=True)
class InspectionRequest:
    index: SourceIndex


@dataclass(frozen=True, slots=True)
class Inventory:
    index: SourceIndex
    assets: tuple[Asset, ...]


@dataclass(frozen=True, slots=True)
class Selection:
    source_id: str
    state: Literal["selected", "missing", "ambiguous"]
    asset: Asset | None
    candidates: tuple[Asset, ...] = ()


@dataclass(frozen=True, slots=True)
class SelectionRequest:
    inventory: Inventory
    selected_sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Catalog:
    inventory: Inventory
    selections: tuple[Selection, ...]


@dataclass(frozen=True, slots=True)
class AcquireRequest:
    asset: Asset
    expected_identity: ByteIdentity | None = None
    max_bytes: int = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class CaptureRequest:
    """A specialized method supplies bytes, report identity and format directly."""
    source_id: str
    period: ReportPeriod
    payload: SourcePayload
    format: str


@dataclass(frozen=True, slots=True)
class AcquiredReport:
    source_id: str
    period: ReportPeriod
    format: str
    payload: SourcePayload
    route: Literal["filestore", "supplied"]
    file_version: FileVersion | None = None
    entry: FileEntry | None = None

    def __post_init__(self):
        if not isinstance(self.payload, SourcePayload) or not isinstance(self.period, ReportPeriod):
            raise ValueError("frg.material.report_invalid")
        if self.payload.source_id != self.source_id:
            raise ValueError("frg.material.source_mismatch")
        if self.route not in {"filestore", "supplied"}:
            raise ValueError("frg.material.route_invalid")
        if self.file_version is not None:
            if not isinstance(self.file_version, FileVersion) or self.file_version.identity != self.payload.identity:
                raise ValueError("frg.material.identity_mismatch")
        if self.entry is not None and not isinstance(self.entry, FileEntry):
            raise ValueError("frg.material.file_evidence_invalid")
        if self.route == "supplied" and (self.file_version is not None or self.entry is not None):
            raise ValueError("frg.material.supplied_evidence_invalid")
        if self.route == "filestore" and (self.file_version is None or self.entry is None):
            raise ValueError("frg.material.file_evidence_missing")
        if self.route == "filestore" and self.entry.path != self.file_version.path:
            raise ValueError("frg.material.file_evidence_invalid")


@dataclass(frozen=True, slots=True)
class SourceCheckpoint:
    source_id: str
    period: ReportPeriod
    original_identity: ByteIdentity
    entry: FileEntry | None = None

    def __post_init__(self):
        if (not isinstance(self.source_id, str) or not self.source_id
                or not isinstance(self.period, ReportPeriod)
                or not isinstance(self.original_identity, ByteIdentity)
                or (self.entry is not None and not isinstance(self.entry, FileEntry))):
            raise ValueError("frg.update.checkpoint_invalid")


@dataclass(frozen=True, slots=True)
class UpdateRequest:
    catalog: Catalog
    checkpoints: tuple[SourceCheckpoint, ...] = ()
    force_refresh: bool = False


@dataclass(frozen=True, slots=True)
class UpdateDecision:
    source_id: str
    asset: Asset | None
    state: Literal["initial", "metadata_unchanged", "changed", "missing", "ambiguous"]
    acquisition_required: bool
    reason: str


@dataclass(frozen=True, slots=True)
class UpdatePlan:
    decisions: tuple[UpdateDecision, ...]
    index_identity: ByteIdentity
    inventory_coverage: Literal["unknown"] = "unknown"


@dataclass(frozen=True, slots=True)
class MaterialAssessment:
    source_id: str
    state: Literal["initial", "unchanged", "revised", "new_period"]
    original_identity: ByteIdentity


@dataclass(frozen=True, slots=True)
class AssessMaterialRequest:
    report: AcquiredReport
    checkpoint: SourceCheckpoint | None = None


@dataclass(frozen=True, slots=True)
class PrepareFileRequest:
    report: AcquiredReport


@dataclass(frozen=True, slots=True)
class PreparedFile:
    source_id: str
    period: ReportPeriod
    filename: str
    payload: SourcePayload
    naming_profile_id: str
    naming_method_version: str
