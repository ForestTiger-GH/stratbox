"""Conditional crosswalk actions on the standard constrained-model route."""
from __future__ import annotations
from dataclasses import dataclass, replace
from contextlib import nullcontext
from copy import deepcopy
import pandas as pd
from stratbox.shared.data.values import Assessment, DerivedDataset
from stratbox.domains.cbr.calculations.sors.contracts import SorsCrosswalkConfig
from stratbox.domains.cbr.calculations.sors.results import SorsRestorationResult
from stratbox.domains.cbr.calculations.sors.identity import seal_content, validate_content
from stratbox.domains.cbr.calculations.sors.stages import _hash, _frames, _checkpoint, _solver_action, SorsCertifiedValues, observation_rows
from stratbox.domains.cbr.calculations.sors.linear.highs import SorsSolverDependencyError, SolveResult
from stratbox.domains.cbr.calculations.sors.crosswalk import analysis
from stratbox.domains.cbr.calculations.sors.crosswalk.mapping import read_crosswalk_scenarios, mapping_content_fingerprint, capture_mapping_inputs
from stratbox.domains.cbr.calculations.sors.crosswalk.problem import CrosswalkCompilation, compile_crosswalk_problem
from stratbox.domains.cbr.calculations.sors.crosswalk.closure import close_crosswalk_bounds, CrosswalkClosureConflictError


def _compilation_fingerprint(compilation):
    problem = compilation.problem
    arrays = (problem.matrix.indptr, problem.matrix.indices, problem.matrix.data,
              problem.row_lower, problem.row_upper, problem.col_lower, problem.col_upper, problem.objective)
    return _hash(problem.matrix.shape, _frames(problem.constraints_grid, problem.variables_grid,
                 compilation.target_catalog_grid, compilation.mapping_edges_grid, compilation.relations_grid),
                 *((str(a.dtype), a.shape, a.tobytes().hex()) for a in arrays))


@dataclass(frozen=True)
class CrosswalkModel:
    strict: SorsRestorationResult
    config: SorsCrosswalkConfig

    @property
    def fingerprint(self):
        return _hash(self.strict.fingerprint, self.config)


@dataclass(frozen=True)
class CrosswalkState:
    model: CrosswalkModel
    compilations: tuple
    derivations: tuple = ()
    conflicts: tuple = ()
    converged: bool = False
    optimization_complete: bool = False
    executions: tuple = ()

    @property
    def fingerprint(self):
        return _hash(self.model.fingerprint, tuple(_compilation_fingerprint(c) for c in self.compilations),
                     tuple(_frames(f) for f in self.conflicts), self.converged,
                     self.optimization_complete, tuple((e.scenario_id, e.status, _frames(e.grid)) for e in self.executions))


@dataclass(frozen=True)
class CrosswalkCandidates:
    state_basis: str


@dataclass(frozen=True)
class CrosswalkProblem:
    state: CrosswalkState

    @property
    def fingerprint(self):
        return _hash(self.state.fingerprint, 'compiled_crosswalk')


@dataclass(frozen=True)
class CrosswalkFeasibility:
    problem_basis: str
    state_basis: str
    results: tuple
    records: tuple

    @property
    def status(self):
        return analysis._overall_crosswalk_status({result.status for result in self.results})

    @property
    def success(self):
        return self.status in {'OPTIMAL', 'OPTIMAL_WITH_REJECTED_SCENARIOS'}

    @property
    def fingerprint(self):
        return _hash(self.problem_basis, self.state_basis, tuple((r.status, r.success) for r in self.results))


@dataclass(frozen=True)
class CrosswalkOptimization:
    state_basis: str
    problem_basis: str
    executions: tuple

    @property
    def fingerprint(self):
        return _hash(self.state_basis, self.problem_basis,
                     tuple((e.scenario_id, e.status, _frames(e.grid)) for e in self.executions))


def model_inputs(inputs, settings, context):
    value = inputs['datasets']
    value = getattr(value, 'native', None) or value
    previous_config = None
    if isinstance(value, CrosswalkModel):
        previous_config, value = value.config, value.strict
    if not isinstance(value, SorsRestorationResult) or value.source_bundle is None:
        raise ValueError('sors.crosswalk_full_strict_result_required')
    if value.summary.strict_status != 'OPTIMAL':
        raise ValueError('sors.crosswalk_strict_feasibility_required')
    validate_content(value)
    validate_content(value.source_bundle)
    params = getattr(context, 'parameters', {}) if context is not None else {}
    config = params.get('config', previous_config or SorsCrosswalkConfig(mode='feasibility'))
    if not isinstance(config, SorsCrosswalkConfig) or config.mode == 'disabled':
        raise ValueError('sors.crosswalk_config_required')
    with capture_mapping_inputs(context.use) if context is not None and hasattr(context, 'use') else nullcontext():
        known = set(read_crosswalk_scenarios(config.mapping_fingerprint))
        if set(config.scenario_ids) - known:
            raise ValueError('sors.crosswalk_unknown_scenario')
        config = replace(config, mapping_fingerprint=mapping_content_fingerprint())
    if context is not None and hasattr(context, 'use'):
        for receipt in value.source_bundle.lineage:
            context.use(receipt)
    return {'bundle': CrosswalkModel(deepcopy(value), config)}


def constraints_build(inputs, settings, context):
    model = inputs['bundle']
    if not isinstance(model, CrosswalkModel):
        raise TypeError('sors.crosswalk_model_inputs_required')
    compilations = []
    for scenario_id in model.config.scenario_ids:
        _checkpoint(context)
        compilations.append(compile_crosswalk_problem(model.strict.source_bundle,
            model.strict.components_grid, model.config, scenario_id))
    return {'graph': model, 'state': CrosswalkState(model, tuple(compilations))}


def bounds_propagate(inputs, settings, context):
    state = inputs['state']
    compilations, derivations, conflicts = [], [], []
    for compilation in state.compilations:
        _checkpoint(context)
        try:
            closed = close_crosswalk_bounds(compilation.problem,
                tolerance=state.model.config.point_tolerance,
                max_passes=state.model.config.closure_max_passes)
            if not closed.converged:
                raise ValueError('sors.crosswalk_closure_pass_limit')
            compilations.append(replace(compilation, problem=closed.problem))
            prior = state.derivations[len(compilations) - 1] if state.derivations else pd.DataFrame()
            combined = pd.concat([prior, closed.derivations_grid], ignore_index=True) if not closed.derivations_grid.empty else prior.copy(deep=True)
            derivations.append(combined)
            conflicts.append(pd.DataFrame())
        except CrosswalkClosureConflictError as exc:
            compilations.append(compilation)
            derivations.append(pd.DataFrame())
            conflicts.append(exc.conflicts_grid.copy(deep=True))
    return {'state': replace(state, compilations=tuple(compilations),
                             derivations=tuple(derivations), conflicts=tuple(conflicts)),
            'derivations': tuple(derivations)}


def facts_inherit(inputs, settings, context):
    # Conditional mapping equations supply no direct publication inheritance.
    return {'candidates': CrosswalkCandidates(inputs['state'].fingerprint)}


def facts_reconcile(inputs, settings, context):
    state = inputs['state']
    candidates, optimization = inputs.get('candidates'), inputs.get('optimization')
    if candidates is not None:
        if not isinstance(candidates, CrosswalkCandidates) or candidates.state_basis != state.fingerprint:
            raise ValueError('sors.crosswalk_stale_candidate_basis')
        state = replace(state, converged=True)
    elif optimization is not None:
        if not isinstance(optimization, CrosswalkOptimization) or optimization.state_basis != state.fingerprint:
            raise ValueError('sors.crosswalk_stale_optimization_basis')
        state = replace(state, executions=optimization.executions, optimization_complete=True)
    else:
        raise ValueError('sors.crosswalk_reconciliation_input_required')
    return {'state': state, 'assessment': Assessment('complete')}


def model_compile(inputs, settings, context):
    state = inputs['state']
    if not isinstance(state, CrosswalkState) or not state.converged:
        raise ValueError('sors.crosswalk_deterministic_closure_required')
    return {'problem': CrosswalkProblem(state)}


@_solver_action
def model_feasibility(inputs, settings, context):
    problem = inputs['problem']
    state, config = problem.state, problem.state.model.config
    results, records = [], []
    for scenario_id, compilation, conflicts in zip(config.scenario_ids, state.compilations, state.conflicts, strict=True):
        _checkpoint(context)
        rows = []
        if not conflicts.empty:
            result = SolveResult(False, 'INFEASIBLE_BY_CLOSURE', 'interval_conflict', None, None, 0, 0, 0)
        else:
            try:
                with analysis.HighsSession(compilation.problem, time_limit_seconds=config.per_solve_time_limit_seconds,
                                            threads=config.threads) as session:
                    result = session.solve_feasibility()
                rows.append(analysis._solve_record(f'crosswalk:{scenario_id}:feasibility', 'FEASIBILITY',
                                                  result, scenario_id=scenario_id))
            except SorsSolverDependencyError:
                result = SolveResult(False, 'SOLVER_UNAVAILABLE', 'dependency_unavailable', None, None, 0, 0, 0)
        results.append(result)
        records.append(tuple(rows))
    return {'feasibility': CrosswalkFeasibility(problem.fingerprint, state.fingerprint, tuple(results), tuple(records))}


@_solver_action
def bounds_optimize(inputs, settings, context):
    problem, feasible = inputs['problem'], inputs['feasibility']
    state = problem.state
    if feasible.problem_basis != problem.fingerprint or feasible.state_basis != state.fingerprint:
        raise ValueError('sors.crosswalk_stale_feasibility_basis')
    if not feasible.success:
        raise ValueError('sors.crosswalk_global_feasibility_required:' + feasible.status)
    executions = []
    for index, scenario_id in enumerate(state.model.config.scenario_ids):
        _checkpoint(context)
        executions.append(analysis.optimize_scenario(state.model.strict, state.model.config, scenario_id,
            state.compilations[index], feasible.results[index], records=feasible.records[index],
            conflicts=state.conflicts[index], derivations=state.derivations[index],
            checkpoint=lambda: _checkpoint(context)))
    return {'optimization': CrosswalkOptimization(state.fingerprint, problem.fingerprint, tuple(executions))}


def values_certify(inputs, settings, context):
    state, feasible = inputs['state'], inputs['feasibility']
    if feasible.state_basis != state.fingerprint or not feasible.success:
        raise ValueError('sors.crosswalk_current_feasibility_required')
    if not state.optimization_complete or not state.converged:
        raise ValueError('sors.crosswalk_completed_bounds_required')
    result = seal_content(analysis.assemble_crosswalk(state.model.strict, state.model.config, state.executions))
    return {'values': SorsCertifiedValues(result, state.fingerprint, feasible.fingerprint)}


def observations_assemble(inputs, settings, context):
    result = inputs['values'].result
    return {'dataset': DerivedDataset('cbr.sors.crosswalk', observation_rows(result.regional_okved2_grid),
        {'input_topology': 'coupled', 'measure_kind': 'stock', 'unit': 'million_rubles',
         'evidence_layer': 'conditional_crosswalk'}, result.strict_result.summary.as_of_date,
        tuple(result.strict_result.source_bundle.lineage),
        Assessment('complete' if result.status.startswith('OPTIMAL') else 'partial',
                   qualifications=frozenset({'derived', 'conditional_mapping'})), native=result,
        source_uses=tuple(result.strict_result.source_bundle.source_uses))}
