from __future__ import annotations

from dataclasses import dataclass
from math import inf, isfinite

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
    SorsQuantityGraph,
)


class SorsClosureConflictError(ValueError):
    def __init__(self, conflicts_grid: pd.DataFrame):
        super().__init__('Deterministic SORS interval closure found a conflict')
        self.conflicts_grid = conflicts_grid


@dataclass(frozen=True)
class SorsClosureResult:
    quantities_grid: pd.DataFrame
    derivations_grid: pd.DataFrame
    conflicts_grid: pd.DataFrame
    passes: int
    bound_updates: int


def run_deterministic_closure(
    graph: SorsQuantityGraph,
    *,
    tolerance: float = 1e-9,
    max_passes: int = 100,
) -> SorsClosureResult:
    quantities = graph.quantities_grid.copy().reset_index(drop=True)
    quantity_ids = tuple(quantities['quantity_id'].astype(str))
    positions = {quantity_id: i for i, quantity_id in enumerate(quantity_ids)}
    lower = quantities['lower_bound'].astype(float).to_numpy(copy=True)
    upper = quantities['upper_bound'].astype(float).to_numpy(copy=True)
    lower_attained = quantities['lower_attained'].astype(bool).to_numpy(copy=True)
    upper_attained = quantities['upper_attained'].astype(bool).to_numpy(copy=True)

    relations: list[dict[str, object]] = []
    adjacent: list[list[int]] = [[] for _ in quantity_ids]
    for relation_position, row in enumerate(graph.relations_grid.itertuples(index=False)):
        parent = positions[str(row.parent_quantity_id)]
        children = np.asarray(
            [positions[str(quantity_id)] for quantity_id in row.child_quantity_ids],
            dtype=np.int32,
        )
        relations.append(
            {
                'relation_id': str(row.relation_id),
                'relation_kind': str(row.relation_kind),
                'parent': parent,
                'children': children,
                'source_observation_ids': tuple(row.source_observation_ids),
            }
        )
        adjacent[parent].append(relation_position)
        for child in children:
            adjacent[int(child)].append(relation_position)

    derivations: list[dict[str, object]] = []
    conflicts: list[dict[str, object]] = []
    update_count = 0

    def apply_lower(index: int, candidate: float, attained: bool) -> bool:
        current = float(lower[index])
        if candidate > current + tolerance:
            lower[index] = candidate
            lower_attained[index] = attained
            return True
        if abs(candidate - current) <= tolerance and lower_attained[index] and not attained:
            lower_attained[index] = False
            return True
        return False

    def apply_upper(index: int, candidate: float, attained: bool) -> bool:
        current = float(upper[index])
        if candidate < current - tolerance:
            upper[index] = candidate
            upper_attained[index] = attained
            return True
        if abs(candidate - current) <= tolerance and upper_attained[index] and not attained:
            upper_attained[index] = False
            return True
        return False

    def record(
        *,
        pass_number: int,
        rule_id: str,
        relation: dict[str, object],
        result_index: int,
        previous: tuple[float, float, bool, bool],
        support_ids: tuple[str, ...],
        support_count: int,
    ) -> None:
        nonlocal update_count
        update_count += 1
        derivations.append(
            {
                'derivation_id': f'derivation:{update_count:08d}',
                'pass_number': pass_number,
                'rule_id': rule_id,
                'relation_id': relation['relation_id'],
                'relation_kind': relation['relation_kind'],
                'result_quantity_id': quantity_ids[result_index],
                'supporting_quantity_ids': support_ids,
                'supporting_quantity_count': int(support_count),
                'supporting_observation_ids': relation['source_observation_ids'],
                'previous_lower': previous[0],
                'previous_upper': previous[1],
                'new_lower': float(lower[result_index]),
                'new_upper': float(upper[result_index]),
                'previous_lower_attained': previous[2],
                'previous_upper_attained': previous[3],
                'new_lower_attained': bool(lower_attained[result_index]),
                'new_upper_attained': bool(upper_attained[result_index]),
            }
        )

    def check_interval(index: int, relation_id: str) -> None:
        empty = lower[index] > upper[index] + tolerance
        empty_point = (
            abs(lower[index] - upper[index]) <= tolerance
            and not (lower_attained[index] and upper_attained[index])
        )
        if empty or empty_point:
            conflicts.append(
                {
                    'conflict_id': f'closure:{relation_id}:{quantity_ids[index]}',
                    'relation_id': relation_id,
                    'quantity_id': quantity_ids[index],
                    'lower_bound': float(lower[index]),
                    'upper_bound': float(upper[index]),
                    'message': 'Quantity interval became empty during closure',
                }
            )

    current_relations = set(range(len(relations)))
    passes = 0
    for pass_number in range(1, max_passes + 1):
        passes = pass_number
        next_relations: set[int] = set()
        changed_quantities: set[int] = set()
        for relation_position in sorted(current_relations):
            relation = relations[relation_position]
            parent = int(relation['parent'])
            children = relation['children']
            assert isinstance(children, np.ndarray)

            child_lower = lower[children]
            child_upper = upper[children]
            child_lower_flags = lower_attained[children]
            child_upper_flags = upper_attained[children]
            sum_lower = float(child_lower.sum())
            finite_upper = np.isfinite(child_upper)
            upper_inf_count = int((~finite_upper).sum())
            sum_finite_upper = float(child_upper[finite_upper].sum())
            sum_upper = inf if upper_inf_count else sum_finite_upper

            previous = (
                float(lower[parent]),
                float(upper[parent]),
                bool(lower_attained[parent]),
                bool(upper_attained[parent]),
            )
            parent_changed = apply_lower(
                parent,
                sum_lower,
                bool(child_lower_flags.all()),
            )
            parent_changed = apply_upper(
                parent,
                sum_upper,
                bool(upper_inf_count == 0 and child_upper_flags.all()),
            ) or parent_changed
            if parent_changed:
                changed_quantities.add(parent)
                support_ids = (
                    tuple(quantity_ids[int(i)] for i in children)
                    if len(children) <= 8
                    else ()
                )
                record(
                    pass_number=pass_number,
                    rule_id='CHILD_SUM_TO_PARENT',
                    relation=relation,
                    result_index=parent,
                    previous=previous,
                    support_ids=support_ids,
                    support_count=len(children),
                )
                check_interval(parent, str(relation['relation_id']))

            child_lower = lower[children]
            child_upper = upper[children]
            child_lower_flags = lower_attained[children]
            child_upper_flags = upper_attained[children]
            sum_lower = float(child_lower.sum())
            lower_unattained_count = int((~child_lower_flags).sum())
            finite_upper = np.isfinite(child_upper)
            upper_inf_count = int((~finite_upper).sum())
            sum_finite_upper = float(child_upper[finite_upper].sum())
            upper_unattained_finite_count = int(
                ((~child_upper_flags) & finite_upper).sum()
            )

            for local_position, child_raw in enumerate(children):
                child = int(child_raw)
                previous = (
                    float(lower[child]),
                    float(upper[child]),
                    bool(lower_attained[child]),
                    bool(upper_attained[child]),
                )
                child_changed = False
                if isfinite(upper[parent]):
                    candidate_upper = max(
                        0.0,
                        float(upper[parent]) - (sum_lower - float(lower[child])),
                    )
                    other_lower_unattained = lower_unattained_count - int(
                        not bool(lower_attained[child])
                    )
                    child_changed = apply_upper(
                        child,
                        candidate_upper,
                        bool(upper_attained[parent] and other_lower_unattained == 0),
                    )
                other_inf_count = upper_inf_count - int(not finite_upper[local_position])
                if other_inf_count == 0:
                    other_upper = sum_finite_upper - (
                        float(child_upper[local_position])
                        if finite_upper[local_position]
                        else 0.0
                    )
                    candidate_lower = max(0.0, float(lower[parent]) - other_upper)
                    other_upper_unattained = upper_unattained_finite_count - int(
                        finite_upper[local_position]
                        and not bool(child_upper_flags[local_position])
                    )
                    child_changed = apply_lower(
                        child,
                        candidate_lower,
                        bool(lower_attained[parent] and other_upper_unattained == 0),
                    ) or child_changed
                if child_changed:
                    changed_quantities.add(child)
                    record(
                        pass_number=pass_number,
                        rule_id='PARENT_RESIDUAL_TO_CHILD',
                        relation=relation,
                        result_index=child,
                        previous=previous,
                        support_ids=(quantity_ids[parent],),
                        support_count=len(children),
                    )
                    check_interval(child, str(relation['relation_id']))

        if conflicts:
            conflict_grid = pd.DataFrame(conflicts).drop_duplicates('conflict_id')
            raise SorsClosureConflictError(conflict_grid)
        if not changed_quantities:
            break
        for quantity_index in changed_quantities:
            next_relations.update(adjacent[quantity_index])
        current_relations = next_relations
    else:
        raise RuntimeError(
            f'Deterministic closure did not converge in {max_passes} passes'
        )

    quantities['lower_bound'] = lower
    quantities['upper_bound'] = upper
    quantities['lower_attained'] = lower_attained
    quantities['upper_attained'] = upper_attained
    existing_id = (
        quantities['last_derivation_id'].copy()
        if 'last_derivation_id' in quantities
        else pd.Series(None, index=quantities.index, dtype=object)
    )
    existing_pass = (
        quantities['last_derivation_pass'].copy()
        if 'last_derivation_pass' in quantities
        else pd.Series(None, index=quantities.index, dtype=object)
    )
    existing_support = (
        quantities['last_derivation_support_count'].copy()
        if 'last_derivation_support_count' in quantities
        else pd.Series(0, index=quantities.index, dtype=object)
    )
    if derivations:
        last = (
            pd.DataFrame(derivations)
            .drop_duplicates('result_quantity_id', keep='last')
            .set_index('result_quantity_id')
        )
        new_id = quantities['quantity_id'].map(last['derivation_id'])
        new_pass = quantities['quantity_id'].map(last['pass_number'])
        new_support = quantities['quantity_id'].map(
            last['supporting_quantity_count']
        )
        quantities['last_derivation_id'] = new_id.where(
            new_id.notna(), existing_id
        )
        quantities['last_derivation_pass'] = new_pass.where(
            new_pass.notna(), existing_pass
        )
        quantities['last_derivation_support_count'] = new_support.where(
            new_support.notna(), existing_support
        )
    else:
        quantities['last_derivation_id'] = existing_id
        quantities['last_derivation_pass'] = existing_pass
        quantities['last_derivation_support_count'] = existing_support
    return SorsClosureResult(
        quantities_grid=quantities,
        derivations_grid=pd.DataFrame(derivations),
        conflicts_grid=pd.DataFrame(conflicts),
        passes=passes,
        bound_updates=update_count,
    )
