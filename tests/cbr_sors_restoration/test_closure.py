import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.strict.interval_closure import run_interval_closure
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import SorsQuantityGraph


def _graph(parent, children):
    rows = []
    for quantity_id, lower, upper, lower_attained, upper_attained in [parent, *children]:
        rows.append({
            'quantity_id': quantity_id,
            'quantity_kind': 'TEST',
            'lower_bound': lower,
            'upper_bound': upper,
            'lower_attained': lower_attained,
            'upper_attained': upper_attained,
        })
    relations = pd.DataFrame([{
        'relation_id': 'r1',
        'relation_kind': 'SUM',
        'parent_quantity_id': parent[0],
        'child_quantity_ids': tuple(item[0] for item in children),
        'source_observation_ids': (),
    }])
    return SorsQuantityGraph(pd.DataFrame(rows), relations, pd.DataFrame())


def test_publication_zero_propagates_without_becoming_exact_zero() -> None:
    graph = _graph(
        ('parent', 0.0, 0.5, True, False),
        [('a', 0.0, float('inf'), True, False), ('b', 0.0, float('inf'), True, False)],
    )
    result = run_interval_closure(graph)
    children = result.quantities_grid.set_index('quantity_id').loc[['a', 'b']]
    assert (children['upper_bound'] == 0.5).all()
    assert not children['upper_attained'].any()


def test_single_unknown_is_exact_residual() -> None:
    graph = _graph(
        ('parent', 100.0, 100.0, True, True),
        [('a', 30.0, 30.0, True, True), ('b', 20.0, 20.0, True, True), ('c', 0.0, float('inf'), True, False)],
    )
    result = run_interval_closure(graph)
    c = result.quantities_grid.set_index('quantity_id').loc['c']
    assert c.lower_bound == 50.0
    assert c.upper_bound == 50.0
    assert c.lower_attained and c.upper_attained


def test_repeated_closure_preserves_existing_proof_metadata() -> None:
    graph = _graph(
        ('parent', 0.0, 0.5, True, False),
        [('a', 0.0, float('inf'), True, False)],
    )
    first = run_interval_closure(graph)
    repeated = run_interval_closure(
        SorsQuantityGraph(
            first.quantities_grid,
            graph.relations_grid,
            graph.observation_bindings_grid,
        )
    )
    row = repeated.quantities_grid.set_index('quantity_id').loc['a']
    assert row.last_derivation_id == 'derivation:00000001'
    assert row.last_derivation_pass == 1


def test_negative_residual_lower_bound_keeps_attained_nonnegativity_zero() -> None:
    graph = _graph(
        ('parent', 0.0, 10.0, True, False),
        [
            ('a', 0.0, float('inf'), True, False),
            ('b', 0.0, 5.0, True, False),
        ],
    )
    result = run_interval_closure(graph)
    a = result.quantities_grid.set_index('quantity_id').loc['a']

    assert a.lower_bound == 0.0
    assert a.lower_attained


def test_exact_zero_strict_residual_excludes_zero() -> None:
    graph = _graph(
        ('parent', 5.0, 10.0, True, False),
        [
            ('a', 0.0, float('inf'), True, False),
            ('b', 0.0, 5.0, True, False),
        ],
    )
    result = run_interval_closure(graph)
    a = result.quantities_grid.set_index('quantity_id').loc['a']

    assert a.lower_bound == 0.0
    assert not a.lower_attained


def test_negative_child_upper_residual_is_reported_as_conflict() -> None:
    from stratbox.macrobanks.cbr_sors_restoration.strict.interval_closure import (
        SorsIntervalClosureConflictError,
    )

    graph = _graph(
        ('parent', 0.0, 3.0, True, True),
        [
            ('a', 0.0, float('inf'), True, False),
            ('b', 4.0, 4.0, True, True),
        ],
    )

    try:
        run_interval_closure(graph)
    except SorsIntervalClosureConflictError as exc:
        assert not exc.conflicts_grid.empty
        assert 'a' in set(exc.conflicts_grid['quantity_id'])
    else:
        raise AssertionError('Negative residual upper bound must be infeasible')
