"""Explicit execution context, typed results and bounded event streams."""

from stratbox.core.execution.contracts import (
    CancellationToken,
    Clock,
    Correlation,
    Diagnostic,
    EffectDescriptor,
    EffectKey,
    EffectReceipt,
    ExecutionContext,
    ObservabilitySummary,
    OperationDefinition,
    OperationFailure,
    OperationResult,
    Outcome,
    SystemClock,
    RuntimeDependency,
)
from stratbox.core.execution.events import (
    EventSink,
    ExecutionEvent,
    IncidentSink,
    InMemorySink,
    TechnicalIncident,
)
from stratbox.core.execution.admission import AdmissionPhase, ResultAdmission
from stratbox.core.execution.runner import Completion, Invocation, run
from stratbox.core.limits import (
    BudgetError,
    BudgetClockError,
    BudgetExceeded,
    ExecutionBudget,
)
from stratbox.shared.data.operations import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
    OperationKey,
    OperationConnection,
    StageCoverage,
    StageDeclaration,
)
from stratbox.core.execution.handoff import (
    BoundRequest,
    HandoffError,
    ProjectedOutput,
    PreparedInput,
    ResultReference,
    ResultResolver,
    bind_request,
    project_output,
    reference_output,
    resolve_output,
    prepare_input,
    artifact_input,
    collect_inputs,
    adapt_input,
)
from stratbox.core.execution.calls import (
    OperationCall,
    SourceBinding,
    bind_operation,
    bind_source,
)
from stratbox.core.execution.value_context import ValueContext, value_context
