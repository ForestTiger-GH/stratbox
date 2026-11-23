"""Typed admission and calculation boundaries for retained semantic observations."""
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OutputPort, OperationSemantics, ProcessingStage
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.domains.cbr.analytics.reporting_forms.contracts import (
    PrepareFormModelInputsRequest, FormModelInputs, CalculateFormRequest, FormData,
)
from .definitions import _TABLES

_BATCH = DataContract("cbr.forms.observations", 1, DataRole.INTEGRATED)
_INPUTS = DataContract("cbr.forms.model_inputs", 1, DataRole.INTEGRATED)
PREPARE = OperationDefinition("cbr.forms.prepare_model_inputs", 1, "cbr-forms-model-input-admission-1",
    PrepareFormModelInputsRequest, FormModelInputs, limits=_TABLES,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        inputs=(InputPort("batch", _BATCH, path="batch"),), outputs=(OutputPort("inputs", _INPUTS),),
        summary="Admit reviewed metric, source subject, unit, period and formula axes before financial-model evaluation."))
CALCULATE = OperationDefinition("cbr.forms.calculate", 1, "cbr-forms-prepared-model-1",
    CalculateFormRequest, FormData, limits=_TABLES,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        inputs=(InputPort("inputs", _INPUTS, path="inputs"),),
        outputs=(OutputPort("data", DataContract("cbr.forms.data", 1, DataRole.INTEGRATED)),),
        parameters=("banks", "model", "selection_profile"),
        summary="Evaluate a financial model only from admitted semantic model inputs, retaining canonical subjects and periods."))
