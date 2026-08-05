from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.certification import certify_interval
from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsRestorationResult,
    SorsRunConfig,
    SorsSourceBundle,
    SorsSourceFiles,
)
from stratbox.macrobanks.cbr_sors_restoration.evidence import FACT_COLUMNS, published_facts
from stratbox.macrobanks.cbr_sors_restoration.mapping import (
    build_atom_class_edges,
    read_mapping_manifest,
    validate_mapping_version,
)
from stratbox.macrobanks.cbr_sors_restoration.parsers import load_sors_source_grid
from stratbox.macrobanks.cbr_sors_restoration.problem import (
    LinearTarget,
    build_bridge_flow_problem,
    build_strict_problem,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.solver import solve_restoration_batch
from stratbox.macrobanks.cbr_sors_restoration.validation import validate_source_bundle


def _model_run_id(bundle: SorsSourceBundle, config: SorsRunConfig) -> str:
    payload = {
        'date': config.as_of_date,
        'mapping': config.mapping_version,
        'sources': bundle.source_manifest[['source_series', 'sha256']]
        .sort_values('source_series')
        .to_dict('records'),
        'version': '0.3.1',
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:20]


def _constraint_hash(*frames: pd.DataFrame) -> str:
    records: list[dict[str, object]] = []
    for frame in frames:
        if frame.empty:
            continue
        cols = [
            col for col in (
                'constraint_id', 'constraint_kind', 'model_layer',
                'source_observation_id', 'lower_bound', 'upper_bound',
            ) if col in frame.columns
        ]
        records.extend(frame[cols].sort_values(cols[0]).to_dict('records'))
    return hashlib.sha256(
        json.dumps(records, sort_keys=True, default=str).encode()
    ).hexdigest()


def _select_targets(
    bundle: SorsSourceBundle,
    config: SorsRunConfig,
) -> list[tuple[str, str, str]]:
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
        raise ValueError(
            f'Unknown SORS targets: regions={missing_regions}, '
            f'classes={missing_classes}'
        )
    targets = [
        (region, code, metric)
        for region in regions
        for code in classes
        for metric in scope.metrics
    ]
    if scope.max_targets is not None and len(targets) > scope.max_targets:
        raise ValueError(
            f'Target scope contains {len(targets)} metrics, '
            f'maximum is {scope.max_targets}'
        )
    return targets


def _require_pair(
    target: LinearTarget,
    lower,
    upper,
    *,
    layer: str,
) -> None:
    if not all(item.success and item.objective_value is not None for item in (lower, upper)):
        raise RuntimeError(
            f'Failed to certify {layer} target {target.target_id}: '
            f'lower={lower.status}, upper={upper.status}'
        )


def _target_value(target: LinearTarget, values: np.ndarray | None) -> float | None:
    if values is None:
        return None
    return float(np.dot(target.coefficients, values[target.indices]))


def _bridge_diagnostics(
    mapping_edges: pd.DataFrame,
    bridge_problem,
    values: np.ndarray | None,
) -> pd.DataFrame:
    if values is None:
        return pd.DataFrame()
    meta = bridge_problem.metadata
    region_codes = tuple(meta['region_codes'])
    atom_codes = tuple(meta['atom_codes'])
    class_codes = tuple(meta['class_codes'])
    components = tuple(meta['components'])
    preferred_pairs = tuple(meta['preferred_pairs'])
    preferred_offset = int(meta['preferred_offset'])
    atom_residual_offset = int(meta['atom_residual_offset'])
    class_residual_offset = int(meta['class_residual_offset'])

    preferred_values = np.asarray(
        values[preferred_offset:atom_residual_offset], dtype=float
    ).reshape(len(region_codes), len(preferred_pairs), len(components))
    preferred_totals = preferred_values.sum(axis=(0, 2))
    records: list[dict[str, object]] = []
    for position, (atom_code, class_code) in enumerate(preferred_pairs):
        amount = float(preferred_totals[position])
        if amount <= 1e-9:
            continue
        records.append({
            'diagnostic_kind': 'preferred_flow',
            'atom_code': atom_code,
            'class_code': class_code,
            'flow_total_mln_rub': amount,
        })

    atom_residual = np.asarray(
        values[atom_residual_offset:class_residual_offset], dtype=float
    ).reshape(len(region_codes), len(atom_codes), len(components))
    for atom_position, atom_code in enumerate(atom_codes):
        amount = float(atom_residual[:, atom_position, :].sum())
        if amount <= 1e-9:
            continue
        records.append({
            'diagnostic_kind': 'fallback_supply_by_atom',
            'atom_code': atom_code,
            'class_code': None,
            'flow_total_mln_rub': amount,
        })

    class_residual = np.asarray(
        values[class_residual_offset:], dtype=float
    ).reshape(len(region_codes), len(class_codes), len(components))
    for class_position, class_code in enumerate(class_codes):
        amount = float(class_residual[:, class_position, :].sum())
        if amount <= 1e-9:
            continue
        records.append({
            'diagnostic_kind': 'fallback_demand_by_class',
            'atom_code': None,
            'class_code': class_code,
            'flow_total_mln_rub': amount,
        })
    out = pd.DataFrame(records)
    if out.empty:
        return out
    preferred_meta = mapping_edges[
        mapping_edges['is_preferred'].astype(bool)
    ].drop_duplicates(['atom_code', 'class_code'])
    return out.merge(
        preferred_meta,
        on=['atom_code', 'class_code'],
        how='left',
    ).sort_values(
        ['diagnostic_kind', 'flow_total_mln_rub'],
        ascending=[True, False],
    ).reset_index(drop=True)


def _fact_record(
    *,
    config: SorsRunConfig,
    model_run_id: str,
    constraint_set_hash: str,
    target: LinearTarget,
    class_name: str,
    certified,
) -> dict[str, object]:
    return {
        'as_of_date': config.as_of_date,
        'geography_node_id': target.region_code,
        'geography_name': target.region_name,
        'geography_kind': 'atomic_region',
        'classifier_id': 'okved2',
        'activity_code': target.class_code,
        'activity_name': class_name,
        'metric': target.metric,
        'value': certified.published_value,
        'lower_bound': certified.lower,
        'upper_bound': certified.upper,
        'status': certified.status,
        'evidence_layer': 'STRICT',
        'is_published': False,
        'is_reconstructed': True,
        'is_estimate': False,
        'proof_type': 'lp_minmax',
        'observation_id': None,
        'source_series': None,
        'source_file_actual': None,
        'source_sheet': None,
        'source_row': None,
        'source_column': None,
        'source_sha256': None,
        'model_run_id': model_run_id,
        'mapping_version': None,
        'constraint_set_hash': constraint_set_hash,
        'lower_solve_id': f'strict:min:{target.target_id}',
        'upper_solve_id': f'strict:max:{target.target_id}',
        'bridge_objective_value': None,
    }


def _estimate_record(
    *,
    config: SorsRunConfig,
    model_run_id: str,
    constraint_set_hash: str,
    target: LinearTarget,
    class_name: str,
    certified,
    optimum_value: float | None,
    bridge_objective_value: float,
) -> dict[str, object]:
    value = (
        certified.published_value
        if certified.published_value is not None
        else optimum_value
    )
    status = (
        certified.status
        if certified.published_value is not None
        else 'CONDITIONAL_BRIDGE_ESTIMATE'
    )
    return {
        'as_of_date': config.as_of_date,
        'geography_node_id': target.region_code,
        'geography_name': target.region_name,
        'geography_kind': 'atomic_region',
        'classifier_id': 'okved2',
        'activity_code': target.class_code,
        'activity_name': class_name,
        'metric': target.metric,
        'value': value,
        'lower_bound': certified.lower,
        'upper_bound': certified.upper,
        'status': status,
        'evidence_layer': 'CONDITIONAL_BRIDGE_OPTIMUM',
        'is_published': False,
        'is_reconstructed': False,
        'is_estimate': True,
        'proof_type': 'global_optimum_set_minmax',
        'observation_id': None,
        'source_series': None,
        'source_file_actual': None,
        'source_sheet': None,
        'source_row': None,
        'source_column': None,
        'source_sha256': None,
        'model_run_id': model_run_id,
        'mapping_version': config.mapping_version,
        'constraint_set_hash': constraint_set_hash,
        'lower_solve_id': f'bridge:min:{target.target_id}',
        'upper_solve_id': f'bridge:max:{target.target_id}',
        'bridge_objective_value': bridge_objective_value,
    }


def run_sors_restoration(
    source: SorsSourceFiles | SorsSourceBundle,
    config: SorsRunConfig,
) -> SorsRestorationResult:
    bundle = (
        source
        if isinstance(source, SorsSourceBundle)
        else load_sors_source_grid(
            source, config.as_of_date, config.publication_step
        )
    )
    validate_source_bundle(bundle)
    mapping_manifest = validate_mapping_version(config.mapping_version)
    mapping_edges = build_atom_class_edges(
        bundle.okved2_classes, config.mapping_version
    )
    strict_problem, strict_builder = build_strict_problem(bundle)
    bridge_problem = None
    bridge_builder = None
    if config.include_conditional_bridge:
        bridge_problem, bridge_builder = build_bridge_flow_problem(
            bundle, config, mapping_edges
        )

    target_specs = _select_targets(bundle, config)
    strict_targets = [
        strict_builder.target(*spec) for spec in target_specs
    ]
    bridge_targets = (
        [bridge_builder.target(*spec) for spec in target_specs]
        if bridge_builder is not None else []
    )
    batch = solve_restoration_batch(
        strict_problem,
        strict_targets,
        bridge_problem=bridge_problem,
        bridge_targets=bridge_targets,
        bridge_objective_tolerance=config.bridge_objective_tolerance,
        time_limit=config.solver_time_limit_seconds,
        threads=config.solver_threads,
    )

    conflicts: list[dict[str, object]] = []
    if not batch.strict_feasibility.success:
        conflicts.append({
            'model_layer': 'STRICT',
            'status': batch.strict_feasibility.status,
            'message': 'Official publication model is infeasible.',
        })
        return SorsRestorationResult(
            canonical_grid=bundle.canonical_grid,
            facts_grid=published_facts(bundle.canonical_grid),
            estimates_grid=pd.DataFrame(columns=FACT_COLUMNS),
            bounds_grid=pd.DataFrame(),
            bridge_bounds_grid=pd.DataFrame(),
            bridge_diagnostics_grid=pd.DataFrame(),
            constraints_grid=strict_problem.constraints_grid,
            mapping_edges_grid=mapping_edges,
            conflicts_grid=pd.DataFrame(conflicts),
            audit={
                'as_of_date': config.as_of_date,
                'strategy_box_version': '0.3.1',
                'hard_feasible': False,
                'solver_backend': batch.backend,
                'solver_version': batch.version,
            },
        )

    if bridge_problem is not None and (
        batch.bridge_optimum is None or not batch.bridge_optimum.success
    ):
        conflicts.append({
            'model_layer': 'CONDITIONAL_BRIDGE',
            'status': (
                None if batch.bridge_optimum is None
                else batch.bridge_optimum.status
            ),
            'message': 'Conditional atom-flow bridge model is infeasible.',
        })

    model_run_id = _model_run_id(bundle, config)
    constraint_set_hash = _constraint_hash(
        strict_problem.constraints_grid,
        pd.DataFrame() if bridge_problem is None else bridge_problem.constraints_grid,
    )
    policy = RoundingPolicy(step=config.publication_step)
    class_names = (
        bundle.okved2_classes.set_index('class_code')['class_name']
        .astype(str).to_dict()
    )
    strict_bounds: list[dict[str, object]] = []
    bridge_bounds: list[dict[str, object]] = []
    reconstructed: list[dict[str, object]] = []
    estimates: list[dict[str, object]] = []

    for target in strict_targets:
        lower, upper = batch.strict_targets[target.target_id]
        _require_pair(target, lower, upper, layer='STRICT')
        cert = certify_interval(
            float(lower.objective_value),
            float(upper.objective_value),
            policy=policy,
            point_tolerance=config.point_tolerance,
            evidence_layer='STRICT',
        )
        strict_bounds.append({
            'as_of_date': config.as_of_date,
            'region_code': target.region_code,
            'region_name': target.region_name,
            'class_code': target.class_code,
            'class_name': class_names[target.class_code],
            'metric': target.metric,
            'lower_bound': cert.lower,
            'upper_bound': cert.upper,
            'published_value': cert.published_value,
            'status': cert.status,
            'model_run_id': model_run_id,
            'constraint_set_hash': constraint_set_hash,
        })
        if cert.published_value is not None:
            reconstructed.append(_fact_record(
                config=config,
                model_run_id=model_run_id,
                constraint_set_hash=constraint_set_hash,
                target=target,
                class_name=class_names[target.class_code],
                certified=cert,
            ))

    if (
        bridge_problem is not None
        and batch.bridge_optimum is not None
        and batch.bridge_optimum.success
        and batch.bridge_optimum.objective_value is not None
    ):
        for target in bridge_targets:
            lower, upper = batch.bridge_targets[target.target_id]
            _require_pair(
                target, lower, upper, layer='CONDITIONAL_BRIDGE_OPTIMUM'
            )
            cert = certify_interval(
                float(lower.objective_value),
                float(upper.objective_value),
                policy=policy,
                point_tolerance=config.point_tolerance,
                evidence_layer='CONDITIONAL_BRIDGE_OPTIMUM',
            )
            optimum_value = _target_value(
                target, batch.bridge_optimum.values
            )
            bridge_bounds.append({
                'as_of_date': config.as_of_date,
                'region_code': target.region_code,
                'region_name': target.region_name,
                'class_code': target.class_code,
                'class_name': class_names[target.class_code],
                'metric': target.metric,
                'lower_bound': cert.lower,
                'upper_bound': cert.upper,
                'published_value': cert.published_value,
                'optimum_point_value': optimum_value,
                'status': cert.status,
                'bridge_objective_value': batch.bridge_optimum.objective_value,
                'bridge_objective_tolerance': config.bridge_objective_tolerance,
                'model_run_id': model_run_id,
                'mapping_version': config.mapping_version,
                'constraint_set_hash': constraint_set_hash,
            })
            estimates.append(_estimate_record(
                config=config,
                model_run_id=model_run_id,
                constraint_set_hash=constraint_set_hash,
                target=target,
                class_name=class_names[target.class_code],
                certified=cert,
                optimum_value=optimum_value,
                bridge_objective_value=float(
                    batch.bridge_optimum.objective_value
                ),
            ))

    published = published_facts(bundle.canonical_grid)
    reconstructed_frame = pd.DataFrame(reconstructed).reindex(columns=FACT_COLUMNS)
    facts = pd.concat([published, reconstructed_frame], ignore_index=True)
    estimates_frame = pd.DataFrame(estimates).reindex(columns=FACT_COLUMNS)
    strict_constraints = strict_problem.constraints_grid.assign(
        mapping_version=None
    )
    bridge_constraints = (
        pd.DataFrame()
        if bridge_problem is None
        else bridge_problem.constraints_grid.assign(
            mapping_version=config.mapping_version
        )
    )
    constraints = pd.concat(
        [strict_constraints, bridge_constraints], ignore_index=True, sort=False
    )
    diagnostics = (
        pd.DataFrame()
        if bridge_problem is None or batch.bridge_optimum is None
        else _bridge_diagnostics(
            mapping_edges, bridge_problem, batch.bridge_optimum.values
        )
    )
    bridge_fallback_mass = (
        None
        if batch.bridge_optimum is None
        else batch.bridge_optimum.objective_value
    )
    audit = {
        'model_run_id': model_run_id,
        'as_of_date': config.as_of_date,
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'strategy_box_version': '0.3.1',
        'solver_backend': batch.backend,
        'solver_version': batch.version,
        'mapping_version': config.mapping_version,
        'mapping_status': mapping_manifest.get('status'),
        'strict_official_crosswalk': mapping_manifest.get(
            'strict_official_crosswalk'
        ),
        'atomic_regions': len(bundle.atomic_regions),
        'okved2_classes': len(bundle.okved2_classes),
        'strict_variables': strict_problem.num_variables,
        'strict_constraints': int(strict_problem.matrix.shape[0]),
        'bridge_variables': (
            0 if bridge_problem is None else bridge_problem.num_variables
        ),
        'bridge_constraints': (
            0 if bridge_problem is None else int(bridge_problem.matrix.shape[0])
        ),
        'strict_feasible': batch.strict_feasibility.success,
        'bridge_feasible': (
            None if batch.bridge_optimum is None
            else batch.bridge_optimum.success
        ),
        'minimum_off_preferred_bridge_mass_mln_rub': bridge_fallback_mass,
        'bridge_objective_tolerance': config.bridge_objective_tolerance,
        'targets_certified': len(strict_targets),
        'strict_reconstructed_facts': len(reconstructed_frame),
        'conditional_bridge_estimates': len(estimates_frame),
        'source_rows': int(len(bundle.canonical_grid)),
        'constraint_set_hash': constraint_set_hash,
        'important_note': (
            'facts_grid contains only published observations and values '
            'identified by official publication constraints. estimates_grid '
            'contains conditional bridge results certified across the complete '
            'globally minimum-reclassification solution set; these values are '
            'never promoted to reconstructed facts.'
        ),
    }
    return SorsRestorationResult(
        canonical_grid=bundle.canonical_grid,
        facts_grid=facts,
        estimates_grid=estimates_frame,
        bounds_grid=pd.DataFrame(strict_bounds),
        bridge_bounds_grid=pd.DataFrame(bridge_bounds),
        bridge_diagnostics_grid=diagnostics,
        constraints_grid=constraints,
        mapping_edges_grid=mapping_edges,
        conflicts_grid=pd.DataFrame(conflicts),
        audit=audit,
    )
