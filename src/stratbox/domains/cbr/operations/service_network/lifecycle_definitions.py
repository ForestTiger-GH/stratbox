"""Source history, reading, semantic alignment, calculation and products."""

from stratbox.core.execution.semantics import technical_operation, ProcessingFunction
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OutputPort, OperationSemantics, ProcessingStage
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.domains.cbr.tables.service_network.history import OfficeHistoryRequest
from stratbox.domains.cbr.tables.service_network.readable import ReadableOfficesRequest
from stratbox.domains.cbr.integration.service_network.contracts import AlignOfficesRequest
from stratbox.domains.cbr.analytics.service_network.changes import OfficeChangesRequest, OfficeChanges
from stratbox.domains.cbr.products.service_network.views import OfficeViewRequest, RenderOfficeViewRequest

_BATCH=DataContract("cbr.service_network.observations",1,DataRole.INTEGRATED)
_SNAPSHOT=DataContract("dataset.snapshot",1)
_VIEW=DataContract("cbr.service_network.view",1,DataRole.PRODUCTS)
_RELEASE=DataContract("cbr.offices.release",1,DataRole.EXTRACTS)
READABLE=OperationDefinition("cbr.service_network.make_readable",1,"cbr-office-readable-1",ReadableOfficesRequest,Representation,
    processing=OperationSemantics((ProcessingStage.READABLE,),
        inputs=(InputPort("source",DataContract("material.payload",1),path="payload"),),
        outputs=(OutputPort("readable",DataContract("cbr.service_network.readable",1,DataRole.READABLE)),),
        parameters=("family",),summary="Preserve native HTML or transcribe all worksheet cell tokens with formula evidence."))
HISTORY=OperationDefinition("cbr.service_network.build_history",1,"cbr-office-history-1",OfficeHistoryRequest,DatasetSnapshot,
    processing=OperationSemantics((ProcessingStage.EXTRACT,),
        inputs=(InputPort("releases",DataContract("cbr.service_network.releases",1,DataRole.EXTRACTS),path="releases"),),
        outputs=(OutputPort("snapshot",_SNAPSHOT),),parameters=("dataset_id","version_id"),
        summary="Pin selected office captures or source issues without treating history packing as alignment."))
RESTORE_HISTORY=technical_operation(OperationDefinition("cbr.service_network.restore_history",1,"cbr-office-history-replay-1",DatasetSnapshot,tuple,
    processing=OperationSemantics((ProcessingStage.READ_EXTRACT,),inputs=(InputPort("snapshot",_SNAPSHOT),),
        outputs=(OutputPort("releases",DataContract("cbr.service_network.releases",1,DataRole.EXTRACTS)),),
        summary="Restore complete source releases and their period, formula and selection evidence.")), ProcessingFunction.REPLAY)
ALIGN=OperationDefinition("cbr.service_network.align",1,"cbr-office-observations-1",AlignOfficesRequest,ObservationBatch,
    processing=OperationSemantics((ProcessingStage.INTEGRATE,),
        inputs=(InputPort("release",_RELEASE,path="release",alternatives=(DataContract("cbr.offices_reg.release",1,DataRole.EXTRACTS),)),),
        outputs=(OutputPort("batch",_BATCH),),parameters=("dataset_id","version_id","subjects","regions","metrics","require_geography"),
        summary="Apply explicit bank, geography and metric mappings while preserving original identities and unresolved geography."))
CHANGES=OperationDefinition("cbr.service_network.calculate_changes",1,"cbr-office-count-changes-1",OfficeChangesRequest,OfficeChanges,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        inputs=(InputPort("baseline",_BATCH,path="baseline"),InputPort("candidate",_BATCH,path="candidate")),
        outputs=(OutputPort("changes",DataContract("cbr.service_network.changes",1)),OutputPort("batch",_BATCH,path="batch")),
        parameters=("dataset_id","version_id"),summary="Calculate count differences on comparable cells and report unmatched coverage; no individual closure inference."))
VIEW=OperationDefinition("cbr.service_network.build_view",1,"cbr-office-view-1",OfficeViewRequest,DatasetSnapshot,
    processing=OperationSemantics((ProcessingStage.VIEW,),inputs=(InputPort("batch",_BATCH,path="batch"),),
        outputs=(OutputPort("view",_VIEW),OutputPort("snapshot",_SNAPSHOT)),parameters=("dataset_id","version_id","subjects","metrics"),
        summary="Prepare selected office counts and qualifications as a reusable typed view."))
RENDER=OperationDefinition("cbr.service_network.render",1,"cbr-office-render-1",RenderOfficeViewRequest,Representation,
    processing=OperationSemantics((ProcessingStage.RENDER,),inputs=(InputPort("view",_VIEW,path="view",alternatives=(_SNAPSHOT,)),),
        outputs=(OutputPort("product",DataContract("cbr.service_network.product",1,DataRole.PRODUCTS)),),parameters=("format",),
        summary="Render a retained prepared view to CSV or XLSX without source parsing."))
