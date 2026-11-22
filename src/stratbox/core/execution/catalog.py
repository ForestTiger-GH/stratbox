"""Immutable operation registrations and validated, lazy resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib import import_module
from types import MappingProxyType
from typing import Mapping

from stratbox.core.execution.contracts import OperationDefinition, safe_token
from stratbox.core.execution.semantics import StageDeclaration


class RegistryError(ValueError):
    """A declared operation is duplicated or violates its contract."""


@dataclass(frozen=True, slots=True)
class OperationRef:
    operation_id: str
    contract_version: int
    definition_ref: str
    handler_ref: str
    wire_codec_ref: str | None = None
    wire_contract_ref: str | None = None

    def __post_init__(self) -> None:
        try:
            safe_token(self.operation_id)
        except ValueError as exc:
            raise RegistryError("registry.invalid_identity") from exc
        if type(self.contract_version) is not int or self.contract_version < 1:
            raise RegistryError("registry.invalid_identity")
        if (self.wire_codec_ref is None) != (self.wire_contract_ref is None):
            raise RegistryError("registry.wire_contract_required")
        if not isinstance(self.definition_ref, str) or not isinstance(
            self.handler_ref, str
        ):
            raise RegistryError("registry.invalid_reference")
        for ref in (
            self.definition_ref,
            self.handler_ref,
            self.wire_codec_ref,
            self.wire_contract_ref,
        ):
            if ref is not None and (
                not isinstance(ref, str)
                or ref.count(":") != 1
                or not all(ref.split(":"))
            ):
                raise RegistryError("registry.invalid_reference")


@dataclass(frozen=True, slots=True)
class OperationRegistration:
    owner_id: str
    operations: tuple[OperationRef, ...]
    stages: tuple[StageDeclaration, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.owner_id, str)
            or not self.owner_id.strip()
            or not isinstance(self.operations, tuple)
        ):
            raise RegistryError("registry.invalid_registration")
        try:
            safe_token(self.owner_id)
        except ValueError as exc:
            raise RegistryError("registry.invalid_registration") from exc
        if any(not isinstance(op, OperationRef) for op in self.operations):
            raise RegistryError("registry.invalid_reference")
        keys = [(op.operation_id, op.contract_version) for op in self.operations]
        if len(keys) != len(set(keys)):
            raise RegistryError("registry.duplicate_contract")
        if (
            not isinstance(self.stages, tuple)
            or any(not isinstance(item, StageDeclaration) for item in self.stages)
            or len({item.stage for item in self.stages}) != len(self.stages)
        ):
            raise RegistryError("registry.invalid_stage_declarations")


def _load(ref: str):
    module, symbol = ref.split(":")
    return getattr(import_module(module), symbol)


@lru_cache(maxsize=4096)
def _definition(ref: OperationRef):
    try:
        definition = _load(ref.definition_ref)
        if not isinstance(definition, OperationDefinition):
            raise RegistryError("registry.invalid_definition")
        if (definition.operation_id, definition.contract_version) != (
            ref.operation_id,
            ref.contract_version,
        ):
            raise RegistryError("registry.contract_mismatch")
        return definition
    except RegistryError:
        raise
    except (ImportError, AttributeError, ValueError, TypeError) as exc:
        raise RegistryError("registry.unresolvable_reference") from exc


@lru_cache(maxsize=4096)
def _wire_contract(ref: OperationRef):
    if ref.wire_contract_ref is None:
        return None
    from stratbox.core.execution.machine.contracts import ReadOnlyWireContract

    try:
        contract = _load(ref.wire_contract_ref)
        if not isinstance(contract, ReadOnlyWireContract) or (
            contract.operation_id,
            contract.contract_version,
        ) != (ref.operation_id, ref.contract_version):
            raise RegistryError("registry.codec_mismatch")
        if _definition(ref).possible_effects:
            raise RegistryError("registry.read_only_effects")
        return contract
    except RegistryError:
        raise
    except (ImportError, AttributeError, ValueError, TypeError) as exc:
        raise RegistryError("registry.unresolvable_reference") from exc


@lru_cache(maxsize=4096)
def _resolved(ref: OperationRef):
    try:
        definition = _definition(ref)
        handler = _load(ref.handler_ref)
        if not callable(handler):
            raise RegistryError("registry.invalid_handler")
        codec = _load(ref.wire_codec_ref) if ref.wire_codec_ref else None
        if ref.wire_codec_ref is not None:
            from stratbox.core.execution.machine.contracts import ReadOnlyWireCodec

            if not isinstance(
                codec, ReadOnlyWireCodec
            ) or codec.contract != _wire_contract(ref):
                raise RegistryError("registry.codec_mismatch")
        return definition, handler, codec
    except RegistryError:
        raise
    except (ImportError, AttributeError, ValueError, TypeError) as exc:
        raise RegistryError("registry.unresolvable_reference") from exc


@dataclass(frozen=True, slots=True)
class OperationCatalog:
    references: tuple[OperationRef, ...]
    registrations: tuple[OperationRegistration, ...] = ()
    _index: Mapping[tuple[str, int], OperationRef] = field(
        init=False, repr=False, compare=False
    )
    _owners: Mapping[tuple[str, int], str] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not isinstance(self.references, tuple) or any(
            not isinstance(ref, OperationRef) for ref in self.references
        ):
            raise RegistryError("registry.invalid_reference")
        keys = [(ref.operation_id, ref.contract_version) for ref in self.references]
        if len(keys) != len(set(keys)):
            raise RegistryError("Duplicate operation contract")
        if (
            not isinstance(self.registrations, tuple)
            or any(
                not isinstance(item, OperationRegistration)
                for item in self.registrations
            )
            or len({item.owner_id for item in self.registrations})
            != len(self.registrations)
        ):
            raise RegistryError("registry.invalid_catalog_owners")
        index = dict(zip(keys, self.references))
        owners = {}
        for item in self.registrations:
            for ref in item.operations:
                key = (ref.operation_id, ref.contract_version)
                if key in owners or index.get(key) != ref:
                    raise RegistryError("registry.catalog_owner_mismatch")
                owners[key] = item.owner_id
        object.__setattr__(self, "_index", MappingProxyType(index))
        object.__setattr__(self, "_owners", MappingProxyType(owners))

    @classmethod
    def from_registrations(cls, *registrations: OperationRegistration):
        return cls(
            tuple(ref for item in registrations for ref in item.operations),
            registrations,
        )

    def owner_of(self, operation_id: str, contract_version: int) -> str | None:
        self.reference(operation_id, contract_version)
        return self._owners.get((operation_id, contract_version))

    def list_refs(self) -> tuple[OperationRef, ...]:
        return tuple(
            sorted(self.references, key=lambda r: (r.operation_id, r.contract_version))
        )

    def reference(self, operation_id: str, contract_version: int) -> OperationRef:
        if not isinstance(operation_id, str) or type(contract_version) is not int:
            from stratbox.core.execution.machine.contracts import WireRequestError

            raise WireRequestError("operation.contract_unavailable")
        ref = self._index.get((operation_id, contract_version))
        if ref is not None:
            return ref
        from stratbox.core.execution.machine.contracts import WireRequestError

        raise WireRequestError("operation.contract_unavailable")

    def resolve(self, operation_id: str, contract_version: int):
        return _resolved(self.reference(operation_id, contract_version))

    def get(self, operation_id: str, contract_version: int) -> OperationDefinition:
        return _definition(self.reference(operation_id, contract_version))

    def wire_contract(self, operation_id: str, contract_version: int):
        return _wire_contract(self.reference(operation_id, contract_version))

    @property
    def definitions(self) -> tuple[OperationDefinition, ...]:
        return tuple(_definition(ref) for ref in self.list_refs())

    def describe(self) -> tuple[dict, ...]:
        """Inspect every definition without loading executable handlers."""
        from stratbox.core.execution.discovery import describe_operation

        return tuple(describe_operation(self, ref) for ref in self.list_refs())

    def page(self, **filters):
        """Bounded, filterable descriptions for application/protocol adapters."""
        from stratbox.core.execution.discovery import catalog_page

        return catalog_page(self, **filters)

    def compatible_next(self, operation_id: str, contract_version: int, *, output=None):
        """Return conditional port links; values/providers still require admission."""
        from stratbox.core.execution.discovery import compatible_next

        return compatible_next(self, operation_id, contract_version, output=output)

    def coverage(self, owner_id: str):
        from stratbox.core.execution.discovery import stage_coverage

        return stage_coverage(self, owner_id)


def merge_catalogs(*catalogs: OperationCatalog) -> OperationCatalog:
    return OperationCatalog(
        tuple(ref for cat in catalogs for ref in cat.references),
        tuple(item for cat in catalogs for item in cat.registrations),
    )
