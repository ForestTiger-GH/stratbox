"""One domain operation surface, with truthful source and stage contracts."""
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort,OutputPort,OperationSemantics,ProcessingStage as P,ProcessingFunction as F
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract,DataRole as R
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.workbooks import (
    WorkbookExtract,WorkbookComparison,WORKBOOK_EXTRACT,WORKBOOK_SNAPSHOT as WORKBOOK_SNAPSHOT_CONTRACT,
)
from stratbox.shared.data.documents import (
    DocumentExtract,DOCUMENT_EXTRACT,DOCUMENT_SNAPSHOT as DOCUMENT_SNAPSHOT_CONTRACT,
)
from stratbox.shared.data.views import ObservationView,OBSERVATION_VIEW,OBSERVATION_VIEW_SNAPSHOT
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.observations import ObservationBatch
from ..publications.contracts import RosstatPublicationIndex,PublicationIndexDelta
from ..publications.archives import RegionalArchiveInventory
from ..tables.contracts import RosstatSourceFlake,Kep2Request
from ..tables.snapshots import FLAKE_CONTRACT,FLAKE_SNAPSHOT_CONTRACT
from ..integration.datasets import RosstatDataset,DATASET_CONTRACT,DATASET_SNAPSHOT_CONTRACT
from ..analytics.indicators import DatasetComparison
from .contracts import (
    SelectRequest,IndexComparisonRequest,ApproveIndexRequest,PhysicalRequest,PayloadRequest,MembersRequest,
    WorkbookRequest,WorkbookComparisonRequest,DocumentRequest,StructureDocumentRequest,MapCellsRequest,
    FlakeRequest,SnapshotRequest,IntegrateRequest,DatasetRequest,DatasetComparisonRequest,GrowthRequest,
    ViewRequest,PrepareViewRequest,RenderViewRequest,
)

_ORIGINAL=DataContract("source.payload",1,R.ORIGINALS)
_INDEX=DataContract("rosstat.publications.index",1)
_SNAPSHOT=DataContract("dataset.snapshot",1)
_REPRESENTATION=DataContract("representation",1)
_BUDGET=ExecutionBudget(input_bytes=256*1024*1024,output_bytes=512*1024*1024,temporary_bytes=512*1024*1024,
    decoded_bytes=512*1024*1024,cells=20_000_000,objects=2_000_000,seconds=600)
_PARTIAL=frozenset({"succeeded","partial"})


def _definition(name,request,value,stage,summary,inputs=(),outputs=(),parameters=(),partial=False):
    function=F.ENCODE if name.endswith("_snapshot") else F.REPLAY if name.split(".")[-1].startswith("read_") else F.PROCESS
    stages=() if function in {F.ENCODE,F.REPLAY} else (stage,)
    return OperationDefinition("rosstat."+name,1,"rosstat-"+name.replace(".","-")+"-1",request,value,
        partial_allowed=partial,limits=_BUDGET,processing=OperationSemantics(stages,inputs,outputs,parameters,summary,function=function))


def _input(name,contract):
    return InputPort(name,contract,path=name,outcomes=_PARTIAL)


def _output(name,contract,partial=False):
    return OutputPort(name,contract,outcomes=_PARTIAL if partial else frozenset({"succeeded"}))

def _snapshot_outputs(contract):
    return (_output("snapshot",contract),_output("storage_snapshot",_SNAPSHOT))


SELECT=_definition("publications.select",SelectRequest,tuple,P.INSPECT,"Select explicit publisher issues and assets from a qualified index.",
    (_input("index",_INDEX),),(_output("assets",DataContract("rosstat.publications.assets",1)),),("issue_ids","asset_roles","policy","max_assets"))
PLAN_UPDATES=_definition("publications.plan_updates",IndexComparisonRequest,PublicationIndexDelta,P.COMPARE,"Compare scoped publication inventories without asserting absence from unverified pages.",
    (_input("before",_INDEX),_input("after",_INDEX)),(_output("delta",DataContract("rosstat.publications.delta",1)),))
APPROVE_INDEX=_definition("publications.review_index",ApproveIndexRequest,RosstatPublicationIndex,P.VALIDATE,"Apply explicit reviewed scope evidence to one exact publisher index.",
    (_input("index",_INDEX),),(_output("index",_INDEX),),("evidence",))
EXTRACT_WORKBOOK=_definition("tables.extract_workbook",PhysicalRequest,WorkbookExtract,P.EXTRACT,"Capture full workbook physical cells separately from economic selection.",
    (_input("payload",_ORIGINAL),),(_output("workbook",WORKBOOK_EXTRACT),),("series_id","issue_id","asset_id","container_identity","member"))
EXTRACT_DOCUMENT=_definition("tables.extract_document",PhysicalRequest,DocumentExtract,P.EXTRACT,"Capture ordered document text and explicit structured tables without inferring PDF cells.",
    (_input("payload",_ORIGINAL),),(_output("document",DOCUMENT_EXTRACT,True),),("series_id","issue_id","asset_id","container_identity","member"),True)
INSPECT_ARCHIVE=_definition("publications.inspect_archive",PayloadRequest,RegionalArchiveInventory,P.INSPECT,"Inspect the actual regional archive membership under archive safety limits.",
    (_input("payload",_ORIGINAL),),(_output("inventory",DataContract("rosstat.regional_archive.inventory",1)),),("limits",))
EXTRACT_MEMBERS=_definition("publications.extract_members",MembersRequest,tuple,P.ACQUIRE,"Read explicitly selected archive members and retain container/member evidence.",
    (_input("payload",_ORIGINAL),_input("inventory",DataContract("rosstat.regional_archive.inventory",1))),
    (_output("members",DataContract("rosstat.regional_archive.members",1,R.ORIGINALS)),),("names","limits"))
WORKBOOK_SNAPSHOT=_definition("tables.workbook_snapshot",WorkbookRequest,DatasetSnapshot,P.PRESERVE,"Encode every physical workbook field as a portable snapshot.",
    (_input("workbook",WORKBOOK_EXTRACT),),_snapshot_outputs(WORKBOOK_SNAPSHOT_CONTRACT))
READ_WORKBOOK=_definition("tables.read_workbook",SnapshotRequest,WorkbookExtract,P.READ_EXTRACT,"Restore physical workbook evidence from a complete stored snapshot.",
    (_input("snapshot",WORKBOOK_SNAPSHOT_CONTRACT),),(_output("workbook",WORKBOOK_EXTRACT),))
READABLE_WORKBOOK=_definition("tables.readable_workbook",WorkbookRequest,Representation,P.READABLE,"Render full physical workbook evidence as structured readable records.",
    (_input("workbook",WORKBOOK_EXTRACT),),(_output("representation",_REPRESENTATION),))
COMPARE_WORKBOOKS=_definition("tables.compare_workbooks",WorkbookComparisonRequest,WorkbookComparison,P.COMPARE,"Compare exact physical workbook cells and layout before economic interpretation.",
    (_input("before",WORKBOOK_EXTRACT),_input("after",WORKBOOK_EXTRACT)),(_output("changes",DataContract("workbook.changes",1)),))
DOCUMENT_SNAPSHOT=_definition("tables.document_snapshot",DocumentRequest,DatasetSnapshot,P.PRESERVE,"Encode all document blocks and source qualifications for independent replay.",
    (_input("document",DOCUMENT_EXTRACT),),_snapshot_outputs(DOCUMENT_SNAPSHOT_CONTRACT))
READ_DOCUMENT=_definition("tables.read_document",SnapshotRequest,DocumentExtract,P.READ_EXTRACT,"Restore ordered physical document evidence from a stored snapshot.",
    (_input("snapshot",DOCUMENT_SNAPSHOT_CONTRACT),),(_output("document",DOCUMENT_EXTRACT,True),),partial=True)
READABLE_DOCUMENT=_definition("tables.readable_document",DocumentRequest,Representation,P.READABLE,"Render all extracted document blocks and qualified extraction errors.",
    (_input("document",DOCUMENT_EXTRACT),),(_output("representation",_REPRESENTATION),))
STRUCTURE_DOCUMENT=_definition("tables.structure_document",StructureDocumentRequest,DocumentExtract,P.EXTRACT,"Apply an exact-original reviewed text layout to document table regions, retaining original blocks.",
    (_input("document",DOCUMENT_EXTRACT),),(_output("document",DOCUMENT_EXTRACT,True),),("layout",),True)
KEP2=_definition("tables.extract_kep2",Kep2Request,RosstatSourceFlake,P.EXTRACT,"Extract the reviewed eleven-indicator KEP2 selection with all periods, footnotes and source row decisions.",
    (_input("workbook",WORKBOOK_EXTRACT),),(_output("flake",FLAKE_CONTRACT,True),),("duplicate_year_policy","required_indicators","title_aliases","unit_overrides"),True)
MAP_CELLS=_definition("tables.map_reviewed_cells",MapCellsRequest,RosstatSourceFlake,P.EXTRACT,"Build a source flake through an exact-original reviewed coordinate profile and explicit statistical semantics.",
    (InputPort("physical",WORKBOOK_EXTRACT,path="physical",outcomes=_PARTIAL,alternatives=(DOCUMENT_EXTRACT,)),),
    (_output("flake",FLAKE_CONTRACT,True),),("profile",),True)
FLAKE_SNAPSHOT=_definition("tables.flake_snapshot",FlakeRequest,DatasetSnapshot,P.PRESERVE,"Encode complete selected source-flake values, units, notes and row decisions.",
    (_input("flake",FLAKE_CONTRACT),),_snapshot_outputs(FLAKE_SNAPSHOT_CONTRACT))
READ_FLAKE=_definition("tables.read_flake",SnapshotRequest,RosstatSourceFlake,P.READ_EXTRACT,"Replay a complete selected source flake without the original reader.",
    (_input("snapshot",FLAKE_SNAPSHOT_CONTRACT),),(_output("flake",FLAKE_CONTRACT,True),),partial=True)
READABLE_FLAKE=_definition("tables.readable_flake",FlakeRequest,Representation,P.READABLE,"Render selected source values with actual periods, units and source coordinates.",
    (_input("flake",FLAKE_CONTRACT),),(_output("representation",_REPRESENTATION),))
INTEGRATE=_definition("integration.integrate",IntegrateRequest,RosstatDataset,P.INTEGRATE,"Integrate explicitly resolved source-flake observations; reject collisions and unresolved semantics.",
    (_input("flakes",FLAKE_CONTRACT),),(_output("dataset",DATASET_CONTRACT),),("dataset_id","release_id"))
DATASET_SNAPSHOT=_definition("integration.dataset_snapshot",DatasetRequest,DatasetSnapshot,P.PRESERVE,"Encode integrated observations and their source selection context for dataset storage.",
    (_input("dataset",DATASET_CONTRACT),),_snapshot_outputs(DATASET_SNAPSHOT_CONTRACT))
READ_DATASET=_definition("integration.read_dataset",SnapshotRequest,RosstatDataset,P.READ_EXTRACT,"Replay integrated data and source context independently of extraction.",
    (_input("snapshot",DATASET_SNAPSHOT_CONTRACT),),(_output("dataset",DATASET_CONTRACT),))
COMPARE_DATASETS=_definition("analytics.compare_datasets",DatasetComparisonRequest,DatasetComparison,P.COMPARE,"Compare semantic observation revisions under explicit source scopes.",
    (_input("before",DATASET_CONTRACT),_input("after",DATASET_CONTRACT)),(_output("comparison",DataContract("rosstat.dataset.comparison",1)),))
DERIVE_GROWTH=_definition("analytics.derive_index_growth",GrowthRequest,ObservationBatch,P.CALCULATE,"Explicitly derive percentage changes as published percent-of-baseline indices minus 100.",
    (_input("dataset",DATASET_CONTRACT),),(_output("observations",DataContract("observations.batch",1,R.INTEGRATED)),),("release_id",))
PREPARE_VIEW=_definition("products.prepare_view",PrepareViewRequest,ObservationView,P.VIEW,"Prepare a portable observation view from an integrated Rosstat dataset.",
    (_input("dataset",DATASET_CONTRACT),),(_output("view",OBSERVATION_VIEW),),("view_id","metric_ids"))
KEP2_MONTHLY_VIEW=_definition("products.prepare_kep2_monthly",DatasetRequest,ObservationView,P.VIEW,"Select monthly KEP2 observations with explicit next-period display dates and retained indices.",
    (_input("dataset",DATASET_CONTRACT),),(_output("view",OBSERVATION_VIEW),))
VIEW_SNAPSHOT=_definition("products.view_snapshot",ViewRequest,DatasetSnapshot,P.PRESERVE,"Encode a prepared view with all evidence for independent rendering later.",
    (_input("view",OBSERVATION_VIEW),),_snapshot_outputs(OBSERVATION_VIEW_SNAPSHOT))
READ_VIEW=_definition("products.read_view",SnapshotRequest,ObservationView,P.READ_EXTRACT,"Restore a prepared view from its complete stored snapshot.",
    (_input("snapshot",OBSERVATION_VIEW_SNAPSHOT),),(_output("view",OBSERVATION_VIEW),))
RENDER_VIEW=_definition("products.render_view",RenderViewRequest,Representation,P.RENDER,"Render prepared observations as CSV, JSON or JSONL with exact values and evidence.",
    (_input("view",OBSERVATION_VIEW),),(_output("representation",_REPRESENTATION),),("format",))
RENDER_KEP2_XLSX=_definition("products.render_kep2_xlsx",ViewRequest,Representation,P.RENDER,"Render the monthly eleven-indicator workbook and a separate exact-value evidence sheet.",
    (_input("view",OBSERVATION_VIEW),),(_output("representation",_REPRESENTATION),))

from .contracts import FlakeComparisonRequest
from ..tables.comparison import FlakeComparison,FlakeValidation
VALIDATE_FLAKE=_definition("tables.validate_flake",FlakeRequest,FlakeValidation,P.VALIDATE,"Validate selected source values, explicit semantic admission and remaining diagnostics before integration.",
    (_input("flake",FLAKE_CONTRACT),),(_output("validation",DataContract("rosstat.flake.validation",1),True),),partial=True)
COMPARE_FLAKES=_definition("tables.compare_flakes",FlakeComparisonRequest,FlakeComparison,P.COMPARE,"Compare selected source facts with coordinate movement distinguished from values and profile scope changes.",
    (_input("before",FLAKE_CONTRACT),_input("after",FLAKE_CONTRACT)),(_output("comparison",DataContract("rosstat.flake.comparison",1)),))
