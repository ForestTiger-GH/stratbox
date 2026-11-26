"""Explicit revisions, composable histories and content-bound validation."""
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from stratbox.shared.data.values import SourceDataset, canonical_tree, restore_tree
from stratbox.shared.data.history import (RevisionPolicy, resolve_revisions, make_validation_certificate,
    verify_history_certificates, dataset_content_identity)
from stratbox.shared.data.selection import ObservationQuery, select_observations
from stratbox.core.commands.observations import observations_merge


def dataset(issue, value='1', period='2026-01-01'):
    return SourceDataset('s', ({'period': period, 'metric': 'debt', 'value': Decimal(value)},),
                         {'unit': 'RUB'}, issue_id=issue)


def validated(value):
    certificate = make_validation_certificate(value, rule_id='source.geometry',
        method_identity='reviewed-parser', build_identity='test-build')
    return replace(value, validation_certificates=(certificate,))


def test_equal_duplicates_coalesce_and_keep_contributing_members():
    result, decisions = resolve_revisions((dataset('jan'), dataset('feb')), RevisionPolicy())
    assert len(result.rows) == 1 and len(result.history_membership.members) == 2
    assert decisions[0].rule == 'equal' and len(decisions[0].selected_inputs) == 2


def test_conflicts_require_explicit_order_and_retain_rejected_values():
    values = (dataset('jan'), dataset('feb', '2'))
    with pytest.raises(ValueError, match='ambiguous_revision'):
        resolve_revisions(values, RevisionPolicy())
    policy = RevisionPolicy(conflicts='latest', ordered_issues=('jan', 'feb'), ordering_basis='publisher.release_order')
    result, decisions = resolve_revisions(values, policy)
    assert result.rows[0]['value'] == Decimal('2')
    assert decisions[0].alternative_rows[0]['value'] == Decimal('1')
    with pytest.raises(ValueError, match='revision_order_required'):
        RevisionPolicy(conflicts='latest')


def test_resolved_history_can_be_extended_and_revisited_as_of():
    policy = RevisionPolicy(conflicts='latest', ordered_issues=('jan', 'feb', 'mar'), ordering_basis='publisher.release_order')
    first, _ = resolve_revisions((dataset('jan'), dataset('feb', '2')), policy)
    extended, _ = resolve_revisions((first, dataset('mar', '3')), policy)
    assert extended.rows[0]['value'] == Decimal('3')
    assert len(extended.history_membership.members) == 3
    old, _ = resolve_revisions((extended,), replace(policy, as_of='jan'))
    assert old.rows[0]['value'] == Decimal('1')


def test_expected_issue_coverage_cannot_be_inferred_from_available_rows():
    result, _ = resolve_revisions((dataset('jan'),), RevisionPolicy(expected_issues=('jan', 'feb')))
    assert result.history_membership.missing_issues == ('feb',)
    assert not result.assessment.complete


def test_strict_merge_remains_strict_and_membership_is_not_semantics():
    context = SimpleNamespace(parameters={})
    jan = dataset('jan', period='2026-01-01')
    feb = dataset('feb', period='2026-02-01')
    merged = observations_merge({'datasets': (jan, feb)}, {}, context)['dataset']
    assert 'source_issues' not in merged.semantics
    extended = observations_merge({'datasets': (merged, dataset('mar', period='2026-03-01'))}, {}, context)['dataset']
    assert len(extended.history_membership.members) == 3
    with pytest.raises(Exception, match='duplicate_grain'):
        observations_merge({'datasets': (jan, jan)}, {}, context)


def test_portable_certificate_requires_authority_and_exact_row_values():
    original = validated(dataset('jan'))
    cert = original.validation_certificates[0]
    assert cert.binds(original) and cert.dataset_identity == dataset_content_identity(original)
    history, _ = resolve_revisions((original,), RevisionPolicy())
    trusted = lambda item: item.identity == cert.identity
    assert verify_history_certificates(history, trusted)
    assert not verify_history_certificates(history, lambda _: False)
    forged = replace(history, rows=({**history.rows[0], 'value': Decimal('999')},))
    assert not verify_history_certificates(forged, trusted)
    for forged in (replace(history, semantics={'unit': 'USD'}),
                   replace(history, source_id='another-source'), replace(history, issue_id='another-issue')):
        assert not verify_history_certificates(forged, trusted)
    selected = select_observations(original, ObservationQuery(metrics=('debt',)))
    assert verify_history_certificates(selected, trusted)


def test_same_issue_conflict_and_incompatible_semantics_remain_errors():
    policy = RevisionPolicy(conflicts='latest', ordered_issues=('jan',), ordering_basis='publisher.release_order')
    with pytest.raises(ValueError, match='ambiguous_same_revision'):
        resolve_revisions((dataset('jan'), dataset('jan', '2')), policy)
    with pytest.raises(ValueError, match='semantic_mismatch'):
        resolve_revisions((dataset('jan'), replace(dataset('feb'), semantics={'unit': 'USD'})), RevisionPolicy())
