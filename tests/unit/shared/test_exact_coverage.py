"""Complete axis marginals never establish a complete observation cube."""
from dataclasses import replace
from itertools import product
import pytest
from stratbox.shared.data.assessment import CoverageAssessment, CoverageCoordinate, assessment_from, assessment_value


def coordinate(subject, metric, period, **changes):
    return CoverageCoordinate('source', subject, metric, 'as_of', period, 'population', **changes)


def sparse():
    members = (coordinate('A', 'X', '2026-01-01'), coordinate('B', 'Y', '2026-02-01'))
    return members, CoverageAssessment('supplied', tuple(item.identity for item in members), True,
        ('subject:A', 'subject:B', 'metric:X', 'metric:Y', 'period:2026-01-01', 'period:2026-02-01'),
        ('subject:A', 'subject:B', 'metric:X', 'metric:Y', 'period:2026-01-01', 'period:2026-02-01'))


def test_complete_marginals_leave_joint_coverage_unknown():
    _, coverage = sparse()
    assert coverage.axis_status == 'complete'
    assert coverage.status == 'unknown'
    assert 'coverage.complete' not in coverage.facts


def test_explicit_cube_detects_six_missing_values_and_replays_exactly():
    _, coverage = sparse()
    full = tuple(coordinate(*args) for args in product(('A', 'B'), ('X', 'Y'), ('2026-01-01', '2026-02-01')))
    coverage = replace(coverage, expected_coordinates=full)
    assert coverage.status == 'partial'
    assert len({item.identity for item in full} - set(coverage.members)) == 6
    assert assessment_from('CoverageAssessment', assessment_value(coverage)) == coverage


def test_explicit_sparse_requirement_can_be_complete():
    members, coverage = sparse()
    assert replace(coverage, expected_coordinates=members).status == 'complete'
    assert replace(coverage, expected_coordinates=members, membership_closed=False).status == 'partial'


@pytest.mark.parametrize('changes', ({'dimensions': (('currency', 'RUB'),)},))
def test_grain_includes_dimensions(changes):
    value = coordinate('A', 'X', '2026-01-01')
    assert replace(value, **changes).identity != value.identity
    assert replace(value, perimeter='different').identity != value.identity
    assert replace(value, period_kind='capture').identity != value.identity
