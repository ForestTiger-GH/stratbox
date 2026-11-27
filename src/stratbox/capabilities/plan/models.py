"""Pure physical plan and retained logical acceptance scopes."""
from dataclasses import dataclass, field
from collections.abc import Mapping
from ..model import PortContract, AcceptanceContract, SourceRequirement, MethodRef, ReuseContract
from ..model.immutable import freeze, freeze_bindings


def _freeze_controls(task):
    """Detach authored collections without traversing a shared plan template."""
    for name in ('deps', 'guards', 'input_guards'):
        object.__setattr__(task, name, tuple(getattr(task, name)))
    object.__setattr__(task, 'condition', freeze(task.condition, _typed=True))

@dataclass(frozen=True, slots=True)
class OutputGuard:
    scope_id: str
    port: str

@dataclass(frozen=True, slots=True)
class InputGuard:
    value: object
    contract: PortContract

@dataclass(frozen=True, slots=True)
class ValueRef:
    task_id: str
    port: str = 'value'
    path: str = ''

@dataclass(frozen=True, slots=True)
class TemplateInput:
    name: str

@dataclass(frozen=True, slots=True)
class BoundCommand:
    id: str
    method: MethodRef
    settings: object
    inputs: Mapping[str, PortContract]
    outputs: Mapping[str, PortContract]
    parameters: Mapping[str, object] = field(default_factory=dict)
    resources: Mapping[str, int] = field(default_factory=dict)
    effects: frozenset[str] = frozenset()
    required_providers: frozenset[str] = frozenset()
    reuse: ReuseContract = field(default_factory=ReuseContract)
    source_requirements: tuple[SourceRequirement, ...] = ()
    acceptance: AcceptanceContract = field(default_factory=AcceptanceContract)
    optional_providers: frozenset[str] = frozenset()
    target: object = None
    scientific_limitations: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ('settings','inputs','outputs','parameters','resources'):
            object.__setattr__(self, name, freeze(getattr(self, name)))
        for name in ('effects', 'required_providers', 'optional_providers'):
            object.__setattr__(self, name, frozenset(getattr(self, name)))
        object.__setattr__(self, 'source_requirements', tuple(self.source_requirements))
        object.__setattr__(self, 'scientific_limitations', tuple(self.scientific_limitations))
        if any(not isinstance(code, str) or not code for code in self.scientific_limitations):
            raise ValueError('plan.invalid_scientific_limitation')

    @property
    def command_id(self): return self.id

@dataclass(frozen=True, slots=True)
class CommandTask:
    task_id: str
    command: BoundCommand
    inputs: Mapping[str, object]
    deps: tuple[str, ...] = ()
    scope_id: str = ''
    condition: object = None
    required: bool = True
    guards: tuple[OutputGuard, ...] = ()
    input_guards: tuple[InputGuard, ...] = ()
    kind = 'command'

    def __post_init__(self):
        object.__setattr__(self, 'inputs', freeze_bindings(self.inputs))
        _freeze_controls(self)
    @property
    def dependencies(self): return self.deps

@dataclass(frozen=True, slots=True)
class MapTask:
    task_id: str
    template: object
    items: object
    item_input: str = 'item'
    item_output: str = 'dataset'
    window: int = 4
    max_items: int = 10000
    completion: str = 'all_selected'
    deps: tuple[str, ...] = ()
    scope_id: str = ''
    required: bool = True
    condition: object = None
    guards: tuple[OutputGuard, ...] = ()
    input_guards: tuple[InputGuard, ...] = ()
    kind = 'map'

    def __post_init__(self):
        if (type(self.window) is not int or self.window < 1
                or type(self.max_items) is not int or self.max_items < 0
                or self.completion not in {'all_selected', 'eligible_subset'}):
            raise ValueError('plan.invalid_map_limits')
        object.__setattr__(self, 'items', freeze(self.items, _typed=True))
        _freeze_controls(self)
    @property
    def dependencies(self): return self.deps

@dataclass(frozen=True, slots=True)
class RepeatTask:
    task_id: str
    template: object
    initial: object
    state_input: str = 'state'
    state_output: str = 'state'
    stop: object = None
    max_passes: int = 100
    deps: tuple[str, ...] = ()
    scope_id: str = ''
    required: bool = True
    condition: object = None
    guards: tuple[OutputGuard, ...] = ()
    input_guards: tuple[InputGuard, ...] = ()
    kind = 'repeat'

    def __post_init__(self):
        if type(self.max_passes) is not int or self.max_passes < 1:
            raise ValueError('plan.invalid_repeat_limit')
        object.__setattr__(self, 'initial', freeze(self.initial, _typed=True))
        _freeze_controls(self)
    @property
    def dependencies(self): return self.deps

@dataclass(frozen=True, slots=True)
class CollectTask:
    task_id: str
    items: tuple[object, ...]
    deps: tuple[str, ...] = ()
    scope_id: str = ''
    required: bool = True
    condition: object = None
    guards: tuple[OutputGuard, ...] = ()
    input_guards: tuple[InputGuard, ...] = ()
    optional_items: frozenset[int] = frozenset()
    min_items: int = 0
    item_guards: Mapping[int, tuple[OutputGuard, ...]] = field(default_factory=dict)
    completion: str = 'all_selected'
    kind = 'collect'

    def __post_init__(self):
        object.__setattr__(self, 'items', freeze(tuple(self.items), _typed=True))
        object.__setattr__(self, 'optional_items', frozenset(self.optional_items))
        # Index-keyed control metadata is intentionally not a string-keyed map.
        object.__setattr__(self, 'item_guards', freeze(self.item_guards, _typed=True))
        if type(self.min_items) is not int or not 0 <= self.min_items <= len(self.items):
            raise ValueError('plan.invalid_collection_minimum')
        if self.completion not in {'all_selected', 'eligible_subset', 'diagnostic'}:
            raise ValueError('plan.invalid_collection_completion')
        if any(type(i) is not int or not 0 <= i < len(self.items) for i in self.optional_items):
            raise ValueError('plan.invalid_optional_member')
        _freeze_controls(self)
    @property
    def dependencies(self): return self.deps

@dataclass(frozen=True, slots=True)
class PreparedScope:
    scope_id: str
    capability_id: str
    kind: str
    parent_id: str | None
    outputs: Mapping[str, object]
    output_contracts: Mapping[str, PortContract]
    acceptance: AcceptanceContract = field(default_factory=AcceptanceContract)
    required_tasks: tuple[str, ...] = ()
    required_scopes: tuple[str, ...] = ()
    required: bool = True
    required_checks: tuple[str, ...] = ()
    required_effects: tuple[str, ...] = ()
    condition: object = None

    def __post_init__(self):
        object.__setattr__(self, 'outputs', freeze_bindings(self.outputs))
        object.__setattr__(self, 'output_contracts', freeze(self.output_contracts))
        for name in ('required_tasks', 'required_scopes', 'required_checks', 'required_effects'):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        object.__setattr__(self, 'condition', freeze(self.condition, _typed=True))

@dataclass(frozen=True, slots=True)
class PreparedPlan:
    capability_id: str
    tasks: tuple[object, ...]
    scopes: tuple[PreparedScope, ...]
    outputs: Mapping[str, object]
    fingerprint: str
    build_identity: str
    target: object = None

    def __post_init__(self):
        object.__setattr__(self, 'outputs', freeze_bindings(self.outputs))
        object.__setattr__(self, 'tasks', tuple(self.tasks))
        object.__setattr__(self, 'scopes', tuple(self.scopes))


@dataclass(frozen=True, slots=True)
class DispatchTask:
    task_id: str
    selector: object
    alternatives: Mapping[str, PreparedPlan]
    input_name: str = 'material'
    output_port: str = 'dataset'
    selector_kind: str = 'material_format'
    deps: tuple[str, ...] = ()
    scope_id: str = ''
    required: bool = True
    condition: object = None
    guards: tuple[OutputGuard, ...] = ()
    input_guards: tuple[InputGuard, ...] = ()
    forwarded: object = None
    kind = 'dispatch'

    def __post_init__(self):
        from types import MappingProxyType
        # Prepared alternatives are immutable plans and remain shared templates.
        object.__setattr__(self, 'alternatives', MappingProxyType(dict(self.alternatives)))
        object.__setattr__(self, 'selector', freeze(self.selector, _typed=True))
        object.__setattr__(self, 'forwarded', freeze(self.forwarded, _typed=True))
        _freeze_controls(self)
    @property
    def dependencies(self): return self.deps
