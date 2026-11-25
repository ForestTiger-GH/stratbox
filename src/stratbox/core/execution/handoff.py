"""Typed operation handoff without a scheduler or arbitrary deserialization.

The producer and consumer definitions are trusted executable contracts. Values
are projected only through declared dataclass fields. A retained result is
resolved by the caller's authority and passes the same checks as an in-memory
result. Physical storage and durable job ownership remain with that caller.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from functools import lru_cache
from importlib import import_module, util as import_util
import ast
from types import UnionType
from typing import Any, Callable, Literal, Mapping, Protocol, Union, get_args, get_origin, get_type_hints

from stratbox.core.execution.contracts import (
    EffectReceipt, ExecutionContext, OperationDefinition, OperationResult,
)
from stratbox.shared.identifiers import safe_token
from stratbox.shared.data.operations import OperationKey, assess_input
from stratbox.shared.data.datasets import ComputationReceipt
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.source_context import ValueContext
from stratbox.shared.data.snapshots import DatasetAssembly, DatasetSnapshot, SnapshotReference
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.materials import MaterialArtifact


class HandoffError(ValueError):
    @property
    def code(self) -> str:
        return self.args[0]


@lru_cache(maxsize=256)
def _annotation_imports(module_name):
    """Resolve only imports explicitly declared by a trusted request module."""
    module = import_module(module_name)
    loader = getattr(module, "__loader__", None)
    source = loader.get_source(module_name) if loader is not None and hasattr(loader, "get_source") else None
    if source is None:
        return {}
    result = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0], None)
        elif isinstance(node, ast.ImportFrom):
            name = "." * node.level + (node.module or "")
            target = import_util.resolve_name(name, module.__package__) if node.level else name
            for alias in node.names:
                if alias.name != "*":
                    result[alias.asname or alias.name] = (target, alias.name)
    return result


def request_type_hints(kind):
    """Load optional annotation owners only when an actual request is bound."""
    namespace = dict(vars(import_module(kind.__module__)))
    for _ in range(32):
        try:
            return get_type_hints(kind, namespace)
        except NameError as error:
            reference = _annotation_imports(kind.__module__).get(error.name)
            if reference is None or error.name in namespace:
                raise HandoffError("handoff.request_type_unresolved") from None
            module_name, symbol = reference
            try:
                module = import_module(module_name)
                namespace[error.name] = getattr(module, symbol) if symbol else module
            except (ImportError, AttributeError):
                raise HandoffError("handoff.request_type_unavailable") from None
    raise HandoffError("handoff.request_type_unresolved")


def _field(value: object, name: str) -> object:
    if not is_dataclass(value) or isinstance(value, type) or name not in {
        item.name for item in fields(value)
    }:
        raise HandoffError("handoff.path_unavailable")
    return getattr(value, name)


def _project(value: object, path: str) -> object:
    for name in path.split(".") if path else ():
        value = _field(value, name)
    if value is None:
        raise HandoffError("handoff.output_unavailable")
    return value


def _identity(value: object, computation: ComputationReceipt | None) -> ByteIdentity:
    # Content identity belongs to the exact value. Producer output evidence can
    # describe a wider result and cannot stand in for a projected member.
    from stratbox.core.execution.values import value_identity
    return value_identity(value)


@dataclass(frozen=True, slots=True)
class ProjectedOutput:
    producer: OperationKey
    invocation_id: str
    output_name: str
    contract: DataContract
    outcome: str
    value: object
    qualifications: frozenset[str]
    coverage: frozenset[str]
    used_inputs: tuple[UsedInputReceipt, ...]
    effects: tuple[EffectReceipt, ...]
    computation: ComputationReceipt | None
    identity: ByteIdentity | None
    source_context: ValueContext | None = None


@dataclass(frozen=True, slots=True)
class PreparedInput:
    """An explicitly typed local value, without a fabricated producer.

    Qualifications describe caller-owned preparation. A storage confirmation
    requires projection from an actual verified operation result. Collections
    retain member computations separately instead of inventing a computation.
    """

    contract: DataContract
    value: object
    outcome: str = "succeeded"
    qualifications: frozenset[str] = frozenset()
    coverage: frozenset[str] = frozenset()
    used_inputs: tuple[UsedInputReceipt, ...] = ()
    computation: ComputationReceipt | None = None
    identity: ByteIdentity | None = None
    member_computations: tuple[tuple[str, ComputationReceipt], ...] = ()
    source_context: ValueContext | None = None

    def __post_init__(self):
        if self.source_context is not None and not isinstance(self.source_context, ValueContext):
            raise HandoffError("source.context_invalid")
        if not isinstance(self.contract, DataContract) or self.value is None:
            raise HandoffError("handoff.prepared_input_invalid")
        if self.outcome not in {"succeeded", "partial"}:
            raise HandoffError("processing.outcome_not_accepted")
        for values in (self.qualifications, self.coverage):
            if not isinstance(values, frozenset):
                raise HandoffError("handoff.prepared_input_invalid")
            for name in values:
                safe_token(name)
        if "storage.confirmed" in self.qualifications:
            raise HandoffError("handoff.storage_confirmation_requires_projection")
        if not isinstance(self.used_inputs, tuple) or any(
            not isinstance(item, UsedInputReceipt) for item in self.used_inputs
        ) or self.computation is not None and not isinstance(self.computation, ComputationReceipt):
            raise HandoffError("handoff.prepared_evidence_invalid")
        if self.identity is not None and not isinstance(self.identity, ByteIdentity):
            raise HandoffError("handoff.prepared_evidence_invalid")
        if not isinstance(self.member_computations, tuple) or any(
            not isinstance(item, tuple) or len(item) != 2 or not isinstance(item[1], ComputationReceipt)
            for item in self.member_computations
        ) or len({item[0] for item in self.member_computations}) != len(self.member_computations):
            raise HandoffError("handoff.prepared_evidence_invalid")
        for name, _ in self.member_computations:
            safe_token(name)


def prepare_input(
    value: object, contract: DataContract | None = None, *,
    receipts: tuple[UsedInputReceipt, ...] = (),
    qualifications: frozenset[str] = frozenset(),
    coverage: frozenset[str] = frozenset(),
    computation: ComputationReceipt | None = None,
    source_context: ValueContext | None = None,
) -> PreparedInput:
    """Attach an explicit schema to an inline value without parsing its bytes.

    Only core-owned payload and artifact wrapper contracts have defaults.
    ``artifact_input`` explicitly unwraps an artifact's encoded representation;
    domain decoding remains an independent registered operation.
    """
    if not isinstance(receipts, tuple) or any(not isinstance(item, UsedInputReceipt) for item in receipts):
        raise HandoffError("handoff.prepared_evidence_invalid")
    if isinstance(value, SourcePayload):
        contract = contract or DataContract("source.payload", role=DataRole.ORIGINALS)
        receipts = (*receipts, UsedInputReceipt.for_payload(value, "source"))
    elif isinstance(value, MaterialArtifact):
        contract = contract or DataContract("material.artifact")
        receipts = (*receipts, *value.inputs)
        computation = computation or value.computation
    if contract is None:
        raise HandoffError("handoff.explicit_contract_required")
    return PreparedInput(contract, value, qualifications=qualifications, coverage=coverage,
        used_inputs=tuple(dict.fromkeys(receipts)), computation=computation, identity=_identity(value, computation),
        source_context=source_context)


def artifact_input(artifact: MaterialArtifact) -> PreparedInput:
    """Use a verified artifact's exact representation under its encoded schema."""
    if not isinstance(artifact, MaterialArtifact):
        raise HandoffError("handoff.artifact_required")
    return prepare_input(artifact.representation, artifact.contract,
        receipts=artifact.inputs, computation=artifact.computation)


def collect_inputs(
    items: tuple[ProjectedOutput | PreparedInput, ...], *,
    contract: DataContract, element_contract: DataContract,
) -> PreparedInput:
    """Assemble explicit homogeneous inputs while retaining member evidence.

    A collection has its own declared schema. Common guarantees are intersected;
    a partial member keeps the entire supplied collection partial. An aggregate
    storage confirmation cannot be inferred from stored individual members.
    """
    if not isinstance(items, tuple) or not items:
        raise HandoffError("handoff.collection_empty")
    if not isinstance(contract, DataContract) or not isinstance(element_contract, DataContract):
        raise HandoffError("handoff.explicit_contract_required")
    if any(not isinstance(item, (ProjectedOutput, PreparedInput)) for item in items):
        raise HandoffError("handoff.projection_required")
    if any(item.contract != element_contract for item in items):
        raise HandoffError("processing.schema_mismatch")
    if any(item.outcome not in {"succeeded", "partial"} for item in items):
        raise HandoffError("processing.outcome_not_accepted")
    parents = []
    contexts = []
    from stratbox.core.execution.value_context import value_context
    for index, item in enumerate(items):
        intrinsic = value_context(item.value, item.contract)
        if item.source_context is not None and item.source_context != intrinsic:
            contexts.extend(item.source_context.uses)
        if item.computation is not None:
            parents.append((str(index), item.computation))
        if isinstance(item, PreparedInput):
            parents.extend((f"{index}.{name}", receipt) for name, receipt in item.member_computations)
    values = tuple(item.value for item in items)
    contexts = [*value_context(values, contract).uses, *contexts]
    return PreparedInput(contract, values,
        outcome="partial" if any(item.outcome == "partial" for item in items) else "succeeded",
        qualifications=frozenset.intersection(*(item.qualifications for item in items)) - {"storage.confirmed"},
        coverage=frozenset.intersection(*(item.coverage for item in items)),
        used_inputs=tuple(dict.fromkeys(receipt for item in items for receipt in item.used_inputs)),
        identity=_identity(tuple(item.value for item in items), None),
        member_computations=tuple(parents),
        source_context=ValueContext(tuple(contexts)) if contexts else None)


def project_output(result: OperationResult, output_name: str) -> ProjectedOutput:
    """Project an actually usable declared output, carrying its evidence.

    Qualifiers are guarantees of the trusted operation's declared output, not
    assertions a wire caller may add. Storage confirmation additionally requires
    the corresponding confirmed effect identity in the actual result.
    """
    if not isinstance(result, OperationResult) or result.definition.processing is None:
        raise HandoffError("handoff.processing_unavailable")
    ports = [port for port in result.definition.processing.outputs if port.name == output_name]
    if len(ports) != 1:
        raise HandoffError("handoff.output_unknown")
    port = ports[0]
    if result.outcome not in port.outcomes:
        raise HandoffError("processing.outcome_not_accepted")
    value = _project(result.value, port.path)
    identity = _identity(value, result.computation)
    if "storage.confirmed" in port.qualifications:
        written = any(
            effect.state == "confirmed" and (
                effect.kind.startswith("storage.")
                or effect.kind == "dataset.write" and isinstance(value, SnapshotReference)
            )
            and identity is not None and effect.identity == identity
            for effect in result.effects
        )
        # A verified read can establish an existing object's identity without a
        # fictitious write effect. A writing operation must confirm its effect;
        # seeing its input bytes alone cannot prove publication succeeded.
        read_only = not any(
            kind.startswith("storage.") or kind == "dataset.write"
            for kind in result.definition.possible_effects
        )
        read_back = read_only and identity is not None and any(
            item.identity == identity for item in result.used_inputs
        )
        if not written and not read_back:
            raise HandoffError("handoff.storage_confirmation_missing")
    qualifications, coverage = port.qualifications, port.coverage
    if port.evidence_policy == "value":
        from stratbox.shared.data.assessment import value_evidence
        assessment = value_evidence(value)
        qualifications = assessment.qualifications
        if "storage.confirmed" in port.qualifications and (written or read_back):
            qualifications = qualifications | {"storage.confirmed"}
        coverage = assessment.coverage.facts if assessment.coverage is not None else frozenset()
        if not port.qualifications <= qualifications:
            raise HandoffError("acceptance.qualification_missing")
        if not port.coverage <= coverage:
            raise HandoffError("acceptance.coverage_missing")
    from stratbox.core.execution.value_context import value_context
    carrier = (_project(result.value, port.source_context_path)
        if port.source_context_path is not None else value)
    return ProjectedOutput(
        OperationKey(result.operation_id),
        result.invocation_id, port.name, port.contract, result.outcome, value,
        qualifications, coverage, result.used_inputs, result.effects,
        result.computation, identity,
        value_context(carrier, port.contract if port.source_context_path is None else None),
    )


@dataclass(frozen=True, slots=True)
class ResultReference:
    """Portable, opaque handle issued by a consumer-owned result repository.

    This is an identity/authority claim to resolve, never a file path or an
    instruction to load a Python object. The resolver owns persistence, access
    checks and admitted codecs. The expected output identity is optional only
    for control results that do not declare a content/computation identity.
    """

    owner_id: str
    result_id: str
    producer: OperationKey
    invocation_id: str
    output_name: str
    identity: ByteIdentity | None = None

    def __post_init__(self) -> None:
        for value in (self.owner_id, self.result_id, self.invocation_id, self.output_name):
            safe_token(value)
        if not isinstance(self.producer, OperationKey) or (
            self.identity is not None and not isinstance(self.identity, ByteIdentity)
        ):
            raise ValueError("handoff.reference_invalid")

    def to_dict(self) -> dict:
        return {
            "schema": "stratbox.result_reference", "version": 1,
            "owner_id": self.owner_id, "result_id": self.result_id,
            "operation_id": self.producer.operation_id,
            "invocation_id": self.invocation_id, "output_name": self.output_name,
            "identity": None if self.identity is None else {
                "sha256": self.identity.sha256, "size": self.identity.size,
            },
        }

    @classmethod
    def from_dict(cls, value: Mapping) -> ResultReference:
        required = {
            "schema", "version", "owner_id", "result_id", "operation_id",
            "invocation_id", "output_name", "identity",
        }
        try:
            if not isinstance(value, Mapping) or set(value) != required or (
                value["schema"] != "stratbox.result_reference" or type(value["version"]) is not int
                or value["version"] != 1
            ):
                raise ValueError
            identity = value["identity"]
            if identity is not None:
                if not isinstance(identity, Mapping) or set(identity) != {"sha256", "size"}:
                    raise ValueError
                if not isinstance(identity["sha256"], str) or type(identity["size"]) is not int:
                    raise ValueError
                identity = ByteIdentity(identity["sha256"], identity["size"])
            return cls(
                value["owner_id"], value["result_id"],
                OperationKey(value["operation_id"]),
                value["invocation_id"], value["output_name"], identity,
            )
        except (TypeError, ValueError, KeyError):
            raise HandoffError("handoff.reference_invalid") from None


class ResultResolver(Protocol):
    """Resolve only results admitted by the consumer's authority and codec."""

    owner_id: str

    def resolve(self, reference: ResultReference) -> OperationResult: ...


def resolve_output(reference: ResultReference, resolver: ResultResolver) -> ProjectedOutput:
    if not isinstance(reference, ResultReference):
        raise HandoffError("handoff.reference_invalid")
    if getattr(resolver, "owner_id", None) != reference.owner_id:
        raise HandoffError("handoff.result_owner_mismatch")
    try:
        result = resolver.resolve(reference)
    except Exception:
        raise HandoffError("handoff.result_unavailable") from None
    if not isinstance(result, OperationResult) or (
        result.operation_id != reference.producer.operation_id
        or result.invocation_id != reference.invocation_id
    ):
        raise HandoffError("handoff.result_mismatch")
    projected = project_output(result, reference.output_name)
    if reference.identity is not None and reference.identity != projected.identity:
        raise HandoffError("handoff.identity_mismatch")
    if reference.identity is None and projected.identity is not None:
        raise HandoffError("handoff.identity_required")
    return projected


def adapt_input(
    value: ProjectedOutput | PreparedInput | OperationResult | ResultReference, *,
    output_name: str | None = None, resolver: ResultResolver | None = None,
) -> ProjectedOutput | PreparedInput:
    """Normalize an explicit live, retained or prepared input without guessing.

    Results require an output name even if their contract has a single output.
    Retained references require the caller's resolver and their pinned output.
    Raw values require ``prepare_input`` with an explicit semantic contract.
    """
    if isinstance(value, ResultReference):
        if resolver is None:
            raise HandoffError("handoff.result_resolver_required")
        if output_name is not None and output_name != value.output_name:
            raise HandoffError("handoff.output_mismatch")
        return resolve_output(value, resolver)
    if resolver is not None:
        raise HandoffError("handoff.unexpected_resolver")
    if isinstance(value, OperationResult):
        if output_name is None:
            raise HandoffError("handoff.output_name_required")
        return project_output(value, output_name)
    if isinstance(value, (ProjectedOutput, PreparedInput)):
        if output_name is not None:
            raise HandoffError("handoff.unexpected_output_name")
        return value
    raise HandoffError("handoff.explicit_input_required")


def reference_output(projected: ProjectedOutput, *, owner_id: str, result_id: str) -> ResultReference:
    """Describe a result the consumer has retained; this function performs no write."""
    if not isinstance(projected, ProjectedOutput):
        raise HandoffError("handoff.projection_required")
    return ResultReference(
        owner_id, result_id, projected.producer, projected.invocation_id,
        projected.output_name, projected.identity,
    )


def _matches(value: object, annotation: object) -> bool:
    """Check declared types and tuple members; domains retain value semantics."""
    if annotation is Any:
        return True
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        return any(_matches(value, item) for item in get_args(annotation))
    if origin is Literal:
        return any(type(value) is type(item) and value == item for item in get_args(annotation))
    if annotation is type(None):
        return value is None
    if isinstance(annotation, type):
        return type(value) is annotation if annotation in (bool, int, float, str, bytes) else isinstance(value, annotation)
    if origin is tuple:
        if not isinstance(value, tuple):
            return False
        arguments = get_args(annotation)
        if not arguments:
            return True
        if len(arguments) == 2 and arguments[1] is Ellipsis:
            return all(_matches(item, arguments[0]) for item in value)
        return len(value) == len(arguments) and all(
            _matches(item, kind) for item, kind in zip(value, arguments)
        )
    if isinstance(origin, type):
        return isinstance(value, origin)
    # Literal and similar typing constructs are validated by the request owner;
    # they cannot introduce a class to instantiate or a path to execute.
    return True


def _construct(kind: type, values: dict[str, object]) -> object:
    if not is_dataclass(kind):
        raise HandoffError("handoff.request_dataclass_required")
    declared = {item.name: item for item in fields(kind) if item.init}
    if not set(values) <= set(declared):
        raise HandoffError("handoff.request_field_unknown")
    annotations = request_type_hints(kind)
    for name, value in tuple(values.items()):
        annotation = annotations.get(name, Any)
        if isinstance(value, _Nested):
            if not isinstance(annotation, type) or not is_dataclass(annotation):
                raise HandoffError("handoff.nested_request_unavailable")
            value = values[name] = _construct(annotation, value.values)
        if not _matches(value, annotation):
            raise HandoffError("handoff.input_type_mismatch")
    try:
        return kind(**values)
    except (TypeError, ValueError):
        raise HandoffError("handoff.request_invalid") from None


@dataclass
class _Nested:
    values: dict[str, object]


def _insert(values: dict[str, object], path: str, value: object) -> None:
    head, separator, tail = path.partition(".")
    if not separator:
        if head in values:
            raise HandoffError("handoff.input_parameter_conflict")
        values[head] = value
        return
    if head not in values:
        values[head] = _Nested({})
    nested = values[head]
    if not isinstance(nested, _Nested):
        raise HandoffError("handoff.input_parameter_conflict")
    _insert(nested.values, tail, value)


@dataclass(frozen=True, slots=True)
class BoundRequest:
    """A typed request plus the actual evidence used to assemble its inputs."""

    definition: OperationDefinition
    request: object
    inputs: tuple[tuple[str, ProjectedOutput | PreparedInput], ...]

    def execution_context(self, context: ExecutionContext | None = None) -> ExecutionContext:
        context = context if context is not None else ExecutionContext()
        computations = dict(context.input_computations)
        receipts = list(context.input_receipts)
        transports = list(context.input_transports)
        provenance = list(context.input_provenance)
        source_contexts = (dict(context.input_source_contexts)
            if context.input_source_operation in {None, self.definition.operation_id} else {})
        for name, projected in self.inputs:
            if projected.source_context is not None and projected.source_context.uses:
                existing_context = source_contexts.get(name)
                if existing_context is not None and existing_context != projected.source_context:
                    raise HandoffError("source.context_conflict")
                source_contexts[name] = projected.source_context
            incoming = [(name, projected.computation)] if projected.computation is not None else []
            if isinstance(projected, PreparedInput):
                incoming.extend((f"{name}.{member}", receipt)
                    for member, receipt in projected.member_computations)
            for role, computation in incoming:
                try:
                    safe_token(role)
                except ValueError:
                    raise HandoffError("handoff.parent_role_invalid") from None
                existing = computations.get(role)
                if existing is not None and existing != computation:
                    raise HandoffError("handoff.parent_conflict")
                computations[role] = computation
            receipts.extend(projected.used_inputs)
            provenance.extend(receipt for receipt in projected.used_inputs
                if receipt not in context.input_receipts)
            transports.extend(receipt for receipt in projected.used_inputs
                if projected.identity == receipt.identity and receipt.version is None
                and receipt not in context.input_receipts)
        return replace(context, input_computations=tuple(sorted(computations.items())),
            input_receipts=tuple(dict.fromkeys(receipts)),
            input_transports=tuple(dict.fromkeys(transports)),
            input_provenance=tuple(dict.fromkeys(provenance)),
            input_source_contexts=tuple(sorted(source_contexts.items())),
            input_source_operation=self.definition.operation_id if source_contexts else None)

    def invoke(self, operation: Callable, *, context: ExecutionContext | None = None, **options) -> OperationResult:
        """Invoke an explicitly supplied trusted API; no module names are evaluated."""
        result = operation(self.request, context=self.execution_context(context), **options)
        if not isinstance(result, OperationResult) or result.definition != self.definition:
            raise HandoffError("handoff.operation_mismatch")
        return result


def bind_request(
    definition: OperationDefinition,
    bindings: Mapping[str, ProjectedOutput | PreparedInput],
    *, parameters: Mapping[str, object] | None = None,
) -> BoundRequest:
    """Admit projected inputs and construct only the declared request dataclass.

    No semantic conversion happens here. Different schemas require a declared
    domain operation. Qualifiers, coverage and the producer's actual outcome are
    checked before request construction or consumer invocation.
    """
    if not isinstance(definition, OperationDefinition) or definition.processing is None:
        raise HandoffError("handoff.processing_unavailable")
    semantics = definition.processing
    inputs = {port.name: port for port in semantics.inputs}
    if not isinstance(bindings, Mapping) or not set(bindings) <= set(inputs):
        raise HandoffError("handoff.input_unknown")
    if any(port.required and port.name not in bindings for port in semantics.inputs):
        raise HandoffError("handoff.input_required")
    parameters = {} if parameters is None else parameters
    if not isinstance(parameters, Mapping) or not set(parameters) <= set(semantics.parameters):
        raise HandoffError("handoff.parameter_unknown")
    values = dict(parameters)
    root = None
    admitted = []
    for port in semantics.inputs:
        if port.name not in bindings:
            continue
        projected = bindings[port.name]
        if not isinstance(projected, (ProjectedOutput, PreparedInput)):
            raise HandoffError("handoff.projection_required")
        assessment = assess_input(
            port, projected.contract, outcome=projected.outcome,
            qualifications=projected.qualifications, coverage=projected.coverage,
        )
        if not assessment.compatible:
            raise HandoffError(assessment.reasons[0])
        if port.path:
            _insert(values, port.path, projected.value)
        else:
            if root is not None or values or len(bindings) != 1:
                raise HandoffError("handoff.root_input_conflict")
            root = projected.value
        admitted.append((port.name, projected))
    request = root if root is not None else _construct(definition.request_type, values)
    if not isinstance(request, definition.request_type):
        raise HandoffError("handoff.input_type_mismatch")
    return BoundRequest(definition, request, tuple(admitted))
