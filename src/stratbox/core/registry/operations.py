"""Compile compact canonical operation declarations into runtime contracts.

The declaration schema explicitly defines required fields and defaults. It is
independent of runtime dataclass field inventories and never loads handlers.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from importlib import import_module

from stratbox.core.execution.contracts import OperationDefinition, RuntimeDependency
from stratbox.core.limits import ExecutionBudget
from stratbox.core.registry.catalog import OperationRef, OperationRegistration, RegistryError
from stratbox.core.registry.resources import iter_resources, owner_directory, read_document, resource_owners
from stratbox.shared.data.operations import (
    InputPort, OutputPort, OperationSemantics, ProcessingFunction,
    ProcessingStage, StageDeclaration, OperationKey,
)
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.identifiers import safe_token


def _object(value, required=(), optional=(), code="registry.invalid_document"):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise RegistryError(code)
    return value


def _list(value):
    if not isinstance(value, list):
        raise RegistryError("registry.invalid_sequence")
    return value


def _strings(value):
    values = _list(value)
    if any(type(item) is not str for item in values) or len(values) != len(set(values)):
        raise RegistryError("registry.invalid_tokens")
    return tuple(values)


def _reference(value, *, owner=None, implementation=False):
    if not isinstance(value, str) or value.count(":") != 1:
        raise RegistryError("registry.invalid_reference")
    module, symbol = value.split(":")
    if any(not part.isidentifier() for part in (*module.split("."), *symbol.split("."))):
        raise RegistryError("registry.invalid_reference")
    if owner is not None:
        boundary = "stratbox.core" if owner.startswith("core.") else "stratbox.domains." + owner
        valid = module == boundary or module.startswith(boundary + ".")
        if not implementation:
            valid |= module == "builtins" or module.startswith("stratbox.shared.") or module.startswith("stratbox.core.")
        if not valid:
            raise RegistryError("registry.reference_ownership")
    return value


def _load_type(ref):
    module, symbol = ref.split(":")
    try:
        value = import_module(module)
        for name in symbol.split("."):
            value = getattr(value, name)
    except (ImportError, AttributeError) as error:
        raise RegistryError("registry.unresolvable_type") from error
    if not isinstance(value, type):
        raise RegistryError("registry.invalid_type")
    return value


def _contract(value):
    value = _object(value, ("schema_id",), ("version", "role"))
    return DataContract(value["schema_id"], value.get("version", 1),
                        None if value.get("role") is None else DataRole(value["role"]))


def _port(value, input):
    common = ("path", "qualifications", "coverage", "outcomes")
    value = _object(value, ("name", "contract"), (*common, "required", "alternatives") if input else common)
    options = {"name": value["name"], "contract": _contract(value["contract"]),
               "path": value.get("path", value["name"])}
    for name in ("qualifications", "coverage", "outcomes"):
        options[name] = frozenset(_strings(value.get(name, ["succeeded"] if name == "outcomes" else [])))
    if input:
        options["required"] = value.get("required", True)
        options["alternatives"] = tuple(_contract(item) for item in _list(value.get("alternatives", [])))
    return (InputPort if input else OutputPort)(**options)


def _processing(value):
    if value is None:
        return None
    value = _object(value, ("stages", "summary"), ("inputs", "outputs", "parameters", "composition", "function"))
    return OperationSemantics(
        stages=tuple(ProcessingStage(item) for item in _strings(value["stages"])),
        inputs=tuple(_port(item, True) for item in _list(value.get("inputs", []))),
        outputs=tuple(_port(item, False) for item in _list(value.get("outputs", []))),
        parameters=_strings(value.get("parameters", [])), summary=value["summary"],
        composition=value.get("composition", False), function=ProcessingFunction(value.get("function", "process")),
    )


def _dependency(value):
    return RuntimeDependency(**_object(value, ("role", "phase", "owner")))


def _budget(value):
    if value is None:
        return None
    value = _object(value, (), ("seconds", "input_bytes", "wire_bytes", "decoded_bytes", "output_bytes",
                               "requests", "objects", "cells", "temporary_bytes", "archive_depth"))
    return ExecutionBudget(**value)


def _compile(d, *, typed):
    value_types = d["value_type"]
    return OperationDefinition(
        operation_id=d["operation_id"], method_id=d["method_id"],
        request_type=_load_type(d["request_type"]) if typed else object,
        value_type=(tuple(_load_type(item) for item in value_types) if isinstance(value_types, list) else _load_type(value_types)) if typed else object,
        required_capabilities=frozenset(_strings(d.get("required_capabilities", []))),
        possible_effects=frozenset(_strings(d.get("possible_effects", []))),
        partial_allowed=d.get("partial_allowed", False),
        optional_capabilities=frozenset(_strings(d.get("optional_capabilities", []))),
        limits=_budget(d.get("limits")),
        runtime_dependencies=tuple(_dependency(item) for item in _list(d.get("runtime_dependencies", []))),
        processing=_processing(d.get("processing")),
    )


def validate_operation_document(value, *, owner_id=None):
    """Validate canonical metadata without resolving executable or value types."""
    try:
        value = _object(value, ("schema", "owner_id", "definition", "implementation"), ("source_requirements",))
        if value["schema"] != "stratbox.operation":
            raise RegistryError("registry.invalid_schema")
        owner = value["owner_id"]
        safe_token(owner)
        if owner_id is not None and owner != owner_id:
            raise RegistryError("registry.owner_mismatch")
        d = _object(value["definition"], ("operation_id", "method_id", "request_type", "value_type"),
                    ("required_capabilities", "possible_effects", "partial_allowed", "optional_capabilities",
                     "limits", "runtime_dependencies", "processing"))
        i = _object(value["implementation"], ("handler_ref",), ("wire_codec_ref", "wire_contract_ref"))
        for name in ("handler_ref", "wire_codec_ref", "wire_contract_ref"):
            if i.get(name) is not None:
                _reference(i[name], owner=owner, implementation=True)
        _reference(d["request_type"], owner=owner)
        value_types = d["value_type"] if isinstance(d["value_type"], list) else [d["value_type"]]
        if not value_types or len(value_types) != len(set(value_types)):
            raise RegistryError("registry.invalid_value_types")
        for item in value_types:
            _reference(item, owner=owner)
        _compile(d, typed=False)
        OperationRef(d["operation_id"], **i)
        if "source_requirements" in value:
            from stratbox.core.registry.requirements import decode_requirement
            requirements = tuple(decode_requirement(item) for item in _list(value["source_requirements"]))
            if len({item.input_name for item in requirements}) != len(requirements):
                raise RegistryError("registry.source_requirement_duplicate")
        return value
    except RegistryError:
        raise
    except (ValueError, TypeError, KeyError) as error:
        raise RegistryError("registry.invalid_operation_document") from error


@lru_cache(maxsize=1)
def owner_ids():
    return resource_owners()


@lru_cache(maxsize=32)
def _operation_documents(owner_id=None):
    if owner_id is None:
        return tuple(document for owner in owner_ids() for document in _operation_documents(owner))
    if owner_id not in owner_ids():
        raise RegistryError("registry.owner_unknown")
    documents = []
    keys = set()
    for path in iter_resources(owner_id, "operations"):
        document = validate_operation_document(read_document(path), owner_id=owner_id)
        identity = document["definition"]["operation_id"]
        if path.name != f"OPERATION_{identity}.yaml" or identity in keys:
            raise RegistryError("registry.operation_identity_mismatch")
        keys.add(identity)
        documents.append(document)
    if not documents:
        raise RegistryError("registry.empty_owner")
    return tuple(sorted(documents, key=lambda document: document["definition"]["operation_id"]))


def operation_documents(owner_id=None):
    """Isolated copies of the canonical authority, including optional metadata."""
    return deepcopy(_operation_documents(owner_id))


@lru_cache(maxsize=1)
def _definition_index():
    result = {}
    for document in _operation_documents():
        identity = document["definition"]["operation_id"]
        if identity in result:
            raise RegistryError("registry.duplicate_operation")
        result[identity] = document
    return result


def operation_document(operation_id):
    """Return one isolated declaration without copying the complete catalog."""
    try:
        return deepcopy(_definition_index()[operation_id])
    except (KeyError, TypeError):
        raise RegistryError("registry.operation_unavailable") from None


@lru_cache(maxsize=4096)
def definition(operation_id):
    """Compile the canonical declaration directly, without a Python backlink."""
    if not isinstance(operation_id, str):
        raise RegistryError("registry.operation_unavailable")
    try:
        document = _definition_index()[operation_id]
    except KeyError:
        raise RegistryError("registry.operation_unavailable") from None
    return _compile(document["definition"], typed=True)


def _stage(value):
    value = _object(value, ("stage", "state", "reason"), ("operations", "binding"))
    return StageDeclaration(
        ProcessingStage(value["stage"]), value["state"], value["reason"],
        tuple(OperationKey(**_object(item, ("operation_id",))) for item in _list(value.get("operations", []))),
        value.get("binding"),
    )


@lru_cache(maxsize=32)
def owner_registration(owner_id):
    if owner_id not in owner_ids():
        raise RegistryError("registry.owner_unknown")
    try:
        owner = _object(read_document(owner_directory(owner_id).joinpath("OWNER.yaml")),
                        ("owner_id",), ("stages", "value_contexts"))
        if owner["owner_id"] != owner_id:
            raise RegistryError("registry.owner_mismatch")
        if "value_contexts" in owner:
            from stratbox.core.execution.value_context import validate_value_contexts
            validate_value_contexts(owner["value_contexts"])
        return OperationRegistration(
            owner_id, tuple(OperationRef(document["definition"]["operation_id"], **document["implementation"])
                            for document in _operation_documents(owner_id)),
            tuple(_stage(item) for item in _list(owner.get("stages", []))),
        )
    except RegistryError:
        raise
    except (ValueError, TypeError, KeyError) as error:
        raise RegistryError("registry.invalid_owner_document") from error


def operation_references(owner_id, *, handler_module=None):
    """Project an implementation segment without duplicating operation lists."""
    references = owner_registration(owner_id).operations
    if handler_module is None:
        return references
    return tuple(ref for ref in references if (module := ref.handler_ref.split(":")[0]) == handler_module
                 or module.startswith(handler_module + "."))
