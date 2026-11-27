"""Sustained polling, bounded cold maintenance and explicit history retirement."""
from datetime import datetime, timedelta, timezone

import pytest

from stratbox.core.observability.journal.stream import MemoryJournal
from stratbox.core.observability.projections.source_state import SourceStateIndex
from stratbox.core.storage.source_state import SQLiteSourceState, SourceStateRetention
from stratbox.shared.data.values import ByteIdentity, FetchEvidence, fingerprint


def poll(journal, number):
    evidence = FetchEvidence('request', datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=number),
                             200, ByteIdentity.of(b'unchanged'), observation_id=str(number))
    journal.append(kind='output.accepted', run_id=str(number), command_id='command.material.fetch', output_name='evidence',
        data={'accepted_value_id': 'poll-' + str(number), 'value_identity': fingerprint(evidence),
              'output_disposition': 'accepted', 'output_role': 'data',
              'acquisition_evidence_id': fingerprint(evidence),
              'observation': {'source_id': 's', 'issue_id': 'issue', 'asset_id': 'main',
                  'observation_id': str(number), 'observed_at': evidence.observed_at,
                  'evidence_identity': fingerprint(evidence), 'material_identity': evidence.material_identity,
                  'acquisition_evidence': evidence}})
    return fingerprint(evidence)


def maintain(store, journal, disposition, *, limit=2, **kwargs):
    results = []
    while True:
        report = store.maintain(stream_id=journal.stream_id,
            policy=SourceStateRetention(journal.checkpoint().tail, disposition, limit, **kwargs))
        assert report.records + report.authority + report.retention_links <= limit
        results.append(report)
        if not report.has_more:
            return results
        assert len(results) < 100


def test_sustained_unchanged_polling_archives_under_a_small_hot_limit(tmp_path):
    journal = MemoryJournal()
    with SQLiteSourceState(tmp_path / 'state.sqlite', max_records=4) as store:
        index = SourceStateIndex(store)
        ids = []
        for number in range(40):
            ids.append(poll(journal, number))
            index.advance(journal)
            maintain(store, journal, 'archive')
            assert store.storage_usage()['hot_records'] <= 1
            assert journal.checkpoint().consumers['source-state'] == number + 1
        current = store.read(('s',), stream_id=journal.stream_id)
        history = store.read(('s',), stream_id=journal.stream_id, view='history')
        assert current.complete and len(current.observations) == 1
        assert history.complete and len(history.observations) == 40
        assert all(store.has_acquisition_evidence(identity) for identity in ids)
        assert store.storage_usage()['archive_records'] == 79
        store.export_checkpoint(tmp_path / 'snapshot.sqlite')
    with SQLiteSourceState(tmp_path / 'snapshot.sqlite') as restored:
        assert len(restored.read(('s',), stream_id=journal.stream_id, view='history').observations) == 40
        assert restored.has_acquisition_evidence(ids[0])


def test_declared_history_retirement_bounds_all_polling_evidence(tmp_path):
    journal = MemoryJournal()
    with SQLiteSourceState(tmp_path / 'state.sqlite', max_records=5) as store:
        index = SourceStateIndex(store)
        first = None
        for number in range(60):
            identity = poll(journal, number)
            first = first or identity
            index.advance(journal)
            maintain(store, journal, 'discard')
            assert store.storage_usage()['hot_records'] == 2
            assert store.storage_usage()['archive_records'] == 0
            assert store.has_acquisition_evidence(identity)
        current = store.read(('s',), stream_id=journal.stream_id)
        history = store.read(('s',), stream_id=journal.stream_id, view='history')
        assert current.complete and current.history_retained_after == 59
        assert not history.complete and history.history_retained_after == 59
        assert not store.has_acquisition_evidence(first)
        assert store.storage_usage()['physical_bytes']['database'] > 0


def test_archive_capacity_failure_rolls_back_the_entire_maintenance_batch(tmp_path):
    journal = MemoryJournal()
    with SQLiteSourceState(tmp_path / 'state.sqlite', max_archive_records=1) as store:
        for number in range(2):
            poll(journal, number)
        SourceStateIndex(store).advance(journal)
        before = store.storage_usage()
        with pytest.raises(ValueError, match='archive_capacity_exhausted'):
            maintain(store, journal, 'archive', limit=10)
        after = store.storage_usage()
        assert (before['hot_records'], before['archive_records']) == (after['hot_records'], after['archive_records'])
        assert len(store.read(('s',), stream_id=journal.stream_id, view='history').observations) == 2
        assert store.checkpoint(journal.stream_id).applied_through == 2


def test_explicit_authority_pin_survives_retirement_and_cold_history_is_retirable(tmp_path):
    journal = MemoryJournal()
    with SQLiteSourceState(tmp_path / 'state.sqlite') as store:
        first = poll(journal, 0)
        poll(journal, 1)
        SourceStateIndex(store).advance(journal)
        maintain(store, journal, 'archive')
        maintain(store, journal, 'discard', protected_authority=(('acquisition', first),))
        assert store.has_acquisition_evidence(first)
        assert len(store.read(('s',), stream_id=journal.stream_id, view='history').observations) == 1
        maintain(store, journal, 'discard')
        assert not store.has_acquisition_evidence(first)


def test_reported_or_diagnostic_ports_cannot_create_reusable_scientific_state(tmp_path):
    journal = MemoryJournal()
    for disposition, role in (('reported', 'data'), ('accepted', 'diagnostic')):
        journal.append(kind='output.accepted', run_id='test', command_id='command.observations.validate', output_name='dataset',
            data={'accepted_value_id': disposition + role, 'value_identity': 'value', 'source_id': 's',
                  'output_disposition': disposition, 'output_role': role, 'certificate_ids': ('unqualified',)})
    with SQLiteSourceState(tmp_path / 'state.sqlite') as store:
        SourceStateIndex(store).advance(journal)
        assert not store.read(('s',), stream_id=journal.stream_id).outputs
        assert not store.has_validation_certificate('unqualified')
