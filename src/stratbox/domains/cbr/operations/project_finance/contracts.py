"""Typed requests compose independently owned escrow value contracts."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from stratbox.shared.data.snapshots import DatasetSnapshot, SnapshotCoverage
from stratbox.shared.evidence import SourcePayload
from stratbox.domains.cbr.publications.project_finance.contracts import EscrowSourceLink
from stratbox.domains.cbr.tables.project_finance.contracts import ParsedEscrowFile
from stratbox.domains.cbr.integration.project_finance.contracts import EscrowDataset
from stratbox.domains.cbr.products.project_finance.contracts import EscrowPivotPack, EscrowViewBuildRequest

@dataclass(frozen=True, slots=True)
class DiscoverEscrowRequest:
    index: SourcePayload | None = None


@dataclass(frozen=True, slots=True)
class ParseEscrowRequest:
    payload: SourcePayload
    source_name: str
    as_of: date | None = None


@dataclass(frozen=True, slots=True)
class EscrowHistoryBuildRequest:
    sources: tuple[ParseEscrowRequest, ...]
    continue_on_error: bool = False


@dataclass(frozen=True, slots=True)
class IntegrateEscrowRequest:
    flakes: tuple[ParsedEscrowFile, ...]
    coverage: SnapshotCoverage = SnapshotCoverage(
        "unknown", "Selected publication flakes; publisher historical coverage is unspecified."
    )


@dataclass(frozen=True, slots=True)
class EscrowFlakeSnapshotRequest:
    flake: ParsedEscrowFile
    dataset_id: str = "cbr.escrow.flake"
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class EscrowDatasetSnapshotRequest:
    dataset: EscrowDataset
    dataset_id: str = "cbr.escrow.integrated"
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class EscrowViewSnapshotRequest:
    view: EscrowPivotPack
    dataset_id: str = "cbr.escrow.prepared_view"
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReadEscrowSnapshotRequest:
    snapshot: DatasetSnapshot


@dataclass(frozen=True)
class BuildEscrowViewsRequest:
    dataset: EscrowDataset
    view: EscrowViewBuildRequest = EscrowViewBuildRequest()

@dataclass(frozen=True, slots=True)
class CompareEscrowFlakesRequest:
    before: ParsedEscrowFile
    after: ParsedEscrowFile


from stratbox.domains.cbr.integration.project_finance.mapping import EscrowGeographyRule
from stratbox.domains.cbr.tables.project_finance.validation import EscrowFlakeValidation, EscrowFlakeComparison

@dataclass(frozen=True, slots=True)
class AlignEscrowObservationsRequest:
    dataset: EscrowDataset
    geography: tuple[EscrowGeographyRule, ...] = ()
