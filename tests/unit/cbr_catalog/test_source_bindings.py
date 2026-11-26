"""Static source records expose exact scientific scope without route builders."""
import pytest

from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.capabilities.model.methods import MethodRef
from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material, WorkbookEvidence
from stratbox.shared.data.workbook_cells import WorkbookCells


def test_all_57_publications_bind_direct_standard_contracts():
    assert len(DOMAIN.series) == 57
    assert len({record.publication.family_id for record in DOMAIN.series.values()}) == 12
    for identifier, record in DOMAIN.series.items():
        assert record.id == record.publication.series_id == identifier
        for command_id in ("command.request.prepare", "command.publication.scan",
                "command.issue.select", "command.material.identify", "command.table.extract",
                "command.table.interpret", "command.observations.validate", "command.observations.align"):
            spec = record.commands[command_id]
            assert callable(spec.method.resolve())
            assert spec.applicability.source_ids == {identifier}


def test_source_table_meaning_is_owned_by_the_exact_series():
    left = DOMAIN.series["cbr.funding.funds_all"]
    right = DOMAIN.series["cbr.funding.funds_clients"]
    assert left.commands["command.table.interpret"].settings.series_id == left.id
    assert right.commands["command.table.interpret"].settings.series_id == right.id
    assert left.id != right.id
    with pytest.raises(TypeError):
        DOMAIN.series[left.id] = right


def test_source_only_forms_expose_the_actual_remaining_model_obligation():
    from types import SimpleNamespace
    from stratbox.shared.data.values import SourceDataset
    for code in ("134", "803"):
        identifier = "cbr.reporting_forms.f" + code
        record = DOMAIN.series[identifier]
        assert record.commands["command.table.interpret"].settings.require_measurement
        calculation = DOMAIN.calculations["cbr.forms.f" + code + ".model"].commands["command.calculate.formula"]
        with pytest.raises(ValueError, match="requires_publisher_evidence"):
            calculation.method.resolve()({"dataset": SourceDataset(identifier, ())},
                calculation.settings, SimpleNamespace(parameters={}, checkpoint=lambda: None))


def test_historical_html_does_not_inherit_workbook_table_extraction():
    identifier = "cbr.project_finance.escrow"
    spec = DOMAIN.series[identifier].commands["command.table.extract"]
    from types import SimpleNamespace
    with pytest.raises(ValueError, match="physical_evidence_required"):
        spec.method.resolve()({"physical": Material(b"<html>retained original</html>", "text/html", identifier)},
            spec.settings, SimpleNamespace(parameters={}, checkpoint=lambda: None))


def test_variant_names_units_and_metadata_stay_explicit():
    record = DOMAIN.series["cbr.monetary_statistics.balance_odc"]
    settings = record.commands["command.table.interpret"].settings
    variants = {variant.variant_id: variant for variant in settings.variants}
    assert {"table_2", "table_3", "table_4"} <= variants.keys()
    assert {variants[key].unit_anchor for key in ("table_2", "table_3", "table_4")} == {"A2"}
    assert all(variant.unit_policy and variant.qualification for variant in variants.values())


def test_sors_is_an_independent_coupled_model_with_exact_source_dependencies():
    model = DOMAIN.calculations["cbr.sors"]
    assert model.input_topology == "coupled"
    assert sum(bool(item["required"]) for item in model.inputs.values()) == 10
    assert sum(not item["required"] for item in model.inputs.values()) == 1
    assert all(item["source_id"] in DOMAIN.series for item in model.inputs.values())
    for record in DOMAIN.series.values():
        assert not any(".sors." in spec.method.locator for spec in record.commands.values())
    assert "command.model.inputs" in model.commands and "command.values.certify" in model.commands


def test_metadata_description_does_not_resolve_handlers(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Description must not resolve or execute a method")
    monkeypatch.setattr(MethodRef, "resolve", forbidden)
    with StrategyBox(domains=DomainCatalog({"cbr": DOMAIN})) as box:
        values = box.sources.list(domain_id="cbr")
        assert len(values) == 57
        assert box.sources.describe("cbr.reporting_forms.f101")["id"] == "cbr.reporting_forms.f101"


def test_source_applicability_rejects_cross_series_material_before_execution():
    material = Material(b"other source", source_id="cbr.funding.funds_all")
    physical = WorkbookEvidence(material, WorkbookCells((), material.identity))
    with StrategyBox(domains=DomainCatalog({"cbr": DOMAIN})) as box:
        with pytest.raises(ValueError, match="source|context"):
            box.prepare("command.table.extract", inputs={"physical": physical},
                target=SeriesTarget("cbr.funding.funds_clients"))


def test_standard_extraction_graph_keeps_decode_selection_interpretation_and_validation_separate():
    identifier = "cbr.funding.funds_all"
    with StrategyBox(domains=DomainCatalog({"cbr": DOMAIN})) as box:
        prepared = box.prepare("operation.series.extract_workbook",
            inputs={"material": Material(b"not executed", source_id=identifier)},
            target=SeriesTarget(identifier))
        commands = [task.command.id for task in prepared.tasks if getattr(task, "command", None)]
        assert commands == ["command.workbook.decode", "command.table.extract",
            "command.table.interpret", "command.observations.validate"]
