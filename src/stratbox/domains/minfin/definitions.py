"""Lightweight typed operation contracts for the Minfin domain."""
from __future__ import annotations

from stratbox.core.execution import OperationDefinition, OperationSemantics, ProcessingStage, InputPort, OutputPort
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from .models import (
    AcquireRequest, AcquiredAsset, CaptureRequest, CaptureResult, CompareRequest,
    DiscoverRequest, ExtractRequest, InspectRequest, Inspection, MapRequest,
    MappedObservations, PublicationIndex, ReadableDocument, ReadableRequest,
    RenderRequest, TableComparison, TableExtract, ValidateRequest, Validation,
    SerializeRequest, ReadRepresentationRequest,
)

_ORIGINAL = DataContract("minfin.publisher_material", 1, DataRole.ORIGINALS)
_INDEX = DataContract("minfin.publication_index", 1, None)
_TABLES = DataContract("minfin.source_cells", 1, DataRole.EXTRACTS)
_OBSERVATIONS = DataContract("minfin.mapped_observations", 1, DataRole.EXTRACTS)
_HTML = DataContract("minfin.publisher_page", 1, DataRole.ORIGINALS)
_HTTP = frozenset({"http"})
_LIMIT = ExecutionBudget(input_bytes=64 * 1024 * 1024, output_bytes=64 * 1024 * 1024,
                         temporary_bytes=256 * 1024 * 1024, cells=500_000)

DISCOVER = OperationDefinition(
    "minfin.discover", 1, "minfin-index-1", DiscoverRequest, PublicationIndex,
    optional_capabilities=_HTTP, limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.DISCOVER,),
        inputs=(InputPort("index", _HTML, "index", required=False),),
        outputs=(OutputPort("index", _INDEX),),
        parameters=("family_id", "max_links"),
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
    "minfin.acquire", 1, "minfin-original-1", AcquireRequest, AcquiredAsset,
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
        inputs=(InputPort("original", _ORIGINAL, "payload", qualifications=frozenset({"source.minfin"}),
                          alternatives=(DataContract("source.payload", 1, DataRole.ORIGINALS),)),),
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
    processing=OperationSemantics((ProcessingStage.VALIDATE,),
        inputs=(InputPort("extract", _TABLES, "extract"),),
        outputs=(OutputPort("validation", DataContract("minfin.structural_validation", 1, None)),),
        summary="Validate source-cell geometry and report structural coverage, never economic correctness."),
)
COMPARE = OperationDefinition(
    "minfin.compare", 1, "minfin-cell-delta-1", CompareRequest, TableComparison,
    processing=OperationSemantics((ProcessingStage.COMPARE,),
        inputs=(InputPort("before", _TABLES, "before"), InputPort("after", _TABLES, "after")),
        outputs=(OutputPort("changes", DataContract("minfin.source_cell_delta", 1, None)),),
        parameters=("max_changes",),
        summary="Report cell-level revisions between source-compatible extracts without claiming semantic equality."),
)
MAP = OperationDefinition(
    "minfin.map_observations", 1, "minfin-reviewed-mapping-1", MapRequest, MappedObservations,
    processing=OperationSemantics((ProcessingStage.EXTRACT,),
        inputs=(InputPort("extract", _TABLES, "extract"),),
        outputs=(OutputPort("observations", _OBSERVATIONS),),
        summary="Map only explicitly reviewed source-cell coordinates to metric, geography, unit and period IDs."),
)
RENDER = OperationDefinition(
    "minfin.render_csv", 1, "minfin-cells-csv-1", RenderRequest, Representation,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("extract", _TABLES, "extract"),),
        outputs=(OutputPort("csv", DataContract("minfin.source_cells.csv", 1, DataRole.PRODUCTS)),),
        summary="Render a deterministic UTF-8 CSV with exact cell coordinates, source digest and formula evidence."),
)
READABLE = OperationDefinition(
    "minfin.readable", 1, "minfin-pdf-text-1", ReadableRequest, ReadableDocument,
    partial_allowed=True, limits=_LIMIT,
    processing=OperationSemantics((ProcessingStage.READABLE,),
        inputs=(InputPort("original", _ORIGINAL, "payload"),),
        outputs=(OutputPort("text", DataContract("minfin.document_text", 1, DataRole.READABLE),
                            outcomes=frozenset({"partial"}), qualifications=frozenset({"text_only"})),),
        parameters=("max_pages",),
        summary="Extract PDF text only, with an explicit incomplete-visual-coverage qualification."),
)

SERIALIZE = OperationDefinition(
    "minfin.serialize", 1, "minfin-extract-json-1", SerializeRequest, Representation,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("extract", _TABLES, "extract"),),
        outputs=(OutputPort("representation", DataContract("minfin.source_cells.json", 1, DataRole.EXTRACTS)),),
        summary="Serialize complete source-cell extracts including blank-sheet geometry to a repeatable JSON representation."),
)
READ_EXTRACT = OperationDefinition(
    "minfin.read_representation", 1, "minfin-extract-json-1", ReadRepresentationRequest, TableExtract,
    processing=OperationSemantics((ProcessingStage.READ_EXTRACT,),
        inputs=(InputPort("representation", DataContract("minfin.source_cells.json", 1, DataRole.EXTRACTS), "representation"),),
        outputs=(OutputPort("extract", _TABLES),),
        summary="Read a retained exact extract representation without re-acquiring source material."),
)