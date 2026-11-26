"""Metadata and explicit selection for capabilities of trusted adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Callable, Iterable, Literal

Readiness = Literal["not_configured", "unavailable", "degraded", "ready"]
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", re.ASCII)


def _identifier(value: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError("Expected a bounded capability identifier")


@dataclass(frozen=True, slots=True)
class CapabilityRequirement:
    role: str
    guarantees: frozenset[str] = frozenset()

    def __post_init__(self):
        _identifier(self.role)
        for name in self.guarantees:
            _identifier(name)


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    """An explicit adapter/scope choice, independent of a physical locator.

    A selection never falls back to a different binding or to local defaults.
    Leaving one coordinate absent is allowed only when the remaining choice is
    unambiguous. An empty selection is rejected: omit it to request the default.
    """

    provider_id: str | None = None
    scope_id: str | None = None

    def __post_init__(self) -> None:
        if self.provider_id is None and self.scope_id is None:
            raise ValueError("provider.selection_required")
        for value in (self.provider_id, self.scope_id):
            if value is not None:
                _identifier(value)


@dataclass(frozen=True, slots=True)
class ProviderBinding:
    """Selection and observed readiness supplied by the application."""

    provider_id: str
    capability: CapabilityRequirement
    readiness: Readiness
    provider: object = field(repr=False)
    scope_id: str | None = None

    def __post_init__(self):
        _identifier(self.provider_id)
        if self.scope_id is not None:
            _identifier(self.scope_id)
        if self.readiness not in {"not_configured", "unavailable", "degraded", "ready"}:
            raise ValueError("Invalid provider readiness")
        if self.provider is None and self.readiness in {"ready", "degraded"}:
            raise ValueError("Ready capability requires a provider")


class BindingError(ValueError):
    @property
    def code(self) -> str:
        return self.args[0]


def select_provider(
    requirement: CapabilityRequirement,
    bindings: Iterable[ProviderBinding],
    *,
    provider_id: str | None = None,
    scope_id: str | None = None,
) -> ProviderBinding:
    candidates = tuple(
        item for item in bindings
        if item.capability.role == requirement.role
        and (provider_id is None or item.provider_id == provider_id)
        and (scope_id is None or item.scope_id == scope_id)
    )
    if not candidates:
        raise BindingError("provider.capability_missing")
    if len(candidates) != 1:
        raise BindingError("provider.binding_conflict")
    binding = candidates[0]
    if binding.readiness not in {"ready", "degraded"}:
        raise BindingError(f"provider.{binding.readiness}")
    if not requirement.guarantees <= binding.capability.guarantees:
        raise BindingError("provider.guarantee_missing")
    return binding


def probe_provider(binding: ProviderBinding, probe: Callable[[object], Readiness]) -> ProviderBinding:
    """Explicitly inspect readiness using the application-supplied probe."""
    from dataclasses import replace

    if binding.provider is None:
        return binding
    try:
        readiness = probe(binding.provider)
    except Exception:
        readiness = "unavailable"
    return replace(binding, readiness=readiness)
