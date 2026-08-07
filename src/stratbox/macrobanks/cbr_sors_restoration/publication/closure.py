from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.publication.inheritance import (
    SorsInheritanceResult,
    run_value_inheritance,
)
from stratbox.macrobanks.cbr_sors_restoration.publication.ledger import (
    SorsPublicationLedger,
)
from stratbox.macrobanks.cbr_sors_restoration.publication.partitions import (
    SorsPublicationGraph,
    publication_hierarchy_relations,
)
from stratbox.macrobanks.cbr_sors_restoration.publication.rounding import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.strict.interval_closure import SorsIntervalClosureState


class SorsPublicationFixedPointLimitError(RuntimeError):
    """The deterministic publication phase failed to reach its required fixed point."""


@dataclass(frozen=True)
class SorsPublicationClosureExecution:
    quantities_grid: pd.DataFrame
    facts_ledger_grid: pd.DataFrame
    current_facts_grid: pd.DataFrame
    derivations_grid: pd.DataFrame
    inheritance_events_grid: pd.DataFrame
    tokens_grid: pd.DataFrame
    promotion_events_grid: pd.DataFrame
    passes_grid: pd.DataFrame
    passes: int
    bound_updates: int
    new_facts: int
    status: str


def run_publication_fixed_point(
    closure_state: SorsIntervalClosureState,
    publication_graph: SorsPublicationGraph,
    ledger: SorsPublicationLedger,
    *,
    policy: RoundingPolicy,
    point_tolerance: float,
    max_passes: int,
    optimization_round: int | None = None,
    inheritance_enabled: bool = True,
) -> SorsPublicationClosureExecution:
    """Exhaust deterministic zero/bucket closure and published-value inheritance.

    The loop is intentionally completed before any optimization search.  Every new
    publication fact constrains its latent quantity to the corresponding publication
    bucket, which can create new zeros; those zeros can unlock further inheritance.
    """

    if max_passes <= 0:
        raise ValueError('Publication fixed-point pass limit must be positive')

    # Complete/disjoint publication hierarchy describes exact identities between
    # the *hidden* monetary aggregates.  Add those equations to interval closure
    # once (idempotently) so grouped residuals can participate in the cheap fixed
    # point.  The rounded representatives themselves are never added/subtracted.
    hierarchy_relations = publication_hierarchy_relations(publication_graph)
    hierarchy_relations_added = closure_state.add_relations(hierarchy_relations)

    if not ledger.current_quantity_ids:
        ledger.seed_source_facts(closure_state.quantities_grid)

    pass_rows: list[dict[str, object]] = []
    inheritance_frames: list[pd.DataFrame] = []
    latest_tokens_grid = pd.DataFrame()
    total_bound_updates = 0
    initial_fact_count = len(ledger.current_quantity_ids)
    seed_quantity_ids: tuple[str, ...] | None = None
    status = 'FIXED_POINT'

    for pass_number in range(1, max_passes + 1):
        before_facts = len(ledger.current_quantity_ids)
        closure = closure_state.run(seed_quantity_ids=seed_quantity_ids)
        total_bound_updates += closure.bound_updates

        interval_promoted = ledger.promote_interval_facts(
            closure_state.quantities_grid,
            policy=policy,
            point_tolerance=point_tolerance,
            restoration_pass=pass_number,
            optimization_round=optimization_round,
        )
        updated, interval_bound_changes = ledger.apply_current_facts_to_quantities(
            closure_state.quantities_grid,
            policy=policy,
            tolerance=point_tolerance,
        )
        if interval_bound_changes:
            closure_state.replace_quantities(updated)

        inheritance = (
            run_value_inheritance(
                publication_graph,
                closure_state.quantities_grid,
                ledger,
                restoration_pass=pass_number,
                optimization_round=optimization_round,
            )
            if inheritance_enabled
            else SorsInheritanceResult(frozenset(), pd.DataFrame(), pd.DataFrame())
        )
        latest_tokens_grid = inheritance.tokens_grid
        if not inheritance.events_grid.empty:
            inheritance_frames.append(inheritance.events_grid)
        updated, inherited_bound_changes = ledger.apply_current_facts_to_quantities(
            closure_state.quantities_grid,
            policy=policy,
            tolerance=point_tolerance,
        )
        fact_bound_changes = set(interval_bound_changes) | set(inherited_bound_changes)
        if fact_bound_changes:
            closure_state.replace_quantities(updated)

        after_facts = len(ledger.current_quantity_ids)
        new_facts = after_facts - before_facts
        zero_count = 0
        current = ledger.facts_grid(current_only=True)
        if not current.empty:
            zero_count = int(current['published_value'].astype(float).eq(0.0).sum())
        pass_rows.append(
            {
                'publication_pass': pass_number,
                'optimization_round': optimization_round,
                'interval_closure_passes': closure.passes,
                'interval_bound_updates': closure.bound_updates,
                'publication_hierarchy_relations': len(hierarchy_relations),
                'new_hierarchy_relations_added': (
                    hierarchy_relations_added if pass_number == 1 else 0
                ),
                'new_interval_facts': len(interval_promoted),
                'new_inherited_facts': len(inheritance.promoted_quantity_ids),
                'inheritance_sweeps': inheritance.sweeps,
                'new_facts': new_facts,
                'fact_bucket_bound_updates': len(fact_bound_changes),
                'total_current_facts': after_facts,
                'total_publication_zeros': zero_count,
                'stop_reason': None,
            }
        )

        if not fact_bound_changes:
            pass_rows[-1]['stop_reason'] = 'NO_NEW_LATENT_BUCKET_BOUNDS'
            break
        seed_quantity_ids = (
            tuple(sorted(fact_bound_changes)) if fact_bound_changes else None
        )
    else:
        if pass_rows:
            pass_rows[-1]['stop_reason'] = 'PASS_LIMIT'
        raise SorsPublicationFixedPointLimitError(
            'Deterministic publication closure did not reach a fixed point within '
            f'{max_passes} passes; optimization is not allowed to start from a '
            'partially closed publication state.'
        )

    inheritance_grid = (
        pd.concat(inheritance_frames, ignore_index=True, sort=False)
        if inheritance_frames
        else pd.DataFrame()
    )
    return SorsPublicationClosureExecution(
        quantities_grid=closure_state.quantities_grid.copy(),
        facts_ledger_grid=ledger.facts_grid(),
        current_facts_grid=ledger.facts_grid(current_only=True),
        derivations_grid=closure_state.derivations_grid.copy(),
        inheritance_events_grid=inheritance_grid,
        tokens_grid=latest_tokens_grid,
        promotion_events_grid=ledger.promotion_events_grid(),
        passes_grid=pd.DataFrame(pass_rows),
        passes=len(pass_rows),
        bound_updates=total_bound_updates,
        new_facts=len(ledger.current_quantity_ids) - initial_fact_count,
        status=status,
    )
