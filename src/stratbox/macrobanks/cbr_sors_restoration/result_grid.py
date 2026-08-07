from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsSourceBundle
from stratbox.macrobanks.cbr_sors_restoration.metrics import METRIC_NAMES_RU, METRIC_ORDER
from stratbox.macrobanks.cbr_sors_restoration.publication import PublicationInterval




def _lp_proof_flags(
    evidence_method: str, proof_ids: tuple[str, ...]
) -> tuple[bool, bool, bool]:
    """Return direct Solver-proof flags without inferring provenance from method names."""

    is_lp_certified = bool(proof_ids)
    has_two_sided_bounds = bool(
        is_lp_certified
        and len(proof_ids) >= 2
        and evidence_method
        in {
            'LATENT_POINT_IDENTIFIED',
            'PUBLISHED_BUCKET_IDENTIFIED',
            'ROUNDING_OPTIMUM_IDENTIFIED',
        }
    )
    return is_lp_certified, has_two_sided_bounds, has_two_sided_bounds


def _fact_lookup(facts_grid: pd.DataFrame) -> pd.DataFrame:
    if facts_grid.empty:
        return pd.DataFrame()
    current = facts_grid[facts_grid['is_current'].astype(bool)].copy()
    return current.set_index('quantity_id', drop=False)


def build_regional_okved2_grid(
    bundle: SorsSourceBundle,
    quantities_grid: pd.DataFrame,
    facts_grid: pd.DataFrame,
    *,
    as_of_date: str,
    dataset_id: str,
    strict_model_id: str,
    execution_run_id: str,
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
            'region_code', 'region_name', 'region_order',
            'federal_district_code', 'federal_district_name', 'federal_district_order',
        ]
    ]
    classes = bundle.okved2_classes_grid[
        [
            'class_code', 'class_name', 'class_order',
            'section_code', 'section_name', 'section_order',
            'publication_category_code', 'is_individually_published',
        ]
    ]
    metrics = metrics.merge(regions, on='region_code', how='left', validate='many_to_one')
    metrics = metrics.merge(classes, on='class_code', how='left', validate='many_to_one')
    facts = _fact_lookup(facts_grid)
    records: list[dict[str, object]] = []
    for row in metrics.itertuples(index=False):
        quantity_id = str(row.quantity_id)
        fact = None
        if not facts.empty and quantity_id in facts.index:
            fact = facts.loc[quantity_id]
            if isinstance(fact, pd.DataFrame):
                fact = fact.iloc[-1]
        accepted = bool(
            feasibility_confirmed
            and fact is not None
            and bool(fact.is_accepted_fact)
        )
        value = float(fact.published_value) if accepted else None
        latent_status = str(fact.latent_status) if fact is not None else 'UNRESOLVED'
        evidence_method = str(fact.evidence_method) if fact is not None else 'UNRESOLVED'
        assumption_tier = int(fact.assumption_tier) if fact is not None else 0
        evidence_strength = int(fact.evidence_strength) if fact is not None else None
        interval = PublicationInterval(
            float(row.lower_bound),
            float(row.upper_bound),
            bool(row.lower_attained),
            bool(row.upper_attained),
        )
        proof_ids = (
            tuple(fact.proof_ids)
            if fact is not None and isinstance(fact.proof_ids, (tuple, list))
            else ()
        )
        (
            has_solver_proof,
            lp_lower_certified,
            lp_upper_certified,
        ) = _lp_proof_flags(evidence_method, proof_ids)
        value_precision = 'NONE'
        exact_value = None
        if accepted:
            if latent_status == 'POINT' and fact.latent_value is not None:
                value_precision = 'EXACT'
                exact_value = float(fact.latent_value)
            else:
                value_precision = 'PUBLISHED'
        records.append(
            {
                'dataset_id': dataset_id,
                'strict_model_id': strict_model_id,
                'execution_run_id': execution_run_id,
                'as_of_date': as_of_date,
                'portfolio_scope': getattr(row, 'portfolio_scope', 'CORPORATE_TOTAL'),
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
                'value': value,
                'value_precision': value_precision,
                'identified_value': value,
                'identified_value_precision': value_precision,
                'published_value': value,
                'exact_value': exact_value,
                'publication_status': 'EXACT' if accepted else 'UNKNOWN',
                'latent_status': latent_status,
                'evidence_method': evidence_method,
                'assumption_tier': assumption_tier,
                'evidence_strength': evidence_strength,
                'identification_status': evidence_method if accepted else 'UNRESOLVED',
                'derivation_method': evidence_method,
                'fact_id': None if fact is None else fact.fact_id,
                'feasibility_confirmed': bool(feasibility_confirmed),
                'lower_bound': interval.lower,
                'upper_bound': interval.upper,
                'lower_attained': interval.lower_attained,
                'upper_attained': interval.upper_attained,
                'interval_width': interval.width,
                'evidence_layer': 'PRIMARY',
                'is_primary_fact': accepted,
                'is_reconstructed': accepted,
                'is_final_accepted': accepted,
                'value_identified': accepted,
                'bounds_certified': bool(feasibility_confirmed),
                'is_estimate': False,
                'is_benchmark_estimate': False,
                'benchmark_value': None,
                'is_zero_at_published_precision': bool(accepted and value == 0.0),
                'is_exact_zero': bool(
                    accepted and latent_status == 'POINT' and exact_value == 0.0
                ),
                'is_lp_certified': bool(has_solver_proof),
                'lp_lower_certified': bool(lp_lower_certified),
                'lp_upper_certified': bool(lp_upper_certified),
                'source_observation_ids': (
                    tuple(fact.source_observation_ids)
                    if fact is not None and isinstance(fact.source_observation_ids, (tuple, list))
                    else ()
                ),
                'supporting_partition_ids': (
                    tuple(fact.supporting_partition_ids)
                    if fact is not None and isinstance(fact.supporting_partition_ids, (tuple, list))
                    else ()
                ),
                # Publication facts currently track publication partitions, not
                # latent quantity-relation IDs.  Keep this field empty rather
                # than mislabelling partition IDs as relation provenance.
                'supporting_relation_ids': (),
                'supporting_fact_ids': (
                    tuple(fact.supporting_fact_ids)
                    if fact is not None and isinstance(fact.supporting_fact_ids, (tuple, list))
                    else ()
                ),
                'proof_ids': proof_ids,
                'rules_version': rules_version,
                'solver_backend': solver_backend,
                'solver_version': solver_version,
            }
        )
    return pd.DataFrame(records).sort_values(
        ['region_order', 'class_order', 'metric_order'], kind='stable'
    ).reset_index(drop=True)


def build_components_grid(
    bundle: SorsSourceBundle,
    quantities_grid: pd.DataFrame,
    facts_grid: pd.DataFrame,
    *,
    as_of_date: str,
    dataset_id: str,
    strict_model_id: str,
    execution_run_id: str,
) -> pd.DataFrame:
    components = quantities_grid[
        quantities_grid['quantity_kind'].eq('ATOMIC_COMPONENT')
    ].copy()
    facts = _fact_lookup(facts_grid)
    if not facts.empty:
        columns = [
            'quantity_id', 'published_value', 'publication_status', 'latent_status',
            'evidence_method', 'fact_id', 'feasibility_confirmed', 'is_accepted_fact',
        ]
        available = [column for column in columns if column in facts.columns]
        components = components.merge(
            facts.reset_index(drop=True)[available],
            on='quantity_id',
            how='left',
            validate='one_to_one',
        )
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
        ['region_order', 'class_order', 'component'], kind='stable'
    ).reset_index(drop=True)
