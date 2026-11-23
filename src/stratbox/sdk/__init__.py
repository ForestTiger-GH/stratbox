"""The portable Strategy Box entry point for discovery and execution."""

from .client import StrategyBox
from stratbox.core.execution.session import ExecutionSettings
from stratbox.composition import (
    CascadeDefinition, CollectSpec, CollectStep, Condition, InputRef, MapStep,
    OperationStep, PlanOutputRef, RetryPolicy, ScenarioDefinition, ScenarioStep,
    SourceSelection,
)

__all__ = (
    "StrategyBox", "ExecutionSettings", "CascadeDefinition", "CollectSpec",
    "CollectStep", "Condition", "InputRef", "MapStep", "OperationStep",
    "PlanOutputRef", "RetryPolicy", "ScenarioDefinition", "ScenarioStep",
    "SourceSelection",
)
