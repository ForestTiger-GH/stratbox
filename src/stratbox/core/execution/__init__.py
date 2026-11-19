"""Explicit execution context, typed results and bounded event streams."""

from stratbox.core.execution.contracts import (
    CancellationToken, Clock, Correlation, Diagnostic, EffectDescriptor, EffectReceipt, ExecutionContext,
    ObservabilitySummary, OperationDefinition, OperationFailure, OperationResult, Outcome, SystemClock,
    RuntimeDependency,
)
from stratbox.core.execution.events import EventSink, ExecutionEvent, IncidentSink, InMemorySink, TechnicalIncident
from stratbox.core.execution.runner import Completion, Invocation, run
from stratbox.core.limits import BudgetExceeded, ExecutionBudget
