"""Exact and goal requests share one preparation service."""
from dataclasses import dataclass, field
from typing import Mapping
from types import MappingProxyType
from stratbox.capabilities.model.graph import frozen_mapping


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
    selection: Mapping[str, object] = field(default_factory=dict)
    recipe_id: str | None = None

    def __post_init__(self):
        for name in ("parameters","selection"):
            object.__setattr__(self,name,frozen_mapping(getattr(self,name)))
        for name in ("inputs","supplied_outputs"):
            object.__setattr__(self,name,MappingProxyType(dict(getattr(self,name))))


@dataclass(frozen=True, slots=True)
class GoalRequest:
    goal: str
    inputs: Mapping[str, object] = field(default_factory=dict)
    parameters: Mapping[str, object] = field(default_factory=dict)
    selection: Mapping[str, object] = field(default_factory=dict)
    outputs: tuple[str, ...] | None = None
    supplied_outputs: Mapping[str, object] = field(default_factory=dict)
    recipe_id: str | None = None

    def __post_init__(self):
        for name in ("parameters","selection"):
            object.__setattr__(self,name,frozen_mapping(getattr(self,name)))
        for name in ("inputs","supplied_outputs"):
            object.__setattr__(self,name,MappingProxyType(dict(getattr(self,name))))
