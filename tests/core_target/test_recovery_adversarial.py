"""Recovery preserves effect truth even without projected output acceptance."""
from contextlib import contextmanager
from dataclasses import replace
import json
from pathlib import Path

import pytest

from stratbox.core.commands._storage import _provider_scope
from stratbox.core.execution.service import EffectReceipt
from stratbox.core.execution.effect_state import FileEffectState
from stratbox.core.recovery import restore_recovery_artifacts, restore_recovery_package
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk.profile import LocalProfile, PersistentLimits
from stratbox.shared.data.materials import NamedEffectIntent
from stratbox.shared.data.values import ImmutableMaterialRef, SourceDataset, fingerprint, restore_tree
from stratbox.shared.identity import ByteIdentity


def _retention(profile, *, status='confirmed', data=b'accepted by storage before journal failure'):
    store = profile.providers['filestore']
    identity = ByteIdentity.of(data)
    location = str(Path('objects') / identity.sha256)
    scope = _provider_scope(store, location)
    effect_id = fingerprint(('storage.write', scope, location, identity))
    reference = ImmutableMaterialRef(location, identity, store.provider_id,
        effect_id=effect_id, provider_scope=scope)
    state = profile.providers['effect_state']
    receipt, _ = state.begin(EffectReceipt(effect_id, 'storage.write', 'unknown',
        resource=location, intent=reference))
    if status == 'confirmed':
        store.create_immutable(location, data)
        receipt = state.put(replace(receipt, status='confirmed', value=reference))
    return reference, receipt


def test_recovery_inventory_includes_confirmed_unprojected_receipt_bytes(tmp_path):
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        reference, _ = _retention(profile)
        assert profile.journal.checkpoint().tail == 0
        assert not tuple(profile.providers['source_state'].retained_references())
        manifest = profile.export_recovery(tmp_path / 'backup')
        assert manifest['dependencies'] == 1
        with (tmp_path / 'backup' / 'dependencies.jsonl').open() as stream:
            entries = [json.loads(line) for line in stream]
        assert len(entries) == 1 and restore_tree(entries[0]['reference']) == reference
        assert (tmp_path / 'backup' / entries[0]['path']).read_bytes() == b'accepted by storage before journal failure'


def test_unknown_destination_is_excluded_but_known_prerequisite_is_retained(tmp_path):
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        kept, _ = _retention(profile)
        unknown, _ = _retention(profile, status='unknown', data=b'never made available')
        intent = NamedEffectIntent('delete', 'scope', 'unknown-source', source='unknown-source',
            expected_source=ByteIdentity.of(b'original'), prerequisites=({'reference': kept},))
        profile.providers['effect_state'].begin(EffectReceipt('conditional-delete', 'storage.write',
            'unknown', resource='unknown-source', intent=intent))
        assert not (tmp_path / 'files' / unknown.location).exists()
        assert profile.export_recovery(tmp_path / 'backup')['dependencies'] == 1


def test_complete_export_rejects_missing_confirmed_unprojected_content(tmp_path):
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        reference, receipt = _retention(profile)
        (tmp_path / 'files' / reference.location).unlink()
        with pytest.raises((OSError, ValueError)):
            profile.export_recovery(tmp_path / 'backup')
        assert not (tmp_path / 'backup').exists()
        assert profile.providers['effect_state'].get(receipt.effect_id) == receipt


def test_profile_dataset_roles_share_its_owned_snapshot_store(tmp_path):
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        value = SourceDataset('fixture', ({'period': '2026-11', 'value': 1},))
        result = profile.box.invoke('command.dataset.ingest', inputs={'dataset': value, 'destination': 'series'})
        assert result.outcome == 'succeeded', result.diagnostics
        queried = profile.box.invoke('command.dataset.query', inputs={'reference': result.output('reference')})
        assert queried.outcome == 'succeeded', queried.diagnostics
        assert queried.output('observations') == value
        assert profile.providers['dataset_reader'] is profile.providers['dataset_writer'] is profile.providers['datasets']


def test_profile_reconciliation_can_release_full_unknown_reservation(tmp_path):
    limits = PersistentLimits(effects={'max_receipt_bytes': 4000, 'max_hot_bytes': 4000})
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files', limits=limits) as profile:
        reference, receipt = _retention(profile, status='unknown', data=b'completed before lost acknowledgement')
        profile.providers['filestore'].create_immutable(reference.location, b'completed before lost acknowledgement')
        assert profile.providers['effect_state'].usage()['effective_hot_bytes'] == 4000
        result = profile.box.invoke('command.artifact.reconcile', inputs={'effect': receipt})
        assert result.outcome == 'succeeded', result.diagnostics
        assert result.output('assessment').complete
        assert profile.providers['effect_state'].usage()['reserved_bytes'] == 0


def _close_restored(restored):
    if restored is not None:
        restored['providers']['source_state'].close()
        restored['journal'].close()


def test_one_package_cannot_transfer_the_same_journal_namespace_to_two_live_owners(tmp_path):
    package = tmp_path / 'backup'
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        profile.export_recovery(package)
    first = second = None
    try:
        first = restore_recovery_package(package, tmp_path / 'first-restore')
        first['journal'].append(kind='first.owner', run_id='first')
        with pytest.raises((OSError, ValueError), match='owner|transfer|writer'):
            second = restore_recovery_package(package, tmp_path / 'second-restore')
        assert not (tmp_path / 'second-restore' / 'recovery.json').exists()
    finally:
        _close_restored(second)
        _close_restored(first)


def test_interrupted_transfer_resumes_only_the_same_destination(tmp_path, monkeypatch):
    from stratbox.core.observability.journal import stream as journal_module
    package, destination = tmp_path / 'backup', tmp_path / 'restored'
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        profile.export_recovery(package)
    original = journal_module._atomic_json
    failed = False
    def interrupted(path, value):
        nonlocal failed
        if Path(path).name == 'recovery.json' and not failed:
            failed = True
            raise OSError('Injected interruption after original writer retirement')
        return original(path, value)
    monkeypatch.setattr(journal_module, '_atomic_json', interrupted)
    with pytest.raises(OSError, match='Injected interruption'):
        restore_recovery_package(package, destination)
    assert (destination / 'restore-in-progress.json').exists()
    restored = None
    try:
        restored = restore_recovery_package(package, destination)
        assert not (destination / 'restore-in-progress.json').exists()
        restored['journal'].append(kind='restored.owner', run_id='restored')
    finally:
        _close_restored(restored)


def test_export_detects_concurrent_intent_enrichment_with_unchanged_receipt_counts(tmp_path, monkeypatch):
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        state = profile.providers['effect_state']
        current, _ = state.begin(EffectReceipt('concurrent', 'test.write', 'unknown', intent={'id': 'same'}))
        before = state.recovery_metadata()
        original = state.export_checkpoint
        def concurrent(destination, **kwargs):
            result = original(destination, **kwargs)
            state.put(replace(current, intent={**current.intent, 'observation': 'new'}))
            return result
        monkeypatch.setattr(state, 'export_checkpoint', concurrent)
        with pytest.raises(ValueError, match='owner_changed_during_export'):
            profile.export_recovery(tmp_path / 'backup')
        after = state.recovery_metadata()
        assert before['unknown_count'] == after['unknown_count'] == 1
        assert after['revision_sum'] > before['revision_sum']
        assert not (tmp_path / 'backup').exists()


def test_restored_artifact_receipt_keeps_admitted_evidence_and_a_new_occurrence(tmp_path):
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        reference, historical = _retention(profile)
        providers = {'filestore': profile.providers['filestore']}
        profile.export_recovery(tmp_path / 'backup')
        original_state = profile.providers['effect_state']
    path = tmp_path / 'files' / reference.location
    path.unlink()
    report = restore_recovery_artifacts(tmp_path / 'backup', providers=providers,
        state_directory=tmp_path / 'repair-ledger', occurrence_id='repair-one')
    ledger = FileEffectState(tmp_path / 'repair-ledger')
    summary, = ledger.page()
    repaired = ledger.get(summary['effect_id'])
    assert report['restored'] == 1 and repaired.effect_id != historical.effect_id
    assert repaired.evidence['evidence_identity'] == fingerprint(repaired.value)
    assert repaired.evidence['effect_id'] == repaired.effect_id
    assert original_state.get(historical.effect_id) == historical
    path.unlink()
    with pytest.raises(ValueError, match='new_restore_occurrence_required'):
        restore_recovery_artifacts(tmp_path / 'backup', providers=providers,
            state_directory=tmp_path / 'repair-ledger', occurrence_id='repair-one')
    assert ledger.get(repaired.effect_id) == repaired


def test_malformed_restore_commit_acknowledgement_stays_unknown(tmp_path):
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        reference, _ = _retention(profile)
        profile.export_recovery(tmp_path / 'backup')
    (tmp_path / 'files' / reference.location).unlink()
    class Malformed(LocalFileStore):
        @contextmanager
        def stage_write(self, location):
            with super().stage_write(location) as stage:
                class Wrapped:
                    stream = stage.stream
                    def commit(self, mode, revision):
                        stage.commit(mode, revision)
                        return 'created'
                yield Wrapped()
    with pytest.raises((TypeError, ValueError), match='protocol|commit|acknowledgement'):
        restore_recovery_artifacts(tmp_path / 'backup', providers={'filestore': Malformed(tmp_path / 'files')},
            state_directory=tmp_path / 'repair-ledger', occurrence_id='repair-one')
    ledger = FileEffectState(tmp_path / 'repair-ledger')
    summary, = ledger.page()
    assert ledger.get(summary['effect_id']).status == 'unknown'


def test_restore_preserves_exact_post_cut_tail_and_replays_projection(tmp_path):
    from stratbox.core.observability.projections.source_state import SourceStateIndex
    from stratbox.shared.data.processing import SourceStateKey
    package, limits = tmp_path / 'backup', PersistentLimits(journal={'segment_size': 3})
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files', limits=limits) as profile:
        for number in range(1, 3):
            profile.journal.append(kind='source.observed', run_id=str(number), data={
                'source_id': 'fixture', 'evidence_identity': str(number), 'comparison_scope': 'fixture'})
        manifest = profile.export_recovery(package)
        assert manifest['owners']['journal']['checkpoint']['tail'] == 2
        for number in range(3, 9):
            profile.journal.append(kind='source.observed', run_id=str(number), data={
                'source_id': 'fixture', 'evidence_identity': str(number), 'comparison_scope': 'fixture'})
        SourceStateIndex(profile.providers['source_state']).advance(profile.journal)
        expected = profile.journal.read()
        assert profile.providers['source_state'].checkpoint(profile.journal.stream_id).applied_through == 8
    restored = None
    try:
        restored = restore_recovery_package(package, tmp_path / 'restored')
        journal, state = restored['journal'], restored['providers']['source_state']
        assert restored['manifest']['owners']['journal']['checkpoint']['tail'] == 2
        assert restored['recovery']['recovered_tail'] == 8
        assert journal.read() == expected
        assert state.checkpoint(journal.stream_id).applied_through == 8
        current = state.read((SourceStateKey('fixture'),), stream_id=journal.stream_id)
        assert current.observations[-1].evidence_identity == '8'
        journal.append(kind='after.transfer', run_id='new')
        assert journal.read()[-1].sequence == 9
    finally:
        _close_restored(restored)


@pytest.mark.parametrize('damage', ('expired', 'diverged', 'missing'))
def test_restore_rejects_unrecoverable_original_suffix_before_writer_transfer(tmp_path, damage):
    from stratbox.core.observability.projections.source_state import SourceStateIndex
    package = tmp_path / 'backup'
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files',
                      limits=PersistentLimits(journal={'segment_size': 2})) as profile:
        for number in range(2):
            profile.journal.append(kind='fixture', run_id=str(number))
        profile.export_recovery(package)
        for number in range(2, 6):
            profile.journal.append(kind='fixture', run_id=str(number))
        if damage == 'expired':
            SourceStateIndex(profile.providers['source_state']).advance(profile.journal)
            profile.journal.archive(through=6)
            profile.journal.prune(through=6)
        original = profile.journal.directory
    if damage == 'diverged':
        segment = original / 'facts-000000000000.jsonl'
        records = [json.loads(line) for line in segment.read_text().splitlines()]
        records[0]['kind'] = 'forked-history'
        segment.write_text(''.join(json.dumps(record) + '\n' for record in records))
    elif damage == 'missing':
        (original / 'facts-000000000002.jsonl').unlink()
    restored = None
    try:
        with pytest.raises(ValueError, match='expired|diverged|gap|missing|behind'):
            restored = restore_recovery_package(package, tmp_path / 'restored')
        assert not (original / 'writer-closed.json').exists()
        assert not (tmp_path / 'restored' / 'recovery.json').exists()
    finally:
        _close_restored(restored)


@pytest.mark.parametrize('journal_acceptance', (False, True))
def test_restore_imports_post_cut_retained_effect_authority_and_usable_bytes(tmp_path, journal_acceptance):
    from stratbox.sdk import StrategyBox
    from stratbox.shared.data.values import Material
    package = tmp_path / 'backup'
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        profile.export_recovery(package)
        if journal_acceptance:
            with profile.box.invoke('command.artifact.commit', inputs={'material': Material(b'post-cut retained',
                    source_id='fixture'), 'destination': 'objects'}) as result:
                assert result.outcome == 'succeeded', result.diagnostics
                reference = result.output('reference')
                receipt = profile.providers['effect_state'].get(reference.effect_id)
        else:
            reference, receipt = _retention(profile, data=b'post-cut retained')
        providers = {'filestore': profile.providers['filestore']}
    restored = None
    try:
        restored = restore_recovery_package(package, tmp_path / 'restored', providers=providers)
        ledger = restored['providers']['effect_state']
        assert ledger.get(reference.effect_id) == receipt
        assert ledger.recovery_metadata()['namespace_state'] == 'closed'
        assert restored['recovery']['effect_authority'] == 'surviving_original'
        with StrategyBox(providers=restored['providers'], journal=restored['journal']) as box:
            with box.invoke('command.material.inspect', inputs={'material': reference}) as result:
                assert result.outcome == 'succeeded', result.diagnostics
    finally:
        _close_restored(restored)


def test_restore_rejects_post_cut_retained_reference_without_receipt_authority(tmp_path):
    from stratbox.shared.data.values import Material
    package = tmp_path / 'backup'
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        profile.export_recovery(package)
        with profile.box.invoke('command.artifact.commit', inputs={'material': Material(b'post-cut',
                source_id='fixture'), 'destination': 'objects'}) as result:
            assert result.outcome == 'succeeded', result.diagnostics
        providers = {'filestore': profile.providers['filestore']}
    (tmp_path / 'profile' / 'effects' / 'effects.sqlite').unlink()
    restored = None
    try:
        with pytest.raises(ValueError, match='retained_effect_authority_missing'):
            restored = restore_recovery_package(package, tmp_path / 'restored', providers=providers)
        assert not (tmp_path / 'profile' / 'journal' / 'writer-closed.json').exists()
    finally:
        _close_restored(restored)


def test_restored_post_cut_snapshot_uses_the_verified_dataset_roles(tmp_path):
    from stratbox.sdk import StrategyBox
    package = tmp_path / 'backup'
    dataset = SourceDataset('fixture', ({'key': 'a', 'value': 7},), {'grain': ('key',)})
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        profile.export_recovery(package)
        with profile.box.invoke('command.dataset.ingest', inputs={'dataset': dataset, 'destination': 'series'}) as result:
            assert result.outcome == 'succeeded', result.diagnostics
            reference = result.output('reference')
        providers = {'datasets': profile.providers['datasets']}
    restored = None
    try:
        restored = restore_recovery_package(package, tmp_path / 'restored', providers=providers)
        assert restored['providers']['dataset_reader'] is providers['datasets']
        assert restored['providers']['dataset_writer'] is providers['datasets']
        with StrategyBox(providers=restored['providers'], journal=restored['journal']) as box:
            with box.invoke('command.dataset.query', inputs={'reference': reference}) as result:
                assert result.outcome == 'succeeded', result.diagnostics
                assert result.output('observations') == dataset
    finally:
        _close_restored(restored)


def test_successful_restore_removes_temporary_authority_checkpoints(tmp_path, monkeypatch):
    from stratbox.core.recovery import packages
    package = tmp_path / 'backup'
    with LocalProfile(tmp_path / 'profile', artifact_root=tmp_path / 'files') as profile:
        profile.export_recovery(package)
    temporary_directory, locations = packages.tempfile.TemporaryDirectory, []
    def capture(*args, **kwargs):
        directory = temporary_directory(*args, **kwargs)
        locations.append(Path(directory.name))
        return directory
    monkeypatch.setattr(packages.tempfile, 'TemporaryDirectory', capture)
    restored = None
    try:
        restored = restore_recovery_package(package, tmp_path / 'restored')
        assert any(path.name.startswith('stratbox-effect-authority-') for path in locations)
        assert any(path.name.startswith('stratbox-notification-authority-') for path in locations)
        assert all(not path.exists() for path in locations)
    finally:
        _close_restored(restored)
