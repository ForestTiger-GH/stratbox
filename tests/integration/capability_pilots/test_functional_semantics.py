"""Actual extraction scope, representation roles and admitted analytical pairs."""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from stratbox.capabilities.commands import OBSERVATIONS, READABLE, REPRESENTATION
from stratbox.capabilities.model import CommandDefinition, PortContract
from stratbox.core.execution.values.codec import encode_value, decode_value
from stratbox.shared.data.assessment import value_evidence
from stratbox.shared.data.processing import DataRole
from stratbox.sdk import StrategyBox
from .conftest import row_profile, ratio_pair, workbook


def echo_value(request, invocation):
    return request["value"]


def test_readable_role_and_actual_evidence_survive_portable_carrier(profiled_catalog, two_tables):
    definition = profiled_catalog.definition("convert.readable")
    assert definition.outputs["readable"].schema.role == DataRole.READABLE
    assert READABLE.value_type is REPRESENTATION.value_type
    assert READABLE.schema != REPRESENTATION.schema
    with StrategyBox(capabilities=profiled_catalog) as box:
        result = box.invoke("convert.readable", inputs={"material": two_tables}, timeout=10)
        assert result.outcome == "succeeded"
        value = result.output("readable")
        actual = value_evidence(value)
        assert "readable.physical" in actual.qualifications
        assert actual.method_fingerprints
        assert actual.coverage.membership_closed
        assert actual.coverage.status == "unknown"
        restored = decode_value(encode_value(value, READABLE.schema)).value
        assert restored.evidence == actual


def test_extraction_accepts_one_coherent_assessed_value_and_real_missing_coverage(profiled_catalog, two_tables):
    profile = row_profile(expected_subjects=("Region-A", "Region-B", "Region-C"))
    with StrategyBox(capabilities=profiled_catalog) as box:
        plan = box.prepare("extract.observations", inputs={"material": two_tables}, parameters={"profile": profile},
            outputs=("observations",))
        root = next(scope for scope in plan.scopes if scope.scope_id == "extract.observations")
        assert set(root.outputs) == {"observations", "coverage", "findings"}
        result = box.run(plan, timeout=10)
        assert result.outcome == "succeeded"
        assessed = result.scope_outputs["extract.observations"]
        batch, coverage, findings = assessed["observations"], assessed["coverage"], assessed["findings"]
        assert batch.evidence.coverage == coverage and batch.evidence.findings == findings
        assert coverage.membership_closed and coverage.status == "partial"
        assert len(coverage.members) == 2
        assert "subject:source:Region-C" not in coverage.observed
        assert next(item for item in findings if item.code == "extraction.expected_coverage_missing").count == 1
        assert "extraction.validated" in batch.evidence.qualifications
        assert batch.evidence.method_fingerprints and batch.evidence.profile_fingerprints
        restored = decode_value(encode_value(batch, OBSERVATIONS.schema)).value
        assert restored == batch


def test_contract_cannot_promote_partial_actual_coverage_to_complete(profiled_catalog, two_tables):
    demanding = CommandDefinition("fixture.require_complete", __name__ + ":echo_value",
        inputs={"value": PortContract(OBSERVATIONS.schema, OBSERVATIONS.value_type,
            expected_coverage=frozenset({"coverage.complete"}))}, outputs={"value": OBSERVATIONS})
    with StrategyBox(capabilities=profiled_catalog) as box:
        extracted = box.invoke("extract.observations", inputs={"material": two_tables},
            parameters={"profile": row_profile(expected_subjects=("Region-A", "Region-B", "Region-C"))}, timeout=10)
        partial = extracted.output("observations")
        with pytest.raises(ValueError):
            box.invoke(demanding, inputs={"value": partial}, timeout=10)
        assert value_evidence(partial).coverage.status == "partial"


def test_selected_view_retains_findings_with_their_original_assessment_scope(profiled_catalog, two_tables):
    with StrategyBox(capabilities=profiled_catalog) as box:
        extracted = box.invoke("extract.observations", inputs={"material": two_tables},
            parameters={"profile": row_profile(expected_subjects=("Region-A", "Region-B", "Region-C"))}, timeout=10)
        batch = extracted.output("observations")
        source_scope = batch.evidence.coverage.scope_id
        viewed = box.invoke("view.table", inputs={"observations": batch},
            parameters={"subject_ids": ("Region-A",)}, timeout=10).output("view")
        evidence = value_evidence(viewed)
        assert len(evidence.coverage.members) == 1
        assert evidence.coverage.scope_id != source_scope
        assert evidence.findings == batch.evidence.findings
        assert {finding.scope_id for finding in evidence.findings} == {source_scope}
        assert "view.selected" in evidence.qualifications


def test_ratio_requires_analytical_pair_and_rejects_metric_revision_mismatch(profiled_catalog, two_tables):
    with StrategyBox(capabilities=profiled_catalog) as box:
        left = box.invoke("extract.observations", inputs={"material": two_tables}, profile_id="fixture.debt", timeout=10).output("observations")
        right = box.invoke("extract.observations", inputs={"material": two_tables}, profile_id="fixture.total", timeout=10).output("observations")
        with pytest.raises(ValueError, match="parameter_required"):
            box.prepare("calculate.ratio", inputs={"numerator": left, "denominator": right})
        pair = ratio_pair()
        wrong = {**pair, "numerator": {**pair["numerator"], "definition_version": "another-edition"}}
        rejected = box.invoke("calculate.ratio", inputs={"numerator": left, "denominator": right}, parameters={"pair": wrong}, timeout=10)
        assert rejected.outcome == "failed"
        assert any(d.code == "calculation.pair_metric_mismatch" for item in rejected.results.values() for d in item.diagnostics)
        accepted = box.invoke("calculate.ratio", inputs={"numerator": left, "denominator": right}, parameters={"pair": pair}, timeout=10)
        assert accepted.outcome == "succeeded"
        value = accepted.output("observations")
        basis, = value.evidence.calculations
        assert basis.rule_id == pair["id"] and basis.rule_revision == "1"
        assert {role for role, _, _ in basis.inputs} == {"numerator", "denominator"}
        assert value.release_id != left.release_id
        viewed = box.invoke("view.table", inputs={"observations": value}, timeout=10).output("view")
        rendered = box.invoke("render.table", inputs={"view": viewed}, timeout=10).output("representation")
        assert rendered.evidence.calculations == value.evidence.calculations
        assert decode_value(encode_value(rendered, REPRESENTATION.schema)).value.evidence == rendered.evidence


def test_explicit_stock_flow_pair_uses_admitted_period_end_policy(profiled_catalog):
    material = workbook({"Debt": (("Region", "Value"), ("Region-A", 10)),
        "Total": (("Region", "Value"), ("Region-A", 100))})
    common = {"release_id": "2026-12-31", "expected_subjects": ("Region-A",)}
    stock = row_profile(as_of="2026-12-31", **common)
    flow = row_profile("Total", "fixture.total", quantity_kind="flow", period_kind="interval",
        start="2026-01-01", end="2026-12-31", **common)
    pair = ratio_pair(period_policy="same_end", rationale="Year-end debt stock divided by the matching annual income flow.")
    pair["denominator"] = {**pair["denominator"], "quantity_kind": "flow"}
    pair["result"] = {**pair["result"], "unit": "years"}
    with StrategyBox(capabilities=profiled_catalog) as box:
        left = box.invoke("extract.observations", inputs={"material": material}, parameters={"profile": stock}, timeout=10).output("observations")
        right = box.invoke("extract.observations", inputs={"material": material}, parameters={"profile": flow}, timeout=10).output("observations")
        result = box.invoke("calculate.ratio", inputs={"numerator": left, "denominator": right}, parameters={"pair": pair}, timeout=10)
        assert result.outcome == "succeeded"
        row, = result.output("observations").observations
        assert row.value == Decimal("0.1") and row.metric.unit == "years"
        assert row.period.as_of == date(2026, 12, 31)


def test_ratio_pins_both_input_releases_instead_of_silently_borrowing_one(profiled_catalog, two_tables):
    with StrategyBox(capabilities=profiled_catalog) as box:
        left = box.invoke("extract.observations", inputs={"material": two_tables}, profile_id="fixture.debt", timeout=10).output("observations")
        right = box.invoke("extract.observations", inputs={"material": two_tables},
            parameters={"profile": row_profile("Total", "fixture.total", release_id="2026-10-02")}, timeout=10).output("observations")
        ordinary = box.invoke("calculate.ratio", inputs={"numerator": left, "denominator": right}, parameters={"pair": ratio_pair()}, timeout=10)
        assert ordinary.outcome == "failed"
        pair = ratio_pair(release_policy="pinned")
        pair["numerator"] = {**pair["numerator"], "release_id": left.release_id}
        pair["denominator"] = {**pair["denominator"], "release_id": right.release_id}
        admitted = box.invoke("calculate.ratio", inputs={"numerator": left, "denominator": right}, parameters={"pair": pair}, timeout=10)
        assert admitted.outcome == "succeeded"
        basis, = admitted.output("observations").evidence.calculations
        assert [(role, release) for role, _, release in basis.inputs] == [
            ("numerator", "2026-10-01"), ("denominator", "2026-10-02")]
