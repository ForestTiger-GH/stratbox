"""Independent SORS actions over owned, fingerprinted scientific states.

No action acquires a source, schedules another action, persists a result or sends
a notification. The standard operation owns the iteration and its admission.
Mutable numerical helpers are private to one action and copied before use.
"""
from __future__ import annotations
from stratbox.domains.cbr.calculations.sors.fingerprints import implementation_fingerprint

from copy import deepcopy
from dataclasses import dataclass, field, replace
from hashlib import sha256
from functools import wraps
from stratbox.domains.cbr.calculations.sors.linear.highs import solver_budget
from collections.abc import Mapping

import pandas as pd

from stratbox.domains.cbr.calculations.sors.assembly import _identities, assemble_result
from stratbox.domains.cbr.calculations.sors.contracts import SorsRunConfig
from stratbox.domains.cbr.calculations.sors.inputs.contracts import SorsSourceBundle, SorsSourceInputs
from stratbox.domains.cbr.calculations.sors.inputs.validation import validate_source_bundle
from stratbox.domains.cbr.calculations.sors.portfolio import PORTFOLIO_SCOPES, PRIMARY_PORTFOLIO_SCOPE
from stratbox.domains.cbr.calculations.sors.publication import RoundingPolicy, SorsPublicationLedger
from stratbox.domains.cbr.calculations.sors.publication.closure import SorsPublicationClosureExecution
from stratbox.domains.cbr.calculations.sors.publication.inheritance import run_value_inheritance
from stratbox.domains.cbr.calculations.sors.publication.partitions import build_publication_graph, publication_hierarchy_relations
from stratbox.domains.cbr.calculations.sors.strict.quantities import build_quantity_graph, attach_observation_bindings
from stratbox.domains.cbr.calculations.sors.strict.interval_closure import SorsIntervalClosureState
from stratbox.domains.cbr.calculations.sors.strict.compiler import compile_strict_problem
from stratbox.domains.cbr.calculations.sors.strict.solver import run_strict_feasibility
from stratbox.domains.cbr.calculations.sors.optimization.targets import select_optimization_targets, solve_target_minmax, apply_strict_minmax_bounds
from stratbox.domains.cbr.calculations.sors.optimization.distortion import solve_rounding_profile, configure_optimal_face_session
from stratbox.domains.cbr.calculations.sors.optimization.selection import run_controlled_selection
from stratbox.domains.cbr.calculations.sors.optimization.proposals import _model_assumption_tier, _promote_rounding_optimal_buckets, _promote_selected
from stratbox.shared.data.tables import table_identity
from stratbox.shared.data.values import Assessment


def _hash(*parts):
    return sha256("\n".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def _frames(*items):
    return table_identity(tuple((str(index), frame) for index, frame in enumerate(items)),
                          allow_infinite=True).sha256


def linear_fingerprint(problem):
    arrays = (problem.matrix.indptr, problem.matrix.indices, problem.matrix.data,
              problem.row_lower, problem.row_upper, problem.col_lower, problem.col_upper, problem.objective)
    return _hash(problem.model_layer, problem.matrix.shape,
                 _frames(problem.constraints_grid, problem.variables_grid),
                 *((str(a.dtype), a.shape, a.tobytes().hex()) for a in arrays))


def _concat(items):
    frames = [frame for frame in items if frame is not None and not frame.empty]
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def _checkpoint(context):
    if context is not None:
        check = getattr(context, "checkpoint", None) or getattr(context, "check_cancelled", None)
        if check is not None:
            check()


def _solver_action(method):
    @wraps(method)
    def execute(inputs, settings, context):
        def remaining():
            _checkpoint(context)
            if context is not None and hasattr(context, "remaining_seconds"):
                return context.remaining_seconds()
            return float("inf")
        with solver_budget(remaining):
            return method(inputs, settings, context)
    return execute


def parse_source_inputs(*args, **kwargs):
    from stratbox.domains.cbr.calculations.sors.inputs.loader import parse_source_inputs as prepare
    return prepare(*args, **kwargs)


def _config(settings, context, bundle=None):
    parameters = getattr(context, "parameters", {}) if context is not None else {}
    candidate = parameters.get("config")
    if candidate is None and isinstance(settings, SorsRunConfig):
        candidate = settings
    if candidate is None and hasattr(settings, "get"):
        candidate = settings.get("config")
    if candidate is not None:
        if not isinstance(candidate, SorsRunConfig):
            raise TypeError("sors.run_config_required")
        return candidate
    if bundle is not None and bundle.as_of_date:
        return SorsRunConfig(bundle.as_of_date, publication_step=bundle.publication_step or 1.0)
    raise ValueError("sors.run_config_required")


@dataclass(frozen=True)
class SorsModelInputs:
    bundle: SorsSourceBundle
    config: SorsRunConfig
    identities: tuple[str, str, str]
    implementation: str = field(default_factory=implementation_fingerprint)

    @property
    def fingerprint(self):
        return _hash(*self.identities, self.bundle.fingerprint, self.config, self.implementation)


@dataclass(frozen=True)
class SorsConstraintModel:
    inputs: SorsModelInputs
    quantity_graph: object = field(repr=False)
    publication_graph: object = field(repr=False)

    @property
    def fingerprint(self):
        return _hash(self.inputs.fingerprint, _frames(
            self.quantity_graph.quantities_grid, self.quantity_graph.relations_grid,
            self.quantity_graph.observation_bindings_grid, self.publication_graph.partitions_grid))


@dataclass(frozen=True)
class SorsInferenceState:
    model: SorsConstraintModel
    _closure: SorsIntervalClosureState = field(repr=False)
    _ledger: SorsPublicationLedger = field(repr=False)
    passes: tuple[dict, ...] = ()
    inheritance_events: tuple[object, ...] = ()
    tokens: object = field(default_factory=pd.DataFrame, repr=False)
    last_new_facts: int = 0
    last_bound_updates: int = 0
    closure_steps: int = 0
    converged: bool = False
    optimization_phase: str = "strict"
    optimization_round: int = 0
    optimization_complete: bool = False
    optimization_results: tuple[object, ...] = ()

    @property
    def scientific_fingerprint(self):
        return _hash(self.model.fingerprint, _frames(
            self._closure.quantities_grid, self._ledger.facts_grid()))

    @property
    def fingerprint(self):
        return _hash(self.scientific_fingerprint, self.converged, self.last_new_facts, self.last_bound_updates, self.closure_steps,
                     self.optimization_phase, self.optimization_round,
                     self.optimization_complete, tuple(record.fingerprint for record in self.optimization_results))

    @property
    def quantities(self):
        return self._closure.quantities_grid.copy(deep=True)

    @property
    def facts(self):
        return self._ledger.facts_grid().copy(deep=True)


@dataclass(frozen=True)
class SorsCandidateFacts:
    state_basis: str
    _ledger: SorsPublicationLedger = field(repr=False)
    events: object = field(default_factory=pd.DataFrame)
    tokens: object = field(default_factory=pd.DataFrame)

    @property
    def fingerprint(self):
        return _hash(self.state_basis, _frames(self._ledger.facts_grid(), self.events, self.tokens))


@dataclass(frozen=True)
class SorsCompiledProblem:
    state: SorsInferenceState
    compilation: object = field(repr=False)

    @property
    def fingerprint(self):
        return _hash(self.state.fingerprint, linear_fingerprint(self.compilation.problem),
                     _frames(self.compilation.target_catalog_grid))


@dataclass(frozen=True)
class SorsFeasibilityAssessment:
    problem_basis: str
    state_basis: str
    execution: object = field(repr=False)
    problem: SorsCompiledProblem | None = field(default=None, repr=False)

    @property
    def success(self):
        return bool(self.execution.feasibility.success)

    @property
    def status(self):
        return self.execution.status

    @property
    def fingerprint(self):
        return _hash(self.problem_basis, self.state_basis, self.status,
                     _frames(self.execution.solver_runs_grid))


@dataclass(frozen=True)
class SorsOptimizationRecord:
    """Compact proof history; accepted waves retain no duplicate inference engine."""
    phase: str
    status: str
    changed: bool
    complete: bool
    next_phase: str
    bounds: object
    solver_runs: object
    rounding_profiles: object
    selection_attempts: object
    feasibility: object
    new_facts: int

    @property
    def fingerprint(self):
        return _hash(self.phase, self.status, self.changed, self.complete, self.next_phase, self.new_facts,
                     _frames(self.bounds, self.solver_runs, self.rounding_profiles, self.selection_attempts))


@dataclass(frozen=True)
class SorsOptimizationProposal:
    state_basis: str
    problem_basis: str
    phase: str
    status: str
    _closure: SorsIntervalClosureState = field(repr=False)
    _ledger: SorsPublicationLedger = field(repr=False)
    changed: bool = False
    complete: bool = False
    next_phase: str = "strict"
    bounds: object = field(default_factory=pd.DataFrame)
    solver_runs: object = field(default_factory=pd.DataFrame)
    rounding_profiles: object = field(default_factory=pd.DataFrame)
    selection_attempts: object = field(default_factory=pd.DataFrame)
    feasibility: object = field(default=None, repr=False)
    new_facts: int = 0

    @property
    def fingerprint(self):
        return _hash(self.state_basis, self.problem_basis, self.phase, self.status,
                     self.changed, self.complete, self.next_phase, self.new_facts,
                     _frames(self._closure.quantities_grid, self._ledger.facts_grid(), self.bounds,
                             self.solver_runs, self.rounding_profiles, self.selection_attempts))


@dataclass(frozen=True)
class SorsCertifiedValues:
    result: object
    state_basis: str
    feasibility_basis: str

    @property
    def fingerprint(self):
        return _hash(self.state_basis, self.feasibility_basis, self.result.fingerprint)


def model_inputs(inputs, settings, context):
    """Admit full interpreted inputs; source decoding is an upstream action."""
    _checkpoint(context)
    value = inputs.get("datasets", inputs.get("bundle"))
    if isinstance(value, SorsModelInputs):
        settings = value.config
        value = value.bundle
    native = getattr(value, "native", None)
    if native is not None:
        value = native
    config = _config(settings, context, value if isinstance(value, SorsSourceBundle) else None)
    retained_uses = []
    if isinstance(value, Mapping):
        from stratbox.domains.cbr.calculations.sors.inputs.dependencies import DEPENDENCIES, original_input
        known = {item.input_name for item in DEPENDENCIES}
        if set(value) - known:
            raise ValueError("sors.unknown_input_role")
        roles = {}
        for dependency in DEPENDENCIES:
            supplied = value.get(dependency.input_name)
            if supplied is None:
                if dependency.required:
                    raise ValueError("sors.required_source_missing:" + dependency.input_name)
                roles[dependency.input_name] = None
                continue
            actual = getattr(supplied, "source_id", getattr(supplied, "series_id", None))
            # New shared dataset wrappers establish source identity independently
            # of the native scientific schema retained for exact interpretation.
            if hasattr(supplied, "native"):
                if actual != dependency.series_id:
                    raise ValueError("sors.input_source_mismatch:" + dependency.input_name)
                wrapper = supplied
                supplied = supplied.native
                for use in getattr(wrapper, "source_uses", ()):
                    if use.coordinate.source_id != dependency.series_id:
                        raise ValueError("sors.input_origin_mismatch:" + dependency.input_name)
                    if supplied is not None and use.coordinate.material_identity != original_input(supplied, dependency.source_series).identity:
                        raise ValueError("sors.input_material_origin_mismatch:" + dependency.input_name)
                    retained_uses.append(replace(use, input_role=dependency.input_name))
                if supplied is None:
                    raise ValueError("sors.source_numerical_schema_required:" + dependency.input_name)
            roles[dependency.input_name] = supplied
        value = SorsSourceInputs(**roles)
    if isinstance(value, SorsSourceInputs):
        from stratbox.shared.evidence import SourcePayload
        from dataclasses import fields
        if any(isinstance(getattr(value, item.name), SourcePayload) for item in fields(value)):
            raise ValueError("sors.interpreted_inputs_required")
        value = parse_source_inputs(value, config.as_of_date, config.publication_step)
    if not isinstance(value, SorsSourceBundle):
        raise TypeError("sors.source_bundle_required")
    if retained_uses:
        from stratbox.domains.cbr.calculations.sors.identity import seal_content
        roles_with_origin = {use.input_role for use in retained_uses}
        uses = (*retained_uses, *(use for use in value.source_uses if use.input_role not in roles_with_origin))
        value = seal_content(replace(value, source_uses=tuple(uses)))
    if value.as_of_date is not None and value.as_of_date != config.as_of_date:
        raise ValueError("sors.report_date_mismatch")
    if value.publication_step is not None and value.publication_step != config.publication_step:
        raise ValueError("sors.publication_step_mismatch")
    from stratbox.domains.cbr.calculations.sors.admission import validate_bundle_context
    validate_bundle_context(value)
    validate_source_bundle(value, raise_on_error=True)
    if "portfolio_scope" not in value.source_grid or set(value.source_grid["portfolio_scope"]) != set(PORTFOLIO_SCOPES):
        raise ValueError("sors.full_coupled_portfolio_inputs_required")
    basis = _identities(value, config)
    if context is not None and hasattr(context, "use"):
        for receipt in value.lineage:
            context.use(receipt)
    return {"bundle": SorsModelInputs(deepcopy(value), config, basis)}


def constraints_build(inputs, settings, context):
    _checkpoint(context)
    bundle = inputs["bundle"]
    if not isinstance(bundle, SorsModelInputs):
        raise TypeError("sors.model_inputs_required")
    _check_build(bundle)
    quantities = build_quantity_graph(bundle.bundle)
    admitted = replace(bundle, bundle=attach_observation_bindings(bundle.bundle, quantities))
    publication = build_publication_graph(quantities)
    model = SorsConstraintModel(admitted, quantities, publication)
    config = admitted.config
    closure = SorsIntervalClosureState(quantities, tolerance=config.point_tolerance / 10,
                                      max_passes=config.deterministic.interval_closure_max_passes)
    closure.add_relations(publication_hierarchy_relations(publication))
    ledger = SorsPublicationLedger()
    ledger.seed_source_facts(closure.quantities_grid)
    state = SorsInferenceState(model, closure, ledger,
                              optimization_complete=config.optimization.mode == "none")
    return {"graph": model, "state": state}


def _check_build(inputs):
    from .fingerprints import implementation_fingerprint
    if inputs.implementation != implementation_fingerprint():
        raise ValueError("sors.retained_model_build_mismatch")


def _state(inputs):
    state = inputs["state"]
    if not isinstance(state, SorsInferenceState):
        raise TypeError("sors.inference_state_required")
    _check_build(state.model.inputs)
    model = inputs.get("graph", state.model)
    if model is not state.model and model.fingerprint != state.model.fingerprint:
        raise ValueError("sors.constraint_graph_mismatch")
    return state


def bounds_propagate(inputs, settings, context):
    _checkpoint(context)
    state = _state(inputs)
    config = state.model.inputs.config
    if state.closure_steps >= config.deterministic.max_fixed_point_passes:
        raise ValueError("sors.deterministic_pass_limit")
    closure, ledger = deepcopy(state._closure), deepcopy(state._ledger)
    before = len(ledger.current_quantity_ids)
    result = closure.run()
    ledger.promote_interval_facts(closure.quantities_grid, policy=RoundingPolicy(config.publication_step),
                                  point_tolerance=config.point_tolerance,
                                  restoration_pass=len(state.passes) + 1,
                                  optimization_round=state.optimization_round or None)
    updated, changed = ledger.apply_current_facts_to_quantities(
        closure.quantities_grid, policy=RoundingPolicy(config.publication_step),
        tolerance=config.point_tolerance)
    if changed:
        closure.replace_quantities(updated)
    if result.bound_updates or changed or len(ledger.current_quantity_ids) != before:
        ledger.confirm_feasibility(False)
    next_state = replace(state, _closure=closure, _ledger=ledger,
                         last_new_facts=len(ledger.current_quantity_ids) - before,
                         last_bound_updates=result.bound_updates + len(changed), converged=False)
    return {"state": next_state, "derivations": result.derivations_grid.copy(deep=True)}


def facts_inherit(inputs, settings, context):
    _checkpoint(context)
    state = _state(inputs)
    ledger = deepcopy(state._ledger)
    config = state.model.inputs.config
    if config.deterministic.inheritance_enabled:
        result = run_value_inheritance(state.model.publication_graph, state._closure.quantities_grid,
                                       ledger, restoration_pass=len(state.passes) + 1,
                                       optimization_round=state.optimization_round or None)
        events, tokens = result.events_grid, result.tokens_grid
    else:
        events = tokens = pd.DataFrame()
    return {"candidates": SorsCandidateFacts(state.fingerprint, ledger, events.copy(deep=True), tokens.copy(deep=True))}


def facts_reconcile(inputs, settings, context):
    _checkpoint(context)
    state = _state(inputs)
    config = state.model.inputs.config
    proposal = inputs.get("optimization")
    if proposal is not None:
        if not isinstance(proposal, SorsOptimizationProposal) or proposal.state_basis != state.fingerprint:
            raise ValueError("sors.stale_optimization_basis")
        if proposal.status not in {"OPTIMAL", "NO_TARGETS", "DISABLED"}:
            raise ValueError("sors.optimization_unresolved:" + proposal.status)
        if state.optimization_round >= config.optimization.max_fixed_point_rounds and not proposal.complete:
            raise ValueError("sors.optimization_round_limit")
        closure, ledger = deepcopy(proposal._closure), deepcopy(proposal._ledger)
        if proposal.changed:
            ledger.confirm_feasibility(False)
        record = SorsOptimizationRecord(proposal.phase, proposal.status, proposal.changed,
            proposal.complete, proposal.next_phase, proposal.bounds, proposal.solver_runs,
            proposal.rounding_profiles, proposal.selection_attempts, proposal.feasibility, proposal.new_facts)
        next_state = replace(state, _closure=closure, _ledger=ledger,
                             optimization_phase=proposal.next_phase,
                             optimization_round=state.optimization_round + 1,
                             optimization_complete=proposal.complete,
                             optimization_results=(*state.optimization_results, record),
                             converged=state.converged and not proposal.changed,
                             last_new_facts=0, last_bound_updates=0, closure_steps=0)
        return {"state": next_state, "assessment": Assessment("complete", qualifications=frozenset({"optimization_" + proposal.status.lower()}))}
    candidates = inputs.get("candidates")
    if not isinstance(candidates, SorsCandidateFacts) or candidates.state_basis != state.fingerprint:
        raise ValueError("sors.stale_candidate_basis")
    closure, ledger = deepcopy(state._closure), deepcopy(candidates._ledger)
    before = len(state._ledger.current_quantity_ids)
    updated, changed = ledger.apply_current_facts_to_quantities(
        closure.quantities_grid, policy=RoundingPolicy(config.publication_step), tolerance=config.point_tolerance)
    if changed:
        closure.replace_quantities(updated)
    new_facts = state.last_new_facts + len(ledger.current_quantity_ids) - before
    converged = not changed and new_facts == 0 and state.last_bound_updates == 0
    if not converged:
        ledger.confirm_feasibility(False)
    row = {"publication_pass": len(state.passes) + 1, "optimization_round": state.optimization_round,
           "interval_bound_updates": state.last_bound_updates, "new_facts": new_facts,
           "fact_bucket_bound_updates": len(changed), "total_current_facts": len(ledger.current_quantity_ids),
           "stop_reason": "NO_NEW_FACTS_OR_LATENT_BUCKET_BOUNDS" if converged else None}
    next_state = replace(state, _closure=closure, _ledger=ledger, passes=(*state.passes, row),
                         inheritance_events=(*state.inheritance_events, candidates.events),
                         tokens=candidates.tokens.copy(deep=True), converged=converged,
                         last_new_facts=0, last_bound_updates=0, closure_steps=state.closure_steps + 1)
    return {"state": next_state, "assessment": Assessment("complete", qualifications=frozenset({"fixed_point" if converged else "continue_closure"}))}


def model_compile(inputs, settings, context):
    _checkpoint(context)
    state = _state(inputs)
    if not state.converged:
        raise ValueError("sors.deterministic_closure_required")
    model = state.model
    compilation = compile_strict_problem(model.inputs.bundle, model.quantity_graph,
                                         state._closure.quantities_grid,
                                         point_tolerance=model.inputs.config.point_tolerance)
    return {"problem": SorsCompiledProblem(state, compilation)}


@_solver_action
def model_feasibility(inputs, settings, context):
    _checkpoint(context)
    problem = inputs["problem"]
    if not isinstance(problem, SorsCompiledProblem):
        raise TypeError("sors.compiled_problem_required")
    _check_build(problem.state.model.inputs)
    execution = run_strict_feasibility(problem.compilation.problem, problem.state.model.inputs.config.optimization)
    return {"feasibility": SorsFeasibilityAssessment(problem.fingerprint, problem.state.fingerprint, execution, problem)}


@_solver_action
def bounds_optimize(inputs, settings, context):
    """Propose one numerical phase without applying facts or running closure."""
    _checkpoint(context)
    problem, feasibility = inputs["problem"], inputs["feasibility"]
    if not isinstance(problem, SorsCompiledProblem) or not isinstance(feasibility, SorsFeasibilityAssessment):
        raise TypeError("sors.feasible_problem_required")
    if feasibility.problem_basis != problem.fingerprint or feasibility.state_basis != problem.state.fingerprint:
        raise ValueError("sors.stale_feasibility_basis")
    if not feasibility.success:
        raise ValueError("sors.global_feasibility_required:" + feasibility.status)
    state = problem.state
    _check_build(state.model.inputs)
    if "state" in inputs and inputs["state"].fingerprint != state.fingerprint:
        raise ValueError("sors.optimization_state_mismatch")
    closure, ledger = deepcopy(state._closure), deepcopy(state._ledger)
    config = state.model.inputs.config
    optimization = config.optimization
    phase = state.optimization_phase
    bounds = solver_runs = profiles = selections = pd.DataFrame()
    before = _frames(closure.quantities_grid, ledger.facts_grid())
    targets = select_optimization_targets(state.model.inputs.bundle, problem.compilation,
                                          closure.quantities_grid, optimization,
                                          already_fact_quantity_ids=ledger.current_quantity_ids)
    requested = inputs.get("targets")
    if requested is not None:
        requested = frozenset(str(value) for value in requested)
        available = set(targets.get("quantity_id", ()))
        if requested - available:
            raise ValueError("sors.optimization_target_unknown")
        if not targets.empty:
            targets = targets[targets["quantity_id"].astype(str).isin(requested)].copy()
    status, complete, next_phase = "OPTIMAL", False, phase
    if optimization.mode == "none" or state.optimization_complete:
        status, complete = "DISABLED" if optimization.mode == "none" else "OPTIMAL", True
    elif targets.empty:
        status, complete = "NO_TARGETS", True
    elif phase == "strict":
        if optimization.strict_minmax_enabled:
            execution = solve_target_minmax(problem.compilation.problem, targets, optimization)
            bounds, solver_runs, status = execution.bounds_grid, execution.solver_runs_grid, execution.status
            updated, changed, proofs = apply_strict_minmax_bounds(
                closure.quantities_grid, bounds, tolerance=config.point_tolerance,
                assumption_tier=_model_assumption_tier(closure.quantities_grid))
            if changed:
                closure.replace_quantities(updated)
            ledger.promote_interval_facts(closure.quantities_grid, policy=RoundingPolicy(config.publication_step),
                                          point_tolerance=config.point_tolerance, restoration_pass=0,
                                          optimization_round=state.optimization_round + 1,
                                          proof_ids_by_quantity=proofs)
        changed = before != _frames(closure.quantities_grid, ledger.facts_grid())
        next_phase = "strict" if changed else "rounding"
        if not changed and not optimization.rounding_optimal_enabled:
            complete = True
    elif phase == "rounding":
        profile = solve_rounding_profile(problem.compilation.problem, optimization,
                                         point_tolerance=config.point_tolerance)
        solver_runs, status = profile.solver_runs_grid, profile.status
        profiles = pd.DataFrame([{"optimization_round": state.optimization_round + 1,
                                  "status": profile.status, "tau_star_mln": profile.tau_star,
                                  "l1_star_mln": profile.l1_star,
                                  "relaxed_l1_star_mln": profile.relaxed_l1_star,
                                  "relaxed_linf_at_l1_mln": profile.relaxed_linf_at_l1}])
        if status == "OPTIMAL":
            def setup(session):
                configure_optimal_face_session(session, profile, linf_extra=config.point_tolerance,
                                               l1_extra=config.point_tolerance)
            execution = solve_target_minmax(profile.problem, targets, optimization,
                                              model_layer="ROUNDING_OPTIMAL_MINMAX", session_setup=setup)
            bounds, status = execution.bounds_grid, execution.status
            solver_runs = _concat((solver_runs, execution.solver_runs_grid))
            _promote_rounding_optimal_buckets(bounds, closure.quantities_grid, ledger,
                RoundingPolicy(config.publication_step), optimization_round=state.optimization_round + 1,
                model_assumption_tier=_model_assumption_tier(closure.quantities_grid))
            updated, changed = ledger.apply_current_facts_to_quantities(
                closure.quantities_grid, policy=RoundingPolicy(config.publication_step),
                tolerance=config.point_tolerance)
            if changed:
                closure.replace_quantities(updated)
        changed = before != _frames(closure.quantities_grid, ledger.facts_grid())
        next_phase = "strict" if changed else "selection"
        if not changed and not optimization.selection.enabled:
            complete = True
    elif phase == "selection":
        profile = solve_rounding_profile(problem.compilation.problem, optimization,
                                         point_tolerance=config.point_tolerance)
        solver_runs, status = profile.solver_runs_grid, profile.status
        if status == "OPTIMAL":
            def setup(session):
                configure_optimal_face_session(session, profile, linf_extra=config.point_tolerance,
                                               l1_extra=config.point_tolerance)
            execution = solve_target_minmax(profile.problem, targets, optimization,
                                              model_layer="ROUNDING_OPTIMAL_MINMAX", session_setup=setup)
            bounds, status = execution.bounds_grid, execution.status
            solver_runs = _concat((solver_runs, execution.solver_runs_grid))
            if status == "OPTIMAL":
                selection = run_controlled_selection(targets, bounds, profile, optimization,
                                                      RoundingPolicy(config.publication_step))
                solver_runs = _concat((solver_runs, selection.solver_runs_grid))
                selections = selection.attempts_grid
                _promote_selected(selection.accepted_grid, closure.quantities_grid, ledger,
                                  optimization_round=state.optimization_round + 1)
                updated, changed = ledger.apply_current_facts_to_quantities(
                    closure.quantities_grid, policy=RoundingPolicy(config.publication_step),
                    tolerance=config.point_tolerance)
                if changed:
                    closure.replace_quantities(updated)
        changed = before != _frames(closure.quantities_grid, ledger.facts_grid())
        next_phase, complete = "strict", not changed
    else:
        raise ValueError("sors.optimization_phase_invalid")
    changed = before != _frames(closure.quantities_grid, ledger.facts_grid())
    if not bounds.empty:
        bounds = bounds.assign(optimization_round=state.optimization_round + 1, phase=phase)
    proposal = SorsOptimizationProposal(state.fingerprint, problem.fingerprint, phase, status,
        closure, ledger, changed, complete, next_phase, bounds, solver_runs, profiles, selections,
        feasibility.execution, len(ledger.current_quantity_ids) - len(state._ledger.current_quantity_ids))
    return {"optimization": proposal}


def values_certify(inputs, settings, context):
    _checkpoint(context)
    state, feasibility = _state(inputs), inputs["feasibility"]
    if not isinstance(feasibility, SorsFeasibilityAssessment) or feasibility.state_basis != state.fingerprint:
        raise ValueError("sors.stale_certification_basis")
    if not feasibility.success:
        raise ValueError("sors.global_feasibility_required:" + feasibility.status)
    if not state.converged or not state.optimization_complete:
        raise ValueError("sors.completed_fixed_point_required")
    problem = feasibility.problem
    if not isinstance(problem, SorsCompiledProblem):
        raise ValueError("sors.compiled_problem_evidence_required")
    if problem.fingerprint != feasibility.problem_basis:
        raise ValueError("sors.stale_feasibility_basis")
    ledger = deepcopy(state._ledger)
    ledger.confirm_feasibility(feasibility.success)
    model, config = state.model, state.model.inputs.config
    deterministic = SorsPublicationClosureExecution(
        state.quantities, ledger.facts_grid(), ledger.facts_grid(current_only=True),
        state._closure.derivations_grid.copy(deep=True), _concat(state.inheritance_events),
        state.tokens.copy(deep=True), ledger.promotion_events_grid(), pd.DataFrame(state.passes),
        len(state.passes), sum(row["interval_bound_updates"] for row in state.passes),
        sum(row["new_facts"] for row in state.passes), "FIXED_POINT")
    optimization = None
    if state.optimization_results:
        from stratbox.domains.cbr.calculations.sors.optimization.proposals import SorsOptimizationExecution
        results = state.optimization_results
        phase_solver_frames = []
        for i, item in enumerate(results, start=1):
            for frame, kind in ((item.solver_runs, item.phase),
                                (item.feasibility.solver_runs_grid if item.feasibility is not None else pd.DataFrame(), "global_feasibility")):
                if not frame.empty:
                    frame = frame.copy(deep=True)
                    frame["optimization_round"] = i
                    frame["phase"] = kind
                    if "solve_id" in frame:
                        frame["solve_id"] = frame["solve_id"].map(lambda key: f"wave:{i}:{kind}:{key}")
                    phase_solver_frames.append(frame)
        optimization = SorsOptimizationExecution(
            state.quantities, ledger.facts_grid(), ledger.facts_grid(current_only=True),
            state._closure.derivations_grid.copy(deep=True), _concat(phase_solver_frames),
            _concat(item.bounds for item in results), _concat(item.rounding_profiles for item in results),
            _concat(item.selection_attempts for item in results),
            pd.DataFrame([{"optimization_round": i + 1, "status": item.status, "phase": item.phase,
                           "targets_attempted": len(item.bounds), "new_facts": item.new_facts, "changed": item.changed,
                           "complete": item.complete, "next_phase": item.next_phase}
                          for i, item in enumerate(results)]),
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "DISABLED" if config.optimization.mode == "none" else "FIXED_POINT", len(results),
            sum(len(item.bounds) for item in results),
            sum(item.new_facts for item in results))
    result = assemble_result(model.inputs.bundle, config, model.quantity_graph, model.publication_graph,
                             deepcopy(state._closure), ledger, problem.compilation,
                             feasibility.execution, deterministic, optimization)
    from stratbox.domains.cbr.calculations.sors.identity import seal_content
    return {"values": SorsCertifiedValues(seal_content(result), state.fingerprint, feasibility.fingerprint)}


def observation_rows(frame):
    """Neutral rows use missing values plus explicit unbounded flags.

    The native scientific grids retain IEEE infinities and exact endpoint data.
    """
    from math import isfinite, isinf
    import numpy as np
    def scalar(value):
        if value is pd.NA or value is pd.NaT:
            return None
        if isinstance(value, np.generic):
            value = value.item()
        if isinstance(value, float) and not isfinite(value):
            return None
        if isinstance(value, (tuple, list)):
            return tuple(scalar(item) for item in value)
        return value
    rows = []
    for original in frame.to_dict("records"):
        row = {name: scalar(value) for name, value in original.items()}
        for name in ("lower_bound", "upper_bound"):
            value = original.get(name)
            row[name.removesuffix("_bound") + "_unbounded"] = isinstance(value, float) and isinf(value)
        rows.append(row)
    return tuple(rows)

def observations_assemble(inputs, settings, context):
    _checkpoint(context)
    value = inputs["values"]
    if not isinstance(value, SorsCertifiedValues):
        raise TypeError("sors.certified_values_required")
    from stratbox.shared.data.values import DerivedDataset, Assessment
    result = value.result
    rows = observation_rows(result.regional_okved2_grid)
    dataset = DerivedDataset(
        source_id="cbr.sors", rows=rows, issue_id=result.summary.as_of_date,
        semantics={"input_topology": "coupled", "measure_kind": "stock",
                   "unit": "million_rubles", "portfolio_scope": PRIMARY_PORTFOLIO_SCOPE,
                   "rules_fingerprint": str(result.audit_grid.set_index("key").loc["rules_fingerprint", "value"])},
        lineage=tuple(result.source_bundle.lineage),
        assessment=Assessment("complete" if result.summary.strict_status == "OPTIMAL" else "partial",
                              qualifications=frozenset({"derived", "reconstructed"})), native=result,
        source_uses=tuple(result.source_bundle.source_uses))
    return {"dataset": dataset}
