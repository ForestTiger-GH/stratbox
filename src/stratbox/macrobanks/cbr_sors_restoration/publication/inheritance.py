from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.publication.ledger import SorsPublicationLedger
from stratbox.macrobanks.cbr_sors_restoration.publication.partitions import SorsPublicationGraph
from stratbox.macrobanks.cbr_sors_restoration.publication.tokens import (
    PublicationSupport,
    PublishedMassToken,
)


@dataclass(frozen=True)
class SorsInheritanceResult:
    promoted_quantity_ids: frozenset[str]
    events_grid: pd.DataFrame
    tokens_grid: pd.DataFrame
    sweeps: int = 0


def _tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return tuple(str(item) for item in value)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted(str(item) for item in value))
    if pd.isna(value):
        return ()
    return (str(value),)


def _support(row) -> PublicationSupport:
    return PublicationSupport(
        frozenset(_tuple(getattr(row, 'support_region_codes', ()))),
        frozenset(_tuple(getattr(row, 'support_class_codes', ()))),
        str(getattr(row, 'metric', '')),
    )


def _seed_tokens(
    partitions: pd.DataFrame,
    quantity_lookup: pd.DataFrame,
    ledger: SorsPublicationLedger,
) -> dict[str, PublishedMassToken]:
    parent_ids = set(partitions['parent_quantity_id'].astype(str))
    tokens: dict[str, PublishedMassToken] = {}
    for quantity_id in sorted(parent_ids):
        fact = ledger.current_record(quantity_id)
        if fact is None or float(fact['published_value']) <= 0.0:
            continue
        if quantity_id not in quantity_lookup.index:
            continue
        row = quantity_lookup.loc[quantity_id]
        if isinstance(row, pd.DataFrame):
            raise ValueError(f'Duplicate quantity ID in publication graph: {quantity_id}')
        support = _support(row)
        if support.is_empty:
            continue
        token_id = f'published_mass_token:{fact["fact_id"]}'
        tokens[token_id] = PublishedMassToken(
            token_id=token_id,
            root_fact_id=str(fact['fact_id']),
            root_quantity_id=quantity_id,
            portfolio_scope=fact.get('portfolio_scope'),
            metric=str(fact.get('metric') or support.metric),
            published_value=float(fact['published_value']),
            support=support,
            anchor_quantity_ids=frozenset({quantity_id}),
            supporting_fact_ids=(str(fact['fact_id']),),
            supporting_partition_ids=(),
            assumption_tier=int(fact.get('assumption_tier', 0)),
        )
    return tokens


def _matching_child(
    token: PublishedMassToken,
    partition,
    ledger: SorsPublicationLedger,
    *,
    tolerance: float = 1e-9,
) -> tuple[str, tuple[str, ...], int] | None:
    """Locate a token only when the visible child values explicitly preserve it.

    The rule is intentionally stronger than ``parent=v + zero siblings``.  One
    child must *already* be an exact publication fact equal to ``v`` and every
    sibling must already be an exact publication zero.  This is what prevents a
    parent publication 6 with sub-million zero dust from inventing an unknown
    child publication 6.
    """

    matching: list[tuple[str, dict[str, object]]] = []
    zeros: list[tuple[str, dict[str, object]]] = []
    for child_id in tuple(str(value) for value in partition.child_quantity_ids):
        child_fact = ledger.current_record(child_id)
        if child_fact is None:
            return None
        child_value = float(child_fact['published_value'])
        if abs(child_value - token.published_value) <= tolerance:
            matching.append((child_id, child_fact))
        elif abs(child_value) <= tolerance:
            zeros.append((child_id, child_fact))
        else:
            return None
    if len(matching) != 1 or len(zeros) != len(tuple(partition.child_quantity_ids)) - 1:
        return None
    child_id, child_fact = matching[0]
    supporting = tuple(
        str(fact['fact_id']) for _, fact in (*matching, *zeros)
    )
    tier = max(
        [token.assumption_tier]
        + [int(fact.get('assumption_tier', 0)) for _, fact in (*matching, *zeros)]
    )
    return child_id, supporting, tier


def _singleton_target_id(
    token: PublishedMassToken,
    metric_target_lookup: dict[tuple[str, str, str], str],
) -> str | None:
    if not token.support.is_single_cell:
        return None
    region_code = next(iter(token.support.region_codes))
    class_code = next(iter(token.support.class_codes))
    return metric_target_lookup.get((region_code, class_code, token.metric))


def _tokens_grid(tokens: dict[str, PublishedMassToken]) -> pd.DataFrame:
    rows = []
    for token in tokens.values():
        rows.append(
            {
                'token_id': token.token_id,
                'root_fact_id': token.root_fact_id,
                'root_quantity_id': token.root_quantity_id,
                'portfolio_scope': token.portfolio_scope,
                'metric': token.metric,
                'published_value': token.published_value,
                'support_region_codes': tuple(sorted(token.support.region_codes)),
                'support_class_codes': tuple(sorted(token.support.class_codes)),
                'support_region_count': len(token.support.region_codes),
                'support_class_count': len(token.support.class_codes),
                'support_cell_count': (
                    len(token.support.region_codes) * len(token.support.class_codes)
                ),
                'anchor_quantity_ids': tuple(sorted(token.anchor_quantity_ids)),
                'supporting_fact_ids': token.supporting_fact_ids,
                'supporting_partition_ids': token.supporting_partition_ids,
                'assumption_tier': token.assumption_tier,
                'status': token.status,
            }
        )
    return pd.DataFrame(rows).sort_values('token_id', kind='stable').reset_index(drop=True) if rows else pd.DataFrame()


def run_value_inheritance(
    publication_graph: SorsPublicationGraph,
    quantities_grid: pd.DataFrame,
    ledger: SorsPublicationLedger,
    *,
    restoration_pass: int,
    optimization_round: int | None = None,
) -> SorsInheritanceResult:
    """Exhaust source-preserving published-mass token localization.

    A token starts at a positive publication fact.  It may pass through a complete
    and disjoint partition only when one child publication fact has *the same*
    visible value and every sibling is publication-zero.  Different partitions of
    the same token independently narrow geography/class support; only a singleton
    support is promoted to a new region×class published fact.

    This is deliberately not arithmetic rounding.  In particular ``parent=6`` and
    zero siblings do not by themselves assign 6 to an unknown remaining child.
    """

    if publication_graph.partitions_grid.empty:
        return SorsInheritanceResult(frozenset(), pd.DataFrame(), pd.DataFrame(), 0)
    partitions = publication_graph.partitions_grid
    if 'inheritance_enabled' in partitions:
        partitions = partitions[partitions['inheritance_enabled'].astype(bool)].copy()
    if partitions.empty:
        return SorsInheritanceResult(frozenset(), pd.DataFrame(), pd.DataFrame(), 0)

    quantity_lookup = quantities_grid.set_index('quantity_id', drop=False)
    tokens = _seed_tokens(partitions, quantity_lookup, ledger)
    if not tokens:
        return SorsInheritanceResult(frozenset(), pd.DataFrame(), pd.DataFrame(), 0)

    partitions_by_parent: dict[str, list[object]] = {}
    for partition in partitions.itertuples(index=False):
        if not (bool(partition.is_complete) and bool(partition.is_disjoint)):
            continue
        partitions_by_parent.setdefault(str(partition.parent_quantity_id), []).append(partition)

    metric_target_lookup = {
        (str(row.region_code), str(row.class_code), str(row.metric)): str(row.quantity_id)
        for row in quantities_grid[
            quantities_grid['quantity_kind'].astype(str).eq('REGIONAL_CLASS_METRIC')
        ].itertuples(index=False)
    }

    events: list[dict[str, object]] = []
    promoted: set[str] = set()
    sweeps = 0
    # Every successful localization adds a previously unseen anchor to one token,
    # and every successful promotion adds a ledger fact.  This finite monotone
    # upper bound is intentionally generous and acts only as a corruption fuse.
    max_sweeps = max(2, len(partitions) + len(tokens) + 1)

    for sweep in range(1, max_sweeps + 1):
        sweeps = sweep
        sweep_changes = 0
        for token_id in sorted(tokens):
            token = tokens[token_id]
            if token.status != 'ACTIVE':
                continue
            for parent_id in sorted(token.anchor_quantity_ids):
                for partition in partitions_by_parent.get(parent_id, ()):
                    match = _matching_child(token, partition, ledger)
                    if match is None:
                        continue
                    child_id, supporting_fact_ids, tier = match
                    if child_id in token.anchor_quantity_ids:
                        continue
                    if child_id not in quantity_lookup.index:
                        continue
                    child_row = quantity_lookup.loc[child_id]
                    if isinstance(child_row, pd.DataFrame):
                        raise ValueError(f'Duplicate quantity ID in inheritance graph: {child_id}')
                    localized = token.localize(
                        child_quantity_id=child_id,
                        child_support=_support(child_row),
                        partition_id=str(partition.partition_id),
                        supporting_fact_ids=supporting_fact_ids,
                        assumption_tier=tier,
                    )
                    tokens[token_id] = localized
                    token = localized
                    sweep_changes += 1
                    events.append(
                        {
                            'inheritance_event_id': (
                                f'inheritance:{restoration_pass}:{len(events)+1:08d}'
                            ),
                            'event_kind': 'TOKEN_LOCALIZATION',
                            'restoration_pass': restoration_pass,
                            'optimization_round': optimization_round,
                            'inheritance_sweep': sweep,
                            'token_id': token_id,
                            'root_quantity_id': token.root_quantity_id,
                            'partition_id': str(partition.partition_id),
                            'partition_kind': str(partition.partition_kind),
                            'parent_quantity_id': parent_id,
                            'published_value': token.published_value,
                            'matched_child_quantity_id': child_id,
                            'supporting_fact_ids': supporting_fact_ids,
                            'support_region_count': len(token.support.region_codes),
                            'support_class_count': len(token.support.class_codes),
                            'support_cell_count': (
                                len(token.support.region_codes)
                                * len(token.support.class_codes)
                            ),
                            'assumption_tier': token.assumption_tier,
                            'status': token.status,
                        }
                    )
                    if token.support.is_empty:
                        # Independent rounded views can, in principle, produce
                        # contradictory visible-token localizations while the
                        # latent interval system remains feasible.  Such a token
                        # is blocked rather than turning this into a false global
                        # infeasibility claim.
                        break
                if token.status != 'ACTIVE':
                    break

            token = tokens[token_id]
            target_id = _singleton_target_id(token, metric_target_lookup)
            if target_id is None or target_id not in quantity_lookup.index:
                continue
            target_row = quantity_lookup.loc[target_id]
            if isinstance(target_row, pd.DataFrame):
                raise ValueError(f'Duplicate target quantity ID: {target_id}')
            changed = ledger.promote_inherited(
                target_row,
                published_value=token.published_value,
                root_fact_id=token.root_fact_id,
                supporting_partition_ids=token.supporting_partition_ids,
                supporting_fact_ids=token.supporting_fact_ids,
                assumption_tier=max(1, token.assumption_tier),
                restoration_pass=restoration_pass,
                optimization_round=optimization_round,
            )
            if changed:
                promoted.add(target_id)
                sweep_changes += 1
                events.append(
                    {
                        'inheritance_event_id': (
                            f'inheritance:{restoration_pass}:{len(events)+1:08d}'
                        ),
                        'event_kind': 'SINGLETON_PROMOTION',
                        'restoration_pass': restoration_pass,
                        'optimization_round': optimization_round,
                        'inheritance_sweep': sweep,
                        'token_id': token_id,
                        'root_quantity_id': token.root_quantity_id,
                        'published_value': token.published_value,
                        'target_quantity_id': target_id,
                        'supporting_partition_ids': token.supporting_partition_ids,
                        'supporting_fact_ids': token.supporting_fact_ids,
                        'assumption_tier': max(1, token.assumption_tier),
                        'status': 'PROMOTED',
                    }
                )
        if sweep_changes == 0:
            break
    else:  # pragma: no cover - finite monotone token/ledger state should converge
        raise RuntimeError('Published-mass token inheritance did not converge')

    return SorsInheritanceResult(
        frozenset(promoted),
        pd.DataFrame(events),
        _tokens_grid(tokens),
        sweeps,
    )
