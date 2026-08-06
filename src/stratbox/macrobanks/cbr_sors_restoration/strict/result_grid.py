from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsSourceBundle
from stratbox.macrobanks.cbr_sors_restoration.metrics import (
    METRIC_NAMES_RU,
    METRIC_ORDER,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    PublicationInterval,
    RoundingPolicy,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.certification import (
    certify_interval,
)


def _present(value: object) -> bool:
    return value is not None and not pd.isna(value) and str(value) != ''


def _derivation_method(row) -> str:
    if _present(getattr(row, 'cell_lower_solve_id', None)) or _present(
        getattr(row, 'cell_upper_solve_id', None)
    ):
        return 'TARGET_CELL_SYSTEM'
    if _present(getattr(row, 'lp_lower_solve_id', None)) or _present(
        getattr(row, 'lp_upper_solve_id', None)
    ):
        return 'LEGACY_TARGET_SYSTEM'
    if _present(getattr(row, 'last_derivation_id', None)):
        return 'DETERMINISTIC_CLOSURE'
    return 'NONE'


def build_regional_okved2_grid(
    bundle: SorsSourceBundle,
    quantities_grid: pd.DataFrame,
    *,
    as_of_date: str,
    dataset_id: str,
    strict_model_id: str,
    execution_run_id: str,
    policy: RoundingPolicy,
    point_tolerance: float,
    feasibility_confirmed: bool,
    rules_version: str,
    solver_backend: str | None,
    solver_version: str | None,
) -> pd.DataFrame:
    metrics = quantities_grid[
        quantities_grid['quantity_kind'].eq('REGIONAL_CLASS_METRIC')
    ].copy()
    regions = bundle.atomic_regions_grid[
        [
            'region_code',
            'region_name',
            'region_order',
            'federal_district_code',
            'federal_district_name',
            'federal_district_order',
        ]
    ]
    classes = bundle.okved2_classes_grid[
        [
            'class_code',
            'class_name',
            'class_order',
            'section_code',
            'section_name',
            'section_order',
            'publication_category_code',
            'is_individually_published',
        ]
    ]
    metrics = metrics.merge(regions, on='region_code', how='left', validate='many_to_one')
    metrics = metrics.merge(classes, on='class_code', how='left', validate='many_to_one')
    records: list[dict[str, object]] = []
    for row in metrics.itertuples(index=False):
        interval = PublicationInterval(
            float(row.lower_bound),
            float(row.upper_bound),
            bool(row.lower_attained),
            bool(row.upper_attained),
        )
        certification = certify_interval(
            interval,
            policy=policy,
            point_tolerance=point_tolerance,
        )
        identified = certification.identification_status in {
            'POINT_IDENTIFIED',
            'PUBLISHED_BUCKET_IDENTIFIED',
        }
        strict_fact = bool(feasibility_confirmed and identified)
        method = _derivation_method(row)
        status = certification.identification_status
        if not feasibility_confirmed and identified:
            status = f'PROVISIONAL_{status}'
        records.append(
            {
                'dataset_id': dataset_id,
                'strict_model_id': strict_model_id,
                'execution_run_id': execution_run_id,
                'as_of_date': as_of_date,
                'region_code': row.region_code,
                'region_name': row.region_name,
                'region_order': row.region_order,
                'federal_district_code': row.federal_district_code,
                'federal_district_name': row.federal_district_name,
                'federal_district_order': row.federal_district_order,
                'section_code': row.section_code,
                'section_name': row.section_name,
                'section_order': row.section_order,
                'class_code': row.class_code,
                'class_name': row.class_name,
                'class_order': row.class_order,
                'publication_category_code': row.publication_category_code,
                'is_individually_published': row.is_individually_published,
                'metric': row.metric,
                'metric_name': METRIC_NAMES_RU[str(row.metric)],
                'metric_order': METRIC_ORDER[str(row.metric)],
                'unit': 'million_rubles',
                'value': certification.value if strict_fact else None,
                'value_precision': (
                    certification.value_precision if strict_fact else 'NONE'
                ),
                'identified_value': certification.value if identified else None,
                'identified_value_precision': (
                    certification.value_precision if identified else 'NONE'
                ),
                'feasibility_confirmed': feasibility_confirmed,
                'exact_value': certification.exact_value if strict_fact else None,
                'published_value': (
                    certification.published_value if strict_fact else None
                ),
                'lower_bound': interval.lower,
                'upper_bound': interval.upper,
                'lower_attained': interval.lower_attained,
                'upper_attained': interval.upper_attained,
                'interval_width': interval.width,
                'evidence_layer': 'STRICT',
                'identification_status': status,
                'derivation_method': method,
                'is_strict_fact': strict_fact,
                'is_reconstructed': strict_fact,
                'is_zero_at_published_precision': bool(
                    certification.is_zero_at_published_precision
                ),
                'is_exact_zero': bool(certification.is_exact_zero),
                'is_lp_certified': bool(
                    identified and method in {'TARGET_CELL_SYSTEM', 'LEGACY_TARGET_SYSTEM'}
                ),
                'proof_id': (
                    getattr(row, 'cell_lower_solve_id', None)
                    if _present(getattr(row, 'cell_lower_solve_id', None))
                    else (
                        getattr(row, 'lp_lower_solve_id', None)
                        if _present(getattr(row, 'lp_lower_solve_id', None))
                        else (
                            getattr(row, 'last_derivation_id', None)
                            if _present(getattr(row, 'last_derivation_id', None))
                            else None
                        )
                    )
                ),
                'closure_pass': getattr(row, 'last_derivation_pass', None),
                'supporting_constraint_count': getattr(
                    row, 'last_derivation_support_count', 0
                ),
                'lower_solve_id': (
                    getattr(row, 'cell_lower_solve_id', None)
                    if _present(getattr(row, 'cell_lower_solve_id', None))
                    else getattr(row, 'lp_lower_solve_id', None)
                ),
                'upper_solve_id': (
                    getattr(row, 'cell_upper_solve_id', None)
                    if _present(getattr(row, 'cell_upper_solve_id', None))
                    else getattr(row, 'lp_upper_solve_id', None)
                ),
                'cell_resolution_status': getattr(
                    row, 'cell_resolution_status', None
                ),
                'cell_largest_horizon': getattr(
                    row, 'cell_largest_horizon', None
                ),
                'cell_attempt_id': getattr(row, 'cell_attempt_id', None),
                'cell_subsystem_id': getattr(row, 'cell_subsystem_id', None),
                'rules_version': rules_version,
                'solver_backend': solver_backend,
                'solver_version': solver_version,
            }
        )
    return pd.DataFrame(records).sort_values(
        ['region_order', 'class_order', 'metric_order'],
        kind='stable',
    ).reset_index(drop=True)


def build_components_grid(
    bundle: SorsSourceBundle,
    quantities_grid: pd.DataFrame,
    *,
    as_of_date: str,
    dataset_id: str,
    strict_model_id: str,
    execution_run_id: str,
) -> pd.DataFrame:
    components = quantities_grid[
        quantities_grid['quantity_kind'].eq('ATOMIC_COMPONENT')
    ].copy()
    components = components.merge(
        bundle.atomic_regions_grid,
        on='region_code',
        how='left',
        validate='many_to_one',
    ).merge(
        bundle.okved2_classes_grid,
        on='class_code',
        how='left',
        validate='many_to_one',
    )
    components.insert(0, 'execution_run_id', execution_run_id)
    components.insert(0, 'strict_model_id', strict_model_id)
    components.insert(0, 'dataset_id', dataset_id)
    components.insert(3, 'as_of_date', as_of_date)
    return components.sort_values(
        ['region_order', 'class_order', 'component'],
        kind='stable',
    ).reset_index(drop=True)
