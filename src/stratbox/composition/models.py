"""Portable workflow definitions and resolved execution plans.

Definitions describe work; plans identify concrete calls. Neither owns workers,
network clients, result mutation, nor delivery state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping
import re

from stratbox.shared.data.processing import DataContract


class CompositionError(ValueError):
    @property
    def code(self):
        return self.args[0]


def _name(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", value):
        raise CompositionError("composition.invalid_name")


def _mapping(value):
    if not isinstance(value, Mapping) or any(not isinstance(k, str) for k in value):
        raise CompositionError("composition.invalid_mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True)
class PlanOutputRef:
    task: str
    port: str = "value"
    item: str | None = None

    def __post_init__(self):
        if not isinstance(self.task, str) or not self.task or any(part in {"", ".", ".."} for part in self.task.split("/")):
            raise CompositionError("composition.invalid_reference")
        _name(self.port)
        if self.item is not None and not isinstance(self.item, str):
            raise CompositionError("composition.invalid_item")


@dataclass(frozen=True, slots=True)
class InputRef:
    name: str

    def __post_init__(self):
        _name(self.name)


@dataclass(frozen=True, slots=True)
class SourceSelection:
    series_id: str
    format: str | None = None
    group_id: str | None = None
    edition: str | None = None


@dataclass(frozen=True, slots=True)
class Condition:
    """Select by task state, or equality at a declared output field path."""
    task: str
    statuses: tuple[str, ...] = ()
    port: str | None = None
    field: str = ""
    equals: object = True

    def __post_init__(self):
        if bool(self.statuses) == (self.port is not None):
            raise CompositionError("composition.condition_mode_required")
        if self.statuses and (not isinstance(self.statuses, tuple) or not set(self.statuses) <= {
            "succeeded", "partial", "failed", "cancelled", "unknown", "blocked", "skipped"
        }):
            raise CompositionError("composition.invalid_condition_state")
        if self.port is not None:
            _name(self.port)
        if not isinstance(self.field, str) or any(not p.isidentifier() or p.startswith("_") for p in self.field.split(".") if self.field):
            raise CompositionError("composition.invalid_condition_field")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 1
    delay: float = 0.0
    retry_codes: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.max_attempts) is not int or self.max_attempts < 1 or not isinstance(self.delay, (float, int)) or self.delay < 0:
            raise CompositionError("composition.invalid_retry")
        if not isinstance(self.retry_codes, tuple) or any(not isinstance(x, str) for x in self.retry_codes):
            raise CompositionError("composition.invalid_retry")


@dataclass(frozen=True, slots=True)
class OperationStep:
    step_id: str
    operation_id: str
    inputs: Mapping[str, object] = field(default_factory=dict)
    parameters: Mapping[str, object] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    source: SourceSelection | None = None
    condition: Condition | None = None
    required: bool = True
    share_key: str | None = None
    resources: Mapping[str, int] = field(default_factory=dict)
    retry: RetryPolicy = field(default_factory=RetryPolicy)

    def __post_init__(self):
        _name(self.step_id)
        _name(self.operation_id)
        for name in ("inputs", "parameters", "resources"):
            object.__setattr__(self, name, _mapping(getattr(self, name)))
        if not isinstance(self.depends_on, tuple) or any(not isinstance(v, str) for v in self.depends_on):
            raise CompositionError("composition.invalid_dependencies")
        if type(self.required) is not bool or any(type(v) is not int or v < 1 for v in self.resources.values()):
            raise CompositionError("composition.invalid_resources")
        if self.source is not None and not isinstance(self.source, SourceSelection):
            raise CompositionError("composition.invalid_source")
        if self.condition is not None and not isinstance(self.condition, Condition):
            raise CompositionError("composition.invalid_condition")
        if not isinstance(self.retry, RetryPolicy):
            raise CompositionError("composition.invalid_retry")
        if self.share_key is not None:
            _name(self.share_key)


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    scenario_id: str
    steps: tuple[object, ...]
    outputs: Mapping[str, object] = field(default_factory=dict)
    inputs: Mapping[str, DataContract | None] = field(default_factory=dict)
    policy: str = "continue"
    expenditure: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self):
        _name(self.scenario_id)
        if not isinstance(self.steps, tuple) or any(not isinstance(s, (OperationStep, ScenarioStep, MapStep, CollectStep)) for s in self.steps):
            raise CompositionError("composition.invalid_steps")
        if len({s.step_id for s in self.steps}) != len(self.steps):
            raise CompositionError("composition.duplicate_step")
        for name in ("inputs", "outputs"):
            object.__setattr__(self, name, _mapping(getattr(self, name)))
        if any(v is not None and not isinstance(v, DataContract) for v in self.inputs.values()):
            raise CompositionError("composition.invalid_input_contract")
        if self.policy not in {"continue", "fail_fast"}:
            raise CompositionError("composition.invalid_policy")
        object.__setattr__(self, "expenditure", _mapping(self.expenditure))
        if any(type(value) is not int or value < 0 for value in self.expenditure.values()):
            raise CompositionError("composition.invalid_expenditure")


@dataclass(frozen=True, slots=True)
class ScenarioStep:
    step_id: str
    scenario: ScenarioDefinition
    inputs: Mapping[str, object] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    required: bool = True

    def __post_init__(self):
        _name(self.step_id)
        if not isinstance(self.scenario, ScenarioDefinition):
            raise CompositionError("composition.invalid_scenario")
        object.__setattr__(self, "inputs", _mapping(self.inputs))


@dataclass(frozen=True, slots=True)
class CascadeDefinition:
    cascade_id: str
    scenarios: tuple[ScenarioStep, ...]
    outputs: Mapping[str, object] = field(default_factory=dict)
    inputs: Mapping[str, DataContract | None] = field(default_factory=dict)
    policy: str = "continue"
    expenditure: Mapping[str, int] = field(default_factory=dict)

    def as_scenario(self):
        return ScenarioDefinition(self.cascade_id, self.scenarios, self.outputs, self.inputs, self.policy, self.expenditure)


@dataclass(frozen=True, slots=True)
class MapStep:
    step_id: str
    body: ScenarioDefinition
    items: object
    item_input: str = "item"
    key_field: str | None = None
    window: int | None = None
    inputs: Mapping[str, object] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    required: bool = True
    allow_partial: bool = False

    def __post_init__(self):
        _name(self.step_id)
        _name(self.item_input)
        if not isinstance(self.body, ScenarioDefinition) or self.item_input not in self.body.inputs:
            raise CompositionError("composition.map_item_input_required")
        if self.window is not None and (type(self.window) is not int or self.window < 1):
            raise CompositionError("composition.invalid_window")
        if self.key_field is not None and (not isinstance(self.key_field, str) or not self.key_field.isidentifier() or self.key_field.startswith("_")):
            raise CompositionError("composition.invalid_key_field")
        object.__setattr__(self, "inputs", _mapping(self.inputs))


@dataclass(frozen=True, slots=True)
class CollectSpec:
    inputs: tuple[PlanOutputRef, ...]
    contract: DataContract
    element_contract: DataContract
    allow_partial: bool = False
    allow_empty: bool = False

    def __post_init__(self):
        if not isinstance(self.inputs, tuple) or any(not isinstance(v, PlanOutputRef) for v in self.inputs):
            raise CompositionError("composition.invalid_collection")
        if not isinstance(self.contract, DataContract) or not isinstance(self.element_contract, DataContract):
            raise CompositionError("composition.invalid_collection_contract")
        if not self.inputs and not self.allow_empty:
            raise CompositionError("composition.collection_empty")
        if len(set(self.inputs)) != len(self.inputs):
            raise CompositionError("composition.collection_duplicate")


@dataclass(frozen=True, slots=True)
class CollectStep:
    step_id: str
    collect: CollectSpec
    depends_on: tuple[str, ...] = ()
    required: bool = True

    def __post_init__(self):
        _name(self.step_id)
        if not isinstance(self.collect, CollectSpec):
            raise CompositionError("composition.invalid_collection")


@dataclass(frozen=True, slots=True)
class CompiledMap:
    body: ScenarioDefinition
    items: object
    item_input: str = "item"
    key_field: str | None = None
    window: int | None = None
    inputs: Mapping[str, object] = field(default_factory=dict)
    allow_partial: bool = False
    body_fingerprint: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "inputs", _mapping(self.inputs))


@dataclass(frozen=True, slots=True)
class PlanScope:
    scope_id: str
    definition_id: str
    parent_id: str | None = None
    expenditure: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "expenditure", _mapping(self.expenditure))
        if any(type(value) is not int or value < 0 for value in self.expenditure.values()):
            raise CompositionError("composition.invalid_expenditure")


@dataclass(frozen=True, slots=True)
class CompiledTask:
    task_id: str
    operation_id: str | None
    inputs: Mapping[str, object]
    parameters: Mapping[str, object]
    dependencies: tuple[str, ...]
    scope_id: str
    required: bool = True
    condition: Condition | None = None
    source: SourceSelection | None = None
    map: CompiledMap | None = None
    collect: CollectSpec | None = None
    resources: Mapping[str, int] = field(default_factory=dict)
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    aliases: tuple[str, ...] = ()
    method_id: str | None = None
    method_fingerprint: str | None = None
    share_key: str | None = None

    def __post_init__(self):
        for name in ("inputs", "parameters", "resources"):
            object.__setattr__(self, name, _mapping(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    plan_id: str
    definition_id: str
    tasks: tuple[CompiledTask, ...]
    outputs: Mapping[str, object]
    scopes: tuple[PlanScope, ...]
    policy: str = "continue"

    def __post_init__(self):
        object.__setattr__(self, "outputs", _mapping(self.outputs))

    def task(self, task_id):
        for task in self.tasks:
            if task.task_id == task_id or task_id in task.aliases:
                return task
        raise CompositionError("composition.task_unknown")

    def to_dict(self):
        from .codec import encode
        return encode(self)

    @classmethod
    def from_dict(cls, value):
        from .codec import decode
        result = decode(value)
        if not isinstance(result, cls):
            raise CompositionError("composition.plan_required")
        return result


OutputRef = PlanOutputRef
PlanInputRef = InputRef
