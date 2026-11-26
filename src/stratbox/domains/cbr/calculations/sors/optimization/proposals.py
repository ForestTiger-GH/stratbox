from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from stratbox.domains.cbr.calculations.sors.evidence import ROUNDING_OPTIMAL_TIER
from stratbox.domains.cbr.calculations.sors.evidence import ROUNDING_PREFERRED_TIER
from stratbox.domains.cbr.calculations.sors.evidence import ROUNDING_SELECTED_TIER
from stratbox.domains.cbr.calculations.sors.publication import RoundingPolicy
from stratbox.domains.cbr.calculations.sors.publication import SorsPublicationLedger


@dataclass(frozen=True)
class SorsOptimizationExecution:
    quantities_grid: pd.DataFrame
    facts_ledger_grid: pd.DataFrame
    current_facts_grid: pd.DataFrame
    derivations_grid: pd.DataFrame
    solver_runs_grid: pd.DataFrame
    target_bounds_grid: pd.DataFrame
    rounding_profiles_grid: pd.DataFrame
    selection_attempts_grid: pd.DataFrame
    optimization_rounds_grid: pd.DataFrame
    deterministic_passes_grid: pd.DataFrame
    inheritance_events_grid: pd.DataFrame
    tokens_grid: pd.DataFrame
    status: str
    rounds: int
    targets_attempted: int
    new_facts: int


def _model_assumption_tier(quantities_grid: pd.DataFrame) -> int:
    lower = (
        int(quantities_grid['lower_assumption_tier'].fillna(0).astype(int).max())
        if 'lower_assumption_tier' in quantities_grid and not quantities_grid.empty
        else 0
    )
    upper = (
        int(quantities_grid['upper_assumption_tier'].fillna(0).astype(int).max())
        if 'upper_assumption_tier' in quantities_grid and not quantities_grid.empty
        else 0
    )
    return max(lower, upper)


def _promote_rounding_optimal_buckets(
    optimal_bounds: pd.DataFrame,
    quantities_grid: pd.DataFrame,
    ledger: SorsPublicationLedger,
    policy: RoundingPolicy,
    *,
    optimization_round: int,
    model_assumption_tier: int,
) -> set[str]:
    if optimal_bounds.empty:
        return set()
    lookup = quantities_grid.set_index('quantity_id', drop=False)
    promoted: set[str] = set()
    for row in optimal_bounds.itertuples(index=False):
        if row.lower_bound is None or row.upper_bound is None:
            continue
        bucket = policy.single_bucket(
            float(row.lower_bound),
            float(row.upper_bound),
            lower_attained=True,
            upper_attained=True,
        )
        if bucket is None:
            continue
        quantity_id = str(row.quantity_id)
        if quantity_id not in lookup.index:
            continue
        quantity = lookup.loc[quantity_id]
        fact_tier = max(ROUNDING_OPTIMAL_TIER, int(model_assumption_tier))
        if fact_tier <= ROUNDING_OPTIMAL_TIER:
            method = 'ROUNDING_OPTIMUM_IDENTIFIED'
        elif fact_tier == ROUNDING_PREFERRED_TIER:
            method = 'ROUNDING_PREFERRED_CLOSURE'
        else:
            method = 'ROUNDING_SELECTED_CLOSURE'
        changed = ledger.promote_external_bucket(
            quantity,
            published_value=float(bucket),
            evidence_method=method,
            restoration_pass=0,
            optimization_round=optimization_round,
            proof_ids=(str(row.lower_solve_id), str(row.upper_solve_id)),
            details='One publication bucket across the minimum-rounding-distortion optimal face.',
            assumption_tier=fact_tier,
        )
        if changed:
            promoted.add(quantity_id)
    return promoted


def _promote_selected(
    accepted: pd.DataFrame,
    quantities_grid: pd.DataFrame,
    ledger: SorsPublicationLedger,
    *,
    optimization_round: int,
) -> set[str]:
    if accepted.empty:
        return set()
    lookup = quantities_grid.set_index('quantity_id', drop=False)
    promoted: set[str] = set()
    for row in accepted.itertuples(index=False):
        quantity_id = str(row.quantity_id)
        if quantity_id not in lookup.index:
            continue
        evidence_method = str(
            getattr(row, 'selection_evidence_method', 'ROUNDING_SELECTED')
        )
        preferred = evidence_method == 'ROUNDING_PREFERRED'
        proof_ids = tuple(
            str(value)
            for value in (
                getattr(row, 'competition_attempt_id', None),
                getattr(row, 'selection_attempt_id', None),
            )
            if value is not None and str(value) != 'nan'
        )
        changed = ledger.promote_external_bucket(
            lookup.loc[quantity_id],
            published_value=float(row.selected_bucket),
            evidence_method=evidence_method,
            restoration_pass=0,
            optimization_round=optimization_round,
            proof_ids=proof_ids,
            details=(
                'Publication bucket is decisively cheaper than alternative buckets by global '
                'L1 source-rounding cost inside the hard official publication '
                'intervals and is jointly validated inside the configured budget.'
                if preferred
                else
                'Common-benchmark publication bucket jointly validated without exceeding the '
                'configured relaxed-L1 budget and any optional L∞ cap.'
            ),
            assumption_tier=(
                ROUNDING_PREFERRED_TIER if preferred else ROUNDING_SELECTED_TIER
            ),
        )
        if changed:
            promoted.add(quantity_id)
    return promoted


