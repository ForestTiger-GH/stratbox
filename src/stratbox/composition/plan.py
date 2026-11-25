"""Physical Plan IR and retained semantic scopes, separate from authoring AST."""
from __future__ import annotations
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, TYPE_CHECKING, Protocol
from ._validation import CompositionError, _mapping, _name
if TYPE_CHECKING:
    from .models import ScenarioDefinition, Condition, SourceSelection, CollectSpec, RetryPolicy

def _retry_policy():
    from .models import RetryPolicy
    return RetryPolicy()

class ExpansionValueResolver(Protocol):
    """Resolve promises without discarding typed input evidence.

    The execution owner retains any required read leases until the admitted
    child fragment has finished. Control selector unwrapping is separate from
    material/data input resolution.
    """
    def __call__(self, value: object) -> object: ...


@dataclass(frozen=True, slots=True)
class ScopeOutputRef:
    """A named promise owned by one capability acceptance boundary."""
    scope_id: str
    port: str = "value"
    task_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.scope_id,str) or not self.scope_id or any(part in {"",".",".."} for part in self.scope_id.split("/")):
            raise CompositionError("composition.invalid_scope")
        _name(self.port)
        if self.task_id is not None and (not isinstance(self.task_id,str) or not self.task_id):
            raise CompositionError("composition.invalid_reference")

    @property
    def task(self):
        return self.task_id or self.scope_id + "/accept"

    @property
    def item(self):
        return None


def task_conditions(task):
    """Return the conjunction retained by canonical and transitional tasks."""
    result = []
    for condition in ((task.condition,) if task.condition is not None else ()) + task.conditions:
        if condition not in result:
            result.append(condition)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class CanonicalMapTemplate:
    capability_id: str
    outputs: tuple[str, ...]
    catalog_fingerprint: str
    selection: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self,"selection",_mapping(self.selection))


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
    max_items: int | None = None

    def __post_init__(self):
        object.__setattr__(self, "inputs", _mapping(self.inputs))


@dataclass(frozen=True, slots=True)
class PlanScope:
    scope_id: str
    definition_id: str
    parent_id: str | None = None
    expenditure: Mapping[str, int] = field(default_factory=dict)
    kind: str = "scenario"
    outputs: Mapping[str, object] = field(default_factory=dict)
    required_checks: tuple[str, ...] = ()
    required_effects: tuple[str, ...] = ()
    required: bool = True
    output_contracts: Mapping[str, object] = field(default_factory=dict)
    acceptance: object | None = None
    membership: object | None = None
    conditions: tuple[Condition, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "expenditure", _mapping(self.expenditure))
        object.__setattr__(self, "outputs", _mapping(self.outputs))
        object.__setattr__(self, "output_contracts", _mapping(self.output_contracts))
        if self.kind not in {"command", "operation", "scenario", "cascade"}:
            raise CompositionError("composition.invalid_kind")
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
    retry: RetryPolicy = field(default_factory=_retry_policy)
    aliases: tuple[str, ...] = ()
    method_id: str | None = None
    method_fingerprint: str | None = None
    share_key: str | None = None
    capability_kind: str = "operation"
    work_identity: str | None = None
    reuse_eligible: bool = False
    acceptance_scope: str | None = None
    conditions: tuple[Condition, ...] = ()
    reuse_contract: object | None = None
    reuse_identity: object | None = None

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
    root_kind: str = "scenario"
    selected_bindings: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "outputs", _mapping(self.outputs))
        object.__setattr__(self, "selected_bindings", _mapping(self.selected_bindings))

    @property
    def logical_to_physical(self):
        owners, result = {}, {}
        for task in self.tasks:
            key = task.work_identity if task.reuse_eligible and task.work_identity else task.task_id
            owner = owners.setdefault(key,task.task_id)
            for logical in (task.task_id,*task.aliases):
                result[logical] = owner
        return MappingProxyType(result)

    @property
    def physical_to_logical(self):
        grouped = {}
        for logical,physical in self.logical_to_physical.items():
            grouped.setdefault(physical,[]).append(logical)
        return MappingProxyType({key:tuple(values) for key,values in grouped.items()})

    def task(self, task_id):
        for task in self.tasks:
            if task.task_id == task_id or task_id in task.aliases:
                return task
        raise CompositionError("composition.task_unknown")

    def explain(self, **options):
        from .explain import explain_plan
        return explain_plan(self,**options)

    def to_dict(self):
        from .codec import encode
        return {"format":"stratbox.plan","version":1,"plan":encode(self)}

    @classmethod
    def from_dict(cls, value):
        from .codec import decode
        if not isinstance(value,dict) or set(value) != {"format","version","plan"} or value["format"] != "stratbox.plan" or type(value["version"]) is not int or value["version"] != 1:
            raise CompositionError("composition.unsupported_plan_format")
        result = decode(value["plan"])
        if not isinstance(result, cls):
            raise CompositionError("composition.plan_required")
        return result

