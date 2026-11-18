"""Immutable operation registrations and validated, lazy resolution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from importlib import import_module

from stratbox.core.execution.contracts import OperationDefinition


class RegistryError(ValueError):
    """A declared operation is duplicated or violates its contract."""


@dataclass(frozen=True, slots=True)
class OperationRef:
    operation_id: str
    contract_version: int
    definition_ref: str
    handler_ref: str
    wire_codec_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.operation_id or type(self.contract_version) is not int or self.contract_version < 1:
            raise RegistryError("registry.invalid_identity")
        for ref in (self.definition_ref, self.handler_ref, self.wire_codec_ref):
            if ref is not None and (ref.count(":") != 1 or not all(ref.split(":"))):
                raise RegistryError("registry.invalid_reference")


@dataclass(frozen=True, slots=True)
class OperationRegistration:
    owner_id: str
    operations: tuple[OperationRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.owner_id, str) or not self.owner_id.strip() or not isinstance(self.operations, tuple):
            raise RegistryError("registry.invalid_registration")
        if any(not isinstance(op, OperationRef) for op in self.operations):
            raise RegistryError("registry.invalid_reference")
        keys = [(op.operation_id, op.contract_version) for op in self.operations]
        if len(keys) != len(set(keys)):
            raise RegistryError("registry.duplicate_contract")


def _load(ref: str):
    module, symbol = ref.split(":")
    return getattr(import_module(module), symbol)


@lru_cache(maxsize=None)
def _resolved(ref: OperationRef):
    try:
        definition = _load(ref.definition_ref)
        handler = _load(ref.handler_ref)
        if not isinstance(definition, OperationDefinition):
            raise RegistryError("registry.invalid_definition")
        if (definition.operation_id, definition.contract_version) != (
            ref.operation_id, ref.contract_version
        ):
            raise RegistryError("registry.contract_mismatch")
        if not callable(handler):
            raise RegistryError("registry.invalid_handler")
        codec = _load(ref.wire_codec_ref) if ref.wire_codec_ref else None
        if codec is not None and (
            codec.operation_id != definition.operation_id
            or codec.contract_version != definition.contract_version
        ):
            raise RegistryError("registry.codec_mismatch")
        return definition, handler, codec
    except RegistryError:
        raise
    except (ImportError, AttributeError, ValueError, TypeError) as exc:
        raise RegistryError("registry.unresolvable_reference") from exc


@dataclass(frozen=True, slots=True)
class OperationCatalog:
    references: tuple[OperationRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.references, tuple) or any(
            not isinstance(ref, OperationRef) for ref in self.references
        ):
            raise RegistryError("registry.invalid_reference")
        keys = [(ref.operation_id, ref.contract_version) for ref in self.references]
        if len(keys) != len(set(keys)):
            raise RegistryError("Duplicate operation contract")

    def list_refs(self) -> tuple[OperationRef, ...]:
        return tuple(sorted(self.references, key=lambda r: (r.operation_id, r.contract_version)))

    def reference(self, operation_id: str, contract_version: int) -> OperationRef:
        for ref in self.references:
            if (ref.operation_id, ref.contract_version) == (operation_id, contract_version):
                return ref
        from stratbox.core.execution.machine.contracts import WireRequestError
        raise WireRequestError("operation.contract_unavailable")

    def resolve(self, operation_id: str, contract_version: int):
        return _resolved(self.reference(operation_id, contract_version))

    def get(self, operation_id: str, contract_version: int) -> OperationDefinition:
        return self.resolve(operation_id, contract_version)[0]

    @property
    def definitions(self) -> tuple[OperationDefinition, ...]:
        return tuple(_resolved(ref)[0] for ref in self.list_refs())

    def describe(self) -> tuple[dict, ...]:
        descriptions = []
        for ref in self.list_refs():
            op, _, codec = _resolved(ref)
            required = sorted(op.required_capabilities)
            optional = sorted(op.optional_capabilities)
            name = lambda kind: f"{kind.__module__}.{kind.__qualname__}"
            descriptions.append({
                "operation_id": op.operation_id,
                "contract_version": op.contract_version,
                "method_version": op.method_version,
                "purpose": op.operation_id.rsplit(".", 1)[-1].replace("_", " "),
                "python_request": name(op.request_type),
                "machine_input_roles": sorted(codec.input_fields) if codec else [],
                "machine_result_fields": sorted(codec.output_fields) if codec else [],
                "python_result": " | ".join(name(kind) for kind in op.value_type)
                    if isinstance(op.value_type, tuple) else name(op.value_type),
                "capabilities": [
                    {"role": role, "required": role in required,
                     "version": op.capability(role).version,
                     "managed_guarantees": sorted(op.capability(role, managed=True).guarantees)}
                    for role in required + optional
                ],
                "effects": [asdict(effect) for effect in op.effects],
                "limits": asdict(op.limits) if op.limits else None,
                "partial_allowed": op.partial_allowed,
                "cancellation": "cooperative",
                "diagnostic_envelope": 3,
                "machine_read_only": codec is not None,
            })
        return tuple(descriptions)


def merge_catalogs(*catalogs: OperationCatalog) -> OperationCatalog:
    return OperationCatalog(tuple(ref for cat in catalogs for ref in cat.references))
