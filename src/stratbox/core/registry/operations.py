"""Canonical operation contracts assembled from packaged declarative resources.

JSON is the supported deterministic YAML subset. Registry discovery validates
metadata and symbolic references without importing handlers or data engines.
Python request/value types resolve only when a typed definition is requested.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import fields
from functools import lru_cache
from importlib import import_module

from stratbox.core.execution.contracts import OperationDefinition, RuntimeDependency
from stratbox.core.limits import ExecutionBudget
from stratbox.core.registry.catalog import OperationRef, OperationRegistration, RegistryError
from stratbox.shared.data.operations import (
    InputPort, OutputPort, OperationSemantics, ProcessingFunction,
    ProcessingStage, StageDeclaration, OperationKey,
)
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.identifiers import safe_token


def _object(value, names, code="registry.invalid_document"):
    if not isinstance(value, dict) or set(value) != set(names):
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
    value = _object(value, ("schema_id", "version", "role"))
    return DataContract(value["schema_id"], value["version"],
                        None if value["role"] is None else DataRole(value["role"]))


def _port(value, input):
    kind = InputPort if input else OutputPort
    value = _object(value, (item.name for item in fields(kind)))
    options = dict(value)
    options["contract"] = _contract(value["contract"])
    for name in ("qualifications", "coverage", "outcomes"):
        options[name] = frozenset(_strings(value[name]))
    if input:
        options["alternatives"] = tuple(_contract(item) for item in _list(value["alternatives"]))
    return kind(**options)


def _processing(value):
    if value is None:
        return None
    value = _object(value, (item.name for item in fields(OperationSemantics)))
    return OperationSemantics(
        stages=tuple(ProcessingStage(item) for item in _strings(value["stages"])),
        inputs=tuple(_port(item, True) for item in _list(value["inputs"])),
        outputs=tuple(_port(item, False) for item in _list(value["outputs"])),
        parameters=_strings(value["parameters"]), summary=value["summary"],
        composition=value["composition"], function=ProcessingFunction(value["function"]),
    )


def _dependency(value):
    return RuntimeDependency(**_object(value, (item.name for item in fields(RuntimeDependency))))


def _budget(value):
    if value is None:
        return None
    return ExecutionBudget(**_object(value, (item.name for item in fields(ExecutionBudget))))


def validate_operation_document(value, *, owner_id=None):
    """Validate every metadata field without loading a referenced Python module."""
    try:
        value = _object(value, ("schema_version", "owner_id", "definition", "implementation"))
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise RegistryError("registry.unsupported_schema")
        owner = value["owner_id"]
        safe_token(owner)
        if owner_id is not None and owner != owner_id:
            raise RegistryError("registry.owner_mismatch")
        d = _object(value["definition"], (item.name for item in fields(OperationDefinition)))
        i = _object(value["implementation"], ("definition_ref", "handler_ref", "wire_codec_ref", "wire_contract_ref"))
        for name in ("definition_ref", "handler_ref", "wire_codec_ref", "wire_contract_ref"):
            if i[name] is not None:
                _reference(i[name], owner=owner, implementation=True)
        _reference(d["request_type"], owner=owner)
        value_types = d["value_type"] if isinstance(d["value_type"], list) else [d["value_type"]]
        if not value_types or len(value_types) != len(set(value_types)):
            raise RegistryError("registry.invalid_value_types")
        for item in value_types:
            _reference(item, owner=owner)
        # Construct the full policy with sentinel types, validating all fields
        # while leaving optional format/parser implementations unimported.
        OperationDefinition(
            operation_id=d["operation_id"], contract_version=d["contract_version"],
            method_version=d["method_version"], request_type=object, value_type=object,
            required_capabilities=frozenset(_strings(d["required_capabilities"])),
            possible_effects=frozenset(_strings(d["possible_effects"])),
            partial_allowed=d["partial_allowed"],
            optional_capabilities=frozenset(_strings(d["optional_capabilities"])),
            limits=_budget(d["limits"]),
            runtime_dependencies=tuple(_dependency(item) for item in _list(d["runtime_dependencies"])),
            processing=_processing(d["processing"]),
        )
        OperationRef(d["operation_id"], d["contract_version"], **i)
        return value
    except RegistryError:
        raise
    except (ValueError, TypeError, KeyError) as error:
        raise RegistryError("registry.invalid_operation_document") from error


def _root():
    from stratbox.core.registry.resources import registry_root
    return registry_root()


def _read(path):
    from stratbox.core.registry.resources import read_document
    return read_document(path)


@lru_cache(maxsize=1)
def owner_ids():
    """Derive owner identities from packaged OWNER declarations."""
    from stratbox.core.registry.resources import resource_owners
    return resource_owners()


@lru_cache(maxsize=32)
def _operation_documents(owner_id=None):
    """Return complete canonical documents in stable owner/identity order."""
    if owner_id is None:
        return tuple(document for owner in owner_ids() for document in _operation_documents(owner))
    if owner_id not in owner_ids():
        raise RegistryError("registry.owner_unknown")
    directory = _root().joinpath(owner_id, "operations")
    if not directory.is_dir():
        raise RegistryError("registry.operations_required")
    documents = []
    keys = set()
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        if not path.is_file() or not path.name.startswith("OPERATION_") or not path.name.endswith(".yaml"):
            raise RegistryError("registry.unexpected_operation_resource")
        document = validate_operation_document(_read(path), owner_id=owner_id)
        d = document["definition"]
        key = (d["operation_id"], d["contract_version"])
        if path.name != f"OPERATION_{key[0]}_v{key[1]}.yaml" or key in keys:
            raise RegistryError("registry.operation_identity_mismatch")
        keys.add(key)
        documents.append(document)
    if not documents:
        raise RegistryError("registry.empty_owner")
    return tuple(documents)


def operation_documents(owner_id=None):
    """Return independent document copies; callers cannot mutate registry authority."""
    return deepcopy(_operation_documents(owner_id))


@lru_cache(maxsize=1)
def _definition_index():
    result = {}
    for document in _operation_documents():
        d = document["definition"]
        key = (d["operation_id"], d["contract_version"])
        if key in result:
            raise RegistryError("registry.duplicate_contract")
        result[key] = document
    return result


@lru_cache(maxsize=4096)
def definition(operation_id, contract_version=1):
    """Assemble a typed contract from its single declarative authority."""
    if not isinstance(operation_id, str) or type(contract_version) is not int or contract_version < 1:
        raise RegistryError("registry.contract_unavailable")
    try:
        d = _definition_index()[(operation_id, contract_version)]["definition"]
    except (KeyError, TypeError):
        raise RegistryError("registry.contract_unavailable") from None
    value_types = d["value_type"]
    return OperationDefinition(
        operation_id=d["operation_id"], contract_version=d["contract_version"],
        method_version=d["method_version"], request_type=_load_type(d["request_type"]),
        value_type=tuple(_load_type(item) for item in value_types) if isinstance(value_types, list) else _load_type(value_types),
        required_capabilities=frozenset(d["required_capabilities"]),
        possible_effects=frozenset(d["possible_effects"]), partial_allowed=d["partial_allowed"],
        optional_capabilities=frozenset(d["optional_capabilities"]), limits=_budget(d["limits"]),
        runtime_dependencies=tuple(_dependency(item) for item in d["runtime_dependencies"]),
        processing=_processing(d["processing"]),
    )


def _stage(value):
    value = _object(value, (item.name for item in fields(StageDeclaration)))
    return StageDeclaration(
        ProcessingStage(value["stage"]), value["state"], value["reason"],
        tuple(OperationKey(**_object(item, ("operation_id", "contract_version")))
              for item in _list(value["operations"])), value["binding"],
    )


@lru_cache(maxsize=32)
def owner_registration(owner_id):
    """Derive all references and coverage declarations from an owner resource."""
    if owner_id not in owner_ids():
        raise RegistryError("registry.owner_unknown")
    try:
        owner = _object(_read(_root().joinpath(owner_id, "OWNER.yaml")),
                        ("schema_version", "owner_id", "stages"))
        if type(owner["schema_version"]) is not int or owner["schema_version"] != 1:
            raise RegistryError("registry.unsupported_schema")
        if owner["owner_id"] != owner_id:
            raise RegistryError("registry.owner_mismatch")
        return OperationRegistration(
            owner_id, tuple(OperationRef(document["definition"]["operation_id"],
                                          document["definition"]["contract_version"],
                                          **document["implementation"])
                            for document in _operation_documents(owner_id)),
            tuple(_stage(item) for item in _list(owner["stages"])),
        )
    except RegistryError:
        raise
    except (ValueError, TypeError, KeyError) as error:
        raise RegistryError("registry.invalid_owner_document") from error


def operation_references(owner_id, *, definition_module=None):
    """Project a module segment without repeating operation identity lists."""
    references = owner_registration(owner_id).operations
    if definition_module is None:
        return references
    return tuple(ref for ref in references if (module := ref.definition_ref.split(":")[0]) == definition_module
                 or module.startswith(definition_module + "."))
