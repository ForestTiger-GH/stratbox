"""Pure physical plan and retained logical acceptance scopes."""
from dataclasses import dataclass, field
from collections.abc import Mapping
from ..model import PortContract, AcceptanceContract, SourceRequirement, MethodRef, ReuseContract
from ..model.immutable import freeze

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

    def __post_init__(self):
        for name in ('settings','inputs','outputs','parameters','resources'):
            object.__setattr__(self, name, freeze(getattr(self, name)))

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

    def __post_init__(self): object.__setattr__(self, 'inputs', freeze(self.inputs))
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
    kind = 'collect'
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

    def __post_init__(self):
        for name in ('outputs','output_contracts'): object.__setattr__(self, name, freeze(getattr(self, name)))

@dataclass(frozen=True, slots=True)
class PreparedPlan:
    capability_id: str
    tasks: tuple[object, ...]
    scopes: tuple[PreparedScope, ...]
    outputs: Mapping[str, object]
    fingerprint: str
    build_identity: str
    target: object = None

    def __post_init__(self): object.__setattr__(self, 'outputs', freeze(self.outputs))


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
    kind = 'dispatch'
    @property
    def dependencies(self): return self.deps
