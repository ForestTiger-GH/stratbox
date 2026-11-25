"""Typed capability contracts; imports do not activate executable backends."""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from hashlib import sha256
from json import dumps
from types import MappingProxyType
from datetime import date, datetime
from decimal import Decimal
from typing import ClassVar, Mapping

from stratbox.shared.data.processing import DataContract
from stratbox.shared.identifiers import safe_token
from .graph import GraphBody, MethodSlot, RetryPolicy, frozen_mapping, _freeze
from .reuse import ReuseContract


def declaration_tree(value):
    """Canonical metadata projection including type identity without importing it."""
    if isinstance(value, type):
        return {"python_type": value.__module__ + ":" + value.__qualname__}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        return {"bytes_sha256": sha256(value).hexdigest(), "length": len(value)}
    if isinstance(value, (date, datetime)):
        return {"type": type(value).__name__, "iso": value.isoformat()}
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    if is_dataclass(value):
        result = {"$type": type(value).__module__ + ":" + type(value).__qualname__,
                  **{item.name: declaration_tree(getattr(value, item.name)) for item in fields(value)}}
        if hasattr(value, "kind"):
            result["kind"] = value.kind
        return result
    if isinstance(value, Mapping):
        return {key: declaration_tree(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [declaration_tree(item) for item in value]
    if isinstance(value, (frozenset, set)):
        return sorted((declaration_tree(item) for item in value), key=lambda item: dumps(item, sort_keys=True))
    if value is None or type(value) in {str, int, float, bool}:
        return value
    raise ValueError("capability.nonportable_metadata")


def declaration_fingerprint(value):
    return sha256(dumps(declaration_tree(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _field(value, path):
    for part in path.split(".") if path else ():
        value = value[part] if isinstance(value, Mapping) else getattr(value, part)
    return value


@dataclass(frozen=True, slots=True)
class SemanticPredicate:
    """Portable semantic checks, evaluated at the acceptance boundary."""
    path: str = ""
    operator: str = "nonempty"
    expected: object = None
    code: str = "acceptance.semantic_predicate_failed"

    def __post_init__(self):
        if self.operator not in {"nonempty", "equals", "minimum", "maximum", "contains", "one_of"}:
            raise ValueError("capability.invalid_predicate")
        if any(not part.isidentifier() or part.startswith("_") for part in self.path.split(".") if self.path):
            raise ValueError("capability.invalid_predicate_path")
        safe_token(self.code)
        object.__setattr__(self, "expected", _freeze(self.expected))

    def accepts(self, value):
        try:
            actual = _field(value, self.path)
            if self.operator == "nonempty":
                return actual is not None and (len(actual) > 0 if hasattr(actual, "__len__") else bool(actual))
            if self.operator == "equals":
                return actual == self.expected
            if self.operator == "minimum":
                return actual >= self.expected
            if self.operator == "maximum":
                return actual <= self.expected
            if self.operator == "contains":
                return self.expected in actual
            return actual in self.expected
        except (KeyError, AttributeError, TypeError, ValueError):
            return False


@dataclass(frozen=True, slots=True)
class PortContract:
    schema: DataContract | None = None
    value_type: type = object
    required: bool = True
    qualifications: frozenset[str] = frozenset()
    expected_coverage: frozenset[str] = frozenset()
    collection: bool = False
    predicates: tuple[SemanticPredicate, ...] = ()

    def __post_init__(self):
        if self.schema is not None and not isinstance(self.schema, DataContract):
            raise ValueError("capability.invalid_port_schema")
        if not isinstance(self.value_type, type) or type(self.required) is not bool or type(self.collection) is not bool:
            raise ValueError("capability.invalid_port_contract")
        if any(not isinstance(group, frozenset) or any(not isinstance(item, str) for item in group)
               for group in (self.qualifications, self.expected_coverage)):
            raise ValueError("capability.invalid_port_qualification")
        if not isinstance(self.predicates, tuple) or any(not isinstance(item, SemanticPredicate) for item in self.predicates):
            raise ValueError("capability.invalid_predicates")

    @property
    def contract(self):
        return self.schema

    def validate(self, value):
        valid = type(value) is self.value_type if self.value_type in {bool, int, float, str, bytes} else isinstance(value, self.value_type)
        if not valid:
            raise ValueError("acceptance.value_type_mismatch")
        for predicate in self.predicates:
            if not predicate.accepts(value):
                raise ValueError(predicate.code)
        return value

    def compatible_with(self, producer):
        return (isinstance(producer, PortContract)
                and (self.schema is None or self.schema == producer.schema)
                and (producer.value_type is self.value_type if self.value_type in {bool, int, float, str, bytes}
                     else issubclass(producer.value_type, self.value_type))
                and self.qualifications <= producer.qualifications
                and self.expected_coverage <= producer.expected_coverage
                and self.collection == producer.collection)


@dataclass(frozen=True, slots=True)
class CollectionMembership:
    """Closed membership records item identity; coverage is a separate claim."""
    members: tuple[str, ...] = ()
    closed: bool = False
    expected_coverage: frozenset[str] = frozenset()
    observed_coverage: frozenset[str] = frozenset()

    def __post_init__(self):
        if (not isinstance(self.members, tuple) or any(not isinstance(item, str) for item in self.members)
                or len(set(self.members)) != len(self.members) or type(self.closed) is not bool):
            raise ValueError("capability.invalid_membership")
        if any(not isinstance(group, frozenset) or any(not isinstance(item, str) for item in group)
               for group in (self.expected_coverage, self.observed_coverage)):
            raise ValueError("capability.invalid_coverage")

    @property
    def complete(self):
        return self.closed and self.expected_coverage <= self.observed_coverage


@dataclass(frozen=True, slots=True)
class ValueSemantics:
    source_dataset: str | None = None
    source_use: str | None = None
    representation: str | None = None
    schema_edition: str | None = None
    method_fingerprint: str | None = None
    reference_fingerprints: tuple[str, ...] = ()
    qualifications: frozenset[str] = frozenset()
    effect_evidence: tuple[str, ...] = ()
    membership: CollectionMembership | None = None


@dataclass(frozen=True, slots=True)
class AcceptanceContract:
    coherent_outputs: tuple[str, ...] = ()
    predicates: tuple[SemanticPredicate, ...] = ()
    required_checks: tuple[str, ...] = ()
    required_effects: tuple[str, ...] = ()
    partial_allowed: bool = False

    def __post_init__(self):
        for names in (self.coherent_outputs, self.required_checks, self.required_effects):
            if not isinstance(names, tuple) or len(set(names)) != len(names):
                raise ValueError("capability.invalid_acceptance")
        if type(self.partial_allowed) is not bool:
            raise ValueError("capability.invalid_acceptance")
        if not isinstance(self.predicates, tuple) or any(not isinstance(item, SemanticPredicate) for item in self.predicates):
            raise ValueError("capability.invalid_predicates")

    def assess_outputs(self, outputs: Mapping[str, object], *, names=None, settled=()):
        """Return definite rejections and outputs awaiting predicate dependencies.

        Named predicates depend on that named output. A predicate over the
        output map waits for every named output to settle, so a partial map
        never grants an acceptance that a later member can revoke.
        """
        names = tuple(dict.fromkeys((*outputs, *self.coherent_outputs))) if names is None else tuple(names)
        settled = frozenset(settled)
        errors = {name: [] for name in names}
        pending = set()
        coherent = tuple(name for name in self.coherent_outputs if name in errors)
        ready = lambda dependencies: all(name in outputs or name in settled for name in dependencies)
        def reject(targets, code):
            for name in targets:
                if name in errors and code not in errors[name]:
                    errors[name].append(code)
        if coherent:
            if not ready(coherent):
                pending.update(coherent)
            elif not set(self.coherent_outputs) <= outputs.keys():
                reject(coherent, "acceptance.coherent_outputs_missing")
        for predicate in self.predicates:
            first = predicate.path.split(".", 1)[0] if predicate.path else None
            named = first in errors
            dependencies = (first,) if named else names
            targets = (coherent if first in coherent else (first,)) if named else coherent or names
            if not ready(dependencies):
                pending.update(targets)
                continue
            if not predicate.accepts(outputs):
                reject(targets, predicate.code)
        # A coherent group is indivisible even for a predicate naming one
        # member. Definitive errors take precedence over waiting dependencies.
        group_errors = tuple(dict.fromkeys(code for name in coherent for code in errors[name]))
        for code in group_errors:
            reject(coherent, code)
        rejected = {name: tuple(values) for name, values in errors.items() if values}
        pending.difference_update(rejected)
        return MappingProxyType(rejected), frozenset(pending)

    def output_errors(self, outputs: Mapping[str, object], *, names=None):
        """Assess a finalized group whose named outputs have all settled."""
        names = tuple(dict.fromkeys((*outputs, *self.coherent_outputs))) if names is None else tuple(names)
        errors, _ = self.assess_outputs(outputs, names=names, settled=names)
        return errors

    def validate(self, outputs: Mapping[str, object]):
        if not set(self.coherent_outputs) <= outputs.keys():
            raise ValueError("acceptance.coherent_outputs_missing")
        for predicate in self.predicates:
            if not predicate.accepts(outputs):
                raise ValueError(predicate.code)


@dataclass(frozen=True, slots=True)
class CapabilityDefinition:
    capability_id: str
    revision: str = field(default="1", kw_only=True)
    summary: str = field(default="", kw_only=True)
    inputs: Mapping[str, PortContract] = field(default_factory=dict, kw_only=True)
    outputs: Mapping[str, PortContract] = field(default_factory=lambda: {"value": PortContract()}, kw_only=True)
    parameters: Mapping[str, object] = field(default_factory=dict, kw_only=True)
    fixed: Mapping[str, object] = field(default_factory=dict, kw_only=True)
    required_parameters: tuple[str, ...] = field(default=(), kw_only=True)
    required_capabilities: frozenset[str] = field(default=frozenset(), kw_only=True)
    effects: frozenset[str] = field(default=frozenset(), kw_only=True)
    resources: Mapping[str, int] = field(default_factory=dict, kw_only=True)
    reuse: ReuseContract = field(default_factory=ReuseContract, kw_only=True)
    retry: RetryPolicy = field(default_factory=RetryPolicy, kw_only=True)
    acceptance: AcceptanceContract = field(default_factory=AcceptanceContract, kw_only=True)
    schema_ids: tuple[str, ...] = field(default=(), kw_only=True)
    reference_ids: tuple[str, ...] = field(default=(), kw_only=True)
    kind: ClassVar[str] = "capability"

    def __post_init__(self):
        safe_token(self.capability_id)
        if not isinstance(self.revision, str) or not self.revision:
            raise ValueError("capability.revision_required")
        for name in ("inputs", "outputs", "parameters", "fixed", "resources"):
            object.__setattr__(self, name, frozen_mapping(getattr(self, name)))
        for ports in (self.inputs, self.outputs):
            if any(not isinstance(port, PortContract) for port in ports.values()):
                raise ValueError("capability.invalid_ports")
            for name in ports:
                safe_token(name)
        if any(type(value) is not int or value < 1 for value in self.resources.values()):
            raise ValueError("capability.invalid_resources")
        if set(self.inputs) & (self.parameters.keys() | self.fixed.keys() | set(self.required_parameters)):
            raise ValueError("capability.input_parameter_overlap")
        if (not isinstance(self.required_parameters, tuple)
                or len(set(self.required_parameters)) != len(self.required_parameters)):
            raise ValueError("capability.invalid_required_parameters")
        for group in (self.required_capabilities, self.effects):
            if not isinstance(group, frozenset):
                raise ValueError("capability.invalid_effects_or_providers")
            for name in group:
                safe_token(name)
        for name in (*self.parameters, *self.fixed, *self.required_parameters):
            safe_token(name)
        for dependencies in (self.schema_ids, self.reference_ids):
            if not isinstance(dependencies, tuple) or len(set(dependencies)) != len(dependencies):
                raise ValueError("capability.invalid_semantic_dependencies")
            for dependency in dependencies:
                safe_token(dependency)
        if not isinstance(self.acceptance, AcceptanceContract):
            raise ValueError("capability.invalid_acceptance")
        if not set(self.acceptance.coherent_outputs) <= self.outputs.keys():
            raise ValueError("capability.unknown_coherent_output")
        if not isinstance(self.reuse, ReuseContract) or not isinstance(self.retry, RetryPolicy):
            raise ValueError("capability.invalid_policy")

    @property
    def id(self):
        return self.capability_id

    @property
    def fingerprint(self):
        return declaration_fingerprint(self)


@dataclass(frozen=True, slots=True)
class CommandDefinition(CapabilityDefinition):
    implementation_ref: str
    cancellation_boundary: str = "cooperative"
    resource_parameters: Mapping[str, str] = field(default_factory=dict, kw_only=True)
    kind: ClassVar[str] = "command"

    def __post_init__(self):
        CapabilityDefinition.__post_init__(self)
        if not isinstance(self.implementation_ref, str) or self.implementation_ref.count(":") != 1 or not all(self.implementation_ref.split(":")):
            raise ValueError("capability.invalid_implementation_ref")
        if self.cancellation_boundary not in {"cooperative", "atomic", "provider"}:
            raise ValueError("capability.invalid_cancellation_boundary")
        object.__setattr__(self, "resource_parameters", frozen_mapping(self.resource_parameters))
        parameters = self.parameters.keys() | self.fixed.keys() | set(self.required_parameters)
        for resource, parameter in self.resource_parameters.items():
            safe_token(resource)
            if not isinstance(parameter, str) or parameter not in parameters:
                raise ValueError("capability.resource_parameter_undeclared")


@dataclass(frozen=True, slots=True)
class OperationDefinition(CapabilityDefinition):
    body: GraphBody | None = None
    method_slot: str | MethodSlot | None = None
    kind: ClassVar[str] = "operation"

    def __post_init__(self):
        CapabilityDefinition.__post_init__(self)
        if self.body is not None and not isinstance(self.body, GraphBody):
            raise ValueError("capability.invalid_body")
        if self.body is None and self.method_slot is None:
            raise ValueError("capability.operation_body_required")
        if self.body is not None and self.method_slot is not None:
            raise ValueError("capability.operation_body_ambiguous")


@dataclass(frozen=True, slots=True)
class ScenarioDefinition(CapabilityDefinition):
    body: GraphBody
    purpose: str = ""
    policy: str = "continue"
    expenditure: Mapping[str, int] = field(default_factory=dict)
    kind: ClassVar[str] = "scenario"

    def __post_init__(self):
        CapabilityDefinition.__post_init__(self)
        if not isinstance(self.body, GraphBody) or self.policy not in {"continue", "fail_fast"}:
            raise ValueError("capability.invalid_scenario")
        object.__setattr__(self, "expenditure", frozen_mapping(self.expenditure))


@dataclass(frozen=True, slots=True)
class CascadeDefinition(CapabilityDefinition):
    body: GraphBody
    membership: CollectionMembership = field(default_factory=CollectionMembership)
    policy: str = "continue"
    expenditure: Mapping[str, int] = field(default_factory=dict)
    kind: ClassVar[str] = "cascade"

    def __post_init__(self):
        CapabilityDefinition.__post_init__(self)
        if not isinstance(self.body, GraphBody) or not isinstance(self.membership, CollectionMembership) or self.policy not in {"continue", "fail_fast"}:
            raise ValueError("capability.invalid_cascade")
        object.__setattr__(self, "expenditure", frozen_mapping(self.expenditure))


@dataclass(frozen=True, slots=True)
class CapabilityRef:
    capability_id: str
    revision: str | None = None
    fingerprint: str | None = None

    def __post_init__(self):
        safe_token(self.capability_id)


@dataclass(frozen=True, slots=True)
class CompletionState:
    """Orthogonal observations; a completed worker need not mean accepted output."""
    phase: str = "pending"
    outcome: str = "pending"
    qualification: str = "unresolved"
    effect_knowledge: str = "none"
    consumer_acceptance: str = "pending"

    def __post_init__(self):
        choices = {
            "phase": {"pending", "waiting", "running", "completed"},
            "outcome": {"pending", "succeeded", "partial", "failed", "cancelled", "unknown"},
            "qualification": {"unresolved", "reported", "derived", "reconstructed", "partial"},
            "effect_knowledge": {"none", "pending", "confirmed", "failed", "unknown"},
            "consumer_acceptance": {"pending", "accepted", "rejected", "cancelled"},
        }
        if any(getattr(self, name) not in values for name, values in choices.items()):
            raise ValueError("capability.invalid_completion_state")
