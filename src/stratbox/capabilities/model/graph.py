"""Authoring graphs; control structures carry no publisher implementation."""
from dataclasses import dataclass, field
from collections.abc import Mapping
from .immutable import freeze

@dataclass(frozen=True, slots=True)
class InputRef:
    name: str
    path: str = ''

@dataclass(frozen=True, slots=True)
class ParameterRef:
    name: str
    path: str = ''

@dataclass(frozen=True, slots=True)
class TargetRef:
    name: str = 'target'

@dataclass(frozen=True, slots=True)
class OutputRef:
    step: str
    port: str = 'value'
    path: str = ''

@dataclass(frozen=True, slots=True)
class Condition:
    value: object
    equals: object = True
    path: str = ''

@dataclass(frozen=True, slots=True)
class Call:
    step_id: str
    capability_id: str
    inputs: Mapping[str, object] = field(default_factory=dict)
    parameters: Mapping[str, object] = field(default_factory=dict)
    target: object = field(default_factory=TargetRef)
    depends_on: tuple[str, ...] = ()
    condition: Condition | None = None
    required: bool = True

    def __post_init__(self):
        for name in ('inputs', 'parameters'): object.__setattr__(self, name, freeze(getattr(self, name)))

@dataclass(frozen=True, slots=True)
class MapCall:
    step_id: str
    capability_id: str
    items: object
    item_input: str = 'item'
    inputs: Mapping[str, object] = field(default_factory=dict)
    parameters: Mapping[str, object] = field(default_factory=dict)
    target: object = field(default_factory=TargetRef)
    max_items: int = 10000
    window: int = 4
    completion: str = 'all_selected'
    output_port: str = 'dataset'
    required: bool = True

    def __post_init__(self):
        if self.max_items < 0 or self.window < 1 or self.completion not in {'all_selected', 'eligible_subset'}:
            raise ValueError('graph.invalid_map')
        object.__setattr__(self, 'inputs', freeze(self.inputs))
        object.__setattr__(self, 'parameters', freeze(self.parameters))

@dataclass(frozen=True, slots=True)
class RepeatUntil:
    step_id: str
    body: object
    initial: object
    state_input: str = 'state'
    state_output: str = 'state'
    stop: object = None
    max_passes: int = 100
    required: bool = True
    inputs: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        if self.max_passes < 1: raise ValueError('graph.invalid_repeat_limit')

@dataclass(frozen=True, slots=True)
class CollectCall:
    step_id: str
    items: tuple[object, ...]
    required: bool = True

@dataclass(frozen=True, slots=True)
class GraphBody:
    steps: tuple[object, ...]
    outputs: Mapping[str, object] = field(default_factory=dict)
    required_checks: tuple[str, ...] = ()
    required_effects: tuple[str, ...] = ()
    required_completions: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, 'steps', tuple(self.steps))
        object.__setattr__(self, 'outputs', freeze(self.outputs))
        names = tuple(step.step_id for step in self.steps)
        if len(names) != len(set(names)): raise ValueError('graph.duplicate_step')
        for roots in (self.required_checks, self.required_effects, self.required_completions):
            if not set(roots) <= set(names): raise ValueError('graph.unknown_obligation')
