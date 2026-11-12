from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
from time import monotonic
from typing import Generic, Literal, Protocol, TypeVar, TYPE_CHECKING

from stratbox.data import UsedInputReceipt

if TYPE_CHECKING:
    from .events import EventSink

T = TypeVar("T")
Outcome = Literal["succeeded", "partial", "failed", "cancelled", "unknown"]
EffectState = Literal["confirmed", "failed", "unknown"]
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", re.ASCII)


def safe_token(value: str) -> str:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError("Expected a bounded identifier")
    return value


@dataclass(frozen=True, slots=True)
class OperationDefinition:
    operation_id: str
    contract_version: int
    method_version: str
    request_type: type
    value_type: type
    required_capabilities: frozenset[str] = frozenset()
    possible_effects: frozenset[str] = frozenset()
    partial_allowed: bool = False

    def __post_init__(self) -> None:
        for token in (
            self.operation_id,
            self.method_version,
            *self.required_capabilities,
            *self.possible_effects,
        ):
            safe_token(token)
        if self.contract_version < 1:
            raise ValueError("Invalid operation contract version")


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


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str

    def __post_init__(self) -> None:
        safe_token(self.code)


@dataclass(frozen=True, slots=True)
class EffectReceipt:
    kind: str
    state: EffectState
    reference: str | None = None

    def __post_init__(self) -> None:
        safe_token(self.kind)
        if self.state not in {"confirmed", "failed", "unknown"}:
            raise ValueError("Invalid effect state")


@dataclass(frozen=True, slots=True)
class ObservabilitySummary:
    emitted: int
    dropped: int

    @property
    def degraded(self) -> bool:
        return self.dropped > 0


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
        code: str,
        *,
        outcome: Literal["failed", "cancelled", "unknown"] = "failed",
    ):
        self.diagnostic = Diagnostic(code)
        self.outcome = outcome
        super().__init__(code)
