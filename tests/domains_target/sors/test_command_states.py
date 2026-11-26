"""Scientific action boundaries retain proofs and isolate continuation state."""
from dataclasses import replace
from pathlib import Path
from runpy import run_path
from types import SimpleNamespace

import pandas as pd
import pytest

from stratbox.domains.cbr.calculations.sors import stages
from stratbox.domains.cbr.calculations.sors.contracts import SorsRunConfig, SorsDeterministicConfig
from stratbox.domains.cbr.calculations.sors.inputs.contracts import SorsSourceInputs
from stratbox.domains.cbr.calculations.sors.publication import SorsPublicationLedger, build_publication_graph
from stratbox.domains.cbr.calculations.sors.strict.interval_closure import SorsIntervalClosureState
from stratbox.shared.evidence import SourcePayload


@pytest.fixture
def state():
    # Reuse the established synthetic publication system, including independent
    # source partitions which justify direct inheritance of the published six.
    fixture = Path(__file__).parents[2] / "cbr_sors_restoration/test_publication_fixed_point.py"
    graph = run_path(str(fixture))["_udmurtia_like_graph"](with_cascade=True)
    config = SorsRunConfig("2026-07-01")
    inputs = stages.SorsModelInputs(SimpleNamespace(fingerprint="synthetic-source"), config,
                                   ("dataset", "model", "run"))
    model = stages.SorsConstraintModel(inputs, graph, build_publication_graph(graph))
    closure = SorsIntervalClosureState(graph, tolerance=1e-7, max_passes=100)
    closure.add_relations(stages.publication_hierarchy_relations(model.publication_graph))
    ledger = SorsPublicationLedger()
    ledger.seed_source_facts(closure.quantities_grid)
    return stages.SorsInferenceState(model, closure, ledger, optimization_complete=True)


def test_independent_actions_reach_same_inherited_fixed_point_without_mutating_input(state):
    original = state.quantities
    original_fingerprint = state.fingerprint
    current = state
    for _ in range(20):
        propagated = stages.bounds_propagate({"state": current}, None, None)["state"]
        candidates = stages.facts_inherit({"state": propagated}, None, None)["candidates"]
        current = stages.facts_reconcile({"state": propagated, "candidates": candidates}, None, None)["state"]
        if current.converged:
            break
    assert current.converged
    fact = current.facts.set_index("quantity_id").loc["metric:U:47:debt_rub"]
    assert fact.published_value == 6
    assert fact.evidence_method == "PUBLISHED_VALUE_INHERITED"
    # Publication facts remain provisional until a global feasibility action.
    assert not bool(fact.is_accepted_fact)
    pd.testing.assert_frame_equal(state.quantities, original)
    assert state.fingerprint == original_fingerprint


def test_candidate_facts_are_bound_to_exact_state(state):
    propagated = stages.bounds_propagate({"state": state}, None, None)["state"]
    candidates = stages.facts_inherit({"state": propagated}, None, None)["candidates"]
    with pytest.raises(ValueError, match="stale_candidate_basis"):
        stages.facts_reconcile({"state": state, "candidates": candidates}, None, None)


def test_compile_cannot_start_from_partial_deterministic_state(state):
    with pytest.raises(ValueError, match="deterministic_closure_required"):
        stages.model_compile({"state": state}, None, None)


def test_pass_limit_is_not_a_successful_fixed_point(state):
    config = replace(state.model.inputs.config,
                     deterministic=SorsDeterministicConfig(max_fixed_point_passes=1))
    limited = replace(state, model=replace(state.model, inputs=replace(state.model.inputs, config=config)))
    propagated = stages.bounds_propagate({"state": limited}, None, None)["state"]
    candidates = stages.facts_inherit({"state": propagated}, None, None)["candidates"]
    current = stages.facts_reconcile({"state": propagated, "candidates": candidates}, None, None)["state"]
    assert not current.converged
    with pytest.raises(ValueError, match="deterministic_pass_limit"):
        stages.bounds_propagate({"state": current}, None, None)


def test_fingerprint_ignores_observational_pass_rows_when_scientific_state_is_same(state):
    same = replace(state, passes=({"publication_pass": 1},))
    assert same.fingerprint == state.fingerprint


def test_model_input_action_rejects_bytes_before_any_hidden_decode(monkeypatch):
    original = SourcePayload(b"not-a-workbook", "application/octet-stream", "source")
    sources = SorsSourceInputs(*([original] * 10))
    monkeypatch.setattr(stages, "parse_source_inputs", lambda *args: pytest.fail("hidden source decoding"))
    context = SimpleNamespace(parameters={"config": SorsRunConfig("2026-07-01")})
    with pytest.raises(ValueError, match="interpreted_inputs_required"):
        stages.model_inputs({"datasets": sources}, None, context)


def test_certification_rejects_stale_global_feasibility(state):
    feasibility = stages.SorsFeasibilityAssessment("problem", "old-state", SimpleNamespace(status="OPTIMAL"))
    with pytest.raises(ValueError, match="stale_certification_basis"):
        stages.values_certify({"state": state, "feasibility": feasibility}, None, None)


def test_only_repository_release_is_manually_versioned():
    assert "rules_version" not in SorsRunConfig.__dataclass_fields__
    config = SorsRunConfig("2026-07-01")
    assert len(config.rules_fingerprint) == 64
