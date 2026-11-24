"""Exact work identity shared by preparation and execution coordinators."""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from hashlib import sha256
from json import dumps
from collections.abc import Mapping
from enum import Enum


def canonical(value):
    """Return a stable typed JSON tree; reject opaque values conservatively."""
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is float:
        if value != value or value in {float("inf"), float("-inf")}:
            raise ValueError("reuse.nonfinite_identity")
        return {"float": value.hex()}
    if isinstance(value, Enum):
        return {"enum": type(value).__module__ + "." + type(value).__qualname__, "value": canonical(value.value)}
    if isinstance(value, bytes):
        return {"bytes": sha256(value).hexdigest(), "length": len(value)}
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("reuse.string_mapping_keys_required")
        return {key: canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return {type(value).__name__: [canonical(item) for item in value]}
    if isinstance(value, (set, frozenset)):
        return {type(value).__name__: sorted((canonical(item) for item in value), key=lambda item: dumps(item, sort_keys=True))}
    if is_dataclass(value):
        return {"type": type(value).__module__ + "." + type(value).__qualname__,
                "fields": {item.name: canonical(getattr(value, item.name)) for item in fields(value) if item.compare}}
    raise ValueError("reuse.opaque_identity")


def fingerprint(value) -> str:
    return sha256(dumps(canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class WorkIdentity:
    command_id: str
    implementation_revision: str
    input_identities: tuple[tuple[str, str], ...] = ()
    parameters_fingerprint: str = ""
    method_fingerprint: str = ""
    profile_fingerprint: str = ""
    schema_fingerprint: str = ""
    reference_fingerprints: tuple[str, ...] = ()
    access_scope: str = ""
    freshness: str = ""
    observation: str = ""
    state_epoch: str = ""

    def __post_init__(self):
        if not self.command_id or not self.implementation_revision:
            raise ValueError("reuse.incomplete_identity")
        names = [name for name, _ in self.input_identities]
        if len(names) != len(set(names)):
            raise ValueError("reuse.duplicate_input_identity")
        object.__setattr__(self, "input_identities", tuple(sorted(self.input_identities)))

    @property
    def fingerprint(self):
        return fingerprint(self)


@dataclass(frozen=True, slots=True)
class ReuseContract:
    deterministic: bool = True
    shareable: bool = True
    completed: bool = True
    mutation: str = "isolated"
    effects: frozenset[str] = frozenset()
    significant_parameters: tuple[str, ...] = ()
    observation_scoped: bool = False

    def __post_init__(self):
        if self.mutation not in {"isolated", "immutable", "exclusive"}:
            raise ValueError("reuse.invalid_mutation_contract")
        if any(type(value) is not bool for value in (self.deterministic, self.shareable, self.completed, self.observation_scoped)):
            raise ValueError("reuse.invalid_contract")

    @property
    def eligible(self):
        return ((self.deterministic or self.observation_scoped) and self.shareable
                and self.mutation != "exclusive"
                and (not self.effects or self.observation_scoped and self.effects <= {"network.receive"}))


@dataclass(frozen=True, slots=True)
class ConsumerEligibility:
    allow_network: bool = True
    access_scope: str = ""
    freshness: str = ""
    observation: str = ""
    state_epoch: str = ""

    def eligible_for(self, identity: WorkIdentity, effects=frozenset()):
        return (not (not self.allow_network and "network.receive" in effects)
                and all(getattr(self, key) == getattr(identity, key)
                        for key in ("access_scope", "freshness", "observation", "state_epoch")))
