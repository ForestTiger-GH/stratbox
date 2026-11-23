"""Bounded catalog projections and conditional, non-executing route discovery."""

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from stratbox.shared.data.operations import (
    OperationConnection,
    OperationKey,
    ProcessingStage,
    StageCoverage,
    compatible_ports,
)
from stratbox.shared.data.processing import DataRole

if TYPE_CHECKING:
    from stratbox.core.registry.catalog import OperationCatalog, OperationRef


@dataclass(frozen=True, slots=True)
class CatalogPage:
    entries: tuple[dict, ...]
    offset: int
    total: int
    next_offset: int | None


def _port(port) -> dict:
    return {
        "name": port.name,
        "path": port.path,
        "schema_id": port.contract.schema_id,
        "schema_version": port.contract.version,
        "role": port.contract.role.value if port.contract.role else None,
        "qualifications": sorted(port.qualifications),
        "coverage": sorted(port.coverage),
        "outcomes": sorted(port.outcomes),
        **(
            {
                "required": port.required,
                "alternatives": [
                    {
                        "schema_id": item.schema_id,
                        "schema_version": item.version,
                        "role": item.role.value if item.role else None,
                    }
                    for item in port.alternatives
                ],
            }
            if hasattr(port, "required")
            else {}
        ),
    }


def describe_operation(catalog: "OperationCatalog", ref: "OperationRef") -> dict:
    op = catalog.get(ref.operation_id)
    codec = catalog.wire_contract(ref.operation_id)
    required, optional = (
        sorted(op.required_capabilities),
        sorted(op.optional_capabilities),
    )

    def name(kind):
        return f"{kind.__module__}.{kind.__qualname__}"

    processing = op.processing
    from stratbox.core.registry.requirements import describe_source_requirements
    return {
        "operation_id": op.operation_id,
        "source_requirements": describe_source_requirements(catalog, op.operation_id),
        "owner_id": catalog.owner_of(op.operation_id),
        "method_id": op.method_id,
        "purpose": processing.summary
        if processing
        else op.operation_id.rsplit(".", 1)[-1].replace("_", " "),
        "python_request": name(op.request_type),
        "python_result": " | ".join(name(kind) for kind in op.value_type)
        if isinstance(op.value_type, tuple)
        else name(op.value_type),
        "processing": None
        if processing is None
        else {
            "function": processing.function.value,
            "stages": [stage.value for stage in processing.stages],
            "inputs": [_port(port) for port in processing.inputs],
            "outputs": [_port(port) for port in processing.outputs],
            "parameters": list(processing.parameters),
            "composition": processing.composition,
            "routing": "requires_value_and_runtime_admission",
        },
        "machine_input_roles": sorted(codec.input_fields) if codec else [],
        "machine_result_fields": sorted(codec.output_fields) if codec else [],
        "capabilities": [
            {
                "role": role,
                "required": role in required,
                "version": op.capability(role).version,
                "managed_guarantees": sorted(
                    op.capability(role, managed=True).guarantees
                ),
            }
            for role in required + optional
        ],
        "effects": [asdict(effect) for effect in op.effects],
        "runtime_dependencies": [asdict(item) for item in op.runtime_dependencies],
        "limits": asdict(op.limits) if op.limits else None,
        "partial_allowed": op.partial_allowed,
        "cancellation": "cooperative_at_checkpoints",
        "diagnostic_envelope": 3,
        "machine_read_only": codec is not None,
        "machine_typed_references": True,
    }


def catalog_page(
    catalog: "OperationCatalog",
    *,
    owner_id: str | None = None,
    stage: ProcessingStage | str | None = None,
    role: DataRole | str | None = None,
    query: str | None = None,
    machine_only: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> CatalogPage:
    if (
        type(offset) is not int
        or offset < 0
        or type(limit) is not int
        or not 1 <= limit <= 200
    ):
        raise ValueError("registry.invalid_page")
    if type(machine_only) is not bool or (
        query is not None and (not isinstance(query, str) or len(query) > 256)
    ):
        raise ValueError("registry.invalid_filter")
    if owner_id is not None and not isinstance(owner_id, str):
        raise ValueError("registry.invalid_filter")
    stage = ProcessingStage(stage) if stage is not None else None
    role = DataRole(role) if role is not None else None
    query = query.casefold() if query else None
    matches = []
    for ref in catalog.list_refs():
        if (
            owner_id is not None
            and catalog.owner_of(ref.operation_id) != owner_id
        ):
            continue
        if machine_only and ref.wire_contract_ref is None:
            continue
        processing = catalog.get(ref.operation_id).processing
        if stage is not None and (processing is None or stage not in processing.stages):
            continue
        if role is not None and (
            processing is None
            or not any(
                any(
                    contract.role == role
                    for contract in (port.contract, *getattr(port, "alternatives", ()))
                )
                for port in (*processing.inputs, *processing.outputs)
            )
        ):
            continue
        if (
            query
            and query not in ref.operation_id.casefold()
            and (processing is None or query not in processing.summary.casefold())
        ):
            continue
        matches.append(ref)
    selected = matches[offset : offset + limit]
    following = offset + len(selected)
    return CatalogPage(
        tuple(describe_operation(catalog, ref) for ref in selected),
        offset,
        len(matches),
        following if following < len(matches) else None,
    )


def compatible_next(
    catalog: "OperationCatalog",
    operation_id: str,
    *,
    output: str | None = None,
) -> tuple[OperationConnection, ...]:
    producer = catalog.get(operation_id)
    if producer.processing is None:
        return ()
    outputs = producer.processing.outputs
    if output is not None:
        outputs = tuple(port for port in outputs if port.name == output)
        if not outputs:
            raise ValueError("processing.output_unavailable")
    result = []
    for ref in catalog.list_refs():
        if ref.operation_id == operation_id:
            continue
        consumer = catalog.get(ref.operation_id)
        if consumer.processing is None:
            continue
        for produced in outputs:
            for accepted in consumer.processing.inputs:
                if compatible_ports(produced, accepted):
                    result.append(
                        OperationConnection(
                            OperationKey(operation_id),
                            produced.name,
                            OperationKey(ref.operation_id),
                            accepted.name,
                            tuple(sorted(produced.outcomes & accepted.outcomes)),
                            tuple(
                                sorted(
                                    accepted.qualifications - produced.qualifications
                                )
                            ),
                            tuple(sorted(accepted.coverage - produced.coverage)),
                            tuple(
                                port.name
                                for port in consumer.processing.inputs
                                if port.required and port.name != accepted.name
                            ),
                            consumer.processing.parameters,
                        )
                    )
    return tuple(result)


def stage_coverage(
    catalog: "OperationCatalog", owner_id: str
) -> tuple[StageCoverage, ...]:
    from stratbox.core.registry.catalog import RegistryError

    registration = next(
        (item for item in catalog.registrations if item.owner_id == owner_id), None
    )
    if registration is None:
        raise RegistryError("registry.owner_unavailable")
    declarations = {item.stage: item for item in registration.stages}
    result = []
    for stage in ProcessingStage:
        direct, composites = [], []
        for ref in registration.operations:
            op = catalog.get(ref.operation_id)
            if op.processing and stage in op.processing.stages:
                target = composites if op.processing.composition else direct
                target.append(OperationKey(ref.operation_id))
        declaration = declarations.get(stage)
        if declaration is not None:
            if direct:
                raise RegistryError("registry.coverage_conflict")
            for key in declaration.operations:
                try:
                    target = catalog.get(key.operation_id)
                except ValueError as exc:
                    raise RegistryError("registry.delegation_unavailable") from exc
                if target.processing is None or stage not in target.processing.stages:
                    raise RegistryError("registry.delegation_stage_mismatch")
                if target.processing.composition:
                    raise RegistryError("registry.delegation_not_independent")
            result.append(
                StageCoverage(
                    owner_id,
                    stage,
                    declaration.state,
                    declaration.operations,
                    declaration.reason,
                    declaration.binding,
                )
            )
        elif direct:
            result.append(StageCoverage(owner_id, stage, "implemented", tuple(direct)))
        elif composites:
            result.append(
                StageCoverage(
                    owner_id,
                    stage,
                    "composite_only",
                    tuple(composites),
                    "processing.independent_operation_missing",
                )
            )
        else:
            result.append(
                StageCoverage(
                    owner_id,
                    stage,
                    "unassessed",
                    (),
                    "processing.applicability_unassessed",
                )
            )
    return tuple(result)
