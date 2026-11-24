"""Authoring graphs independent of compilation and execution state."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from stratbox.shared.identifiers import safe_token


def _freeze(value):
    if isinstance(value, Mapping):
        return frozen_mapping(value)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


def frozen_mapping(value):
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ValueError("capability.invalid_mapping")
    return MappingProxyType({key: _freeze(item) for key, item in value.items()})


@dataclass(frozen=True, slots=True)
class InputRef:
    name: str

    def __post_init__(self):
        safe_token(self.name)


@dataclass(frozen=True, slots=True)
class ParameterRef:
    name: str

    def __post_init__(self):
        safe_token(self.name)


@dataclass(frozen=True, slots=True)
class OutputRef:
    step: str
    port: str = "value"

    def __post_init__(self):
        safe_token(self.step)
        safe_token(self.port)

    @property
    def task(self):
        return self.step


@dataclass(frozen=True, slots=True)
class Condition:
    step: str
    port: str = "value"
    field: str = ""
    equals: object = True
    statuses: tuple[str, ...] = ()

    def __post_init__(self):
        safe_token(self.step)
        safe_token(self.port)
        object.__setattr__(self, "equals", _freeze(self.equals))
        if any(not part.isidentifier() or part.startswith("_") for part in self.field.split(".") if self.field):
            raise ValueError("capability.invalid_condition")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 1
    delay: float = 0.0
    retry_codes: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.max_attempts) is not int or self.max_attempts < 1 or self.delay < 0:
            raise ValueError("capability.invalid_retry")


@dataclass(frozen=True, slots=True)
class Call:
    step_id: str
    capability_id: str
    inputs: Mapping[str, object] = field(default_factory=dict)
    parameters: Mapping[str, object] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    condition: Condition | None = None
    required: bool = True
    method_id: str | None = None
    profile_id: str | None = None
    group_id: str | None = None

    def __post_init__(self):
        safe_token(self.step_id)
        safe_token(self.capability_id)
        object.__setattr__(self, "inputs", frozen_mapping(self.inputs))
        object.__setattr__(self, "parameters", frozen_mapping(self.parameters))
        if not isinstance(self.depends_on, tuple) or type(self.required) is not bool:
            raise ValueError("capability.invalid_call")
        for dependency in self.depends_on:
            safe_token(dependency)
        if self.condition is not None and not isinstance(self.condition, Condition):
            raise ValueError("capability.invalid_condition")


@dataclass(frozen=True, slots=True)
class GraphBody:
    steps: tuple[Call | MapCall | CollectCall, ...]
    outputs: Mapping[str, object] = field(default_factory=dict)
    required_checks: tuple[str, ...] = ()
    required_effects: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.steps, tuple) or any(not isinstance(step, (Call, MapCall, CollectCall)) for step in self.steps):
            raise ValueError("capability.invalid_graph")
        names = {step.step_id for step in self.steps}
        if len(names) != len(self.steps):
            raise ValueError("capability.duplicate_step")
        for roots in (self.required_checks, self.required_effects):
            if not isinstance(roots, tuple) or not set(roots) <= names:
                raise ValueError("capability.invalid_obligation_root")
        object.__setattr__(self, "outputs", frozen_mapping(self.outputs))


@dataclass(frozen=True, slots=True)
class MethodSlot:
    slot_id: str
    allowed_effects: frozenset[str] = frozenset()

    def __post_init__(self):
        safe_token(self.slot_id)


@dataclass(frozen=True, slots=True)
class MapCall:
    """Bounded expansion over a frozen item source; the coordinator owns waiting."""
    step_id: str
    capability_id: str
    items: object
    item_input: str = "item"
    inputs: Mapping[str, object] = field(default_factory=dict)
    parameters: Mapping[str, object] = field(default_factory=dict)
    window: int | None = None
    key_field: str | None = None
    required: bool = True
    allow_partial: bool = False
    depends_on: tuple[str, ...] = ()
    contract: object | None = None
    max_items: int | None = None

    def __post_init__(self):
        safe_token(self.step_id)
        safe_token(self.capability_id)
        safe_token(self.item_input)
        object.__setattr__(self, "inputs", frozen_mapping(self.inputs))
        object.__setattr__(self, "parameters", frozen_mapping(self.parameters))
        object.__setattr__(self, "items", _freeze(self.items))
        if self.window is not None and (type(self.window) is not int or self.window < 1):
            raise ValueError("capability.invalid_map_window")
        if self.max_items is not None and (type(self.max_items) is not int or self.max_items < 0):
            raise ValueError("capability.invalid_map_limit")
        if type(self.required) is not bool or type(self.allow_partial) is not bool or not isinstance(self.depends_on, tuple):
            raise ValueError("capability.invalid_map")
        if self.key_field is not None and (not self.key_field.isidentifier() or self.key_field.startswith("_")):
            raise ValueError("capability.invalid_map_key")
        from .definitions import PortContract
        if self.contract is not None and (not isinstance(self.contract, PortContract) or not self.contract.collection):
            raise ValueError("capability.map_collection_contract_required")


@dataclass(frozen=True, slots=True)
class CollectCall:
    """Structural collection preserves membership without semantic aggregation."""
    step_id: str
    inputs: tuple[OutputRef, ...]
    contract: object
    element_contract: object
    allow_partial: bool = False
    allow_empty: bool = False
    depends_on: tuple[str, ...] = ()
    required: bool = True

    def __post_init__(self):
        safe_token(self.step_id)
        from .definitions import PortContract
        if (not isinstance(self.inputs, tuple) or any(not isinstance(ref, OutputRef) for ref in self.inputs)
                or not isinstance(self.contract, PortContract) or not self.contract.collection
                or not isinstance(self.element_contract, PortContract)):
            raise ValueError("capability.invalid_collection")
        if not self.inputs and not self.allow_empty:
            raise ValueError("capability.empty_collection")
        if any(type(value) is not bool for value in (self.allow_partial, self.allow_empty, self.required)):
            raise ValueError("capability.invalid_collection")
        if not isinstance(self.depends_on, tuple):
            raise ValueError("capability.invalid_collection")
