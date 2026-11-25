"""Declarative processing semantics; routing never executes or admits a value."""

from dataclasses import dataclass, replace
from enum import Enum

from stratbox.shared.data.processing import DataContract
from stratbox.shared.identifiers import safe_token


class ProcessingStage(str, Enum):
    DISCOVER = "discover"
    INSPECT = "inspect"
    ACQUIRE = "acquire"
    PRESERVE = "preserve"
    READABLE = "readable"
    EXTRACT = "extract"
    READ_EXTRACT = "read_extract"
    COMPARE = "compare"
    INTEGRATE = "integrate"
    INGEST = "ingest"
    CALCULATE = "calculate"
    VIEW = "view"
    RENDER = "render"
    PUBLISH = "publish"
    VALIDATE = "validate"


class ProcessingFunction(str, Enum):
    """Technical function, independent of an economic processing stage."""

    PROCESS = "process"
    ENCODE = "encode"
    REPLAY = "replay"
    MAINTAIN = "maintain"
    INSPECT = "inspect"


def technical_operation(definition, function: ProcessingFunction):
    """Declare a technical function without claiming an economic stage."""
    if not isinstance(function, ProcessingFunction) or function is ProcessingFunction.PROCESS or definition.processing is None:
        raise ValueError("processing.technical_function_invalid")
    return replace(definition, processing=replace(definition.processing, stages=(), function=function))


def _tokens(values: frozenset[str]) -> None:
    if not isinstance(values, frozenset):
        raise ValueError("processing.invalid_tokens")
    for value in values:
        safe_token(value)


def _port(name: str, contract: DataContract, path: str) -> None:
    safe_token(name)
    if not isinstance(contract, DataContract):
        raise ValueError("processing.invalid_contract")
    # Paths describe attributes in a typed request/value. They are not Python
    # expressions, file paths, or instructions for arbitrary evaluation.
    if not isinstance(path, str):
        raise ValueError("processing.invalid_path")
    if path:
        for part in path.split("."):
            if not part.isidentifier() or part.startswith("_"):
                raise ValueError("processing.invalid_path")


REQUEST_FIELD_ROLES = frozenset({"input", "parameter", "method", "dependency", "effect", "runtime", "observability"})
COMPUTATIONAL_FIELD_ROLES = frozenset({"input", "parameter", "method", "dependency"})
SOURCE_POLICIES = frozenset({"primary_source_required", "source_collection", "source_optional", "source_inapplicable"})


@dataclass(frozen=True, slots=True)
class RequestField:
    """An exhaustive request coordinate and its responsibility in execution."""
    path: str
    role: str
    reason: str = ""

    def __post_init__(self):
        if not isinstance(self.path, str) or self.role not in REQUEST_FIELD_ROLES:
            raise ValueError("processing.invalid_request_field")
        for segment in self.path.split(".") if self.path else ():
            if not segment.isidentifier() or segment.startswith("_"):
                raise ValueError("processing.invalid_request_path")
        if not isinstance(self.reason, str) or len(self.reason) > 1024:
            raise ValueError("processing.invalid_request_reason")


@dataclass(frozen=True, slots=True)
class InputPort:
    name: str
    contract: DataContract
    path: str = ""
    required: bool = True
    qualifications: frozenset[str] = frozenset()
    coverage: frozenset[str] = frozenset()
    outcomes: frozenset[str] = frozenset({"succeeded"})
    alternatives: tuple[DataContract, ...] = ()
    collection: bool = False

    def __post_init__(self) -> None:
        _port(self.name, self.contract, self.path)
        if type(self.required) is not bool or type(self.collection) is not bool:
            raise ValueError("processing.invalid_required")
        for group in (self.qualifications, self.coverage, self.outcomes):
            _tokens(group)
        if not self.outcomes or not self.outcomes <= {"succeeded", "partial"}:
            raise ValueError("processing.invalid_input_outcomes")
        if (
            not isinstance(self.alternatives, tuple)
            or any(not isinstance(item, DataContract) for item in self.alternatives)
            or len({self.contract, *self.alternatives}) != 1 + len(self.alternatives)
        ):
            raise ValueError("processing.invalid_alternatives")


@dataclass(frozen=True, slots=True)
class OutputPort:
    name: str
    contract: DataContract
    path: str = ""
    qualifications: frozenset[str] = frozenset()
    coverage: frozenset[str] = frozenset()
    outcomes: frozenset[str] = frozenset({"succeeded"})

    source_policy: str = "source_optional"
    collection: bool = False
    source_context_path: str | None = None
    evidence_policy: str = "contract"

    def __post_init__(self) -> None:
        if (self.source_policy not in SOURCE_POLICIES or type(self.collection) is not bool
                or self.evidence_policy not in {"contract", "value"}):
            raise ValueError("processing.invalid_source_policy")
        _port(self.name, self.contract, self.path)
        if self.source_context_path is not None:
            _port(self.name, self.contract, self.source_context_path)
        for group in (self.qualifications, self.coverage, self.outcomes):
            _tokens(group)
        if not self.outcomes or not self.outcomes <= {"succeeded", "partial"}:
            raise ValueError("processing.invalid_output_outcomes")


@dataclass(frozen=True, slots=True)
class OperationSemantics:
    stages: tuple[ProcessingStage, ...]
    inputs: tuple[InputPort, ...] = ()
    outputs: tuple[OutputPort, ...] = ()
    parameters: tuple[str, ...] = ()
    summary: str = ""
    composition: bool = False
    function: ProcessingFunction = ProcessingFunction.PROCESS
    required_parameters: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.stages, tuple)
            or not self.stages and self.function is ProcessingFunction.PROCESS
            or any(not isinstance(stage, ProcessingStage) for stage in self.stages)
            or len(set(self.stages)) != len(self.stages)
        ):
            raise ValueError("processing.invalid_stages")
        if not isinstance(self.function, ProcessingFunction):
            raise ValueError("processing.invalid_function")
        for ports, kind in ((self.inputs, InputPort), (self.outputs, OutputPort)):
            if (
                not isinstance(ports, tuple)
                or any(not isinstance(port, kind) for port in ports)
                or len({port.name for port in ports}) != len(ports)
            ):
                raise ValueError("processing.invalid_ports")
        if not isinstance(self.parameters, tuple) or len(set(self.parameters)) != len(
            self.parameters
        ):
            raise ValueError("processing.invalid_parameters")
        if (not isinstance(self.required_parameters, tuple) or len(set(self.required_parameters)) != len(self.required_parameters)
                or not set(self.required_parameters) <= set(self.parameters)):
            raise ValueError("processing.invalid_required_parameters")
        for name in self.parameters:
            safe_token(name)
        if (
            not isinstance(self.summary, str)
            or not self.summary.strip()
            or len(self.summary) > 1024
            or type(self.composition) is not bool
        ):
            raise ValueError("processing.invalid_summary")


@dataclass(frozen=True, slots=True)
class OperationKey:
    operation_id: str

    def __post_init__(self) -> None:
        safe_token(self.operation_id)


@dataclass(frozen=True, slots=True)
class StageDeclaration:
    """Explicit coverage exceptions and bound delegation, never callable stubs."""

    stage: ProcessingStage
    state: str
    reason: str
    operations: tuple[OperationKey, ...] = ()
    binding: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.stage, ProcessingStage) or self.state not in {
            "missing",
            "inapplicable",
            "delegated",
        }:
            raise ValueError("processing.invalid_coverage_state")
        safe_token(self.reason)
        if (
            not isinstance(self.operations, tuple)
            or any(not isinstance(key, OperationKey) for key in self.operations)
            or len(set(self.operations)) != len(self.operations)
        ):
            raise ValueError("processing.invalid_coverage_operations")
        if self.state == "delegated":
            if (
                not self.operations
                or not isinstance(self.binding, str)
                or not self.binding.strip()
            ):
                raise ValueError("processing.delegation_binding_required")
            if len(self.binding) > 1024:
                raise ValueError("processing.invalid_binding")
        elif self.operations or self.binding is not None:
            raise ValueError("processing.unimplemented_stage_has_operations")


@dataclass(frozen=True, slots=True)
class StageCoverage:
    owner_id: str
    stage: ProcessingStage
    state: str
    operations: tuple[OperationKey, ...]
    reason: str | None = None
    binding: str | None = None


@dataclass(frozen=True, slots=True)
class OperationConnection:
    producer: OperationKey
    output: str
    consumer: OperationKey
    input: str
    outcomes: tuple[str, ...]
    missing_qualifications: tuple[str, ...]
    missing_coverage: tuple[str, ...]
    additional_inputs: tuple[str, ...]
    parameters: tuple[str, ...]

    @property
    def state(self) -> str:
        return (
            "conditional"
            if (
                self.missing_qualifications
                or self.missing_coverage
                or self.additional_inputs
                or self.parameters
            )
            else "compatible"
        )


def compatible_ports(output: OutputPort, input: InputPort) -> bool:
    """Exact editioned contract match, with at least one usable outcome."""
    return output.contract in (input.contract, *input.alternatives) and bool(
        output.outcomes & input.outcomes
    )


@dataclass(frozen=True, slots=True)
class InputAssessment:
    """Metadata compatibility; byte/domain validation still belongs to the operation."""

    compatible: bool
    reasons: tuple[str, ...]


def assess_input(
    port: InputPort,
    contract: DataContract,
    *,
    outcome: str,
    qualifications: frozenset[str] = frozenset(),
    coverage: frozenset[str] = frozenset(),
) -> InputAssessment:
    """Check supplied metadata without promoting a failed or unknown outcome."""
    if not isinstance(port, InputPort) or not isinstance(contract, DataContract):
        raise ValueError("processing.invalid_contract")
    _tokens(qualifications)
    _tokens(coverage)
    if outcome not in {"succeeded", "partial", "failed", "cancelled", "unknown"}:
        raise ValueError("processing.invalid_outcome")
    reasons = []
    if contract not in (port.contract, *port.alternatives):
        reasons.append("processing.schema_mismatch")
    if outcome not in port.outcomes:
        reasons.append("processing.outcome_not_accepted")
    if not port.qualifications <= qualifications:
        reasons.append("processing.qualification_missing")
    if not port.coverage <= coverage:
        reasons.append("processing.coverage_missing")
    return InputAssessment(not reasons, tuple(reasons))
