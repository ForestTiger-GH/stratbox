"""Source novelty and requested completion have independent work decisions."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from stratbox.core.commands.processing import assess_processing
from stratbox.shared.data.processing import (SourceStateKey, SourceObservation, RetainedOutput,
    StateProjectionCheckpoint, SourceStateSnapshot, ProcessingRequirement, ProcessingGoal, ProcessingBasis,
    ReferenceAvailability, ProcessingPolicy, retained_reference_identity)
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.values import Assessment, ByteIdentity, ImmutableMaterialRef


NOW = datetime(2026, 1, 10, tzinfo=timezone.utc)
KEY = SourceStateKey('s', '2026-01-01', 'main')
BYTES = ByteIdentity.of(b'original')
USE = SourceUse(SourceCoordinate('s', issue_id='2026-01-01', asset_id='main', material_identity=BYTES), 'source', 'verified')
OBS = SourceObservation(KEY, 'observation', NOW, 'bytes', 'evidence', BYTES)


def output(stage, *, basis=('inputs', 'rules', 'build'), source=KEY):
    reference = ImmutableMaterialRef('objects/' + stage, ByteIdentity.of(stage.encode()), provider_scope='test')
    return RetainedOutput(source, 'accepted-' + stage, 'value-' + stage, stage, 'command.test', basis,
                          NOW, 1, reference, True, Assessment(), source_uses=(USE,))


def state(*outputs):
    return SourceStateSnapshot((KEY,), StateProjectionCheckpoint('stream', 10, observed_tail=10), tuple(outputs), (OBS,))


def available(*outputs, **changes):
    return ProcessingPolicy(availability=tuple(ReferenceAvailability(retained_reference_identity(value.retained_reference), NOW, 'available')
                                               for value in outputs), **changes)


def test_same_bytes_with_completed_requested_stage_is_no_work_only_with_availability():
    dataset = output('observations')
    goal = ProcessingGoal(KEY, (ProcessingRequirement('observations', dataset.basis_identity),))
    pending = assess_processing(goal, OBS, state(dataset), ProcessingBasis(), ProcessingPolicy(), evaluation_time=NOW)
    assert pending.decisions[0].action == 'verify'
    result = assess_processing(goal, OBS, state(dataset), ProcessingBasis(), available(dataset), evaluation_time=NOW)
    assert result.no_work and result.decisions[0].entrance == dataset.retained_reference
    assert result.identity == assess_processing(goal, OBS, state(dataset), ProcessingBasis(), available(dataset), evaluation_time=NOW).identity


def test_observation_unchanged_does_not_complete_missing_product():
    dataset = output('observations')
    goal = ProcessingGoal(KEY, (ProcessingRequirement('representation', 'new-render-basis'),))
    result = assess_processing(goal, OBS, state(dataset), ProcessingBasis({'observations': dataset.basis_identity}),
                               available(dataset), evaluation_time=NOW)
    assert result.decisions[0].action == 'render' and result.decisions[0].entrance == dataset.retained_reference


def test_changed_rules_reuse_original_without_claiming_old_interpretation():
    original, old = output('original'), output('observations')
    goal = ProcessingGoal(KEY, (ProcessingRequirement('observations', 'new-rules'),))
    result = assess_processing(goal, OBS, state(original, old), ProcessingBasis({'original': original.basis_identity}),
                               available(original, old), evaluation_time=NOW)
    assert result.decisions[0].action == 'interpret' and result.decisions[0].entrance == original.retained_reference


def test_same_bytes_another_issue_is_not_semantic_reuse():
    previous = output('observations', source=replace(KEY, issue_id='2025-12-01'))
    goal = ProcessingGoal(KEY, (ProcessingRequirement('observations', previous.basis_identity),))
    result = assess_processing(goal, OBS, state(previous), ProcessingBasis(), available(previous), evaluation_time=NOW)
    assert not result.no_work and result.decisions[0].action == 'acquire'


def test_unknown_effect_and_lagging_projection_precede_more_processing():
    product = output('representation')
    goal = ProcessingGoal(KEY, (ProcessingRequirement('representation', product.basis_identity),))
    result = assess_processing(goal, OBS, state(product), ProcessingBasis(), available(product, unknown_effect_ids=('write',)), evaluation_time=NOW)
    assert result.decisions[0].action == 'reconcile'
    lagging = replace(state(product), minimum_applied_through=11)
    result = assess_processing(goal, OBS, lagging, ProcessingBasis(), available(product), evaluation_time=NOW)
    assert result.decisions[0].action == 'index_catch_up'


def test_raw_retention_requires_admission_and_ephemeral_events_are_not_restart_entrances():
    raw = output('raw')
    goal = ProcessingGoal(KEY, (ProcessingRequirement('original', 'current-admission'),))
    result = assess_processing(goal, OBS, state(raw), ProcessingBasis(), available(raw), evaluation_time=NOW)
    assert result.decisions[0].action == 'identify' and result.decisions[0].entrance == raw.retained_reference
    ephemeral = replace(output('observations'), persistent=False, retained_reference=None)
    goal = ProcessingGoal(KEY, (ProcessingRequirement('observations', ephemeral.basis_identity),))
    assert not assess_processing(goal, OBS, state(ephemeral), ProcessingBasis(), ProcessingPolicy(), evaluation_time=NOW).no_work


def test_freshness_uses_explicit_time_and_missing_basis_never_implies_rule_equality():
    dataset = output('observations')
    goal = ProcessingGoal(KEY, (ProcessingRequirement('observations'),))
    result = assess_processing(goal, OBS, state(dataset), ProcessingBasis(), available(dataset), evaluation_time=NOW)
    assert not result.no_work
    goal = ProcessingGoal(KEY, (ProcessingRequirement('observations', dataset.basis_identity),))
    result = assess_processing(goal, OBS, state(dataset), ProcessingBasis(), available(dataset, max_observation_age_seconds=60),
                               evaluation_time=NOW + timedelta(hours=1))
    assert result.decisions[0].action == 'observe'
    with pytest.raises(ValueError, match='aware_time_required'):
        assess_processing(goal, OBS, state(dataset), ProcessingBasis(), ProcessingPolicy(), evaluation_time=datetime(2026, 1, 10))


def test_csv_and_required_evidence_are_separate_completion_obligations():
    csv = replace(output('representation'), output_name='csv')
    goal = ProcessingGoal(KEY, (
        ProcessingRequirement('representation', csv.basis_identity, output_name='csv'),
        ProcessingRequirement('representation', csv.basis_identity, output_name='evidence')))
    result = assess_processing(goal, OBS, state(csv), ProcessingBasis(), available(csv), evaluation_time=NOW)
    assert not result.no_work
    assert [(item.output_name, item.action) for item in result.decisions] == [('csv', 'reuse'), ('evidence', 'acquire')]
