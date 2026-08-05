import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.strict.closure import run_deterministic_closure
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
    result = run_deterministic_closure(graph)
    children = result.quantities_grid.set_index('quantity_id').loc[['a', 'b']]
    assert (children['upper_bound'] == 0.5).all()
    assert not children['upper_attained'].any()


def test_single_unknown_is_exact_residual() -> None:
    graph = _graph(
        ('parent', 100.0, 100.0, True, True),
        [('a', 30.0, 30.0, True, True), ('b', 20.0, 20.0, True, True), ('c', 0.0, float('inf'), True, False)],
    )
    result = run_deterministic_closure(graph)
    c = result.quantities_grid.set_index('quantity_id').loc['c']
    assert c.lower_bound == 50.0
    assert c.upper_bound == 50.0
    assert c.lower_attained and c.upper_attained


def test_repeated_closure_preserves_existing_proof_metadata() -> None:
    graph = _graph(
        ('parent', 0.0, 0.5, True, False),
        [('a', 0.0, float('inf'), True, False)],
    )
    first = run_deterministic_closure(graph)
    repeated = run_deterministic_closure(
        SorsQuantityGraph(
            first.quantities_grid,
            graph.relations_grid,
            graph.observation_bindings_grid,
        )
    )
    row = repeated.quantities_grid.set_index('quantity_id').loc['a']
    assert row.last_derivation_id == 'derivation:00000001'
    assert row.last_derivation_pass == 1
