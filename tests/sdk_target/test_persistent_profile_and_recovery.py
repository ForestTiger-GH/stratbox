"""Owned local operation, scoped preflight and a cross-owner restored cut."""
from dataclasses import replace
from pathlib import Path

import pytest

from stratbox.capabilities.catalog import Catalog
from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.capabilities.model import CommandDefinition, PortContract, MethodRef
from stratbox.capabilities.model.domains import DomainSpec, CalculationSpec, CommandSpec
from stratbox.core.execution.service import EffectReceipt
from stratbox.core.observability.journal.stream import FileJournal
from stratbox.core.recovery import validate_recovery_package, restore_recovery_package, restore_recovery_artifacts
from stratbox.sdk import StrategyBox, LocalProfile, PersistentLimits
from stratbox.shared.data.values import Material, SourceDataset


NUMBER = PortContract('test.number', int)


def echo(inputs, settings, context):
    return {'value': inputs['value']}


def definition(**kwargs):
    return CommandDefinition('command.test.echo', inputs={'value': NUMBER}, outputs={'value': NUMBER},
                             method=MethodRef(__name__ + ':echo'), **kwargs)


def test_preflight_uses_actual_provider_binding_without_starting_a_session():
    command = definition(required_providers=frozenset({'test.provider'}))
    with StrategyBox(catalog=Catalog({command.id: command}), domains=DomainCatalog({})) as box:
        report = box.preflight(command.id, inputs={'value': 3})
        assert not report.admissible and report.status == 'blocked'
        assert any(check.code == 'provider.missing:test.provider' for check in report.checks)
        assert box._session is None
    with StrategyBox(catalog=Catalog({command.id: command}), domains=DomainCatalog({}),
                     providers={'test.provider': object()}) as box:
        report = box.preflight(command.id, inputs={'value': 3})
        assert report.admissible and report.status == 'conditional'
        assert report.plan_identity and report.build_identity
        assert any(check.phase == 'acceptance' and check.status == 'deferred' for check in report.checks)


def test_scientific_limitation_is_derived_from_selected_domain_record():
    command = definition()
    record = CalculationSpec('test.unreviewed', {command.id: CommandSpec(command.method)},
        semantics={'readiness': 'requires_publisher_financial_model', 'available': 'published_field_observations'})
    domains = DomainCatalog({'test': DomainSpec('test', {}, {}, {record.id: record})})
    with StrategyBox(catalog=Catalog({command.id: command}), domains=domains) as box:
        report = box.preflight(command.id, inputs={'value': 3}, target=record.id)
        assert not report.admissible
        assert any(check.code == 'requires_publisher_financial_model' for check in report.checks)
        with box.invoke(command.id, inputs={'value': 3}, target=record.id) as result:
            assert result.outcome == 'failed'
            assert any('scientific.binding_unavailable' in str(item) for item in result.diagnostics)
        available = box.preflight(command.id, inputs={'value': 3})
        assert available.admissible


def test_preflight_recognizes_the_executions_default_notification_state():
    from stratbox.core.observability.journal.stream import MemoryJournal
    journal = MemoryJournal()
    journal.append(kind='example', run_id='default-state')
    page = journal.read_page()
    with StrategyBox() as box:
        report = box.preflight('command.notification.prepare', inputs={'facts': page})
        assert report.admissible and box._session is None
        assert any(check.code == 'readiness.default_notification_state' for check in report.checks)
        with box.invoke('command.notification.prepare', inputs={'facts': page}) as result:
            assert result.outcome == 'succeeded', result.diagnostics


def test_profile_excludes_another_coordinator_and_owns_dataset_aliases(tmp_path):
    with LocalProfile(tmp_path / 'live', artifact_root=tmp_path / 'artifacts') as profile:
        with pytest.raises(OSError):
            LocalProfile(tmp_path / 'live', artifact_root=tmp_path / 'artifacts')
        assert profile.providers['dataset_reader'] is profile.providers['dataset_writer'] is profile.providers['datasets']
        dataset = SourceDataset('example', ({'key': 'a', 'value': 1},), {'grain': ('key',)})
        result = profile.box.invoke('command.dataset.ingest', inputs={'dataset': dataset, 'destination': 'observations'})
        assert result.outcome == 'succeeded', result.diagnostics
        reference = result.output('reference')
        result.close()
        result = profile.box.invoke('command.dataset.query', inputs={'reference': reference})
        assert result.outcome == 'succeeded', result.diagnostics
        assert result.output('observations').rows == dataset.rows
        result.close()


def test_cross_owner_restore_fences_prior_namespace_and_transfers_journal_writer(tmp_path):
    live, artifact_root, package = tmp_path / 'live', tmp_path / 'artifacts', tmp_path / 'package'
    with LocalProfile(live, artifact_root=artifact_root) as profile:
        original_journal = profile.journal.directory
        original_stream = profile.journal.stream_id
        effects = profile.providers['effect_state']
        claim, _ = effects.begin(EffectReceipt('unresolved-before-cut', 'test.effect', 'unknown', intent={'value': 1}))
        manifest = profile.export_recovery(package)
        assert manifest['owners']['effect_state']['unknown_count'] == 1
        assert validate_recovery_package(package)['package_id'] == manifest['package_id']
        with pytest.raises(OSError):
            restore_recovery_package(package, tmp_path / 'blocked')
    restored = restore_recovery_package(package, tmp_path / 'restored')
    try:
        ledger = restored['providers']['effect_state']
        assert ledger.get('unresolved-before-cut').status == 'unknown'
        with pytest.raises(ValueError, match='recovery_namespace_closed'):
            ledger.begin(EffectReceipt('possibly-occurred-after-backup', 'test.effect', 'unknown', intent={'value': 2}))
        assert restored['journal'].stream_id == original_stream
        ledger.put(replace(ledger.get('unresolved-before-cut'), status='confirmed', value={'verified': True}))
        assert ledger.get('unresolved-before-cut').status == 'confirmed'
        with FileJournal(original_journal) as old:
            with pytest.raises(RuntimeError, match='writer_namespace_closed'):
                old.append(kind='forbidden', run_id='old')
        restored['journal'].append(kind='recovery.verified', run_id='new')
    finally:
        restored['providers']['source_state'].close()
        restored['journal'].close()


def test_lost_immutable_dependency_is_restored_as_a_new_explicit_occurrence(tmp_path):
    package = tmp_path / 'package'
    with LocalProfile(tmp_path / 'live', artifact_root=tmp_path / 'artifacts') as profile:
        result = profile.box.invoke('command.artifact.commit',
            inputs={'material': Material(b'exact retained bytes', source_id='example'), 'destination': 'objects'})
        assert result.outcome == 'succeeded', result.diagnostics
        reference = result.output('reference')
        result.close()
        providers = {'filestore': profile.providers['filestore'], 'datasets': profile.providers['datasets']}
        profile.export_recovery(package)
    physical = tmp_path / 'artifacts' / reference.location
    physical.unlink()
    with pytest.raises(FileNotFoundError):
        restore_recovery_package(package, tmp_path / 'not-ready', providers=providers)
    recovered = restore_recovery_artifacts(package, providers=providers,
        state_directory=tmp_path / 'restoration-ledger', occurrence_id='approved-recovery-1')
    assert recovered['restored'] == 1 and physical.read_bytes() == b'exact retained bytes'
    again = restore_recovery_artifacts(package, providers=providers,
        state_directory=tmp_path / 'restoration-ledger', occurrence_id='approved-recovery-1')
    assert again['already_present'] == 1
    restored = restore_recovery_package(package, tmp_path / 'restored', providers=providers)
    try:
        assert restored['providers']['effect_state'].get(reference.effect_id).status == 'confirmed'
        with StrategyBox(providers=restored['providers'], journal=restored['journal']) as box:
            assert box.session.lookup_effect(reference.effect_id).value.identity == reference.identity
    finally:
        restored['providers']['source_state'].close()
        restored['journal'].close()


def test_package_hashes_reject_a_corrupted_owner_before_restore(tmp_path):
    package = tmp_path / 'package'
    with LocalProfile(tmp_path / 'live', artifact_root=tmp_path / 'artifacts') as profile:
        profile.export_recovery(package)
    with (package / 'source-state.sqlite').open('ab') as stream:
        stream.write(b'corruption')
    with pytest.raises(ValueError, match='file_identity_conflict'):
        restore_recovery_package(package, tmp_path / 'restore')
    assert not (tmp_path / 'restore').exists()


def test_low_watermark_rejects_new_admission_without_poisoning_service(tmp_path):
    command = definition()
    limits = PersistentLimits(projection_reserve_records=1000000)
    with LocalProfile(tmp_path / 'live', artifact_root=tmp_path / 'artifacts', limits=limits,
                      catalog=Catalog({command.id: command}), domains=DomainCatalog({})) as profile:
        with pytest.raises(Exception, match='profile.projection_maintenance_required'):
            profile.box.invoke(command.id, inputs={'value': 1})
        assert profile.box.session.quiescent


def test_profile_reopens_after_projection_commits_before_journal_acknowledgement(tmp_path):
    live, artifacts = tmp_path / 'live', tmp_path / 'artifacts'
    with LocalProfile(live, artifact_root=artifacts) as profile:
        profile.journal.append(kind='example', run_id='committed')
        original_ack = profile.journal.acknowledge
        def lose_acknowledgement(consumer, page):
            profile.journal.acknowledge = original_ack
            raise OSError('lost acknowledgement')
        profile.journal.acknowledge = lose_acknowledgement
        with pytest.raises(OSError, match='lost acknowledgement'):
            profile.box.advance_source_state()
        assert profile.providers['source_state'].checkpoint(profile.journal.stream_id).applied_through == 1
        assert profile.journal.checkpoint().consumers['source-state'] == 0
    with LocalProfile(live, artifact_root=artifacts) as reopened:
        assert reopened.journal.checkpoint().consumers['source-state'] == 0
        checkpoint = reopened.box.advance_source_state()
        assert checkpoint.applied_through == 1
        assert reopened.journal.checkpoint().consumers['source-state'] == 1


def test_profile_rejects_acknowledgement_ahead_of_durable_projection(tmp_path):
    live, artifacts = tmp_path / 'live', tmp_path / 'artifacts'
    with LocalProfile(live, artifact_root=artifacts) as profile:
        profile.journal.append(kind='example', run_id='unprojected')
        profile.journal.acknowledge('source-state', profile.journal.read_page())
    with pytest.raises(ValueError, match='acknowledgement_ahead'):
        LocalProfile(live, artifact_root=artifacts)
