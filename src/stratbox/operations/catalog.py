"""Immutable operation registrations and validated, lazy resolution."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import lru_cache
from importlib import import_module
from types import MappingProxyType
from typing import Mapping

from stratbox.shared.identifiers import safe_token
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.shared.data.operations import StageDeclaration


class RegistryError(ValueError):
    """A declared operation is duplicated or violates its contract."""


@dataclass(frozen=True, slots=True)
class OperationRef:
    operation_id: str
    handler_ref: str
    wire_codec_ref: str | None = None
    wire_contract_ref: str | None = None
    definition: OperationDefinition | None = None

    def __post_init__(self) -> None:
        try:
            safe_token(self.operation_id)
        except ValueError as exc:
            raise RegistryError("registry.invalid_identity") from exc
        if (self.wire_codec_ref is None) != (self.wire_contract_ref is None):
            raise RegistryError("registry.wire_contract_required")
        if not isinstance(self.handler_ref, str):
            raise RegistryError("registry.invalid_reference")
        for ref in (self.handler_ref, self.wire_codec_ref, self.wire_contract_ref):
            if ref is not None and (
                not isinstance(ref, str) or ref.count(":") != 1
                or not all(ref.split(":"))
            ):
                raise RegistryError("registry.invalid_reference")
        if self.definition is not None and (
            not isinstance(self.definition, OperationDefinition)
            or self.definition.operation_id != self.operation_id
        ):
            raise RegistryError("registry.contract_mismatch")


@dataclass(frozen=True, slots=True)
class OperationRegistration:
    owner_id: str
    operations: tuple[OperationRef, ...]
    stages: tuple[StageDeclaration, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.owner_id, str) or not self.owner_id.strip() or not isinstance(self.operations, tuple):
            raise RegistryError("registry.invalid_registration")
        try:
            safe_token(self.owner_id)
        except ValueError as exc:
            raise RegistryError("registry.invalid_registration") from exc
        if any(not isinstance(op, OperationRef) for op in self.operations):
            raise RegistryError("registry.invalid_reference")
        keys = [op.operation_id for op in self.operations]
        if len(keys) != len(set(keys)):
            raise RegistryError("registry.duplicate_operation")
        if (not isinstance(self.stages, tuple)
            or any(not isinstance(item, StageDeclaration) for item in self.stages)
            or len({item.stage for item in self.stages}) != len(self.stages)):
            raise RegistryError("registry.invalid_stage_declarations")


def _load(ref: str):
    module, symbol = ref.split(":")
    value = import_module(module)
    for name in symbol.split("."):
        value = getattr(value, name)
    return value


@lru_cache(maxsize=4096)
def _definition(ref: OperationRef):
    if ref.definition is not None:
        return ref.definition
    from stratbox.operations.declarations import definition
    value = definition(ref.operation_id)
    if value.method_refs and value.method_refs[0] != ref.handler_ref:
        value = replace(value, method_refs=(ref.handler_ref, *value.method_refs[1:]))
    return value


@lru_cache(maxsize=4096)
def _typed_definition(ref: OperationRef):
    from stratbox.operations.declarations import validate_request_contract
    definition = _definition(ref)
    validate_request_contract(definition, require_classification=ref.definition is None)
    return definition


@lru_cache(maxsize=4096)
def _wire_contract(ref: OperationRef):
    if ref.wire_contract_ref is None:
        return None
    from stratbox.core.execution.machine.contracts import ReadOnlyWireContract
    try:
        contract = _load(ref.wire_contract_ref)
        if not isinstance(contract, ReadOnlyWireContract) or contract.operation_id != ref.operation_id:
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
        definition = _typed_definition(ref)
        handler = _load(ref.handler_ref)
        if not callable(handler):
            raise RegistryError("registry.invalid_handler")
        codec = _load(ref.wire_codec_ref) if ref.wire_codec_ref else None
        if ref.wire_codec_ref is not None:
            from stratbox.core.execution.machine.contracts import ReadOnlyWireCodec
            if not isinstance(codec, ReadOnlyWireCodec) or codec.contract != _wire_contract(ref):
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
    _index: Mapping[str, OperationRef] = field(init=False, repr=False, compare=False)
    _owners: Mapping[str, str] = field(init=False, repr=False, compare=False)
    _metadata_admitted: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.references, tuple) or any(not isinstance(ref, OperationRef) for ref in self.references):
            raise RegistryError("registry.invalid_reference")
        keys = [ref.operation_id for ref in self.references]
        if len(keys) != len(set(keys)):
            raise RegistryError("registry.duplicate_operation")
        if (not isinstance(self.registrations, tuple)
            or any(not isinstance(item, OperationRegistration) for item in self.registrations)
            or len({item.owner_id for item in self.registrations}) != len(self.registrations)):
            raise RegistryError("registry.invalid_catalog_owners")
        index = dict(zip(keys, self.references))
        owners = {}
        for item in self.registrations:
            for ref in item.operations:
                key = ref.operation_id
                if key in owners or index.get(key) != ref:
                    raise RegistryError("registry.catalog_owner_mismatch")
                owners[key] = item.owner_id
        object.__setattr__(self, "_index", MappingProxyType(index))
        object.__setattr__(self, "_owners", MappingProxyType(owners))

    @classmethod
    def from_registrations(cls, *registrations: OperationRegistration):
        return cls(tuple(ref for item in registrations for ref in item.operations), registrations)

    def owner_of(self, operation_id: str) -> str | None:
        self.reference(operation_id)
        return self._owners.get(operation_id)

    def list_refs(self) -> tuple[OperationRef, ...]:
        return tuple(sorted(self.references, key=lambda ref: ref.operation_id))

    def reference(self, operation_id: str) -> OperationRef:
        from stratbox.core.execution.machine.contracts import WireRequestError
        if not isinstance(operation_id, str) or operation_id not in self._index:
            raise WireRequestError("operation.unavailable")
        return self._index[operation_id]

    def resolve(self, operation_id: str):
        reference = self.reference(operation_id)
        if reference.definition is None and not self._metadata_admitted:
            self.admit(level="metadata")
        return _resolved(reference)

    def metadata(self, operation_id: str) -> OperationDefinition:
        """Read complete policies without importing request types or handlers."""
        ref = self.reference(operation_id)
        if ref.definition is not None:
            return ref.definition
        from stratbox.operations.declarations import metadata_definition
        value = metadata_definition(operation_id)
        if value.method_refs and value.method_refs[0] != ref.handler_ref:
            value = replace(value, method_refs=(ref.handler_ref, *value.method_refs[1:]))
        return value

    def document(self, operation_id: str):
        self.reference(operation_id)
        from stratbox.operations.declarations import operation_document
        return operation_document(operation_id)

    def get(self, operation_id: str) -> OperationDefinition:
        reference = self.reference(operation_id)
        if reference.definition is None and not self._metadata_admitted:
            self.admit(level="metadata")
        return _typed_definition(reference)

    def wire_contract(self, operation_id: str):
        return _wire_contract(self.reference(operation_id))

    def source_catalog(self):
        from stratbox.domains.registry.catalog import source_catalog
        return source_catalog(self)

    def bind(self, operation_id: str, *, inputs=None, parameters=None, source_resolver=None, domain_admitter=None):
        """Build a named, typed call without loading or invoking its handler."""
        from stratbox.core.execution.calls import bind_operation
        return bind_operation(self, operation_id, inputs=inputs, parameters=parameters,
                              source_resolver=source_resolver, domain_admitter=domain_admitter)

    def bind_source(self, series_id: str, *, format: str | None = None, group_id=None, edition=None):
        from stratbox.core.execution.calls import bind_source
        return bind_source(self, series_id, format=format, group_id=group_id, edition=edition)

    @property
    def definitions(self) -> tuple[OperationDefinition, ...]:
        return tuple(self.get(ref.operation_id) for ref in self.list_refs())

    def describe(self) -> tuple[dict, ...]:
        from stratbox.operations.discovery import describe_operation
        return tuple(describe_operation(self, ref) for ref in self.list_refs())

    def page(self, **filters):
        from stratbox.operations.discovery import catalog_page
        return catalog_page(self, **filters)

    def compatible_next(self, operation_id: str, *, output=None):
        from stratbox.operations.discovery import compatible_next
        return compatible_next(self, operation_id, output=output)

    def requirements(self, operation_id: str):
        """Describe the operation's named source roles and compatibility rules."""
        from stratbox.domains.registry.requirements import operation_requirements
        return operation_requirements(self, operation_id)

    def readiness(self, operation_id: str, available, **options):
        """Keep claims, materials, domain, runtime and effect admission distinct."""
        from stratbox.domains.registry.requirements import operation_readiness
        return operation_readiness(self, operation_id, available, **options)

    def connections(self, **filters):
        from stratbox.domains.registry.routes import connections
        return connections(self, **filters)

    def explain_route(self, goal, **options):
        from stratbox.domains.registry.routes import explain_route
        return explain_route(self, goal, **options)

    def admit(self, *, level="metadata", refresh=False):
        from stratbox.operations.admission import admit_registry_snapshot
        report = admit_registry_snapshot(self, level=level, refresh=refresh)
        object.__setattr__(self, "_metadata_admitted", True)
        return report

    def coverage(self, owner_id: str):
        from stratbox.operations.discovery import stage_coverage
        return stage_coverage(self, owner_id)


def merge_catalogs(*catalogs: OperationCatalog) -> OperationCatalog:
    return OperationCatalog(tuple(ref for cat in catalogs for ref in cat.references),
                            tuple(item for cat in catalogs for item in cat.registrations))
