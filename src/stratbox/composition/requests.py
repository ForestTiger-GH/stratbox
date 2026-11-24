"""Exact and goal requests share one preparation service."""
from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True, slots=True)
class InvocationRequest:
    capability_id: str
    inputs: Mapping[str, object] = field(default_factory=dict)
    parameters: Mapping[str, object] = field(default_factory=dict)
    outputs: tuple[str, ...] | None = None
    method_id: str | None = None
    profile_id: str | None = None
    group_id: str | None = None
    supplied_outputs: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GoalRequest:
    goal: str
    inputs: Mapping[str, object] = field(default_factory=dict)
    parameters: Mapping[str, object] = field(default_factory=dict)
    selection: Mapping[str, object] = field(default_factory=dict)
    outputs: tuple[str, ...] | None = None
    supplied_outputs: Mapping[str, object] = field(default_factory=dict)
