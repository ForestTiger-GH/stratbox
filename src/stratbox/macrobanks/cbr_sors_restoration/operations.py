from __future__ import annotations

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsRestorationConfig,
    SorsRestorationFiles,
    SorsRestorationResult,
)
from stratbox.macrobanks.cbr_sors_restoration.diagnostics import build_mapping_diagnostics
from stratbox.macrobanks.cbr_sors_restoration.model import (
    VariableIndex,
    bounds_frame,
    build_constraints,
    build_ub_matrix,
    certify_indices,
    check_feasible,
    deterministic_closure,
    initial_bounds,
    minimum_extra_error,
)
from stratbox.macrobanks.cbr_sors_restoration.parsers import load_sors_sources
from stratbox.macrobanks.cbr_sors_restoration.schema import published_bucket


def _select_lp_targets(frame: pd.DataFrame, config: SorsRestorationConfig) -> list[int]:
    work = frame[frame['published_precision_value'].isna()].copy()
    if config.target_region_names:
        work = work[work['region_name'].isin(config.target_region_names)]
    if config.target_class_codes:
        work = work[work['class_code'].isin(config.target_class_codes)]
    if config.certify_mode == 'none':
        return []
    if config.certify_mode == 'targets' and not (config.target_region_names or config.target_class_codes):
        return []
    if config.certify_mode == 'all':
        return work['variable_id'].astype(int).tolist()
    work = work.sort_values(['interval_width', 'region_name', 'class_code', 'component'])
    return work.head(config.max_lp_targets)['variable_id'].astype(int).tolist()


def _component_facts(frame: pd.DataFrame, config: SorsRestorationConfig, method: str) -> pd.DataFrame:
    rows = []
    for _, row in frame.iterrows():
        lo, hi = float(row['lower_bound']), float(row['upper_bound'])
        bucket = published_bucket(lo, hi, config.publication_step, config.point_tolerance)
        if hi - lo <= config.point_tolerance:
            value = (lo + hi) / 2.0
            status = 'POINT_IDENTIFIED'
        elif bucket is not None:
            value = bucket
            status = 'ZERO_AT_PUBLISHED_PRECISION' if abs(bucket) <= config.point_tolerance else 'POINT_IDENTIFIED_AT_PUBLISHED_PRECISION'
        else:
            continue
        rec = row.to_dict()
        rec.update({
            'metric': row['component'],
            'value': value,
            'status': status,
            'is_strict_fact': True,
            'derivation_method': method,
        })
        rows.append(rec)
    return pd.DataFrame(rows)


def _derived_facts(component_facts: pd.DataFrame, config: SorsRestorationConfig) -> pd.DataFrame:
    if component_facts.empty:
        return pd.DataFrame()
    keys = ['region_code', 'region_name', 'federal_district_name', 'class_code', 'section_code']
    pivot = component_facts.pivot_table(index=keys, columns='component', values='value', aggfunc='first').reset_index()
    rows = []
    for _, r in pivot.iterrows():
        vals = {k: r.get(k) for k in ('performing_rub', 'overdue_rub', 'performing_fx', 'overdue_fx')}
        def add(metric: str, needed: tuple[str, ...]):
            if all(pd.notna(vals[k]) for k in needed):
                rows.append({**{k: r[k] for k in keys}, 'metric': metric, 'value': float(sum(vals[k] for k in needed)), 'status': 'EXACT_IDENTITY', 'is_strict_fact': True, 'derivation_method': 'component_identity'})
        add('debt_rub', ('performing_rub', 'overdue_rub'))
        add('debt_fx', ('performing_fx', 'overdue_fx'))
        add('debt_total', ('performing_rub', 'overdue_rub', 'performing_fx', 'overdue_fx'))
        add('overdue_total', ('overdue_rub', 'overdue_fx'))
    return pd.DataFrame(rows)


def run_sors_restoration(files: SorsRestorationFiles, config: SorsRestorationConfig) -> SorsRestorationResult:
    bundle = load_sors_sources(files, config.as_of_date)
    index = VariableIndex(bundle.atomic_regions, bundle.okved2_classes)
    constraints = build_constraints(bundle, index, config.publication_step)
    lower, upper = initial_bounds(index.size, constraints)
    lower, upper, closure_passes, closure_updates = deterministic_closure(
        lower, upper, constraints, max_passes=config.max_closure_passes
    )
    A_ub, b_ub = build_ub_matrix(index.size, constraints)
    feasibility = check_feasible(A_ub, b_ub, lower, upper)
    extra_error = {'minimum_extra_error_mln_rub': 0.0}
    if not feasibility['success']:
        extra_error = minimum_extra_error(A_ub, b_ub, index.size)
        raise ValueError(f'Published constraints are infeasible; minimum extra error: {extra_error}')

    frame = bounds_frame(index, lower, upper, config.publication_step)
    targets = _select_lp_targets(frame, config)
    lp_certified = 0
    fixed_point_rounds = 0
    # Exact LP points can tighten the cheap residual system. Usually one pass is
    # enough; loop is retained as a safe fixed-point orchestrator.
    while targets:
        fixed_point_rounds += 1
        certified = certify_indices(targets, A_ub, b_ub, lower, upper)
        changed = 0
        for idx, (lo, hi) in certified.items():
            lo = max(0.0, lo)
            if lo > lower[idx] + config.point_tolerance:
                lower[idx] = lo; changed += 1
            if hi < upper[idx] - config.point_tolerance:
                upper[idx] = hi; changed += 1
            if hi - lo <= config.point_tolerance:
                lp_certified += 1
        if not changed:
            break
        lower, upper, _, updates = deterministic_closure(lower, upper, constraints, max_passes=config.max_closure_passes)
        closure_updates += updates
        frame = bounds_frame(index, lower, upper, config.publication_step)
        targets = _select_lp_targets(frame, config)
        if fixed_point_rounds >= 5:
            break

    final_bounds = bounds_frame(index, lower, upper, config.publication_step)
    component_facts = _component_facts(final_bounds, config, 'deterministic_or_lp_bounds')
    derived = _derived_facts(component_facts, config)
    facts = pd.concat([component_facts, derived], ignore_index=True, sort=False)
    diagnostics = build_mapping_diagnostics(bundle.regional_grid, bundle.national_okved2_grid)
    audit = {
        'as_of_date': config.as_of_date,
        'atomic_regions': index.n_regions,
        'okved2_classes': index.n_classes,
        'variables': index.size,
        'constraints': len(constraints),
        'regional_constraints': sum(c.source == '01_05_A' for c in constraints),
        'national_class_constraints': sum(c.source == '01_02_C' for c in constraints),
        'fd_section_constraints': sum(c.source == '01_03_C' for c in constraints),
        'deterministic_closure_passes': closure_passes,
        'deterministic_bound_updates': closure_updates,
        'lp_targets_requested': len(_select_lp_targets(bounds_frame(index, *initial_bounds(index.size, constraints), config.publication_step), config)),
        'lp_point_certified': lp_certified,
        'fixed_point_rounds': fixed_point_rounds,
        'strict_component_facts': int(len(component_facts)),
        'strict_derived_facts': int(len(derived)),
        'feasibility': feasibility,
        'minimum_extra_error_mln_rub': extra_error['minimum_extra_error_mln_rub'],
        'important_note': 'Zero aggregate residual proves compatibility, not uniqueness. Only collapsed min/max or a single publication bucket is promoted.',
        'soft_mapping_used_in_strict_solver': False,
    }
    return SorsRestorationResult(facts, final_bounds, audit, diagnostics)
