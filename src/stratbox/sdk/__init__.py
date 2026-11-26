"""Portable discovery, explicit authoring and one invocation facade."""
from .client import StrategyBox, CatalogPage
from stratbox.capabilities.model import (
    CommandDefinition, OperationDefinition, ScenarioDefinition, CascadeDefinition,
    GraphBody, Call, InputRef, OutputRef, ParameterRef, TargetRef, MapCall, RepeatUntil,
)

__all__ = (
    'StrategyBox', 'CatalogPage', 'CommandDefinition', 'OperationDefinition',
    'ScenarioDefinition', 'CascadeDefinition', 'GraphBody', 'Call', 'InputRef',
    'OutputRef', 'ParameterRef', 'TargetRef', 'MapCall', 'RepeatUntil',
)
