"""Independent file lifecycle contracts for the shared operation catalog."""
from __future__ import annotations

from stratbox.core.execution import InputPort, OperationDefinition, OperationSemantics, OutputPort, ProcessingStage
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from ..publications.contracts import (
    AcquiredReport, AcquireRequest, AssessMaterialRequest, CaptureRequest, Catalog,
    DiscoveryRequest, InspectionRequest, Inventory, MaterialAssessment, PreparedFile,
    PrepareFileRequest, SelectionRequest, SourceIndex, UpdatePlan, UpdateRequest,
)

_STORE = frozenset({"filestore"})
_MATERIAL_LIMIT = 512 * 1024 * 1024
_FILE_LIMITS = ExecutionBudget(input_bytes=_MATERIAL_LIMIT, output_bytes=_MATERIAL_LIMIT)
_ACQUIRE_LIMITS = ExecutionBudget(input_bytes=3 * _MATERIAL_LIMIT, output_bytes=_MATERIAL_LIMIT)
_INDEX = DataContract("frg.source_index", 1, None)
_INVENTORY = DataContract("frg.inventory", 1, None)
_SELECTIONS = DataContract("frg.selections", 1, None)
_CATALOG = DataContract("frg.catalog", 2, None)
_REPORT = DataContract("frg.report", 1, DataRole.ORIGINALS)
_PAYLOAD = DataContract("source.payload", 1, DataRole.ORIGINALS)

DISCOVER = OperationDefinition(
    "frg.discover", 1, "frg.directory-profile.v1", DiscoveryRequest, SourceIndex,
    required_capabilities=_STORE,
    processing=OperationSemantics((ProcessingStage.DISCOVER,),
        outputs=(OutputPort("index", _INDEX),), parameters=("directory", "recursive", "family_ids"),
        summary="Enumerate bounded caller-provided storage through the registered discovery profile."),
)
INSPECT = OperationDefinition(
    "frg.inspect", 1, "frg.identification-profile.v1", InspectionRequest, Inventory,
    processing=OperationSemantics((ProcessingStage.INSPECT,),
        inputs=(InputPort("index", _INDEX, "index"),), outputs=(OutputPort("inventory", _INVENTORY),),
        summary="Identify report sources and periods using registered naming evidence without opening files."),
)
SELECT = OperationDefinition(
    "frg.select", 1, "frg.selection-profile.v1", SelectionRequest, tuple,
    processing=OperationSemantics((ProcessingStage.INSPECT,),
        inputs=(InputPort("inventory", _INVENTORY, "inventory"),), outputs=(OutputPort("selections", _SELECTIONS),),
        parameters=("selected_sources",),
        summary="Select the latest report period per source and expose unresolved competing candidates."),
)
SCAN = OperationDefinition(
    "frg.scan", 1, "frg.catalog-profile.v2", DiscoveryRequest, Catalog, required_capabilities=_STORE,
    processing=OperationSemantics((ProcessingStage.DISCOVER, ProcessingStage.INSPECT),
        outputs=(OutputPort("catalog", _CATALOG), OutputPort("index", _INDEX, "inventory.index"),
                 OutputPort("inventory", _INVENTORY, "inventory"), OutputPort("selections", _SELECTIONS, "selections")),
        parameters=("directory", "recursive", "family_ids"), composition=True,
        summary="Compose discovery, identification and period selection into a read-only report catalog."),
)
ACQUIRE = OperationDefinition(
    "frg.acquire", 1, "frg.file-acquisition-profile.v1", AcquireRequest, AcquiredReport,
    required_capabilities=_STORE, limits=_ACQUIRE_LIMITS,
    processing=OperationSemantics((ProcessingStage.ACQUIRE,),
        inputs=(InputPort("asset", DataContract("frg.asset", 1, None), "asset"),),
        outputs=(OutputPort("report", _REPORT), OutputPort("payload", _PAYLOAD, "payload")),
        parameters=("expected_identity", "max_bytes"),
        summary="Acquire one recognized file and verify its observed revision and exact bytes around the read."),
)
CAPTURE = OperationDefinition(
    "frg.capture", 1, "frg.supplied-material-profile.v1", CaptureRequest, AcquiredReport, limits=_FILE_LIMITS,
    processing=OperationSemantics((ProcessingStage.ACQUIRE,),
        inputs=(InputPort("payload", _PAYLOAD, "payload"),),
        outputs=(OutputPort("report", _REPORT), OutputPort("payload", _PAYLOAD, "payload")),
        parameters=("source_id", "period", "format"),
        summary="Admit exact bytes supplied by a specialized method with an explicit logical source and period."),
)
PREPARE_FILE = OperationDefinition(
    "frg.prepare_file", 1, "frg.canonical-name-profile.v1", PrepareFileRequest, PreparedFile, limits=_FILE_LIMITS,
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("report", _REPORT, "report"),),
        outputs=(OutputPort("file", DataContract("frg.prepared_file", 1, DataRole.ORIGINALS)),
                 OutputPort("payload", _PAYLOAD, "payload")),
        summary="Prepare the registered canonical filename while preserving the report's exact original bytes."),
)
PLAN_UPDATES = OperationDefinition(
    "frg.plan_updates", 1, "frg.metadata-update-profile.v1", UpdateRequest, UpdatePlan,
    processing=OperationSemantics((ProcessingStage.INSPECT,),
        inputs=(InputPort("catalog", _CATALOG, "catalog"),),
        outputs=(OutputPort("plan", DataContract("frg.update_plan", 1, None)),),
        parameters=("checkpoints", "force_refresh"),
        summary="Plan file acquisition using caller checkpoints while keeping metadata observations distinct from byte identity."),
)
ASSESS_MATERIAL = OperationDefinition(
    "frg.assess_material", 1, "frg.material-comparison.v1", AssessMaterialRequest, MaterialAssessment,
    processing=OperationSemantics((ProcessingStage.COMPARE,),
        inputs=(InputPort("report", _REPORT, "report"),
                InputPort("checkpoint", DataContract("frg.checkpoint", 1, None), "checkpoint", required=False)),
        outputs=(OutputPort("assessment", DataContract("frg.material_assessment", 1, None)),),
        summary="Compare confirmed original identities and report periods without interpreting workbook contents."),
)

__all__ = ("DISCOVER", "INSPECT", "SELECT", "SCAN", "ACQUIRE", "CAPTURE", "PREPARE_FILE",
           "PLAN_UPDATES", "ASSESS_MATERIAL")
