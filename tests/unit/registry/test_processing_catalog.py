"""Catalog routing remains qualified, bounded and distinct from executable coverage."""

from dataclasses import fields, is_dataclass, replace
import json

import pytest

from stratbox.core.execution import OperationDefinition
from stratbox.core.execution.catalog import (
    OperationCatalog,
    OperationRef,
    OperationRegistration,
    RegistryError,
)
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationKey,
    OperationSemantics,
    ProcessingStage,
    StageDeclaration,
)
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.domains.registry import operation_catalog


def test_pages_cover_the_catalog_in_stable_order_with_bounded_results():
    catalog = operation_catalog()
    all_rows, offset = [], 0
    while True:
        page = catalog.page(offset=offset, limit=7)
        assert len(page.entries) <= 7
        json.dumps(page.entries, allow_nan=False)
        all_rows.extend(page.entries)
        if page.next_offset is None:
            break
        offset = page.next_offset
    assert all_rows == list(catalog.describe())
    assert page.total == len(catalog.references)
    for offset, limit in ((True, 10), (-1, 10), (0, 0), (0, 201)):
        with pytest.raises(ValueError, match="registry.invalid_page"):
            catalog.page(offset=offset, limit=limit)
    assert catalog.page(offset=page.total + 1).entries == ()


def test_stage_role_owner_and_machine_readiness_filters_are_independent():
    catalog = operation_catalog()
    owner = "cbr"
    extracted = catalog.page(owner_id=owner, stage="extract", role="extracts", query="cbr.offices.")
    assert {item["operation_id"] for item in extracted.entries} == {
        "cbr.offices.parse",
        "cbr.offices.capture",
    }
    assert all(item["owner_id"] == owner for item in extracted.entries)
    machines = catalog.page(machine_only=True)
    assert machines.total < len(catalog.references)
    assert all(item["machine_read_only"] for item in machines.entries)
    assert not catalog.page(query="unimplemented imaginary operation").entries


def test_source_and_stock_flow_schemas_cannot_cross_route_by_format_or_role():
    catalog = operation_catalog()
    next_ops = catalog.compatible_next("cbr.offices.acquire", 2)
    assert {item.consumer.operation_id for item in next_ops} == {
        "cbr.escrow.discover",
        "cbr.escrow.parse",
        "cbr.forms.discover_sources",
        "cbr.forms.extract",
        "cbr.forms.parse",
        "cbr.industries.0104a.parse",
        "cbr.industries.0105a.parse",
        "cbr.offices.parse",
        "cbr.offices_reg.parse",
        "cbr.publications.discover",
        "cbr.publications.identify",
        "source.save_original",
        "minfin.extract",
        "minfin.discover",
        "minfin.readable",
        "frg.capture",
        "minfin.extract_document",
        "rosstat.tables.extract_document",
        "rosstat.tables.extract_workbook",
        "rosstat.publications.extract_members",
        "rosstat.publications.inspect_archive",
    }
    # A shared byte payload can reach explicit admission boundaries, but it
    # does not itself establish another publisher's identity or period.
    minfin = next(item for item in next_ops if item.consumer.operation_id == "minfin.extract")
    assert minfin.state == "conditional"
    assert "source.minfin" not in minfin.missing_qualifications
    assert "family_id" in minfin.parameters
    frank = next(item for item in next_ops if item.consumer.operation_id == "frg.capture")
    assert frank.state == "conditional"
    assert set(frank.parameters) == {"source_id", "period", "format"}
    # Naming accepts an admitted Frank RG report, not an arbitrary payload.
    assert not any(item.consumer.operation_id == "frg.prepare_file" for item in next_ops)
    parse = next(
        item for item in next_ops if item.consumer.operation_id == "cbr.offices.parse"
    )
    assert parse.state == "conditional" and "captured_on" in parse.parameters
    debt_next = catalog.compatible_next("cbr.industries.0105a.parse", 3)
    assert debt_next
    assert not any(
        item.consumer.operation_id.startswith("cbr.industries.0104a.")
        for item in debt_next
    )
    with pytest.raises(ValueError, match="processing.output_unavailable"):
        catalog.compatible_next("cbr.offices.parse", 1, output="unknown")


def test_all_builtin_processing_parameters_and_port_roots_match_the_python_contract():
    for definition in operation_catalog().definitions:
        semantics = definition.processing
        assert semantics is not None
        request_fields = (
            {item.name for item in fields(definition.request_type)}
            if is_dataclass(definition.request_type)
            else set()
        )
        assert set(semantics.parameters) <= request_fields, definition.operation_id
        for port in semantics.inputs:
            assert not port.path or port.path.split(".")[0] in request_fields, (
                definition.operation_id,
                port.path,
            )
        value_types = (
            definition.value_type
            if isinstance(definition.value_type, tuple)
            else (definition.value_type,)
        )
        for port in semantics.outputs:
            assert not port.path or any(
                hasattr(kind, port.path.split(".")[0])
                or is_dataclass(kind)
                and port.path.split(".")[0] in {item.name for item in fields(kind)}
                for kind in value_types
            ), (definition.operation_id, port.path)


def test_cbr_scoped_stages_and_shared_storage_are_not_invented_tools():
    catalog = operation_catalog()
    owner = "cbr"
    coverage = {item.stage: item for item in catalog.coverage(owner)}
    assert coverage[ProcessingStage.EXTRACT].state == "implemented"
    assert coverage[ProcessingStage.PRESERVE].state == "delegated"
    assert coverage[ProcessingStage.PRESERVE].binding
    assert coverage[ProcessingStage.INTEGRATE].state == "implemented"
    assert coverage[ProcessingStage.INGEST].state == "delegated"
    assert coverage[ProcessingStage.INGEST].operations == (OperationKey("dataset.write_snapshot", 1),)
    assert coverage[ProcessingStage.PUBLISH].state == "missing"
    assert catalog.page(owner_id=owner, stage="integrate").entries
    from stratbox.domains.cbr.operations.bindings import bind_source
    # Broad publisher coverage must not imply a financial model for every form.
    scoped = bind_source("cbr.reporting_forms.f134", catalog=catalog)
    stages = {item.stage: item for item in scoped.stages}
    assert stages[ProcessingStage.EXTRACT].state == "supported"
    assert stages[ProcessingStage.CALCULATE].state == "missing"
    assert catalog.get("cbr.offices.acquire", 2).required_capabilities == frozenset(
        {"http"}
    )
    with pytest.raises(RegistryError, match="registry.owner_unavailable"):
        catalog.coverage("imaginary.owner")


def test_every_owner_has_consistent_coverage_and_available_delegations():
    catalog = operation_catalog()
    for registration in catalog.registrations:
        coverage = catalog.coverage(registration.owner_id)
        assert {item.stage for item in coverage} == set(ProcessingStage)


def _catalog(monkeypatch, producer, consumer, *, stages=()):
    from stratbox.core.execution import catalog as implementation

    def location(definition):
        return "test_processing_metadata_" + str(id(definition)) + ":DEFINITION"

    def reference(definition):
        return OperationRef(
            definition.operation_id, 1, location(definition), "unavailable.handler:run"
        )

    definitions = {location(item): item for item in (producer, consumer)}
    original = implementation._load
    monkeypatch.setattr(
        implementation,
        "_load",
        lambda ref: definitions[ref] if ref in definitions else original(ref),
    )
    return OperationCatalog.from_registrations(
        OperationRegistration(
            "example", (reference(producer), reference(consumer)), stages=stages
        )
    )


def test_route_conditions_retain_coverage_qualifications_and_additional_inputs(
    monkeypatch,
):
    schema = DataContract("test.extract", 1, DataRole.EXTRACTS)
    producer = OperationDefinition(
        "test.producer",
        1,
        "v1",
        str,
        str,
        processing=OperationSemantics(
            (ProcessingStage.EXTRACT,),
            outputs=(OutputPort("data", schema),),
            summary="Produce data.",
        ),
    )
    consumer = OperationDefinition(
        "test.consumer",
        1,
        "v1",
        str,
        str,
        processing=OperationSemantics(
            (ProcessingStage.CALCULATE,),
            inputs=(
                InputPort(
                    "data",
                    schema,
                    qualifications=frozenset({"reported"}),
                    coverage=frozenset({"all_regions"}),
                ),
                InputPort("reference", schema),
            ),
            summary="Calculate with a reference.",
        ),
    )
    catalog = _catalog(monkeypatch, producer, consumer)
    link = next(
        item
        for item in catalog.compatible_next("test.producer", 1)
        if item.input == "data"
    )
    assert link.state == "conditional"
    assert link.missing_qualifications == ("reported",)
    assert link.missing_coverage == ("all_regions",)
    assert link.additional_inputs == ("reference",)


def test_unresolvable_delegation_and_conflicting_coverage_fail_explicitly(monkeypatch):
    producer = OperationDefinition(
        "test.producer",
        1,
        "v1",
        str,
        str,
        processing=OperationSemantics(
            (ProcessingStage.EXTRACT,), summary="Extract data."
        ),
    )
    consumer = replace(producer, operation_id="test.consumer")
    declaration = StageDeclaration(
        ProcessingStage.RENDER,
        "delegated",
        "test.shared",
        (OperationKey("test.absent", 1),),
        "Bind the existing qualified dataset.",
    )
    catalog = _catalog(monkeypatch, producer, consumer, stages=(declaration,))
    with pytest.raises(RegistryError, match="registry.delegation_unavailable"):
        catalog.coverage("example")
    conflict = StageDeclaration(ProcessingStage.EXTRACT, "missing", "test.missing")
    with pytest.raises(RegistryError, match="registry.coverage_conflict"):
        _catalog(monkeypatch, producer, consumer, stages=(conflict,)).coverage(
            "example"
        )


def test_composition_does_not_claim_an_independently_callable_stage(monkeypatch):
    composite = OperationDefinition(
        "test.producer",
        1,
        "v1",
        str,
        str,
        processing=OperationSemantics(
            (ProcessingStage.ACQUIRE, ProcessingStage.EXTRACT),
            composition=True,
            summary="Capture data.",
        ),
    )
    other = OperationDefinition("test.consumer", 1, "v1", str, str)
    coverage = {
        item.stage: item
        for item in _catalog(monkeypatch, composite, other).coverage("example")
    }
    assert coverage[ProcessingStage.EXTRACT].state == "composite_only"
    assert coverage[ProcessingStage.INTEGRATE].state == "unassessed"
