"""Typed capability contracts; imports do not activate executable backends."""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from hashlib import sha256
from json import dumps
from types import MappingProxyType
from typing import ClassVar, Mapping

from stratbox.shared.data.processing import DataContract
from stratbox.shared.identifiers import safe_token
from .graph import GraphBody, MethodSlot, RetryPolicy, frozen_mapping
from .reuse import ReuseContract


def declaration_tree(value):
    """Canonical metadata projection including type identity without importing it."""
    if isinstance(value, type):
        return {"python_type": value.__module__ + ":" + value.__qualname__}
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        result = {item.name: declaration_tree(getattr(value, item.name)) for item in fields(value)}
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
        if not isinstance(value, self.value_type):
            raise ValueError("acceptance.value_type_mismatch")
        for predicate in self.predicates:
            if not predicate.accepts(value):
                raise ValueError(predicate.code)
        return value

    def compatible_with(self, producer):
        return (isinstance(producer, PortContract)
                and (self.schema is None or self.schema == producer.schema)
                and issubclass(producer.value_type, self.value_type)
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
        if not isinstance(self.members, tuple) or len(set(self.members)) != len(self.members) or type(self.closed) is not bool:
            raise ValueError("capability.invalid_membership")

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
    kind: ClassVar[str] = "command"

    def __post_init__(self):
        CapabilityDefinition.__post_init__(self)
        if not isinstance(self.implementation_ref, str) or self.implementation_ref.count(":") != 1 or not all(self.implementation_ref.split(":")):
            raise ValueError("capability.invalid_implementation_ref")
        if self.cancellation_boundary not in {"cooperative", "atomic", "provider"}:
            raise ValueError("capability.invalid_cancellation_boundary")


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
