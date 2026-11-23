"""Portable aligned observation metadata."""

from stratbox.core.execution.semantics import technical_operation, ProcessingFunction
from dataclasses import dataclass
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OutputPort, OperationSemantics, ProcessingStage
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.snapshots import DatasetSnapshot

@dataclass(frozen=True, slots=True)
class SnapshotFormObservationsRequest:
    batch: ObservationBatch
    dataset_id: str
    version_id: str

_BATCH=DataContract('cbr.forms.observations',1,DataRole.INTEGRATED)
_SNAPSHOT=DataContract("dataset.snapshot",1)
SNAPSHOT=technical_operation(OperationDefinition('cbr.forms.observations_snapshot',1,"observation-snapshot-1",SnapshotFormObservationsRequest,DatasetSnapshot,
    processing=OperationSemantics((ProcessingStage.RENDER,),inputs=(InputPort("batch",_BATCH,path="batch"),),
        outputs=(OutputPort("snapshot",_SNAPSHOT),),parameters=("dataset_id","version_id"),
        summary="Encode a complete aligned observation batch with exact types, periods, units and lineage.")), ProcessingFunction.ENCODE)
RESTORE=technical_operation(OperationDefinition('cbr.forms.restore_observations',1,"observation-snapshot-replay-1",DatasetSnapshot,ObservationBatch,
    processing=OperationSemantics((ProcessingStage.READ_EXTRACT,),inputs=(InputPort("snapshot",_SNAPSHOT),),
        outputs=(OutputPort("batch",_BATCH),),summary="Read a retained observation batch without repeating source extraction or semantic mapping.")), ProcessingFunction.REPLAY)
