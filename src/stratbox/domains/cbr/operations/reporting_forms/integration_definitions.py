"""Lightweight semantic alignment metadata."""
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OutputPort, OperationSemantics, ProcessingStage
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.domains.cbr.integration.reporting_forms.contracts import AlignFormRequest

ALIGN = OperationDefinition("cbr.forms.align", 1, "cbr-forms-observation-alignment-1", AlignFormRequest, ObservationBatch,
    processing=OperationSemantics((ProcessingStage.INTEGRATE,),
        inputs=(InputPort("snapshots", DataContract("cbr.forms.snapshots", 1, DataRole.EXTRACTS), path="snapshots"),),
        outputs=(OutputPort("batch", DataContract("cbr.forms.observations", 1, DataRole.INTEGRATED)),),
        parameters=("dataset_id", "version_id", "periods", "subjects"),
        summary="Align reviewed source fields to versioned observations with distinct bank and banking-group identities and explicit flow periods."))
