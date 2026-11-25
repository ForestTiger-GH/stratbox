"""Canonical SORS projection preserves its complete numerical input closure.

The controlled physical-to-observation adapter admits ten small workbooks as a
finite one-region/one-class publication model. The actual strict compiler,
publication closure, solver and product selection remain production algorithms.
"""
from dataclasses import fields, replace
from io import BytesIO

import pandas as pd
import pytest

from stratbox.capabilities.model import ScenarioDefinition, GraphBody, Call, InputRef, OutputRef, ParameterRef
from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsRunConfig
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceBundle, SorsSourceInputs
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import (
    DEPENDENCIES, dependency_manifest, original_input, source_uses,
)
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.common import source_manifest_record
from stratbox.domains.cbr.products.corporate_lending.sors.contracts import SorsPivotRequest
from stratbox.sdk import StrategyBox
from stratbox.sdk.bootstrap import default_snapshot
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import SourcePayload


@pytest.fixture
def finite_sources(monkeypatch):
    from openpyxl import Workbook
    from stratbox.domains.cbr.analytics.corporate_lending.sors.registries.okved2 import read_okved2_classes
    from stratbox.domains.cbr.analytics.corporate_lending.sors.registries.publication_categories import (
        build_publication_categories, enrich_okved2_classes,
    )
    import stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.loader as loader
    required = tuple(item for item in DEPENDENCIES if item.required)
    originals = {}
    for item in required:
        book = Workbook()
        book.active.append([item.source_series, "controlled finite publication"])
        stream = BytesIO()
        book.save(stream)
        originals[item.input_name] = SourcePayload(stream.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", item.series_id)
    inputs = SorsSourceInputs(**originals)
    reference_inputs = []
    all_classes = read_okved2_classes(inputs=reference_inputs)
    all_categories = build_publication_categories(all_classes)
    classes = enrich_okved2_classes(all_classes, all_categories)
    classes = classes[classes["class_code"].eq("01")].copy()
    categories = all_categories[all_categories["member_class_code"].eq("01")].copy()
    region = pd.DataFrame([{"region_code": "r1", "region_name": "Fixture region", "region_order": 1,
        "federal_district_code": "fd1", "federal_district_name": "Fixture district", "federal_district_order": 1}])
    geography = pd.DataFrame([{"geography_node_id": name, "atomic_region_codes": ("r1",), "geography_kind": kind}
        for name, kind in (("country", "country_total"), ("fd1", "federal_district"), ("r1", "region"))])
    grids = {field.name: pd.DataFrame() for field in fields(SorsSourceBundle) if field.name.endswith("_grid")}
    rows = []
    for item in required:
        scope = "SME_IE" if item.input_name.startswith("sme_ie_") else "SME" if item.input_name.startswith("sme_") else "CORPORATE_TOTAL"
        value = {"CORPORATE_TOTAL": 100.0, "SME": 50.0, "SME_IE": 20.0}[scope]
        activity = "01" if item.source_series in {"01_02_C", "01_11_F", "01_11_I"} else "A" if item.source_series in {"01_03_C", "01_12_A"} else "total"
        geo = "fd1" if item.source_series in {"01_03_C", "01_12_A"} else "r1" if "regional" in item.input_name else "country"
        row = {"observation_id": item.source_series + ":fixture", "source_series": item.source_series,
            "geography_node_id": geo, "activity_code": activity, "metric": "debt_rub", "portfolio_scope": scope,
            "value": value, "published_lower": value - .5, "published_upper": value + .5,
            "published_lower_attained": True, "published_upper_attained": False,
            "source_sheet": "controlled", "source_row": 1, "source_column": 1, "as_of_date": "2026-06-01",
            "unit": "million_rubles", "source_role": item.source_role, "record_origin": "PUBLISHED"}
        rows.append(row)
        grids[item.input_name + "_grid"] = pd.DataFrame([row])
    config = SorsRunConfig(as_of_date="2026-06-01", rules_version="finite-canonical-fixture")
    manifest = pd.DataFrame([{**source_manifest_record(item.source_series, originals[item.input_name], 1,
        required=True, role=item.source_role), "series_id": item.series_id, "method_version": item.method_version,
        "as_of_date": config.as_of_date} for item in required])
    grids.update(source_grid=pd.DataFrame(rows), source_manifest_grid=manifest,
        atomic_regions_grid=region, geography_nodes_grid=geography, okved2_classes_grid=classes,
        publication_categories_grid=categories, validation_grid=pd.DataFrame([{"check_id": "fixture", "status": "PASS"}]),
        dependency_manifest_grid=dependency_manifest(inputs, config.as_of_date, config.publication_step))
    bundle = SorsSourceBundle(**grids, as_of_date=config.as_of_date, publication_step=config.publication_step,
        lineage=tuple(original_input(originals[item.input_name], item.source_series) for item in required) + tuple(reference_inputs),
        source_uses=source_uses(inputs), coverage=SnapshotCoverage("partial", "Controlled one-region/one-class model; ten required input publications."))
    calls = []
    def admit(actual, as_of_date, *, publication_step):
        assert as_of_date == config.as_of_date and publication_step == config.publication_step
        identities = tuple(getattr(actual, item.input_name).identity for item in required)
        assert identities == tuple(originals[item.input_name].identity for item in required)
        calls.append(identities)
        return replace(bundle, **{field.name: getattr(bundle, field.name).copy(deep=True)
            for field in fields(bundle) if field.name.endswith("_grid")})
    monkeypatch.setattr(loader, "parse_source_inputs", admit)
    import stratbox.domains.cbr.operations.corporate_lending.sors.api as former_handlers
    def forbidden(*args, **kwargs):
        pytest.fail("Canonical SORS called a nested operation runner")
    monkeypatch.setattr(former_handlers, "prepare_from_originals", forbidden)
    monkeypatch.setattr(former_handlers, "restore_from_originals", forbidden)
    monkeypatch.setattr(former_handlers, "restore", forbidden)
    return inputs, config, bundle, calls


def _errors(result):
    return [(key, value.outcome, value.diagnostics) for key, value in result.results.items()]


def test_narrow_canonical_pivot_keeps_ten_sources_and_all_auxiliary_portfolio_constraints(finite_sources):
    inputs, config, expected_bundle, calls = finite_sources
    catalog = default_snapshot()
    narrow = ScenarioDefinition("fixture.sors.narrow_product", GraphBody((
        Call("restore", "cbr.sors.restore_from_originals", {"sources": InputRef("sources")}, {"config": ParameterRef("config")}),
        Call("pivot", "cbr.sors.build_pivot", {"result": OutputRef("restore", "result")}, {"pivot": ParameterRef("pivot")}),
    ), {"pivot": OutputRef("pivot", "pivot")}), inputs=catalog.definition("cbr.sors.restore_from_originals").inputs,
        outputs=catalog.definition("cbr.sors.build_pivot").outputs, required_parameters=("config", "pivot"))
    with StrategyBox(capabilities=catalog) as box:
        prepared = box.invoke("cbr.sors.prepare_from_originals", inputs={"sources": inputs}, parameters={"config": config}, timeout=30)
        assert prepared.outcome == "succeeded", _errors(prepared)
        assert len(prepared.output("bundle").source_manifest_grid) == 10
        plan = box.prepare(narrow, inputs={"sources": inputs}, parameters={"config": config,
            "pivot": SorsPivotRequest(region_code="r1", metrics=("debt_rub",))}, outputs=("pivot",))
        assert {task.operation_id for task in plan.tasks if task.operation_id} == {
            "cbr.command.sors.prepare_from_originals", "cbr.command.sors.restore", "cbr.command.sors.build_pivot"}
        result = box.run(plan, timeout=30)
        assert result.outcome == "succeeded", _errors(result)
    pivot = result.output("pivot")
    assert pivot.metrics == ("debt_rub",) and pivot.table["class_code"].tolist() == ["01"]
    assert "debt_fx" not in pivot.table.columns
    numerical = next(value.value for value in result.results.values() if value.operation_id == "cbr.command.sors.restore")
    assert numerical.summary.strict_status == "OPTIMAL"
    # The outward component product is corporate-only; the retained numerical
    # model must still contain both auxiliary constraint cubes.
    assert set(numerical.variables_grid["portfolio_scope"]) == {"CORPORATE_TOTAL", "SME", "SME_IE"}
    assert numerical.summary.primary_component_quantities == 4
    assert numerical.summary.auxiliary_component_quantities == 8
    assert numerical.summary.latent_component_quantities == 12
    assert len(numerical.source_bundle.source_manifest_grid) == 10
    assert len(numerical.source_bundle.source_grid) == 10
    assert len(numerical.source_bundle.source_uses) == 10
    assert int(numerical.source_bundle.dependency_manifest_grid["required"].sum()) == 10
    for name in (item.input_name + "_grid" for item in DEPENDENCIES if item.required):
        pd.testing.assert_frame_equal(getattr(numerical.source_bundle, name), getattr(expected_bundle, name))
    assert all(len(identities) == len(set(identities)) == 10 for identities in calls)


def test_solver_backend_failure_is_qualified_and_keeps_full_nonaccepted_model(finite_sources, monkeypatch):
    inputs, config, _, _ = finite_sources
    from stratbox.domains.cbr.analytics.corporate_lending.sors.linear.highs import SorsSolverDependencyError
    import stratbox.domains.cbr.analytics.corporate_lending.sors.linear.highs as highs
    def unavailable():
        raise SorsSolverDependencyError("Controlled missing official HiGHS backend")
    monkeypatch.setattr(highs, "_load_highs", unavailable)
    with StrategyBox(capabilities=default_snapshot()) as box:
        result = box.invoke("cbr.sors.restore_from_originals", inputs={"sources": inputs}, parameters={"config": config}, timeout=30)
    assert result.outcome == "failed", _errors(result)
    failures = [value for value in result.results.values() if value.operation_id == "cbr.command.sors.restore"]
    assert len(failures) == 1 and failures[0].outcome == "failed"
    assert "provider.capability_missing" in {diagnostic.code for diagnostic in failures[0].diagnostics}
    numerical = failures[0].value
    assert numerical.summary.strict_status == "SOLVER_UNAVAILABLE"
    assert len(numerical.source_bundle.source_manifest_grid) == 10
    assert set(numerical.variables_grid["portfolio_scope"]) == {"CORPORATE_TOTAL", "SME", "SME_IE"}
    assert not numerical.regional_okved2_grid["is_lp_certified"].any()
    assert "result" not in result.outputs
