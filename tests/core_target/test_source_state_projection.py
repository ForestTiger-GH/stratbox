"""Global replay, atomic projection cursors and qualified retained entrances."""
from datetime import datetime, timedelta, timezone

import pytest

from stratbox.core.observability.journal.stream import MemoryJournal
from stratbox.core.observability.projections.source_state import SourceStateIndex, project_page
from stratbox.core.storage.source_state import MemorySourceState, SQLiteSourceState
from stratbox.shared.data.processing import SourceStateKey
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.values import Assessment, ByteIdentity, FetchEvidence, ImmutableMaterialRef, fingerprint


def use(source='s', body=b'original'):
    return SourceUse(SourceCoordinate(source, issue_id='2026-01-01', asset_id='main', material_identity=ByteIdentity.of(body)), 'source', 'verified')


def accepted(journal, *, command='command.observations.validate', accepted_id='accepted', value_id='value',
             output='dataset', uses=None, reference=None, **data):
    return journal.append(kind='output.accepted', run_id='run', command_id=command, output_name=output,
        data={'capability_id': command, 'accepted_value_id': accepted_id, 'value_identity': value_id,
              'processing_basis': ('inputs', 'rules', 'build'), 'source_uses': uses or (use(),),
              'assessment': Assessment(), 'persistent': reference is not None, 'retained_reference': reference, **data})


@pytest.fixture(params=['memory', 'sqlite'])
def store(request, tmp_path):
    value = MemorySourceState() if request.param == 'memory' else SQLiteSourceState(tmp_path / 'state.sqlite')
    yield value
    if hasattr(value, 'close'):
        value.close()


def test_retained_encoded_dataset_is_a_semantic_restart_entrance(store):
    journal = MemoryJournal()
    accepted(journal, accepted_id='dataset', value_id='dataset-content')
    accepted(journal, command='command.value.encode', accepted_id='encoding', value_id='encoded-content',
             output='representation', represents_value_identity='dataset-content')
    reference = ImmutableMaterialRef('objects/abc', ByteIdentity.of(b'encoded'), accepted_value_id='encoding',
                                    effect_id='stored', provider_scope='test')
    accepted(journal, command='command.artifact.commit', accepted_id='commit', output='reference', reference=reference)
    SourceStateIndex(store).advance(journal, page_limit=1)
    state = store.read(('s',), stream_id=journal.stream_id, minimum_applied_through=3)
    assert state.complete
    semantic = next(value for value in state.outputs if value.accepted_value_id == 'dataset')
    assert semantic.persistent and semantic.retained_reference == reference
    assert semantic.restore_via == 'command.value.decode'
    assert journal.checkpoint().consumers['source-state'] == 3


def test_authority_accepts_only_validator_certificates_and_trusted_source_uses(store):
    journal = MemoryJournal()
    accepted(journal, command='command.table.interpret', accepted_id='parser', certificate_ids=('forged',))
    accepted(journal, accepted_id='validator', certificate_ids=('valid',), trusted_source_uses=(use(),))
    SourceStateIndex(store).advance(journal)
    assert store.has_validation_certificate('valid')
    assert not store.has_validation_certificate('forged')
    assert store.has_source_use(fingerprint(use()))
    assert not store.has_source_use(fingerprint(use('other')))


def test_acquisition_authority_survives_without_a_declared_source(store):
    journal = MemoryJournal()
    for command, identity in (('command.material.fetch', 'neutral-fetch'),
                               ('command.value.encode', 'not-fetch')):
        journal.append(kind='output.accepted', run_id='run', command_id=command, output_name='evidence',
            data={'accepted_value_id': identity, 'value_identity': identity,
                  'acquisition_evidence_id': identity})
    SourceStateIndex(store).advance(journal)
    assert store.has_acquisition_evidence('neutral-fetch')
    assert not store.has_acquisition_evidence('not-fetch')


def test_observation_revisions_survive_failure_and_output_duplicates(store):
    journal = MemoryJournal()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index, body in enumerate((b'A', b'B', b'A')):
        observation = {'source_id': 's', 'issue_id': '2026-01-01', 'asset_id': 'main',
            'observation_id': str(index), 'observed_at': start + timedelta(days=index),
            'comparison_scope': 'bytes', 'evidence_identity': f'evidence-{index}', 'material_identity': ByteIdentity.of(body)}
        accepted(journal, command='command.material.fetch', accepted_id=f'material-{index}', output='material', observation=observation)
        accepted(journal, command='command.material.fetch', accepted_id=f'evidence-{index}', output='evidence', observation=observation)
    journal.append(kind='command.failed', run_id='run')
    SourceStateIndex(store).advance(journal)
    state = store.read(('s',), stream_id=journal.stream_id, view='history')
    assert len(state.observations) == 3
    assert [v.material_identity for v in sorted(state.observations, key=lambda v: v.observed_at)] == [ByteIdentity.of(v) for v in (b'A', b'B', b'A')]
    assert not any(v.stage == 'original' for v in state.outputs)


def test_current_acquisition_evidence_is_separate_from_immutable_receipt(store):
    journal = MemoryJournal()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    reference = ImmutableMaterialRef('objects/body', ByteIdentity.of(b'same'), provider_scope='test')
    latest = None
    for index in (0, 2, 1):  # A slow older request finishes after the fresh one.
        evidence = FetchEvidence('request', start + timedelta(days=index), 200, reference.identity,
            {'etag': str(index)}, observation_id=f'poll-{index}', representation_identity='representation')
        observation = {'source_id': 's', 'issue_id': '2026-01-01', 'asset_id': 'main',
            'observation_id': evidence.observation_id, 'observed_at': evidence.observed_at,
            'comparison_scope': 'bytes', 'evidence_identity': fingerprint(evidence),
            'material_identity': reference.identity, 'retained_reference': reference,
            'acquisition_evidence': evidence}
        accepted(journal, command='command.material.receive', accepted_id=f'raw-{index}',
            output='reference', reference=reference, observation=observation)
        accepted(journal, command='command.material.receive', accepted_id=f'request-{index}',
            output='request', observation=observation)
        if index == 2:
            latest = evidence
    forged = FetchEvidence('request', start, 200, reference.identity, {'etag': 'forged'})
    accepted(journal, command='command.table.interpret', accepted_id='not-acquisition', uses=(use('other'),), observation={
        'source_id': 'other', 'observation_id': 'forged', 'observed_at': start,
        'evidence_identity': fingerprint(forged), 'material_identity': reference.identity,
        'acquisition_evidence': forged})
    SourceStateIndex(store).advance(journal)
    current = store.read(('s',), stream_id=journal.stream_id)
    assert len(current.observations) == 1 and current.observations[0].acquisition_evidence == latest
    assert current.observations[0].retained_reference == reference
    assert len(current.outputs) == 1 and current.outputs[0].output_name == 'reference'
    assert store.has_acquisition_evidence(fingerprint(latest))
    assert not store.has_acquisition_evidence(fingerprint(forged))
    history = store.read(('s',), stream_id=journal.stream_id, view='history')
    assert len(history.observations) == 3 and len(history.outputs) == 3


def test_only_primary_stage_ports_are_indexed_and_sidecar_roles_remain_distinct(store):
    journal = MemoryJournal()
    for command, outputs in (
        ('command.archive.pack', ('material', 'manifest', 'assessment')),
        ('command.observations.resolve_revisions', ('dataset', 'datasets', 'decisions')),
        ('command.dbf.export_csv', ('csv', 'evidence', 'summary')),
    ):
        for output in outputs:
            accepted(journal, command=command, accepted_id=command + '/' + output, output=output)
    SourceStateIndex(store).advance(journal)
    state = store.read(('s',), stream_id=journal.stream_id)
    assert {(value.stage, value.output_name) for value in state.outputs} == {
        ('archive', 'material'), ('observations', 'dataset'),
        ('representation', 'csv'), ('representation', 'evidence')}


def test_current_view_keeps_retained_equivalent_when_later_attempt_is_ephemeral(store):
    journal = MemoryJournal()
    accepted(journal, command='command.archive.pack', output='material', accepted_id='first-pack', value_id='first-stage')
    reference = ImmutableMaterialRef('objects/archive', ByteIdentity.of(b'archive'),
        accepted_value_id='first-pack', effect_id='archive-effect', provider_scope='test')
    accepted(journal, command='command.artifact.commit', output='reference', accepted_id='commit', reference=reference)
    accepted(journal, command='command.archive.pack', output='material', accepted_id='repeated-pack', value_id='another-stage')
    accepted(journal, command='command.archive.pack', output='material', accepted_id='different-input',
             processing_basis=('different-input-content', 'rules', 'build'))
    SourceStateIndex(store).advance(journal)
    snapshot = store.read(('s',), stream_id=journal.stream_id)
    archives = {value.accepted_value_id: value for value in snapshot.outputs if value.stage == 'archive'}
    assert set(archives) == {'first-pack', 'different-input'}
    assert archives['first-pack'].persistent and archives['first-pack'].retained_reference == reference
    assert not archives['different-input'].persistent
    history = store.read(('s',), stream_id=journal.stream_id, view='history')
    assert len([value for value in history.outputs if value.stage == 'archive']) == 3
    assert store.compact(stream_id=journal.stream_id, through=journal.checkpoint().tail) == 2
    remaining = store.read(('s',), stream_id=journal.stream_id)
    assert [value.accepted_value_id for value in remaining.outputs if value.stage == 'archive'] == ['first-pack']


def test_lost_acknowledgement_replays_idempotently(store):
    journal = MemoryJournal()
    accepted(journal)
    original_ack = journal.acknowledge
    def fail_once(consumer, page):
        journal.acknowledge = original_ack
        raise OSError('lost acknowledgement')
    journal.acknowledge = fail_once
    index = SourceStateIndex(store)
    with pytest.raises(OSError):
        index.advance(journal)
    assert store.checkpoint(journal.stream_id).applied_through == 1
    assert journal.checkpoint().consumers['source-state'] == 0
    index.advance(journal)
    assert len(store.read(('s',), stream_id=journal.stream_id).outputs) == 1
    assert journal.checkpoint().consumers['source-state'] == 1


def test_filtered_pages_and_partial_read_pages_cannot_claim_global_coverage(store):
    journal = MemoryJournal()
    accepted(journal)
    accepted(journal, accepted_id='second')
    with pytest.raises(ValueError, match='unfiltered_page'):
        project_page(journal.read_page(run_id='run'))
    SourceStateIndex(store).advance(journal)
    first = store.read(('s',), stream_id=journal.stream_id, limit=1, view='history')
    assert first.truncated and not first.complete
    last = store.read(('s',), stream_id=journal.stream_id, limit=1, after=first.next_after, view='history')
    assert not last.truncated and not last.complete
    lag = store.read(('s',), stream_id=journal.stream_id, minimum_applied_through=100)
    assert not lag.complete


def test_sqlite_survives_restart_and_backup_after_journal_pruning(tmp_path):
    journal = MemoryJournal()
    accepted(journal, certificate_ids=('retained-certificate',))
    path = tmp_path / 'state.sqlite'
    backup = tmp_path / 'backup.sqlite'
    with SQLiteSourceState(path) as state:
        SourceStateIndex(state).advance(journal)
        state.export_checkpoint(backup)
    journal.prune(1)
    with SQLiteSourceState(backup) as restored:
        SourceStateIndex(restored).advance(journal)
        assert restored.has_validation_certificate('retained-certificate')
        assert restored.read(('s',), stream_id=journal.stream_id).complete
    with pytest.raises(ValueError, match='history_missing'):
        SourceStateIndex(MemorySourceState()).advance(journal)


def test_projection_capacity_failure_keeps_cursor_and_ack_unchanged(tmp_path):
    journal = MemoryJournal()
    accepted(journal, certificate_ids=('certificate',))
    with SQLiteSourceState(tmp_path / 'limited.sqlite', max_records=1) as state:
        with pytest.raises(ValueError, match='capacity_exhausted'):
            SourceStateIndex(state).advance(journal)
        assert state.checkpoint(journal.stream_id) is None
        assert not state.has_validation_certificate('certificate')
        assert journal.checkpoint().consumers['source-state'] == 0
