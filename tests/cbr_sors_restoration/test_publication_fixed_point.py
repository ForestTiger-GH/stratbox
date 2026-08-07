from __future__ import annotations

import pandas as pd
import pytest

from stratbox.macrobanks.cbr_sors_restoration.publication import (
    RoundingPolicy,
    SorsPublicationLedger,
    SorsPublicationFixedPointLimitError,
    build_publication_graph,
    run_publication_fixed_point,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.interval_closure import SorsIntervalClosureState
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import SorsQuantityGraph


def _row(
    quantity_id,
    kind,
    lower,
    upper,
    *,
    regions,
    classes,
    region_code=None,
    class_code=None,
    representative=None,
    status=None,
):
    return {
        'quantity_id': quantity_id,
        'quantity_kind': kind,
        'portfolio_scope': 'CORPORATE_TOTAL',
        'region_code': region_code,
        'class_code': class_code,
        'component': None,
        'metric': 'debt_rub',
        'support_region_codes': tuple(regions),
        'support_class_codes': tuple(classes),
        'lower_bound': float(lower),
        'upper_bound': float(upper),
        'lower_attained': True,
        'upper_attained': False,
        'initial_lower_bound': float(lower),
        'initial_upper_bound': float(upper),
        'initial_lower_attained': True,
        'initial_upper_attained': False,
        'lower_assumption_tier': 0,
        'upper_assumption_tier': 0,
        'published_representative': representative,
        'published_representative_status': status,
        'source_observation_ids': () if representative is None else (f'obs:{quantity_id}',),
    }


def _relation(relation_id, kind, parent, children):
    return {
        'relation_id': relation_id,
        'relation_kind': kind,
        'parent_quantity_id': parent,
        'child_quantity_ids': tuple(children),
        'source_observation_ids': (),
    }


def _udmurtia_like_graph(*, with_cascade: bool = False) -> SorsQuantityGraph:
    # The root source publication 6 is explicitly localized in two independent
    # complete partitions:
    #   geography: U=6, O=0
    #   industry:  47=6, X=0
    # Their supports intersect only at U×47, so that cell inherits the *source* 6.
    regions = ('U', 'O')
    classes = ('47', 'X')
    rows = [
        _row('publication:national_total:debt_rub', 'PUBLISHED_AGGREGATE', 5.5, 6.5, regions=regions, classes=classes, representative=6, status='STABLE'),
        _row('publication:geography:U:debt_rub', 'PUBLISHED_AGGREGATE', 5.5, 6.5, regions=('U',), classes=classes, representative=6, status='STABLE'),
        _row('publication:geography:O:debt_rub', 'PUBLISHED_AGGREGATE', 0.0, 0.5, regions=('O',), classes=classes, representative=0, status='STABLE'),
        _row('publication:national_class:47:debt_rub', 'PUBLISHED_AGGREGATE', 5.5, 6.5, regions=regions, classes=('47',), representative=6, status='STABLE'),
        _row('publication:national_class:X:debt_rub', 'PUBLISHED_AGGREGATE', 0.0, 0.5, regions=regions, classes=('X',), representative=0, status='STABLE'),
        _row('metric:U:47:debt_rub', 'REGIONAL_CLASS_METRIC', 5.1, 100, regions=('U',), classes=('47',), region_code='U', class_code='47'),
        _row('metric:U:X:debt_rub', 'REGIONAL_CLASS_METRIC', 0, 100, regions=('U',), classes=('X',), region_code='U', class_code='X'),
        _row('metric:O:47:debt_rub', 'REGIONAL_CLASS_METRIC', 0, 100, regions=('O',), classes=('47',), region_code='O', class_code='47'),
        _row('metric:O:X:debt_rub', 'REGIONAL_CLASS_METRIC', 0, 100, regions=('O',), classes=('X',), region_code='O', class_code='X'),
    ]
    relations = [
        _relation('r:root', 'NATIONAL_TOTAL', 'publication:national_total:debt_rub', (
            'metric:U:47:debt_rub', 'metric:U:X:debt_rub',
            'metric:O:47:debt_rub', 'metric:O:X:debt_rub',
        )),
        _relation('r:geoU', 'GEOGRAPHY_TOTAL', 'publication:geography:U:debt_rub', (
            'metric:U:47:debt_rub', 'metric:U:X:debt_rub',
        )),
        _relation('r:geoO', 'GEOGRAPHY_TOTAL', 'publication:geography:O:debt_rub', (
            'metric:O:47:debt_rub', 'metric:O:X:debt_rub',
        )),
        _relation('r:class47', 'NATIONAL_CLASS', 'publication:national_class:47:debt_rub', (
            'metric:U:47:debt_rub', 'metric:O:47:debt_rub',
        )),
        _relation('r:classX', 'NATIONAL_CLASS', 'publication:national_class:X:debt_rub', (
            'metric:U:X:debt_rub', 'metric:O:X:debt_rub',
        )),
    ]

    if with_cascade:
        # A second source token 8 is already localized to R1 by an official
        # geography partition.  Its class-like target partition cannot localize
        # until K2 becomes publication-zero.  The inherited U×47 bucket raises
        # A.lower to 5.5; Q=A+K2 with Q.upper=5.8 then forces K2<0.3.  K1=8 was
        # independently bucket-identified from its latent bounds.  On the next
        # deterministic pass P2 can therefore localize to class C1 and the token's
        # region/class supports intersect at the new target R1×C1.
        rows.extend([
            _row('publication:national_total2:debt_rub', 'PUBLISHED_AGGREGATE', 7.5, 8.5, regions=('R1','R2'), classes=('C1','C2'), representative=8, status='STABLE'),
            _row('publication:geography:R1:debt_rub', 'PUBLISHED_AGGREGATE', 7.5, 8.5, regions=('R1',), classes=('C1','C2'), representative=8, status='STABLE'),
            _row('publication:geography:R2:debt_rub', 'PUBLISHED_AGGREGATE', 0.0, 0.5, regions=('R2',), classes=('C1','C2'), representative=0, status='STABLE'),
            _row('K1', 'REGIONAL_CLASS_METRIC', 7.6, 8.4, regions=('R1','R2'), classes=('C1',)),
            _row('K2', 'REGIONAL_CLASS_METRIC', 0.0, 100, regions=('R1','R2'), classes=('C2',)),
            _row('Q', 'REGIONAL_CLASS_METRIC', 0.0, 5.8, regions=('U',), classes=('47',)),
            _row('metric:R1:C1:debt_rub', 'REGIONAL_CLASS_METRIC', 0.0, 100, regions=('R1',), classes=('C1',), region_code='R1', class_code='C1'),
            _row('metric:R1:C2:debt_rub', 'REGIONAL_CLASS_METRIC', 0.0, 100, regions=('R1',), classes=('C2',), region_code='R1', class_code='C2'),
            _row('metric:R2:C1:debt_rub', 'REGIONAL_CLASS_METRIC', 0.0, 100, regions=('R2',), classes=('C1',), region_code='R2', class_code='C1'),
            _row('metric:R2:C2:debt_rub', 'REGIONAL_CLASS_METRIC', 0.0, 100, regions=('R2',), classes=('C2',), region_code='R2', class_code='C2'),
        ])
        relations.extend([
            _relation('r:P2', 'NATIONAL_TOTAL', 'publication:national_total2:debt_rub', ('K1','K2')),
            _relation('r:Q', 'TEST_BALANCE', 'Q', ('metric:U:47:debt_rub','K2')),
        ])

    return SorsQuantityGraph(
        pd.DataFrame(rows).sort_values('quantity_id').reset_index(drop=True),
        pd.DataFrame(relations).sort_values('relation_id').reset_index(drop=True),
        pd.DataFrame(),
    )


def test_parent_plus_zero_siblings_does_not_invent_unknown_child_value() -> None:
    graph = SorsQuantityGraph(
        pd.DataFrame([
            _row('P', 'PUBLISHED_AGGREGATE', 5.5, 6.5, regions=('R',), classes=('A','B'), representative=6, status='STABLE'),
            _row('X', 'REGIONAL_CLASS_METRIC', 0, 100, regions=('R',), classes=('A',), region_code='R', class_code='A'),
            _row('Z', 'REGIONAL_CLASS_METRIC', 0, 0.4, regions=('R',), classes=('B',), region_code='R', class_code='B'),
        ]),
        pd.DataFrame([_relation('r:P', 'TEST_PARTITION', 'P', ('X','Z'))]),
        pd.DataFrame(),
    )
    state = SorsIntervalClosureState(graph, tolerance=1e-9, max_passes=50)
    ledger = SorsPublicationLedger()
    run_publication_fixed_point(
        state,
        build_publication_graph(graph),
        ledger,
        policy=RoundingPolicy(step=1.0),
        point_tolerance=1e-6,
        max_passes=20,
    )
    assert ledger.current_record('Z')['published_value'] == 0
    assert ledger.current_record('X') is None


def test_equal_source_value_localized_by_independent_partitions_inherits_cell() -> None:
    graph = _udmurtia_like_graph()
    state = SorsIntervalClosureState(graph, tolerance=1e-9, max_passes=50)
    ledger = SorsPublicationLedger()
    execution = run_publication_fixed_point(
        state,
        build_publication_graph(graph),
        ledger,
        policy=RoundingPolicy(step=1.0),
        point_tolerance=1e-6,
        max_passes=20,
    )

    fact = ledger.current_record('metric:U:47:debt_rub')
    assert fact is not None
    assert fact['published_value'] == 6
    assert fact['evidence_method'] == 'PUBLISHED_VALUE_INHERITED'
    assert int(fact['assumption_tier']) == 1
    assert fact['latent_constraint_mode'] == 'PUBLICATION_BUCKET'
    assert fact['latent_status'] == 'BOUNDED'

    q = execution.quantities_grid.set_index('quantity_id')
    assert float(q.loc['metric:U:47:debt_rub', 'lower_bound']) >= 5.5
    token = execution.tokens_grid[
        execution.tokens_grid['root_quantity_id'].eq('publication:national_total:debt_rub')
    ].iloc[0]
    assert token.support_cell_count == 1
    assert set(token.support_region_codes) == {'U'}
    assert set(token.support_class_codes) == {'47'}


def test_inherited_bucket_can_create_zero_that_unlocks_later_token_localization() -> None:
    graph = _udmurtia_like_graph(with_cascade=True)
    state = SorsIntervalClosureState(graph, tolerance=1e-9, max_passes=50)
    ledger = SorsPublicationLedger()
    execution = run_publication_fixed_point(
        state,
        build_publication_graph(graph),
        ledger,
        policy=RoundingPolicy(step=1.0),
        point_tolerance=1e-6,
        max_passes=20,
    )

    first = ledger.current_record('metric:U:47:debt_rub')
    assert first is not None and first['published_value'] == 6
    k2 = ledger.current_record('K2')
    assert k2 is not None and k2['published_value'] == 0
    assert int(k2['assumption_tier']) == 1

    second = ledger.current_record('metric:R1:C1:debt_rub')
    assert second is not None
    assert second['published_value'] == 8
    assert second['evidence_method'] == 'PUBLISHED_VALUE_INHERITED'
    assert int(second['assumption_tier']) == 1
    assert execution.passes >= 2


def test_publication_pass_limit_blocks_transition_to_solver_state() -> None:
    graph = _udmurtia_like_graph(with_cascade=True)
    state = SorsIntervalClosureState(graph, tolerance=1e-9, max_passes=50)
    ledger = SorsPublicationLedger()
    with pytest.raises(SorsPublicationFixedPointLimitError, match='optimization is not allowed'):
        run_publication_fixed_point(
            state,
            build_publication_graph(graph),
            ledger,
            policy=RoundingPolicy(step=1.0),
            point_tolerance=1e-6,
            max_passes=1,
        )


def test_publication_hierarchy_propagates_latent_sums_without_integer_arithmetic() -> None:
    """Rounded 6 + 5 may legitimately coexist with rounded parent 10.

    The hierarchy relation is exact only for hidden monetary quantities.  Closure
    should therefore intersect their publication intervals (and tighten them)
    rather than asserting the false integer identity 6 + 5 == 10.
    """

    graph = SorsQuantityGraph(
        pd.DataFrame([
            _row(
                'publication:national_total:debt_rub',
                'PUBLISHED_AGGREGATE',
                9.5,
                10.5,
                regions=('R',),
                classes=('A', 'B'),
                representative=10,
                status='STABLE',
            ),
            _row(
                'publication:national_class:A:debt_rub',
                'PUBLISHED_AGGREGATE',
                5.5,
                6.5,
                regions=('R',),
                classes=('A',),
                representative=6,
                status='STABLE',
            ),
            _row(
                'publication:national_class:B:debt_rub',
                'PUBLISHED_AGGREGATE',
                4.5,
                5.5,
                regions=('R',),
                classes=('B',),
                representative=5,
                status='STABLE',
            ),
            _row(
                'metric:R:A:debt_rub',
                'REGIONAL_CLASS_METRIC',
                0.0,
                100.0,
                regions=('R',),
                classes=('A',),
                region_code='R',
                class_code='A',
            ),
            _row(
                'metric:R:B:debt_rub',
                'REGIONAL_CLASS_METRIC',
                0.0,
                100.0,
                regions=('R',),
                classes=('B',),
                region_code='R',
                class_code='B',
            ),
        ]),
        pd.DataFrame([
            _relation(
                'r:total',
                'NATIONAL_TOTAL',
                'publication:national_total:debt_rub',
                ('metric:R:A:debt_rub', 'metric:R:B:debt_rub'),
            ),
            _relation(
                'r:A',
                'NATIONAL_CLASS',
                'publication:national_class:A:debt_rub',
                ('metric:R:A:debt_rub',),
            ),
            _relation(
                'r:B',
                'NATIONAL_CLASS',
                'publication:national_class:B:debt_rub',
                ('metric:R:B:debt_rub',),
            ),
        ]),
        pd.DataFrame(),
    )
    state = SorsIntervalClosureState(graph, tolerance=1e-9, max_passes=50)
    ledger = SorsPublicationLedger()
    execution = run_publication_fixed_point(
        state,
        build_publication_graph(graph),
        ledger,
        policy=RoundingPolicy(step=1.0),
        point_tolerance=1e-6,
        max_passes=20,
    )

    quantities = execution.quantities_grid.set_index('quantity_id')
    # Exact hidden identity P=A+B narrows A<6 and B<5 while all three source
    # representatives remain their original 10/6/5 publication facts.
    assert float(quantities.loc['publication:national_class:A:debt_rub', 'upper_bound']) <= 6.0 + 1e-9
    assert float(quantities.loc['publication:national_class:B:debt_rub', 'upper_bound']) <= 5.0 + 1e-9
    assert ledger.current_record('publication:national_total:debt_rub')['published_value'] == 10
    assert ledger.current_record('publication:national_class:A:debt_rub')['published_value'] == 6
    assert ledger.current_record('publication:national_class:B:debt_rub')['published_value'] == 5
