"""Minfin publisher identities, source-faithful tables and explicit value mappings.

The models intentionally do not assume that a filename contains an observation
period, or that a visual row label is a stable economic indicator identifier.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from stratbox.shared.evidence import AcquiredSource, SourcePayload
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.representation import Representation


@dataclass(frozen=True, slots=True)
class Variant:
    source_id: str
    asset_id: str
    title: str
    prefix: str
    suffix: str
    basis_hint: str = "unknown"
    periodicity: str = "unknown"


@dataclass(frozen=True, slots=True)
class SourceFamily:
    family_id: str
    title: str
    landing_url: str
    frequency: str
    formats: tuple[str, ...]
    default_source_id: str
    variants: tuple[Variant, ...]
    operations: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class Asset:
    family_id: str
    source_id: str
    asset_id: str
    url: str
    filename: str
    format: str
    label: str
    recognition: Literal["registered_variant", "unclassified"]
    index_identity: ByteIdentity
    published_on: date | None = None
    modified_on: date | None = None
    document_id: str | None = None
    document_title: str = ""


@dataclass(frozen=True, slots=True)
class PublicationIndex:
    family_id: str
    assets: tuple[Asset, ...]
    index_identity: ByteIdentity
    coverage: Literal["unknown"] = "unknown"
    rejected_links: int = 0
    ambiguous_asset_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DiscoverRequest:
    family_id: str
    index: SourcePayload | None = None
    max_links: int = 2000


@dataclass(frozen=True, slots=True)
class AcquireRequest:
    asset: Asset
    max_bytes: int = 64 * 1024 * 1024
    deadline_seconds: int = 60


@dataclass(frozen=True, slots=True)
class AcquiredAsset:
    asset: Asset
    source: AcquiredSource


@dataclass(frozen=True, slots=True)
class Cell:
    sheet: str
    row: int
    column: int
    kind: str
    value: str
    number_format: str = ""
    cached: str | None = None


@dataclass(frozen=True, slots=True)
class Sheet:
    name: str
    rows: int
    columns: int
    cells: tuple[Cell, ...]


@dataclass(frozen=True, slots=True)
class TableExtract:
    family_id: str
    source_id: str
    source_identity: ByteIdentity
    format: str
    sheets: tuple[Sheet, ...]
    member: str | None = None
    coverage: str = "nonempty_cells"


@dataclass(frozen=True, slots=True)
class ExtractRequest:
    family_id: str
    payload: SourcePayload
    format: str
    member: str | None = None
    selected_sheets: tuple[str, ...] = ()
    max_cells: int = 150_000
    csv_encoding: str = "utf-8-sig"


@dataclass(frozen=True, slots=True)
class CellChange:
    sheet: str
    row: int
    column: int
    before: Cell | None
    after: Cell | None


@dataclass(frozen=True, slots=True)
class SheetChange:
    sheet: str
    before_rows: int | None
    before_columns: int | None
    after_rows: int | None
    after_columns: int | None


@dataclass(frozen=True, slots=True)
class TableComparison:
    family_id: str
    before_identity: ByteIdentity
    after_identity: ByteIdentity
    changes: tuple[CellChange, ...]
    layout_changes: tuple[SheetChange, ...] = ()
    layer: Literal["source_cells"] = "source_cells"


@dataclass(frozen=True, slots=True)
class CompareRequest:
    before: TableExtract
    after: TableExtract
    max_changes: int = 100_000


@dataclass(frozen=True, slots=True)
class InspectRequest:
    before: PublicationIndex
    after: PublicationIndex


@dataclass(frozen=True, slots=True)
class Inspection:
    family_id: str
    added_candidates: tuple[str, ...]
    disappeared_candidates: tuple[str, ...]
    coverage: Literal["unknown"] = "unknown"


@dataclass(frozen=True, slots=True)
class ValidateRequest:
    extract: TableExtract


@dataclass(frozen=True, slots=True)
class Validation:
    family_id: str
    cells: int
    sheets: int
    formulas_without_cache: int
    empty_sheets: tuple[str, ...]
    level: Literal["structural_only"] = "structural_only"


@dataclass(frozen=True, slots=True)
class RenderRequest:
    extract: TableExtract


@dataclass(frozen=True, slots=True)
class MetricBinding:
    """Explicit, reviewed mapping from a source cell to an economic value."""
    sheet: str
    row: int
    column: int
    metric_id: str
    period_id: str
    value_basis: str  # e.g. ytd, period_flow, stock, percent
    unit: str
    geography_id: str = "RU"


@dataclass(frozen=True, slots=True)
class MetricObservation:
    metric_id: str
    period_id: str
    geography_id: str
    value: str
    value_basis: str
    unit: str
    sheet: str
    row: int
    column: int


@dataclass(frozen=True, slots=True)
class MappedObservations:
    family_id: str
    source_identity: ByteIdentity
    observations: tuple[MetricObservation, ...]


@dataclass(frozen=True, slots=True)
class MapRequest:
    extract: TableExtract
    bindings: tuple[MetricBinding, ...]


@dataclass(frozen=True, slots=True)
class ReadableRequest:
    family_id: str
    payload: SourcePayload
    max_pages: int = 100
    format: Literal["pdf", "docx"] = "pdf"


@dataclass(frozen=True, slots=True)
class ReadableDocument:
    family_id: str
    source_identity: ByteIdentity
    pages: tuple[str, ...]
    coverage: Literal["text_only_partial"] = "text_only_partial"


@dataclass(frozen=True, slots=True)
class CaptureRequest:
    asset: Asset
    max_bytes: int = 64 * 1024 * 1024
    max_cells: int = 150_000
    member: str | None = None
    selected_sheets: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CaptureResult:
    acquired: AcquiredAsset
    extracted: TableExtract


@dataclass(frozen=True, slots=True)
class SerializeRequest:
    extract: TableExtract


@dataclass(frozen=True, slots=True)
class ReadRepresentationRequest:
    representation: Representation


__all__ = (
    "SourceFamily", "Variant", "Asset", "PublicationIndex", "DiscoverRequest", "AcquireRequest", "AcquiredAsset",
    "Cell", "Sheet", "TableExtract", "ExtractRequest", "CellChange", "SheetChange", "TableComparison", "CompareRequest",
    "InspectRequest", "Inspection", "ValidateRequest", "Validation", "RenderRequest", "MetricBinding", "MetricObservation", "MappedObservations", "MapRequest", "ReadableRequest",
    "ReadableDocument", "CaptureRequest", "CaptureResult", "SerializeRequest", "ReadRepresentationRequest", "Representation",
)