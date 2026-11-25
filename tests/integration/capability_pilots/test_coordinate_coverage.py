"""Sparse observations never turn matching axis marginals into cell coverage."""
from datetime import date
from decimal import Decimal
from itertools import product

import pytest

from stratbox.capabilities.catalog import CatalogContribution, MethodDefinition
from stratbox.capabilities.commands import SELECTION, OBSERVATIONS, COVERAGE
from stratbox.capabilities.model import CommandDefinition
from stratbox.capabilities.operations import extraction_body
from stratbox.core.execution.values.codec import encode_value, decode_value
from stratbox.shared.data.observations import ObservationBatch, Observation, SubjectRef, MetricRef, PeriodRef
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.sdk import StrategyBox
from .conftest import workbook


def sparse_interpret(request, invocation):
    table = request["table"]
    observations = tuple(Observation(SubjectRef("source", row[0].value),
        MetricRef(row[1].value, "RUB", "stock", "1", Decimal(1)),
        PeriodRef("as_of", as_of=date.fromisoformat(row[2].value)), (), "population", row[3].value,
        "reported", table.source_identity.sha256 + ":" + row[3].coordinate)
        for row in table.rows[1:])
    return ObservationBatch("fixture.sparse", 1, "controlled", observations,
        (UsedInputReceipt("source", table.source_identity,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only"),))


def coordinate(subject, metric, period, **overrides):
    return {"subject_namespace": "source", "subject_id": subject, "metric_id": metric,
        "period_kind": "as_of", "period": period, "dimensions": (), "perimeter": "population", **overrides}


@pytest.fixture
def sparse_source(profiled_catalog):
    content = workbook({"Data": (("Subject", "Metric", "Period", "Value"),
        ("A", "X", "2026-01-01", 1), ("B", "Y", "2026-02-01", 2))})
    catalog = profiled_catalog.overlay(CatalogContribution(definitions=(
        CommandDefinition("fixture.sparse_interpret", __name__ + ":sparse_interpret", inputs={"table": SELECTION},
            outputs={"value": OBSERVATIONS}, parameters={"profile": {}}),), methods=(
        MethodDefinition("fixture.sparse_method", "extract.observations", extraction_body("fixture.sparse_interpret")),)))
    profile = {"sheet": "Data", "expected_subjects": ("A", "B"), "expected_metrics": ("X", "Y"),
        "expected_periods": ("2026-01-01", "2026-02-01")}
    return catalog, content, profile


def extract(box, material, profile):
    return box.invoke("extract.observations", inputs={"material": material}, parameters={"profile": profile},
        method_id="fixture.sparse_method", timeout=10)


def test_complete_axis_marginals_do_not_imply_joint_coordinate_coverage(sparse_source):
    catalog, material, profile = sparse_source
    with StrategyBox(capabilities=catalog) as box:
        result = extract(box, material, profile)
        assert result.outcome == "succeeded"
        coverage = result.output("coverage")
        assert coverage.membership_closed and len(coverage.members) == 2
        assert coverage.axis_status == "complete" and coverage.status == "unknown"
        assert "axis_coverage.complete" in coverage.facts
        assert "coverage.complete" not in coverage.facts


def test_explicit_full_cube_detects_six_missing_coordinates(sparse_source):
    catalog, material, profile = sparse_source
    # The caller explicitly enumerates this required cube. The engine does not
    # infer a Cartesian domain from three independent lists of axis members.
    required = tuple(coordinate(*values) for values in product(("A", "B"), ("X", "Y"),
        ("2026-01-01", "2026-02-01")))
    with StrategyBox(capabilities=catalog) as box:
        result = extract(box, material, {**profile, "expected_coordinates": required})
        coverage = result.output("coverage")
        assert coverage.axis_status == "complete" and coverage.status == "partial"
        assert len(coverage.expected_coordinates) == 8 and len(coverage.members) == 2
        finding, = [item for item in result.output("findings") if item.code == "extraction.expected_coordinates_missing"]
        assert finding.count == 6 and finding.scope_id == coverage.scope_id
        restored = decode_value(encode_value(coverage, COVERAGE.schema)).value
        assert restored == coverage and restored.status == "partial"


def test_explicit_sparse_domain_can_be_complete_without_assuming_a_cube(sparse_source):
    catalog, material, profile = sparse_source
    required = (coordinate("A", "X", "2026-01-01"), coordinate("B", "Y", "2026-02-01"))
    with StrategyBox(capabilities=catalog) as box:
        result = extract(box, material, {**profile, "expected_coordinates": required})
        coverage = result.output("coverage")
        assert coverage.status == "complete" and len(coverage.members) == 2
        assert "coverage.complete" in coverage.facts
        batch = result.output("observations")
        assert decode_value(encode_value(batch, OBSERVATIONS.schema)).value.evidence.coverage == coverage


@pytest.mark.parametrize("changed", [
    {"dimensions": (("currency", "RUB"),)}, {"perimeter": "different_population"}, {"period_kind": "capture"},
])
def test_grain_includes_dimensions_perimeter_and_period_kind(sparse_source, changed):
    catalog, material, profile = sparse_source
    required = (coordinate("A", "X", "2026-01-01", **changed), coordinate("B", "Y", "2026-02-01"))
    with StrategyBox(capabilities=catalog) as box:
        result = extract(box, material, {**profile, "expected_coordinates": required})
        assert result.output("coverage").axis_status == "complete"
        assert result.output("coverage").status == "partial"
        assert next(item for item in result.output("findings")
            if item.code == "extraction.expected_coordinates_missing").count == 1


def test_explicit_coordinate_list_is_bounded_before_expansion(sparse_source):
    catalog, material, profile = sparse_source
    required = (coordinate("A", "X", "2026-01-01"), coordinate("B", "Y", "2026-02-01"))
    with StrategyBox(capabilities=catalog) as box:
        result = extract(box, material, {**profile, "expected_coordinates": required, "max_expected_coordinates": 1})
        assert result.outcome == "failed"
        assert "observations" not in result.outputs
        assert any(item.code == "extraction.expected_coordinate_limit" for value in result.results.values() for item in value.diagnostics)
