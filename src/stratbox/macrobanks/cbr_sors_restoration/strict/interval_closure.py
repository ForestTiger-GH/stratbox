from __future__ import annotations

from dataclasses import dataclass
from math import inf, isfinite

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
    SorsQuantityGraph,
)


class SorsIntervalClosureConflictError(ValueError):
    def __init__(self, conflicts_grid: pd.DataFrame):
        super().__init__('Deterministic SORS interval closure found a conflict')
        self.conflicts_grid = conflicts_grid


@dataclass(frozen=True)
class SorsIntervalClosureResult:
    quantities_grid: pd.DataFrame
    derivations_grid: pd.DataFrame
    conflicts_grid: pd.DataFrame
    passes: int
    bound_updates: int


def run_interval_closure(
    graph: SorsQuantityGraph,
    *,
    tolerance: float = 1e-9,
    max_passes: int = 100,
    seed_quantity_ids: tuple[str, ...] | None = None,
) -> SorsIntervalClosureResult:
    quantities = graph.quantities_grid.copy().reset_index(drop=True)
    quantity_ids = tuple(quantities['quantity_id'].astype(str))
    positions = {quantity_id: i for i, quantity_id in enumerate(quantity_ids)}
    lower = quantities['lower_bound'].astype(float).to_numpy(copy=True)
    upper = quantities['upper_bound'].astype(float).to_numpy(copy=True)
    lower_attained = quantities['lower_attained'].astype(bool).to_numpy(copy=True)
    upper_attained = quantities['upper_attained'].astype(bool).to_numpy(copy=True)
    lower_tier = (
        quantities['lower_assumption_tier'].fillna(0).astype(int).to_numpy(copy=True)
        if 'lower_assumption_tier' in quantities
        else np.zeros(len(quantities), dtype=np.int16)
    )
    upper_tier = (
        quantities['upper_assumption_tier'].fillna(0).astype(int).to_numpy(copy=True)
        if 'upper_assumption_tier' in quantities
        else np.zeros(len(quantities), dtype=np.int16)
    )

    relations: list[dict[str, object]] = []
    adjacent: list[list[int]] = [[] for _ in quantity_ids]
    for relation_position, row in enumerate(graph.relations_grid.itertuples(index=False)):
        parent = positions[str(row.parent_quantity_id)]
        children = tuple(
            positions[str(quantity_id)] for quantity_id in row.child_quantity_ids
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

    def apply_lower(index: int, candidate: float, attained: bool, tier: int) -> bool:
        current = float(lower[index])
        current_attained = bool(lower_attained[index])
        current_tier = int(lower_tier[index])
        candidate_tier = int(tier)
        if candidate > current + tolerance:
            lower[index] = candidate
            lower_attained[index] = attained
            lower_tier[index] = candidate_tier
            return True
        if abs(candidate - current) <= tolerance:
            # Equal constraints intersect.  An open endpoint dominates a closed
            # endpoint; otherwise the strongest independent proof may own the
            # same numerical bound.
            if current_attained and not attained:
                lower_attained[index] = False
                lower_tier[index] = candidate_tier
                return True
            if current_attained == attained and candidate_tier < current_tier:
                lower_tier[index] = candidate_tier
                return True
        return False

    def apply_upper(index: int, candidate: float, attained: bool, tier: int) -> bool:
        current = float(upper[index])
        current_attained = bool(upper_attained[index])
        current_tier = int(upper_tier[index])
        candidate_tier = int(tier)
        if candidate < current - tolerance:
            upper[index] = candidate
            upper_attained[index] = attained
            upper_tier[index] = candidate_tier
            return True
        if abs(candidate - current) <= tolerance:
            if current_attained and not attained:
                upper_attained[index] = False
                upper_tier[index] = candidate_tier
                return True
            if current_attained == attained and candidate_tier < current_tier:
                upper_tier[index] = candidate_tier
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
                'new_lower_assumption_tier': int(lower_tier[result_index]),
                'new_upper_assumption_tier': int(upper_tier[result_index]),
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

    if seed_quantity_ids is None:
        current_relations = set(range(len(relations)))
    else:
        unknown_seeds = sorted(set(seed_quantity_ids) - set(positions))
        if unknown_seeds:
            raise ValueError(f'Unknown closure seed quantities: {unknown_seeds}')
        current_relations: set[int] = set()
        for quantity_id in seed_quantity_ids:
            current_relations.update(adjacent[positions[str(quantity_id)]])
    passes = 0
    for pass_number in range(1, max_passes + 1):
        passes = pass_number
        next_relations: set[int] = set()
        changed_quantities: set[int] = set()
        for relation_position in sorted(current_relations):
            relation = relations[relation_position]
            parent = int(relation['parent'])
            children = relation['children']
            assert isinstance(children, tuple)

            # Scalar accumulation is intentionally used here.  The relation graph
            # contains tens of thousands of tiny (1/2/4-child) equations; creating
            # NumPy slices and temporary arrays for every relation dominated real
            # SORS runtime.  One O(edges) scalar scan is markedly faster and also
            # gives us all flag/tier aggregates needed by residual propagation.
            sum_lower = 0.0
            sum_finite_upper = 0.0
            upper_inf_count = 0
            lower_unattained_count = 0
            upper_unattained_finite_count = 0
            max_lower_tier = 0
            second_lower_tier = 0
            max_lower_count = 0
            max_upper_tier = 0
            second_upper_tier = 0
            max_upper_count = 0
            parent_lower_attained = True
            parent_upper_attained = True
            for child in children:
                lo = float(lower[child])
                hi = float(upper[child])
                lo_attained = bool(lower_attained[child])
                hi_attained = bool(upper_attained[child])
                lo_tier = int(lower_tier[child])
                hi_tier = int(upper_tier[child])
                sum_lower += lo
                if not lo_attained:
                    lower_unattained_count += 1
                    parent_lower_attained = False
                if isfinite(hi):
                    sum_finite_upper += hi
                    if not hi_attained:
                        upper_unattained_finite_count += 1
                        parent_upper_attained = False
                else:
                    upper_inf_count += 1
                    parent_upper_attained = False
                if lo_tier > max_lower_tier:
                    second_lower_tier = max_lower_tier
                    max_lower_tier = lo_tier
                    max_lower_count = 1
                elif lo_tier == max_lower_tier:
                    max_lower_count += 1
                elif lo_tier > second_lower_tier:
                    second_lower_tier = lo_tier
                if hi_tier > max_upper_tier:
                    second_upper_tier = max_upper_tier
                    max_upper_tier = hi_tier
                    max_upper_count = 1
                elif hi_tier == max_upper_tier:
                    max_upper_count += 1
                elif hi_tier > second_upper_tier:
                    second_upper_tier = hi_tier
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
                parent_lower_attained,
                max_lower_tier,
            )
            parent_changed = apply_upper(
                parent,
                sum_upper,
                bool(upper_inf_count == 0 and parent_upper_attained),
                max_upper_tier,
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

            # Use the snapshot aggregates above for every sibling in this
            # relation.  Any child tightened below schedules the relation again in
            # the next closure wave, matching the previous fixed-point semantics.
            for child in children:
                previous = (
                    float(lower[child]),
                    float(upper[child]),
                    bool(lower_attained[child]),
                    bool(upper_attained[child]),
                )
                child_changed = False
                if isfinite(upper[parent]):
                    raw_candidate_upper = float(upper[parent]) - (
                        sum_lower - float(lower[child])
                    )
                    candidate_upper = (
                        0.0
                        if abs(raw_candidate_upper) <= tolerance
                        else raw_candidate_upper
                    )
                    other_lower_unattained = lower_unattained_count - int(
                        not bool(lower_attained[child])
                    )
                    child_lower_tier = int(lower_tier[child])
                    other_lower_max = (
                        second_lower_tier
                        if child_lower_tier == max_lower_tier and max_lower_count == 1
                        else max_lower_tier
                    )
                    candidate_upper_tier = max(
                        int(upper_tier[parent]),
                        other_lower_max,
                    )
                    child_changed = apply_upper(
                        child,
                        candidate_upper,
                        bool(upper_attained[parent] and other_lower_unattained == 0),
                        candidate_upper_tier,
                    )
                child_upper_value = float(upper[child])
                child_upper_finite = isfinite(child_upper_value)
                other_inf_count = upper_inf_count - int(not child_upper_finite)
                if other_inf_count == 0:
                    other_upper = sum_finite_upper - (
                        child_upper_value
                        if child_upper_finite
                        else 0.0
                    )
                    raw_candidate_lower = float(lower[parent]) - other_upper
                    candidate_lower = max(0.0, raw_candidate_lower)
                    other_upper_unattained = upper_unattained_finite_count - int(
                        child_upper_finite
                        and not bool(upper_attained[child])
                    )
                    residual_lower_attained = bool(
                        lower_attained[parent] and other_upper_unattained == 0
                    )
                    # If the algebraic residual lies strictly below zero, the
                    # active lower bound is the independent non-negativity
                    # constraint, whose endpoint zero is attained.  Only an
                    # exactly-zero strict residual can exclude x = 0.
                    candidate_lower_attained = (
                        True
                        if raw_candidate_lower < -tolerance
                        else residual_lower_attained
                    )
                    if raw_candidate_lower < -tolerance:
                        candidate_lower_tier = 0
                    else:
                        child_upper_tier = int(upper_tier[child])
                        other_upper_max = (
                            second_upper_tier
                            if child_upper_tier == max_upper_tier and max_upper_count == 1
                            else max_upper_tier
                        )
                        candidate_lower_tier = max(
                            int(lower_tier[parent]),
                            other_upper_max,
                        )
                    child_changed = apply_lower(
                        child,
                        candidate_lower,
                        candidate_lower_attained,
                        candidate_lower_tier,
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
            raise SorsIntervalClosureConflictError(conflict_grid)
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
    quantities['lower_assumption_tier'] = lower_tier.astype(int)
    quantities['upper_assumption_tier'] = upper_tier.astype(int)
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
    return SorsIntervalClosureResult(
        quantities_grid=quantities,
        derivations_grid=pd.DataFrame(derivations),
        conflicts_grid=pd.DataFrame(conflicts),
        passes=passes,
        bound_updates=update_count,
    )


class SorsIntervalClosureState:
    """Persistent closure state for the RKVS fixed-point engine."""

    def __init__(
        self,
        graph: SorsQuantityGraph,
        *,
        tolerance: float = 1e-9,
        max_passes: int = 100,
    ) -> None:
        self._relations_grid = graph.relations_grid.copy()
        self._bindings_grid = graph.observation_bindings_grid.copy()
        self.quantities_grid = graph.quantities_grid.copy()
        self.derivations_grid = pd.DataFrame()
        self.conflicts_grid = pd.DataFrame()
        self.tolerance = float(tolerance)
        self.max_passes = int(max_passes)
        self.total_passes = 0
        self.total_bound_updates = 0

    def replace_quantities(self, quantities_grid: pd.DataFrame) -> None:
        expected = tuple(self.quantities_grid['quantity_id'].astype(str))
        received = tuple(quantities_grid['quantity_id'].astype(str))
        if expected != received:
            raise ValueError('Closure state quantity ordering cannot change')
        self.quantities_grid = quantities_grid.copy()

    def add_relations(self, relations_grid: pd.DataFrame) -> int:
        """Add exact deterministic relations while preserving quantity identity.

        Publication hierarchy equations are compiled only after source supports
        have been validated as complete/disjoint.  Repeated publication fixed-point
        waves may call this method again; relation IDs therefore make the operation
        idempotent.
        """

        if relations_grid is None or relations_grid.empty:
            return 0
        required = {
            'relation_id', 'relation_kind', 'parent_quantity_id',
            'child_quantity_ids', 'source_observation_ids',
        }
        missing = sorted(required - set(relations_grid.columns))
        if missing:
            raise ValueError(f'Closure relation grid is missing columns: {missing}')
        known_quantities = set(self.quantities_grid['quantity_id'].astype(str))
        existing_ids = set(self._relations_grid['relation_id'].astype(str))
        new_rows: list[dict[str, object]] = []
        for row in relations_grid.itertuples(index=False):
            relation_id = str(row.relation_id)
            if relation_id in existing_ids:
                continue
            parent = str(row.parent_quantity_id)
            children = tuple(str(value) for value in row.child_quantity_ids)
            unknown = ({parent, *children} - known_quantities)
            if unknown:
                raise ValueError(
                    f'Closure relation {relation_id} references unknown quantities: '
                    f'{tuple(sorted(unknown))[:10]}'
                )
            new_rows.append(
                {
                    'relation_id': relation_id,
                    'relation_kind': str(row.relation_kind),
                    'parent_quantity_id': parent,
                    'child_quantity_ids': children,
                    'source_observation_ids': tuple(
                        str(value)
                        for value in (getattr(row, 'source_observation_ids', ()) or ())
                    ),
                }
            )
            existing_ids.add(relation_id)
        if not new_rows:
            return 0
        self._relations_grid = pd.concat(
            [self._relations_grid, pd.DataFrame(new_rows)],
            ignore_index=True,
            sort=False,
        )
        return len(new_rows)

    def _offset_derivations(
        self,
        derivations: pd.DataFrame,
        quantities: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        if derivations.empty:
            return derivations, quantities
        derivations = derivations.copy()
        id_offset = len(self.derivations_grid)
        pass_offset = self.total_passes
        old_ids = tuple(derivations['derivation_id'].astype(str))
        new_ids = tuple(
            f'derivation:{id_offset + position:08d}'
            for position in range(1, len(derivations) + 1)
        )
        remap = dict(zip(old_ids, new_ids, strict=True))
        derivations['derivation_id'] = derivations['derivation_id'].astype(str).map(remap)
        derivations['pass_number'] = derivations['pass_number'].astype(int) + pass_offset
        quantities = quantities.copy()
        changed_quantity_ids = set(derivations['result_quantity_id'].astype(str))
        changed = quantities['quantity_id'].astype(str).isin(changed_quantity_ids)
        quantities.loc[changed, 'last_derivation_id'] = quantities.loc[
            changed, 'last_derivation_id'
        ].map(
            lambda value: remap.get(str(value), value)
            if value is not None and not pd.isna(value)
            else value
        )
        if 'last_derivation_pass' in quantities:
            quantities.loc[changed, 'last_derivation_pass'] = quantities.loc[
                changed, 'last_derivation_pass'
            ].map(
                lambda value: int(value) + pass_offset
                if value is not None and not pd.isna(value)
                else value
            )
        return derivations, quantities

    def run(
        self,
        *,
        seed_quantity_ids: tuple[str, ...] | None = None,
    ) -> SorsIntervalClosureResult:
        graph = SorsQuantityGraph(
            self.quantities_grid,
            self._relations_grid,
            self._bindings_grid,
        )
        result = run_interval_closure(
            graph,
            tolerance=self.tolerance,
            max_passes=self.max_passes,
            seed_quantity_ids=seed_quantity_ids,
        )
        derivations, quantities = self._offset_derivations(
            result.derivations_grid, result.quantities_grid
        )
        self.quantities_grid = quantities
        if not derivations.empty:
            self.derivations_grid = pd.concat(
                [self.derivations_grid, derivations],
                ignore_index=True,
                sort=False,
            )
        self.conflicts_grid = result.conflicts_grid
        self.total_passes += result.passes
        self.total_bound_updates += result.bound_updates
        return SorsIntervalClosureResult(
            quantities_grid=self.quantities_grid.copy(),
            derivations_grid=derivations,
            conflicts_grid=result.conflicts_grid,
            passes=result.passes,
            bound_updates=result.bound_updates,
        )
