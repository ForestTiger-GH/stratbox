"""Explicit execution context, typed results and bounded event streams."""

from .contracts import (
    CancellationToken, Clock, Correlation, Diagnostic, EffectDescriptor, EffectReceipt, ExecutionContext,
    ObservabilitySummary, OperationDefinition, OperationFailure, OperationResult, Outcome, SystemClock,
)
from .events import EventSink, ExecutionEvent, InMemorySink
from .runner import Completion, Invocation, run
from stratbox.base.limits import BudgetExceeded, ExecutionBudget
