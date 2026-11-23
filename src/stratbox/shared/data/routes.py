"""Pure, bounded explanations of declared operation connections and plans."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.shared.data.operations import OperationKey
from stratbox.shared.data.processing import DataContract
from stratbox.shared.identifiers import safe_token


@dataclass(frozen=True, slots=True)
class ExactConnection:
    producer: OperationKey
    output: str
    consumer: OperationKey
    input: str
    kind: str
    source_contract: DataContract
    accepted_contracts: tuple[DataContract, ...]
    state: str
    reasons: tuple[str, ...] = ()
    additional_inputs: tuple[str, ...] = ()
    parameters: tuple[str, ...] = ()
    source_id: str | None = None
    group_id: str | None = None
    edition: str | None = None
    assessment_scope: str = "declarations"
    format: str | None = None


@dataclass(frozen=True, slots=True)
class ConnectionPage:
    entries: tuple[ExactConnection, ...]
    offset: int
    total: int
    next_offset: int | None


@dataclass(frozen=True, slots=True)
class AvailableArtifact:
    """A planning assertion; availability and domain admission remain separate."""

    contract: DataContract
    reference: str | None = None
    outcome: str = "succeeded"
    qualifications: frozenset[str] = frozenset()
    coverage: frozenset[str] = frozenset()
    collection: bool = False

    def __post_init__(self):
        if not isinstance(self.contract, DataContract):
            raise ValueError("planning.contract_invalid")
        if self.reference is not None:
            safe_token(self.reference)
        if self.outcome not in {"succeeded", "partial"}:
            raise ValueError("planning.outcome_invalid")
        if type(self.collection) is not bool:
            raise ValueError("planning.collection_invalid")
        for values in (self.qualifications, self.coverage):
            if not isinstance(values, frozenset):
                raise ValueError("planning.qualifications_invalid")
            for value in values:
                safe_token(value)


@dataclass(frozen=True, slots=True)
class PlannedStep:
    operation_id: str
    dependencies: tuple[str, ...]
    required_inputs: tuple[str, ...]
    conditions: tuple[str, ...]
    effects: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoutePlan:
    steps: tuple[PlannedStep, ...]
    conditions: tuple[str, ...]

    @property
    def state(self):
        return "conditional" if self.conditions else "reachable"


@dataclass(frozen=True, slots=True)
class RouteExplanation:
    goal: str | DataContract
    plans: tuple[RoutePlan, ...]
    missing_inputs: tuple[str, ...]
    reasons: tuple[str, ...]
    examined: int
    truncated: bool
    source_id: str | None = None
    assessment_scope: str = "declaration_planning"
    grants_authority: bool = False
    format: str | None = None
    group_id: str | None = None
    edition: str | None = None

    @property
    def state(self):
        if self.plans:
            return self.plans[0].state
        return "bounded" if self.truncated else "unreachable"
