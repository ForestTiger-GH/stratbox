"""The ordinary SDK route supplies reusable semantic-state journal evidence."""
from dataclasses import replace
from datetime import datetime, timezone

from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.core.observability.journal.stream import MemoryJournal
from stratbox.core.observability.projections.source_state import SourceStateIndex
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.storage.source_state import SQLiteSourceState
from stratbox.sdk import StrategyBox
from stratbox.shared.data.history import make_validation_certificate
from stratbox.shared.data.processing import (ProcessingGoal, ProcessingRequirement, ProcessingPolicy,
    ReferenceAvailability, retained_reference_identity)
from stratbox.shared.data.values import SourceDataset, fingerprint


def test_sdk_retention_journal_lookup_and_pure_work_assessment(tmp_path):
    journal = MemoryJournal()
    with SQLiteSourceState(tmp_path / 'state.sqlite') as state:
        providers = {'filestore': LocalFileStore(str(tmp_path / 'objects')), 'source_state': state}
        with StrategyBox(domains=DomainCatalog({}), journal=journal, providers=providers) as box:
            dataset = SourceDataset('test', ({'period': '2026-01-01', 'metric': 'm', 'value': 1},), issue_id='2026-01-01')
            desired_basis = box.processing_basis('command.observations.validate', inputs={'dataset': dataset})
            checked = box.invoke('command.observations.validate', inputs={'dataset': dataset})
            assert checked.outcome == 'succeeded', checked.diagnostics
            retained = box.invoke('operation.dataset.retain', inputs={'dataset': checked.output('dataset'), 'destination': 'datasets'})
            assert retained.outcome == 'succeeded', retained.diagnostics
            SourceStateIndex(state).advance(journal)
            current = box.invoke('command.source.state.read', inputs={'keys': ('test',), 'stream_id': journal.stream_id})
            assert current.outcome == 'succeeded', current.diagnostics
            snapshot = current.output('state')
            accepted = next(value for value in snapshot.outputs if value.stage == 'observations')
            assert accepted.persistent and accepted.restore_via == 'command.value.decode'
            assert accepted.processing_basis == desired_basis
            assert accepted.value_identity == fingerprint(checked.output('dataset'))
            instant = datetime.now(timezone.utc)
            # Availability is explicit evidence; the journal alone does not prove
            # that an external object is still present at the decision time.
            policy = ProcessingPolicy(availability=(ReferenceAvailability(
                retained_reference_identity(accepted.retained_reference), instant, 'available'),))
            decision = box.invoke('command.processing.assess', inputs={
                'goal': ProcessingGoal(accepted.key, (ProcessingRequirement('observations', fingerprint(desired_basis)),)),
                'state': snapshot, 'policy': policy, 'evaluation_time': instant})
            assert decision.outcome == 'succeeded', decision.diagnostics
            assert decision.output('assessment').no_work
            restored = box.invoke('command.material.read', inputs={'location': accepted.retained_reference})
            decoded = box.invoke('command.value.decode', inputs={'representation': restored.output('material')})
            assert decoded.output('value').rows == dataset.rows


def test_generic_validator_cannot_launder_a_constructed_domain_certificate():
    dataset = SourceDataset('test', ({'period': '2026-01-01', 'metric': 'm', 'value': 1},))
    certificate = make_validation_certificate(dataset, rule_id='publisher.verified', method_identity='claimed', build_identity='claimed')
    supplied = replace(dataset, validation_certificates=(certificate,))
    with StrategyBox(domains=DomainCatalog({})) as box:
        result = box.invoke('command.observations.validate', inputs={'dataset': supplied})
        assert result.outcome == 'failed'
        assert any('validation.history_evidence_unverified' in finding for finding in result.diagnostics)
