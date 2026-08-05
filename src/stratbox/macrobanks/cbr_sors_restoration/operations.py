from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.certification import CertifiedInterval, certify_interval
from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsRestorationResult,
    SorsRunConfig,
    SorsSourceBundle,
    SorsSourceFiles,
)
from stratbox.macrobanks.cbr_sors_restoration.evidence import published_facts
from stratbox.macrobanks.cbr_sors_restoration.mapping import read_bridge_targets
from stratbox.macrobanks.cbr_sors_restoration.metrics import source_metric
from stratbox.macrobanks.cbr_sors_restoration.parsers import load_sors_source_grid
from stratbox.macrobanks.cbr_sors_restoration.problem import (
    LinearTarget,
    ProblemBuilder,
    SorsProblem,
    bridge_profile_problem,
    make_target,
    strict_publication_problem,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.solver import (
    SolveResult,
    solve_restoration_batch,
)
from stratbox.macrobanks.cbr_sors_restoration.validation import validate_source_bundle


def _model_run_id(bundle: SorsSourceBundle, config: SorsRunConfig) -> str:
    payload = {
        'date': config.as_of_date,
        'mapping': config.mapping_version,
        'sources': bundle.source_manifest[['source_series', 'sha256']]
        .sort_values('source_series')
        .to_dict('records'),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]


def _select_targets(bundle: SorsSourceBundle, config: SorsRunConfig) -> list[tuple[str, str, str]]:
    scope = config.target_scope
    if scope.certify_all:
        regions = tuple(bundle.atomic_regions['region_name'].astype(str))
        classes = tuple(bundle.okved2_classes['class_code'].astype(str))
    else:
        regions = scope.region_names
        classes = scope.class_codes
    if not regions or not classes:
        return []
    known_regions = set(bundle.atomic_regions['region_name'].astype(str))
    known_classes = set(bundle.okved2_classes['class_code'].astype(str))
    missing_regions = sorted(set(regions) - known_regions)
    missing_classes = sorted(set(classes) - known_classes)
    if missing_regions or missing_classes:
        raise ValueError(f'Unknown SORS targets: regions={missing_regions}, classes={missing_classes}')
    targets = [(region, code, metric) for region in regions for code in classes for metric in scope.metrics]
    if scope.max_targets is not None and len(targets) > scope.max_targets:
        raise ValueError(f'Target scope contains {len(targets)} metrics, maximum is {scope.max_targets}')
    return targets


def _bridge_diagnostics(problem: SorsProblem, solution: np.ndarray) -> pd.DataFrame:
    dev = problem.variable_grid[
        problem.variable_grid['variable_kind'].isin(
            ['bridge_positive_deviation', 'bridge_negative_deviation']
        )
    ].copy()
    if dev.empty:
        return pd.DataFrame()
    dev['solver_value'] = solution[dev['variable_id'].astype(int)]
    pivot = (
        dev.pivot_table(
            index='bridge_constraint_id',
            columns='variable_kind',
            values='solver_value',
            aggfunc='sum',
            fill_value=0.0,
        )
        .reset_index()
    )
    pivot['bridge_error'] = (
        pivot.get('bridge_positive_deviation', 0.0)
        - pivot.get('bridge_negative_deviation', 0.0)
    )
    meta = problem.constraints_grid[
        problem.constraints_grid['hardness'] == 'BRIDGE_OBJECTIVE'
    ].copy()
    return meta.merge(
        pivot,
        left_on='constraint_id',
        right_on='bridge_constraint_id',
        how='left',
    )


def _require_pair(target: LinearTarget, lower: SolveResult, upper: SolveResult) -> None:
    if not all(item.success and item.objective_value is not None for item in (lower, upper)):
        raise RuntimeError(
            f'Failed to certify target {target.target_id}: '
            f'lower={lower.status}, upper={upper.status}'
        )


def _singleton_bridge_nodes(mapping_edges: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    grouped = mapping_edges.groupby('legacy_node_code', sort=False)['class_code'].agg(
        lambda values: tuple(dict.fromkeys(str(value) for value in values))
    )
    result: dict[str, list[str]] = {}
    for node_code, classes in grouped.items():
        if len(classes) == 1:
            result.setdefault(classes[0], []).append(str(node_code))
    return {code: tuple(nodes) for code, nodes in result.items()}


def _singleton_profile_interval(
    problem: SorsProblem,
    target: LinearTarget,
    bridge_solution: np.ndarray,
    *,
    singleton_nodes: dict[str, tuple[str, ...]],
    tolerance: float,
    policy: RoundingPolicy,
    point_tolerance: float,
) -> CertifiedInterval | None:
    nodes = singleton_nodes.get(target.class_code, ())
    if not nodes:
        return None
    meta = problem.constraints_grid
    geography = meta.get('geography_node_id', pd.Series(index=meta.index, dtype=object))
    activities = meta.get('activity_code', pd.Series(index=meta.index, dtype=object))
    candidates = meta[
        meta['hardness'].astype(str).eq('BRIDGE_OBJECTIVE')
        & geography.astype(str).eq(target.region_code)
        & activities.astype(str).isin(nodes)
    ]
    intervals: list[tuple[float, float]] = []
    for row_position, row in candidates.iterrows():
        if source_metric(str(row['measure']), str(row['currency'])) != target.metric:
            continue
        start = int(problem.matrix.indptr[int(row_position)])
        end = int(problem.matrix.indptr[int(row_position) + 1])
        indices = problem.matrix.indices[start:end]
        coefficients = problem.matrix.data[start:end]
        mask = indices < problem.n_primary_variables
        fitted = float(np.dot(coefficients[mask], bridge_solution[indices[mask]]))
        intervals.append((max(0.0, fitted - tolerance), fitted + tolerance))
    if not intervals:
        return None
    lower = max(value[0] for value in intervals)
    upper = min(value[1] for value in intervals)
    if upper < lower:
        return None
    return certify_interval(
        lower,
        upper,
        policy=policy,
        point_tolerance=point_tolerance,
        evidence_layer='BRIDGE_SINGLETON_PROFILE',
    )


def run_sors_restoration(
    source: SorsSourceFiles | SorsSourceBundle,
    config: SorsRunConfig,
) -> SorsRestorationResult:
    bundle = (
        source
        if isinstance(source, SorsSourceBundle)
        else load_sors_source_grid(source, config.as_of_date, config.publication_step)
    )
    validate_source_bundle(bundle)
    mapping_edges = read_bridge_targets(bundle.okved2_classes, config.mapping_version)
    problem = ProblemBuilder(bundle, config, mapping_edges).build()
    strict_problem = strict_publication_problem(problem)
    model_run_id = _model_run_id(bundle, config)
    policy = RoundingPolicy(step=config.publication_step)

    target_specs = _select_targets(bundle, config)
    targets = [make_target(problem, bundle, *spec) for spec in target_specs]
    singleton_nodes = _singleton_bridge_nodes(mapping_edges)
    profile_lp_targets = [
        target for target in targets if target.class_code not in singleton_nodes
    ]
    batch = solve_restoration_batch(
        problem,
        targets,
        profile_targets=profile_lp_targets,
        profile_tolerance=config.bridge_profile_tolerance,
        time_limit=config.solver_time_limit_seconds,
        threads=config.solver_threads,
    )
    bridge_optimum = batch['bridge']
    bridge_backend = batch['backend']
    bridge_solver_version = batch['version']
    if (
        not bridge_optimum.success
        or bridge_optimum.objective_value is None
        or bridge_optimum.values is None
    ):
        raise ValueError(f'SORS bridge optimization failed: {bridge_optimum.status}')
    bridge_solution_values = bridge_optimum.values.copy()
    strict_feasibility = bridge_optimum
    strict_backend = bridge_backend
    strict_solver_version = bridge_solver_version
    strict_intervals: dict[str, CertifiedInterval] = {}
    for target in targets:
        lower, upper = batch['strict'][target.target_id]
        _require_pair(target, lower, upper)
        strict_intervals[target.target_id] = certify_interval(
            float(lower.objective_value),
            float(upper.objective_value),
            policy=policy,
            point_tolerance=config.point_tolerance,
            evidence_layer='STRICT',
        )

    # Phase 3: conservative local-profile envelopes. Only the selected region's
    # fitted legacy margins are fixed; all other regions remain free under the
    # official national and FD constraints. A point identified here is therefore
    # also point identified under the complete selected bridge profile.
    bounds_records: list[dict[str, object]] = []
    reconstructed_records: list[dict[str, object]] = []
    class_names = (
        bundle.okved2_classes.set_index('class_code')['class_name'].astype(str).to_dict()
    )
    for target in targets:
        strict_cert = strict_intervals[target.target_id]
        bridge_cert = _singleton_profile_interval(
            problem,
            target,
            bridge_solution_values,
            singleton_nodes=singleton_nodes,
            tolerance=config.bridge_profile_tolerance,
            policy=policy,
            point_tolerance=config.point_tolerance,
        )
        if bridge_cert is None:
            bridge_lower, bridge_upper = batch['profile'][target.target_id]
            _require_pair(target, bridge_lower, bridge_upper)
            bridge_cert = certify_interval(
                float(bridge_lower.objective_value),
                float(bridge_upper.objective_value),
                policy=policy,
                point_tolerance=config.point_tolerance,
                evidence_layer='BRIDGE_LOCAL_PROFILE',
            )
        bounds_records.append(
            {
                'as_of_date': config.as_of_date,
                'region_code': target.region_code,
                'region_name': target.region_name,
                'class_code': target.class_code,
                'class_name': class_names[target.class_code],
                'metric': target.metric,
                'strict_lower': strict_cert.lower,
                'strict_upper': strict_cert.upper,
                'strict_status': strict_cert.status,
                'bridge_lower': bridge_cert.lower,
                'bridge_upper': bridge_cert.upper,
                'bridge_status': bridge_cert.status,
                'bridge_published_value': bridge_cert.published_value,
                'model_run_id': model_run_id,
                'mapping_version': config.mapping_version,
            }
        )
        chosen = (
            strict_cert
            if not strict_cert.status.endswith('BOUNDED')
            else bridge_cert
        )
        if chosen.published_value is not None:
            evidence_layer = (
                'STRICT'
                if chosen is strict_cert
                else (
                    'BRIDGE_SINGLETON_PROFILE'
                    if chosen.status.startswith('BRIDGE_SINGLETON_PROFILE')
                    else 'BRIDGE_LOCAL_PROFILE'
                )
            )
            reconstructed_records.append(
                {
                    'as_of_date': config.as_of_date,
                    'geography_node_id': target.region_code,
                    'geography_name': target.region_name,
                    'geography_kind': 'atomic_region',
                    'classifier_id': 'okved2',
                    'activity_code': target.class_code,
                    'activity_name': class_names[target.class_code],
                    'metric': target.metric,
                    'value': chosen.published_value,
                    'lower_bound': chosen.lower,
                    'upper_bound': chosen.upper,
                    'status': chosen.status,
                    'evidence_layer': evidence_layer,
                    'is_published': False,
                    'is_reconstructed': True,
                    'proof_type': (
                        'bridge_singleton_profile'
                        if evidence_layer == 'BRIDGE_SINGLETON_PROFILE'
                        else 'lp_minmax'
                    ),
                    'observation_id': None,
                    'source_series': None,
                    'source_file_actual': None,
                    'source_sheet': None,
                    'source_row': None,
                    'source_column': None,
                    'source_sha256': None,
                    'model_run_id': model_run_id,
                    'mapping_version': config.mapping_version,
                }
            )

    published = published_facts(bundle.canonical_grid)
    reconstructed = pd.DataFrame(reconstructed_records, columns=published.columns)
    facts = pd.concat([published, reconstructed], ignore_index=True)
    bounds = pd.DataFrame(bounds_records)
    diagnostics = _bridge_diagnostics(problem, bridge_solution_values)
    created = datetime.now(timezone.utc).isoformat()
    strict_fact_count = int(
        (reconstructed.get('evidence_layer', pd.Series(dtype=str)) == 'STRICT').sum()
    )
    profile_fact_count = int(
        reconstructed.get('evidence_layer', pd.Series(dtype=str))
        .astype(str)
        .str.startswith('BRIDGE_')
        .sum()
    )
    audit = {
        'model_run_id': model_run_id,
        'as_of_date': config.as_of_date,
        'created_at_utc': created,
        'strategy_box_version': '0.3.0',
        'solver_backend': bridge_backend,
        'solver_version': bridge_solver_version,
        'strict_solver_backend': strict_backend,
        'strict_solver_version': strict_solver_version,
        'mapping_version': config.mapping_version,
        'atomic_regions': len(bundle.atomic_regions),
        'okved2_classes': len(bundle.okved2_classes),
        'primary_variables': problem.n_primary_variables,
        'total_variables': problem.num_variables,
        'constraints': int(problem.matrix.shape[0]),
        'hard_constraints': int(
            (problem.constraints_grid['hardness'] == 'HARD_PUBLICATION').sum()
        ),
        'bridge_constraints': int(
            (problem.constraints_grid['hardness'] == 'BRIDGE_OBJECTIVE').sum()
        ),
        'hard_feasible': strict_feasibility.success,
        'bridge_objective_value': bridge_optimum.objective_value,
        'targets_certified': len(targets),
        'strict_reconstructed_facts': strict_fact_count,
        'bridge_reconstructed_facts': profile_fact_count,
        'source_rows': int(len(bundle.canonical_grid)),
        'important_note': (
            'BRIDGE profile facts are conditional reconstructions. They are '
            'unique under the target region margins fitted by the deterministic '
            'minimum-error methodology-derived bridge and are distinct from STRICT '
            'facts implied by publications alone.'
        ),
    }
    return SorsRestorationResult(
        canonical_grid=bundle.canonical_grid,
        facts_grid=facts,
        bounds_grid=bounds,
        bridge_diagnostics_grid=diagnostics,
        constraints_grid=problem.constraints_grid,
        mapping_edges_grid=mapping_edges,
        conflicts_grid=pd.DataFrame(),
        audit=audit,
    )
