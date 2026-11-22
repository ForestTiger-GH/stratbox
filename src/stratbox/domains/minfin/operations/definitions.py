"""Lightweight typed operation contracts for the Minfin domain."""
from __future__ import annotations

from stratbox.core.execution import OperationDefinition, OperationSemantics, ProcessingStage, InputPort, OutputPort
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import DatasetSnapshot
from ..publications.contracts import (
    AcquireRequest, AcquiredAsset, DiscoverRequest, InspectRequest, Inspection,
    PublicationIndex, ReadableDocument, ReadableRequest, UpdateRequest, UpdatePlan,
)
from ..tables.contracts import (
    CompareRequest, ExtractRequest, MapRequest, MappedObservations, RenderRequest,
    TableComparison, TableExtract, ValidateRequest, Validation, SerializeRequest,
    ReadRepresentationRequest, BuildFlakeRequest, FlakeTable, RenderFlakeRequest,
    SerializeFlakeRequest, ReadFlakeRequest, FlakeSnapshotRequest, ReadFlakeSnapshotRequest,
)
from ..analytics.contracts import SummaryRequest, HeadlineSummary, NoticeRequest, NoticePreparation
from .contracts import CaptureRequest, CaptureResult

_ORIGINAL = DataContract("minfin.publisher_material", 1, DataRole.ORIGINALS)
_INDEX = DataContract("minfin.publication_index", 1, None)
_TABLES = DataContract("minfin.source_cells", 1, DataRole.EXTRACTS)
_OBSERVATIONS = DataContract("minfin.mapped_observations", 1, DataRole.EXTRACTS)
_HTML = DataContract("minfin.publisher_page", 1, DataRole.ORIGINALS)
_HTTP = frozenset({"http"})
_LIMIT = ExecutionBudget(input_bytes=64 * 1024 * 1024, output_bytes=64 * 1024 * 1024,
                         temporary_bytes=256 * 1024 * 1024, cells=500_000)

DISCOVER = OperationDefinition(
    "minfin.discover", 1, "minfin-index-profile-3", DiscoverRequest, PublicationIndex,
    optional_capabilities=_HTTP, limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.DISCOVER,),
        inputs=(InputPort("index", _HTML, "index", required=False,
                          alternatives=(DataContract("source.payload", 1, DataRole.ORIGINALS), DataContract("material.payload"))),),
        outputs=(OutputPort("index", _INDEX),),
        parameters=("family_id", "max_links", "page_url"),
        summary="Inspect one Minfin landing page and return bounded source candidates with unknown inventory coverage."),
)
INSPECT = OperationDefinition(
    "minfin.inspect", 1, "minfin-index-delta-1", InspectRequest, Inspection,
    processing=OperationSemantics((ProcessingStage.INSPECT,),
        inputs=(InputPort("previous", _INDEX, "before"), InputPort("current", _INDEX, "after")),
        outputs=(OutputPort("comparison", DataContract("minfin.index_change", 1, None)),),
        summary="Compare candidate link inventories, without asserting publisher absence or source revision."),
)
ACQUIRE = OperationDefinition(
    "minfin.acquire", 1, "minfin-original-profile-2", AcquireRequest, AcquiredAsset,
    required_capabilities=_HTTP, limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.ACQUIRE,),
        inputs=(InputPort("asset", DataContract("minfin.asset", 1, None), "asset"),),
        outputs=(OutputPort("original", _ORIGINAL, "source.payload", qualifications=frozenset({"source.minfin"})),
                 OutputPort("payload", DataContract("source.payload", 1, DataRole.ORIGINALS), "source.payload")),
        parameters=("max_bytes", "deadline_seconds"),
        summary="Acquire one explicitly selected Minfin asset with publisher URL and file-envelope checks."),
)
EXTRACT = OperationDefinition(
    "minfin.extract", 1, "minfin-source-cells-1", ExtractRequest, TableExtract,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.EXTRACT,),
        inputs=(InputPort("original", _ORIGINAL, "payload",
                          alternatives=(DataContract("source.payload", 1, DataRole.ORIGINALS), DataContract("material.payload"))),),
        outputs=(OutputPort("extract", _TABLES),),
        parameters=("family_id", "format", "member", "selected_sheets", "max_cells", "csv_encoding"),
        summary="Extract explicitly selected workbook or CSV cells without inferring economic axes."),
)
CAPTURE = OperationDefinition(
    "minfin.capture", 1, "minfin-capture-1", CaptureRequest, CaptureResult,
    required_capabilities=_HTTP, limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.ACQUIRE, ProcessingStage.EXTRACT),
        inputs=(InputPort("asset", DataContract("minfin.asset", 1, None), "asset"),),
        outputs=(OutputPort("extract", _TABLES, "extracted"),),
        parameters=("max_bytes", "max_cells", "member", "selected_sheets"),
        composition=True,
        summary="Acquire and extract one selected table asset, returning both acquisition and extracted evidence."),
)
VALIDATE = OperationDefinition(
    "minfin.validate", 1, "minfin-structure-1", ValidateRequest, Validation,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.VALIDATE,),
        inputs=(InputPort("extract", _TABLES, "extract"),),
        outputs=(OutputPort("validation", DataContract("minfin.structural_validation", 1, None)),),
        summary="Validate source-cell geometry and report structural coverage, never economic correctness."),
)
COMPARE = OperationDefinition(
    "minfin.compare", 1, "minfin-cell-delta-1", CompareRequest, TableComparison,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.COMPARE,),
        inputs=(InputPort("before", _TABLES, "before"), InputPort("after", _TABLES, "after")),
        outputs=(OutputPort("changes", DataContract("minfin.source_cell_delta", 1, None)),),
        parameters=("max_changes",),
        summary="Report cell-level revisions between source-compatible extracts without claiming semantic equality."),
)
MAP = OperationDefinition(
    "minfin.map_observations", 1, "minfin-reviewed-mapping-1", MapRequest, MappedObservations,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.EXTRACT,),
        inputs=(InputPort("extract", _TABLES, "extract"),),
        outputs=(OutputPort("observations", _OBSERVATIONS),),
        parameters=("bindings",),
        summary="Map only explicitly reviewed source-cell coordinates to metric, geography, unit and period IDs."),
)
RENDER = OperationDefinition(
    "minfin.render_csv", 1, "minfin-cells-csv-1", RenderRequest, Representation,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("extract", _TABLES, "extract"),),
        outputs=(OutputPort("csv", DataContract("minfin.source_cells.csv", 1, DataRole.PRODUCTS)),),
        summary="Render a deterministic UTF-8 CSV with exact cell coordinates, source digest and formula evidence."),
)
READABLE = OperationDefinition(
    "minfin.readable", 1, "minfin-pdf-text-1", ReadableRequest, ReadableDocument,
    partial_allowed=True, limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.READABLE,),
        inputs=(InputPort("original", _ORIGINAL, "payload",
                          alternatives=(DataContract("source.payload", 1, DataRole.ORIGINALS), DataContract("material.payload"))),),
        outputs=(OutputPort("text", DataContract("minfin.document_text", 1, DataRole.READABLE),
                            outcomes=frozenset({"partial"}), qualifications=frozenset({"text_only"})),),
        parameters=("family_id", "max_pages", "format"),
        summary="Extract PDF text only, with an explicit incomplete-visual-coverage qualification."),
)

SERIALIZE = OperationDefinition(
    "minfin.serialize", 1, "minfin-extract-json-1", SerializeRequest, Representation,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("extract", _TABLES, "extract"),),
        outputs=(OutputPort("representation", DataContract("minfin.source_cells.json", 1, DataRole.EXTRACTS)),),
        summary="Serialize complete source-cell extracts including blank-sheet geometry to a repeatable JSON representation."),
)
READ_EXTRACT = OperationDefinition(
    "minfin.read_representation", 1, "minfin-extract-json-1", ReadRepresentationRequest, TableExtract,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.READ_EXTRACT,),
        inputs=(InputPort("representation", DataContract("minfin.source_cells.json", 1, DataRole.EXTRACTS), "representation"),),
        outputs=(OutputPort("extract", _TABLES),),
        summary="Read a retained exact extract representation without re-acquiring source material."),
)


# Independently callable update, flake, headline and notice stages.
_CELLS = DataContract("minfin.source_cells", 1, DataRole.EXTRACTS)
_FLAKE = DataContract("minfin.flake", 1, DataRole.EXTRACTS)
_SUMMARY = DataContract("minfin.headlines", 1, DataRole.PRODUCTS)
_NOTICE = DataContract("minfin.notice_preparation", 1, None)

PLAN_UPDATES = OperationDefinition(
    "minfin.plan_updates", 1, "minfin.publisher-marker-profile-2", UpdateRequest, UpdatePlan,
    processing=OperationSemantics((ProcessingStage.INSPECT,),
        inputs=(InputPort("index", _INDEX, "index"),),
        outputs=(OutputPort("plan", DataContract("minfin.update_plan", 1, None)),),
        parameters=("target", "selected_sources", "checkpoints", "retained_sources", "force_reprocess", "force_refresh"),
        summary="Compare publisher document modification markers to caller-owned confirmed checkpoints without downloading XLSX."),
)
BUILD_FLAKE = OperationDefinition(
    "minfin.build_flake", 1, "minfin.profile-flake.v2", BuildFlakeRequest, FlakeTable,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.EXTRACT,),
        inputs=(InputPort("source", _CELLS, "extract"),),
        outputs=(OutputPort("flake", _FLAKE),),
        parameters=("source_id", "selected_sheet"),
        summary="Clean the source-local workbook to one wide flake; strip document decoration and normalize economic period headers."),
)
RENDER_FLAKE = OperationDefinition(
    "minfin.render_flake", 1, "minfin.flake-csv.v1", RenderFlakeRequest, Representation,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("flake", _FLAKE, "flake"),),
        outputs=(OutputPort("csv", DataContract("minfin.flake.csv", 1, DataRole.EXTRACTS)),),
        summary="Export source-local flake values as CSV; use the JSON codec for complete replay."),
)
SERIALIZE_FLAKE = OperationDefinition(
    "minfin.serialize_flake", 1, "minfin.flake-json.v1", SerializeFlakeRequest, Representation,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("flake", _FLAKE, "flake"),),
        outputs=(OutputPort("representation", DataContract("minfin.flake.json", 1, DataRole.EXTRACTS)),),
        summary="Serialize the complete source-local flake, including economic axes, units and original evidence."),
)
READ_FLAKE = OperationDefinition(
    "minfin.read_flake", 1, "minfin.flake-json.v1", ReadFlakeRequest, FlakeTable,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.READ_EXTRACT,),
        inputs=(InputPort("representation", DataContract("minfin.flake.json", 1, DataRole.EXTRACTS), "representation"),),
        outputs=(OutputPort("flake", _FLAKE),),
        summary="Restore a complete source-local flake from a verified representation without reacquiring its original."),
)
SUMMARIZE = OperationDefinition(
    "minfin.summarize", 1, "minfin.profile-headlines.v2", SummaryRequest, HeadlineSummary,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        inputs=(InputPort("flake", _FLAKE, "flake"),),
        outputs=(OutputPort("summary", _SUMMARY),),
        parameters=("period_id",),
        summary="Calculate three budget headlines or NWF total/liquid stocks and same-period prior-year percentages."),
)
PREPARE_NOTICE = OperationDefinition(
    "minfin.prepare_notice", 1, "minfin.notice-facts.v2", NoticeRequest, NoticePreparation,
    processing=OperationSemantics((ProcessingStage.VIEW,),
        inputs=(InputPort("summary", _SUMMARY, "summary"),
                InputPort("asset", DataContract("minfin.asset", 1, None), "asset"),
                InputPort("decision", DataContract("minfin.update_decision", 1, None), "decision")),
        outputs=(OutputPort("preparation", _NOTICE),),
        parameters=("include_initial", "baseline_original_identity"),
        summary="Prepare a source-qualified, channel-neutral notification candidate; initial loads are quiet by default."),
)


FLAKE_SNAPSHOT = OperationDefinition(
    "minfin.flake_snapshot", 1, "minfin.flake-snapshot.v1", FlakeSnapshotRequest, DatasetSnapshot,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("flake", _FLAKE, "flake"),),
        outputs=(OutputPort("snapshot", DataContract("minfin.flake.snapshot", 1, DataRole.EXTRACTS)),
                 OutputPort("dataset", DataContract("dataset.snapshot", 1, None))),
        parameters=("dataset_id", "version_id"),
        summary="Encode a complete source-local flake as typed metadata, column and value tables for any logical dataset backend."),
)
READ_FLAKE_SNAPSHOT = OperationDefinition(
    "minfin.read_flake_snapshot", 1, "minfin.flake-snapshot.v1", ReadFlakeSnapshotRequest, FlakeTable,
    limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.READ_EXTRACT,),
        inputs=(InputPort("snapshot", DataContract("minfin.flake.snapshot", 1, DataRole.EXTRACTS), "snapshot",
                          alternatives=(DataContract("dataset.snapshot", 1, None),)),),
        outputs=(OutputPort("flake", _FLAKE),),
        summary="Restore a source-local flake from a complete pinned logical dataset after verifying every component schema."),
)
