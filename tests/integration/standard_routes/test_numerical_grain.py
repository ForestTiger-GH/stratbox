"""Numerical actions preserve each history's economic and demographic axes."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from stratbox.core.commands.calculations import calculate_change, calculate_flow, calculate_formula, calculate_ratio
from stratbox.core.commands.timeseries import timeseries_partition, timeseries_prepare
from stratbox.core.execution.service import ExecutionFailure
from stratbox.shared.data.values import Assessment, FormulaSpec, SourceDataset

CONTEXT = SimpleNamespace(parameters={})


def row(value, *, period='2026-01', **axes):
    return dict(metric='balance', subject='RU', unit='RUB', scale=1, perimeter='all',
        measure_kind='flow', frequency='monthly', period_kind='interval', basis='ytd',
        period=period, value=Decimal(value), value_status='reported', **axes)


def test_deaccumulation_keeps_currencies_and_banks_in_independent_histories():
    from stratbox.core.commands.observations import observations_validate
    dataset = SourceDataset('fixture', tuple(row(value, period=period, currency=currency, bank=bank)
        for currency, bank, values in (('RUB', 'A', (10, 25)), ('USD', 'B', (100, 130)))
        for period, value in zip(('2026-01', '2026-02'), values)))
    assert observations_validate({'dataset': dataset}, {}, CONTEXT)['dataset'] is dataset
    result = calculate_flow({'observations': dataset}, {}, CONTEXT)['dataset']
    assert [(r['currency'], r['bank'], r['value']) for r in result.rows] == [
        ('RUB', 'A', Decimal(10)), ('RUB', 'A', Decimal(15)),
        ('USD', 'B', Decimal(100)), ('USD', 'B', Decimal(30)),
    ]


@pytest.mark.parametrize('axis, values', [
    ('bank', ('A', 'B')), ('portfolio', ('retail', 'corporate')),
    ('sex', ('female', 'male')), ('age', ('young', 'senior')),
    ('activity', ('agriculture', 'mining')), ('value_basis', ('reported', 'adjusted')),
])
def test_partition_preserves_all_standard_series_axes(axis, values):
    dataset = SourceDataset('fixture', tuple(row(index, **{axis: value})
        for index, value in enumerate(values, 1)))
    with pytest.raises(ExecutionFailure, match='unique_grain_required'):
        timeseries_prepare({'observations': dataset}, {}, CONTEXT)
    series = timeseries_partition({'observations': dataset}, {}, CONTEXT)['items']
    assert {item.coordinates[axis] for item in series} == set(values)
    assert len(series) == 2 and all(len(item.values) == 1 for item in series)


def test_ratio_and_formula_reject_economically_different_operands():
    numerator = SourceDataset('fixture', (row(10, currency='RUB'),))
    denominator = SourceDataset('fixture', (row(20, currency='USD'),))
    with pytest.raises(ExecutionFailure, match='incompatible_inputs'):
        calculate_ratio({'numerator': numerator, 'denominator': denominator}, {}, CONTEXT)
    # Even a caller-selected coarse join cannot erase semantic disagreement.
    with pytest.raises(ExecutionFailure, match='semantic_mismatch'):
        calculate_ratio({'numerator': numerator, 'denominator': denominator},
            {'group_by': ('period', 'subject')}, CONTEXT)
    rows = ({**numerator.rows[0], 'metric': 'total'},
            {**denominator.rows[0], 'metric': 'other'})
    formula = FormulaSpec('total - other', {'total': 'total', 'other': 'other'}, 'liquid', 'RUB')
    with pytest.raises(ExecutionFailure, match='semantic_mismatch'):
        calculate_formula({'dataset': SourceDataset('fixture', rows)}, formula, CONTEXT)


def test_selected_change_period_must_exist_and_booleans_are_not_observations():
    dataset = SourceDataset('fixture', (row(10), row(20, period='2026-02')))
    with pytest.raises(ExecutionFailure, match='selected_period_missing'):
        calculate_change({'observations': dataset},
            {'before': '2025-12', 'after': '2026-02'}, CONTEXT)
    invalid = SourceDataset('fixture', ({**row(10), 'value': True}, row(20, period='2026-02')))
    with pytest.raises(ExecutionFailure, match='numeric_value_required'):
        calculate_change({'observations': invalid}, {}, CONTEXT)


def test_derived_assessment_cannot_promote_incomplete_or_one_sided_qualifications():
    from stratbox.core.commands.calculations import observations_compare
    from stratbox.shared.data.assessment import CoverageAssessment
    numerator = SourceDataset('fixture', (row(10),),
        assessment=Assessment(qualifications=frozenset({'reviewed'})))
    denominator = SourceDataset('fixture', (row(20),),
        assessment=Assessment('partial', ('fixture.missing_rows',)))
    result = calculate_ratio({'numerator': numerator, 'denominator': denominator}, {}, CONTEXT)['dataset']
    assert not result.assessment.complete
    assert 'fixture.missing_rows' in result.assessment.findings
    assert 'reviewed' not in result.assessment.qualifications
    compared = observations_compare({'before': numerator, 'after': denominator}, {}, CONTEXT)
    assert not compared['assessment'].complete
    unknown = SourceDataset('fixture', (row(10), row(20, period='2026-02')),
        assessment=Assessment(coverage=CoverageAssessment('fixture', (), True, ())))
    assert unknown.assessment.status == 'complete' and not unknown.assessment.complete
    change = calculate_change({'observations': unknown}, {}, CONTEXT)['dataset']
    assert not change.assessment.complete


def test_merged_qualification_must_apply_to_every_input_partition():
    from stratbox.core.commands.observations import observations_merge
    first = SourceDataset('fixture', (row(10),),
        assessment=Assessment(qualifications=frozenset({'reviewed'})))
    second = SourceDataset('fixture', (row(20, period='2026-02'),))
    merged = observations_merge({'datasets': (first, second)}, {}, CONTEXT)['dataset']
    assert 'reviewed' not in merged.assessment.qualifications
    assert 'partitioned_input_coverage' in merged.assessment.qualifications


def test_domain_industry_formula_preserves_incomplete_source_assessment():
    from stratbox.domains.cbr.calculations.industry.actions import calculate, REQUIRED
    rows = tuple({**row(1), 'metric': metric, 'evidence_ref': 'fixture:' + metric}
        for metric in REQUIRED)
    dataset = SourceDataset('fixture', rows,
        assessment=Assessment('partial', ('fixture.source_incomplete',)))
    result = calculate({'dataset': dataset}, SimpleNamespace(series_id='fixture'),
        SimpleNamespace(checkpoint=lambda: None))['dataset']
    assert not result.assessment.complete
    assert 'fixture.source_incomplete' in result.assessment.findings
