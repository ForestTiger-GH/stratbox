from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import monotonic
from typing import Generic, Literal, Protocol, TypeVar, TYPE_CHECKING

from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding
from stratbox.core.limits import ExecutionBudget, Resource
from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.identifiers import safe_token
from stratbox.shared.data.operations import OperationSemantics, RequestField
from stratbox.shared.data.source_context import ValueContext
from stratbox.core.execution.admission import ResultAdmission

if TYPE_CHECKING:
    from stratbox.core.execution.events import EventSink, IncidentSink

T = TypeVar("T")
Outcome = Literal["succeeded", "partial", "failed", "cancelled", "unknown"]
EffectState = Literal["confirmed", "failed", "unknown"]


@dataclass(frozen=True, slots=True)
class EffectDescriptor:
    kind: str
    resource: str
    owner: str
    confirmation: str
    retry: str


def _effect_description(kind: str) -> EffectDescriptor:
    if kind == "dataset.write":
        return EffectDescriptor(kind, "dataset", "dataset_store", "immutable_snapshot_receipt", "reconcile")
    if kind == "network.receive":
        return EffectDescriptor(
            kind,
            "official_source",
            "transport",
            "acquisition_receipt",
            "qualified_read",
        )
    if kind == "notification.handoff":
        return EffectDescriptor(
            kind, "recipient", "consumer", "acceptance_receipt", "reconcile"
        )
    if kind == "notification.state_commit":
        return EffectDescriptor(
            kind, "notification_state", "store", "state_receipt", "reconcile"
        )
    return EffectDescriptor(kind, "file", "store", "effect_receipt", "reconcile")


@dataclass(frozen=True, slots=True)
class RuntimeDependency:
    """A dependency checked by its own scoped runtime, not eager runner binding."""

    role: str
    phase: Literal["scoped", "conditional"]
    owner: str

    def __post_init__(self) -> None:
        safe_token(self.role)
        safe_token(self.owner)
        if self.phase not in {"scoped", "conditional"}:
            raise ValueError("Invalid runtime binding phase")


@dataclass(frozen=True, slots=True)
class OperationDefinition:
    operation_id: str
    method_id: str
    request_type: type
    value_type: type | tuple[type, ...]
    required_capabilities: frozenset[str] = frozenset()
    possible_effects: frozenset[str] = frozenset()
    partial_allowed: bool = False
    optional_capabilities: frozenset[str] = frozenset()
    limits: ExecutionBudget | None = None
    runtime_dependencies: tuple[RuntimeDependency, ...] = ()
    processing: OperationSemantics | None = None
    request_fields: tuple[RequestField, ...] = ()
    method_refs: tuple[str, ...] = ()
    method_resources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (not isinstance(self.request_fields, tuple)
                or any(not isinstance(item, RequestField) for item in self.request_fields)
                or len({item.path for item in self.request_fields}) != len(self.request_fields)):
            raise ValueError("processing.invalid_request_fields")
        paths = [item.path for item in self.request_fields]
        if any(left != right and (not left or right.startswith(left + ".")) for left in paths for right in paths):
            raise ValueError("processing.overlapping_request_fields")
        for references in (self.method_refs, self.method_resources):
            if (not isinstance(references, tuple) or any(not isinstance(item, str) or item.count(":") != 1 for item in references)
                    or len(set(references)) != len(references)):
                raise ValueError("processing.invalid_method_references")
        if not isinstance(self.request_type, type):
            raise ValueError("Invalid request type")
        value_types = (
            self.value_type
            if isinstance(self.value_type, tuple)
            else (self.value_type,)
        )
        if not value_types or not all(isinstance(kind, type) for kind in value_types):
            raise ValueError("Invalid value type")
        if any(
            not isinstance(group, frozenset)
            or any(not isinstance(name, str) for name in group)
            for group in (
                self.required_capabilities,
                self.optional_capabilities,
                self.possible_effects,
            )
        ):
            raise ValueError("Invalid capability/effect declaration")
        if type(self.partial_allowed) is not bool or (
            self.limits is not None and not isinstance(self.limits, ExecutionBudget)
        ):
            raise ValueError("Invalid operation policy")
        if (
            not isinstance(self.runtime_dependencies, tuple)
            or any(
                not isinstance(item, RuntimeDependency)
                for item in self.runtime_dependencies
            )
            or len({item.role for item in self.runtime_dependencies})
            != len(self.runtime_dependencies)
        ):
            raise ValueError("Invalid runtime dependency declarations")
        if {item.role for item in self.runtime_dependencies} & (
            self.required_capabilities | self.optional_capabilities
        ):
            raise ValueError(
                "Runtime and runner-managed capabilities must have distinct owners"
            )
        for token in (
            self.operation_id,
            self.method_id,
            *self.required_capabilities,
            *self.optional_capabilities,
            *self.possible_effects,
        ):
            safe_token(token)
        if self.required_capabilities & self.optional_capabilities:
            raise ValueError("A capability role must be either required or optional")
        if self.processing is not None:
            if not isinstance(self.processing, OperationSemantics):
                raise ValueError("processing.invalid_semantics")
            if not self.partial_allowed and any(
                "partial" in port.outcomes for port in self.processing.outputs
            ):
                raise ValueError("processing.partial_output_undeclared")

    @property
    def effects(self) -> tuple[EffectDescriptor, ...]:
        # HTTP is a capability. Source acquisition has its own receipt; do not
        # advertise an EffectReceipt kind the runner would reject.
        return tuple(
            _effect_description(kind) for kind in sorted(self.possible_effects)
        )

    def capability(self, role: str, *, managed: bool = False) -> CapabilityRequirement:
        if role not in self.required_capabilities | self.optional_capabilities:
            raise ValueError("provider.capability_undeclared")
        guarantees: set[str] = set()
        if managed:
            guarantees.update(
                {
                    "http": {"destination_bound", "budget_enforced"},
                    "filestore": {"scope_bound"},
                    "descriptor_filestore": {"scope_bound"},
                    "output_filestore": {"scope_bound", "verified_commit"},
                    "dataset_reader": {"scope_bound"},
                    "dataset_catalog": {"scope_bound"},
                    "dataset_writer": {"scope_bound", "verified_commit"},
                    "notification": {"recipient_bound"},
                    "archive_decoder": {"isolation_enforced"},
                }.get(role, ())
            )
            if role == "filestore" and self.possible_effects & {
                "storage.copy",
                "storage.rename",
                "storage.remove",
            }:
                guarantees.add("revision_guarded")
        return CapabilityRequirement(role, guarantees=frozenset(guarantees))


@dataclass(frozen=True, slots=True)
class Correlation:
    run_id: str | None = None
    step_id: str | None = None
    attempt_id: str | None = None
    cause_event_id: str | None = None
    session_id: str | None = None
    plan_id: str | None = None
    workflow_scope_id: str | None = None
    task_id: str | None = None
    item_key: str | None = None
    shared_work_id: str | None = None

    def __post_init__(self) -> None:
        # step_id is the operation-boundary spelling of the same task identity.
        if self.step_id is not None and self.task_id is not None and self.step_id != self.task_id:
            raise ValueError("correlation.task_identity_conflict")
        task = self.task_id or self.step_id
        object.__setattr__(self, "step_id", task)
        object.__setattr__(self, "task_id", task)
        for name in self.__dataclass_fields__:
            token = getattr(self, name)
            if token is not None:
                safe_token(token)


class Clock(Protocol):
    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return monotonic()


class CancellationToken(Protocol):
    def is_set(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    correlation: Correlation = field(default_factory=Correlation)
    clock: Clock = field(default_factory=SystemClock)
    cancellation: CancellationToken | None = None
    sink: EventSink | None = None
    budget: ExecutionBudget | None = None
    ceiling: ExecutionBudget | None = None
    profile: Literal["local", "managed"] = "local"
    bindings: tuple[ProviderBinding, ...] = ()
    incident_sink: IncidentSink | None = field(default=None, repr=False)
    input_computations: tuple[tuple[str, ComputationReceipt], ...] = ()
    input_receipts: tuple[UsedInputReceipt, ...] = ()
    input_provenance: tuple[UsedInputReceipt, ...] = ()
    input_transports: tuple[UsedInputReceipt, ...] = ()
    input_source_contexts: tuple[tuple[str, ValueContext], ...] = ()
    input_source_operation: str | None = None
    result_admissions: tuple[ResultAdmission, ...] = field(default=(), repr=False)
    resource_ledger: object | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.profile not in {"local", "managed"}:
            raise ValueError("Invalid execution profile")
        if (not isinstance(self.result_admissions, tuple)
                or len(self.result_admissions) > 32
                or any(not isinstance(item, ResultAdmission) for item in self.result_admissions)):
            raise ValueError("result.admission_policy_invalid")
        for policy in self.result_admissions:
            try:
                safe_token(policy.policy_id)
            except (AttributeError, TypeError, ValueError):
                raise ValueError("result.admission_policy_invalid") from None
        if (not isinstance(self.input_source_contexts, tuple)
                or any(not isinstance(item, tuple) or len(item) != 2
                       or not isinstance(item[0], str) or not isinstance(item[1], ValueContext)
                       for item in self.input_source_contexts)
                or len({item[0] for item in self.input_source_contexts}) != len(self.input_source_contexts)):
            raise ValueError("source.context_binding_invalid")
        for name, _ in self.input_source_contexts:
            safe_token(name)
        if self.input_source_operation is not None:
            safe_token(self.input_source_operation)
        if not isinstance(self.input_computations, tuple) or any(
            not isinstance(item, tuple) or len(item) != 2
            or not isinstance(item[1], ComputationReceipt)
            for item in self.input_computations
        ):
            raise ValueError("Invalid input computation evidence")
        names = [name for name, _ in self.input_computations]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate input computation role")
        for name in names:
            safe_token(name)
        if not isinstance(self.input_receipts, tuple) or any(
            not isinstance(item, UsedInputReceipt) for item in self.input_receipts
        ):
            raise ValueError("Invalid input receipt evidence")
        if not isinstance(self.input_provenance, tuple) or any(
            not isinstance(item, UsedInputReceipt) or item not in self.input_receipts
            for item in self.input_provenance
        ):
            raise ValueError("Invalid input provenance evidence")
        if not isinstance(self.input_transports, tuple) or any(
            not isinstance(item, UsedInputReceipt) or item not in self.input_receipts
            or item.version is not None
            for item in self.input_transports
        ):
            raise ValueError("Invalid input transport evidence")


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    stage: str | None = None
    component: str | None = None
    reason_class: str | None = None
    retry_disposition: Literal["none", "after_condition", "reconcile"] = "none"
    evidence_ref: str | None = None
    reconciliation_owner: str | None = None
    incident_id: str | None = None

    def __post_init__(self) -> None:
        for value in (
            self.code,
            self.stage,
            self.component,
            self.reason_class,
            self.evidence_ref,
            self.reconciliation_owner,
            self.incident_id,
        ):
            if value is not None:
                safe_token(value)
        if self.retry_disposition not in {"none", "after_condition", "reconcile"}:
            raise ValueError("Invalid retry disposition")


@dataclass(frozen=True, slots=True)
class EffectKey:
    """Identified effect within one invocation; no global provider authority implied."""

    kind: str
    effect_id: str

    def __post_init__(self) -> None:
        safe_token(self.kind)
        safe_token(self.effect_id)


@dataclass(frozen=True, slots=True)
class EffectReceipt:
    kind: str
    state: EffectState
    reference: str | None = field(default=None, repr=False)
    effect_id: str | None = None
    stage: str | None = None
    identity: ByteIdentity | None = None
    guarantee: str | None = None
    reconciliation_owner: str | None = None

    def __post_init__(self) -> None:
        safe_token(self.kind)
        if self.state not in {"confirmed", "failed", "unknown"}:
            raise ValueError("Invalid effect state")
        for value in (
            self.effect_id,
            self.stage,
            self.guarantee,
            self.reconciliation_owner,
        ):
            if value is not None:
                safe_token(value)
        if self.reference is not None and not isinstance(self.reference, str):
            raise ValueError("Invalid effect reference")
        if self.identity is not None and not isinstance(self.identity, ByteIdentity):
            raise ValueError("Invalid effect identity")

    @property
    def key(self) -> EffectKey | None:
        return (
            EffectKey(self.kind, self.effect_id) if self.effect_id is not None else None
        )


@dataclass(frozen=True, slots=True)
class ObservabilitySummary:
    emitted: int
    dropped: int
    incidents_dropped: int = 0
    timing_degraded: bool = False

    @property
    def degraded(self) -> bool:
        return self.dropped > 0 or self.incidents_dropped > 0 or self.timing_degraded


@dataclass(frozen=True, slots=True)
class OperationResult(Generic[T]):
    definition: OperationDefinition
    invocation_id: str
    outcome: Outcome
    value: T | None
    diagnostics: tuple[Diagnostic, ...]
    used_inputs: tuple[UsedInputReceipt, ...]
    effects: tuple[EffectReceipt, ...]
    observability: ObservabilitySummary
    computation: ComputationReceipt | None = None
    resources_used: tuple[tuple[Resource, int], ...] = ()

    @property
    def operation_id(self) -> str:
        return self.definition.operation_id

    def __post_init__(self) -> None:
        if not isinstance(self.definition, OperationDefinition):
            raise ValueError("Invalid operation definition")
        safe_token(self.invocation_id)
        if (
            not isinstance(self.diagnostics, tuple)
            or any(not isinstance(item, Diagnostic) for item in self.diagnostics)
            or not isinstance(self.used_inputs, tuple)
            or any(not isinstance(item, UsedInputReceipt) for item in self.used_inputs)
            or not isinstance(self.effects, tuple)
            or not isinstance(self.observability, ObservabilitySummary)
        ):
            raise ValueError("Invalid operation result evidence envelope")
        if self.computation is not None and not isinstance(
            self.computation, ComputationReceipt
        ):
            raise ValueError("Invalid computation evidence")
        if self.outcome not in {
            "succeeded",
            "partial",
            "failed",
            "cancelled",
            "unknown",
        }:
            raise ValueError("Invalid operation outcome")
        if self.value is not None and not isinstance(
            self.value, self.definition.value_type
        ):
            raise ValueError("Operation value disagrees with its definition")
        if self.outcome in {"succeeded", "partial"} and self.value is None:
            raise ValueError("Operation value is required")
        if self.outcome != "succeeded" and not self.diagnostics:
            raise ValueError("An incomplete outcome requires diagnostics")
        if self.outcome == "partial" and not self.definition.partial_allowed:
            raise ValueError("Partial outcome is outside the operation contract")
        if self.outcome == "cancelled" and self.value is not None:
            raise ValueError("Cancelled operations cannot carry values")
        if any(
            not isinstance(effect, EffectReceipt)
            or effect.kind not in self.definition.possible_effects
            for effect in self.effects
        ):
            raise ValueError("Undeclared or malformed effect")
        effect_keys = [effect.key for effect in self.effects if effect.key is not None]
        if len(effect_keys) != len(set(effect_keys)):
            raise ValueError("Duplicate identified effect in final operation result")
        if self.outcome != "unknown" and any(
            effect.state == "unknown" for effect in self.effects
        ):
            raise ValueError("Unresolved external effect requires unknown outcome")
        if self.outcome == "succeeded" and any(
            effect.state != "confirmed" for effect in self.effects
        ):
            raise ValueError("Successful operation has an incomplete effect")


class OperationFailure(Exception):
    """An expected, safely classified failure at a library boundary."""

    def __init__(
        self,
        code: str | Diagnostic,
        *,
        outcome: Literal["failed", "cancelled", "unknown"] = "failed",
        component: str | None = None,
    ):
        self.diagnostic = (
            code
            if isinstance(code, Diagnostic)
            else Diagnostic(code, component=component)
        )
        self.outcome = outcome
        super().__init__(self.diagnostic.code)
