"""Source comparison and readable record metadata."""
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OutputPort, OperationSemantics, ProcessingStage
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.comparison import Comparison
from stratbox.shared.data.representation import Representation
from stratbox.domains.cbr.tables.reporting_forms.contracts import FormFlakes
from stratbox.domains.cbr.tables.reporting_forms.comparison import CompareFormFlakesRequest

_FLAKES=DataContract("cbr.forms.flakes",1,DataRole.EXTRACTS)
COMPARE=OperationDefinition("cbr.forms.compare",1,"cbr-form-source-comparison-1",CompareFormFlakesRequest,Comparison,
    processing=OperationSemantics((ProcessingStage.INSPECT,ProcessingStage.COMPARE),
        inputs=(InputPort("candidate",_FLAKES,path="candidate"),InputPort("baseline",_FLAKES,path="baseline",required=False)),
        outputs=(OutputPort("comparison",DataContract("cbr.forms.comparison",1)),),parameters=("baseline_state",),
        summary="Compare official form issues, material bytes, schemas and decoded source records independently of financial models."))
READABLE=OperationDefinition("cbr.forms.make_readable",1,"cbr-form-readable-1",FormFlakes,Representation,partial_allowed=True,
    processing=OperationSemantics((ProcessingStage.READABLE,),
        inputs=(InputPort("flakes",_FLAKES,outcomes=frozenset({"succeeded","partial"})),),
        outputs=(OutputPort("readable",DataContract("cbr.forms.readable",1,DataRole.READABLE),outcomes=frozenset({"succeeded","partial"})),),
        summary="Render all admitted DBF tokens, schemas and deletion flags for reading; uncovered members remain explicit."))
