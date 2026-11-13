from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from time import monotonic
from typing import Generic, Literal, Protocol, TypeVar, TYPE_CHECKING

from stratbox.base.capabilities import CapabilityRequirement, ProviderBinding
from stratbox.base.limits import ExecutionBudget, Resource
from stratbox.data import ComputationReceipt, UsedInputReceipt
from stratbox.data.evidence import ByteIdentity

if TYPE_CHECKING:
    from .events import EventSink, IncidentSink

T = TypeVar("T")
Outcome = Literal["succeeded", "partial", "failed", "cancelled", "unknown"]
EffectState = Literal["confirmed", "failed", "unknown"]
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", re.ASCII)


def safe_token(value: str) -> str:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError("Expected a bounded identifier")
    return value


@dataclass(frozen=True, slots=True)
class EffectDescriptor:
    kind: str
    resource: str
    owner: str
    confirmation: str
    retry: str


def _effect_description(kind: str) -> EffectDescriptor:
    if kind == "network.receive":
        return EffectDescriptor(kind, "official_source", "transport", "acquisition_receipt", "qualified_read")
    if kind == "notification.send":
        return EffectDescriptor(kind, "recipient", "channel", "acceptance_receipt", "reconcile")
    return EffectDescriptor(kind, "file", "store", "effect_receipt", "reconcile")


@dataclass(frozen=True, slots=True)
class OperationDefinition:
    operation_id: str
    contract_version: int
    method_version: str
    request_type: type
    value_type: type | tuple[type, ...]
    required_capabilities: frozenset[str] = frozenset()
    possible_effects: frozenset[str] = frozenset()
    partial_allowed: bool = False
    optional_capabilities: frozenset[str] = frozenset()
    limits: ExecutionBudget | None = None

    def __post_init__(self) -> None:
        for token in (
            self.operation_id,
            self.method_version,
            *self.required_capabilities,
            *self.optional_capabilities,
            *self.possible_effects,
        ):
            safe_token(token)
        if type(self.contract_version) is not int or self.contract_version < 1:
            raise ValueError("Invalid operation contract version")
        if self.required_capabilities & self.optional_capabilities:
            raise ValueError("A capability role must be either required or optional")

    @property
    def effects(self) -> tuple[EffectDescriptor, ...]:
        kinds = self.possible_effects
        if "http" in self.required_capabilities | self.optional_capabilities:
            kinds = kinds | {"network.receive"}
        return tuple(_effect_description(kind) for kind in sorted(kinds))

    def capability(self, role: str, *, managed: bool = False) -> CapabilityRequirement:
        guarantees: set[str] = set()
        if managed:
            guarantees.update({
                "http": {"destination_bound", "budget_enforced"},
                "filestore": {"scope_bound"},
                "output_filestore": {"scope_bound", "verified_commit"},
                "notification": {"recipient_bound"},
                "archive_decoder": {"isolation_enforced"},
            }.get(role, ()))
            if role == "filestore" and self.possible_effects & {
                "storage.copy", "storage.rename", "storage.remove",
            }:
                guarantees.add("revision_guarded")
        return CapabilityRequirement(role, guarantees=frozenset(guarantees))


@dataclass(frozen=True, slots=True)
class Correlation:
    run_id: str | None = None
    step_id: str | None = None
    attempt_id: str | None = None
    cause_event_id: str | None = None

    def __post_init__(self) -> None:
        for token in (self.run_id, self.step_id, self.attempt_id, self.cause_event_id):
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

    def __post_init__(self) -> None:
        if self.profile not in {"local", "managed"}:
            raise ValueError("Invalid execution profile")


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
        for value in (self.code, self.stage, self.component, self.reason_class,
                      self.evidence_ref, self.reconciliation_owner, self.incident_id):
            if value is not None:
                safe_token(value)
        if self.retry_disposition not in {"none", "after_condition", "reconcile"}:
            raise ValueError("Invalid retry disposition")


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
        for value in (self.effect_id, self.stage, self.guarantee, self.reconciliation_owner):
            if value is not None:
                safe_token(value)


@dataclass(frozen=True, slots=True)
class ObservabilitySummary:
    emitted: int
    dropped: int
    incidents_dropped: int = 0

    @property
    def degraded(self) -> bool:
        return self.dropped > 0 or self.incidents_dropped > 0


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
            effect.kind not in self.definition.possible_effects
            for effect in self.effects
        ):
            raise ValueError("Undeclared effect")
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
        self.diagnostic = code if isinstance(code, Diagnostic) else Diagnostic(code, component=component)
        self.outcome = outcome
        super().__init__(self.diagnostic.code)
