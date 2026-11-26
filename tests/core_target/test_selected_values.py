"""Exact publication choice and complete selected observation scopes."""
from datetime import date

import pytest

from stratbox.shared.data.selection import (IssueQuery, ObservationQuery, SubjectChoice,
    select_publication_assets, select_observations)
from stratbox.shared.data.values import Assessment, PublicationAsset, PublicationListing, SourceDataset, fingerprint
from stratbox.core.storage.datasets.stores import MemoryDatasetStore


def asset(issue, locator, fmt='xlsx', source='s', **metadata):
    return PublicationAsset(source, issue, 'main', locator, fmt, metadata)


def test_duplicate_inside_one_issue_cannot_hide_among_other_dates():
    listing = PublicationListing('d', (asset('2026-01-01', 'a'), asset('2026-01-01', 'b'), asset('2026-02-01', 'c')))
    with pytest.raises(ValueError, match='ambiguous_asset'):
        select_publication_assets(listing, IssueQuery())
    selection, report = select_publication_assets(listing, IssueQuery(ambiguity='report'))
    assert [a.issue_id for a in selection.entries] == ['2026-02-01']
    assert len(report.ambiguous) == 1 and not selection.assessment.complete


def test_representation_preference_does_not_hide_same_format_revision():
    listing = PublicationListing('d', (asset('2026-01-01', 'html', 'html'), asset('2026-01-01', 'a')))
    selection, _ = select_publication_assets(listing, IssueQuery(formats=('xlsx', 'html')))
    assert selection.entries[0].locator == 'a'
    selection, _ = select_publication_assets(listing, IssueQuery(locators=('html',)))
    assert selection.entries[0].format == 'html'


def test_selected_known_issue_can_complete_without_claiming_full_listing():
    listing = PublicationListing('d', (asset('2026-01-01', 'a'),), Assessment('partial', ('unrelated unknown link',)))
    selection, report = select_publication_assets(listing, IssueQuery(mode='exact', issues=('2026-01-01',)))
    assert selection.assessment.complete
    assert not report.membership_closed and not report.parent_assessment.complete
    selection, _ = select_publication_assets(listing, IssueQuery(mode='exact', issues=('2026-01-01',), coverage_intent='complete_inventory'))
    assert not selection.assessment.complete


def test_missing_calendar_issue_and_incomplete_empty_listing_are_distinct():
    listing = PublicationListing('d', (asset('2026-01-01', 'a'),))
    _, report = select_publication_assets(listing, IssueQuery(mode='calendar', expected_issues=('2026-01-01', '2026-02-01')))
    assert report.missing == ('2026-02-01',)
    empty = PublicationListing('d', (), Assessment('partial'))
    selection, report = select_publication_assets(empty, IssueQuery())
    assert not selection.assessment.complete and report.reasons == ('publication.discovery_incomplete',)
    selection, _ = select_publication_assets(empty, IssueQuery(mode='exact'))
    assert selection.assessment.complete


def test_exact_expectations_are_source_and_asset_qualified():
    listing = PublicationListing('d', (asset('2026-01-01', 'a'),))
    selected, report = select_publication_assets(listing, IssueQuery(
        issues=('2026-01-01',), source_ids=('s', 'other')))
    assert not selected.assessment.complete and len(report.requested) == 2 and len(report.missing) == 1
    selected, report = select_publication_assets(listing, IssueQuery(
        issues=('2026-01-01',), source_ids=('s',), asset_ids=('main', 'annex')))
    assert not selected.assessment.complete and len(report.missing) == 1


def test_typed_issue_fields_cannot_be_silently_ignored():
    assert IssueQuery(issues=('2026-01-01',)).mode == 'exact'
    assert IssueQuery(expected_issues=('2026-01-01',)).mode == 'calendar'
    assert IssueQuery(date_from=date(2026, 1, 1)).mode == 'range'
    with pytest.raises(ValueError, match='incompatible_issue_fields'):
        IssueQuery(mode='latest', issues=('2026-01-01',))


def test_latest_is_per_source_and_uses_explicit_intrinsic_order():
    listing = PublicationListing('d', (asset('2026-01 week1', 'a', issue_order=(2026, 1, 1)),
        asset('2026-01 week2', 'b', issue_order=(2026, 1, 2)),
        asset('2025-12 week1', 'c', source='other', issue_order=(2025, 12, 1))))
    selected, _ = select_publication_assets(listing, IssueQuery(mode='latest', date_axis='issue_order'))
    assert {a.locator for a in selected.entries} == {'b', 'c'}


def data():
    return SourceDataset('s', tuple({'subject_namespace': namespace, 'subject': subject,
        'period': date(2026, 1, 1), 'metric': 'debt', 'value': index}
        for index, (namespace, subject) in enumerate((('bank', '1'), ('bank', '2'), ('group', '1')))))


def test_subject_order_namespace_and_deliberate_empty_scope():
    original = data()
    selected = select_observations(original, ObservationQuery(subjects=(SubjectChoice('group', '1'), SubjectChoice('bank', '1'))))
    assert [(r['subject_namespace'], r['subject']) for r in selected.rows] == [('group', '1'), ('bank', '1')]
    assert selected.assessment.complete and selected.assessment.coverage.parent_identity == original.identity
    assert not select_observations(original, ObservationQuery(subjects=())).rows
    assert select_observations(original, ObservationQuery(subjects=())).assessment.complete


def test_stored_and_in_memory_query_share_scoped_coverage():
    original = data()
    query = ObservationQuery(filters={'subject_namespace': ('bank',)}, limit=1)
    store = MemoryDatasetStore(scope_id='test')
    reference = store.ingest(original, destination='snapshots', identity=fingerprint(original))
    assert store.query(reference, query) == select_observations(original, query)


def test_date_axis_uses_real_interval_semantics_and_missing_members_remain_partial():
    original = SourceDataset('s', ({'period': (date(2026, 1, 1), date(2026, 1, 31)), 'metric': 'flow', 'value': 1},))
    assert not select_observations(original, ObservationQuery(date_from=date(2026, 1, 15))).rows
    assert select_observations(original, ObservationQuery(date_from=date(2026, 1, 15), interval_mode='overlap')).rows
    selected = select_observations(original, ObservationQuery(expected_members=('not-present',)))
    assert not selected.assessment.complete and selected.assessment.coverage.missing == ('not-present',)
