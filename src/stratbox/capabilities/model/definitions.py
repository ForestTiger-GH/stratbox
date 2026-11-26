"""Four explicit callable kinds with one standard execution contract."""
from dataclasses import dataclass, field
from collections.abc import Mapping
from .contracts import PortContract, AcceptanceContract, SemanticPredicate, SourceRequirement
from .graph import GraphBody
from .methods import MethodRef
from .immutable import freeze, fingerprint
from .reuse import ReuseContract

@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    __authored_definition__ = True
    id: str
    inputs: Mapping[str, PortContract] = field(default_factory=dict)
    outputs: Mapping[str, PortContract] = field(default_factory=dict)
    parameters: Mapping[str, object] = field(default_factory=dict)
    required_parameters: tuple[str, ...] = ()
    acceptance: AcceptanceContract = field(default_factory=AcceptanceContract)
    summary: str = ''
    entrances: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id: raise ValueError('definition.id_required')
        for name in ('inputs', 'outputs', 'parameters', 'entrances'): object.__setattr__(self, name, freeze(getattr(self, name)))
        if any(not isinstance(p, PortContract) for p in (*self.inputs.values(), *self.outputs.values())):
            raise TypeError('definition.invalid_ports')
        if not set(self.acceptance.coherent_outputs) <= self.outputs.keys(): raise ValueError('definition.unknown_acceptance_output')

    @property
    def fingerprint(self): return fingerprint(self)

@dataclass(frozen=True, slots=True)
class CommandDefinition(CapabilityDefinition):
    method: MethodRef | None = None
    specification_required: bool = False
    resources: Mapping[str, int] = field(default_factory=lambda: {'cpu': 1})
    effects: frozenset[str] = frozenset()
    required_providers: frozenset[str] = frozenset()
    reuse: ReuseContract = field(default_factory=ReuseContract)
    kind = 'command'

    def __post_init__(self):
        CapabilityDefinition.__post_init__(self)
        if self.method is None and not self.specification_required: raise ValueError('command.method_required')
        object.__setattr__(self, 'resources', freeze(self.resources))
        if any(type(n) is not int or n < 1 for n in self.resources.values()): raise ValueError('command.invalid_resources')

@dataclass(frozen=True, slots=True)
class OperationDefinition(CapabilityDefinition):
    body: GraphBody = field(default_factory=lambda: GraphBody(()))
    kind = 'operation'

@dataclass(frozen=True, slots=True)
class ScenarioDefinition(CapabilityDefinition):
    body: GraphBody = field(default_factory=lambda: GraphBody(()))
    kind = 'scenario'

@dataclass(frozen=True, slots=True)
class CascadeDefinition(CapabilityDefinition):
    body: GraphBody = field(default_factory=lambda: GraphBody(()))
    kind = 'cascade'
