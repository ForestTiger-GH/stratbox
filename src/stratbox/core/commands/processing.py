"""Explicit mutable lookup and a separate pure processing assessment."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields

from stratbox.shared.data.processing import (ProcessingGoal, ProcessingBasis, ProcessingPolicy,
    ProcessingDecision, ProcessingAssessment, SourceStateSnapshot, SourceObservation,
    retained_reference_identity, utc_instant)
from stratbox.core.storage.source_state.ports import matches
from ._settings import _option


_ACTION = {'raw': 'acquire', 'inspection': 'inspect', 'original': 'identify', 'physical': 'extract',
           'tables': 'extract', 'observations': 'interpret', 'calculation': 'calculate', 'view': 'prepare',
           'representation': 'render', 'archive': 'pack', 'retained': 'retain', 'delivery': 'materialize'}
_ANCESTORS = {
    'raw': (), 'inspection': ('raw',), 'original': ('raw',), 'physical': ('original', 'raw'),
    'tables': ('physical', 'original'), 'observations': ('tables', 'physical', 'original'),
    'calculation': ('observations',), 'view': ('calculation', 'observations'),
    'representation': ('view', 'calculation', 'observations'), 'archive': ('original', 'representation'),
    'retained': ('representation', 'archive', 'original'), 'delivery': ('archive', 'representation', 'original'),
}
_BYTE_ONLY_STAGES = {'raw', 'retained', 'delivery'}


def _typed(value, cls):
    if isinstance(value, cls):
        return value
    if isinstance(value, Mapping) and not set(value) - {field.name for field in fields(cls)}:
        return cls(**value)
    raise ValueError('processing.typed_' + cls.__name__ + '_required')


def _material_matches(output, identity):
    if identity is None:
        return True
    digest = getattr(identity, 'sha256', identity)
    candidates = set(output.processing_basis)
    for use in output.source_uses:
        material = getattr(getattr(use, 'coordinate', None), 'material_identity', None)
        if material is not None:
            candidates.add(material.sha256)
    material = getattr(output.retained_reference, 'identity', None)
    if hasattr(material, 'sha256'):
        candidates.add(material.sha256)
    return digest in candidates


def _qualified(output, *, allow_partial=False):
    if output.assessment is not None:
        return output.assessment.complete or allow_partial
    return output.stage in {'raw', 'representation', 'archive', 'retained', 'delivery'}


def assess_processing(goal, candidate, state, basis, policy, *, evaluation_time, observation_cutoff=None):
    """Return required finite actions; all clocks, evidence and policy are inputs."""
    goal, basis, policy = _typed(goal, ProcessingGoal), _typed(basis, ProcessingBasis), _typed(policy, ProcessingPolicy)
    if not isinstance(state, SourceStateSnapshot):
        raise ValueError('processing.state_snapshot_required')
    instant = utc_instant(evaluation_time)
    cutoff = utc_instant(observation_cutoff) if observation_cutoff is not None else instant
    if cutoff > instant:
        raise ValueError('processing.future_observation_cutoff')
    if candidate is not None and not isinstance(candidate, SourceObservation):
        raise ValueError('processing.source_observation_required')
    if candidate is not None and (not matches(goal.key, candidate.key) or candidate.observed_at > cutoff):
        raise ValueError('processing.observation_scope_conflict')
    if candidate is None:
        observed = [item for item in state.observations if matches(goal.key, item.key) and item.observed_at <= cutoff]
        candidate = max(observed, key=lambda item: (item.observed_at, item.observation_id)) if observed else None
    available = {}
    for value in policy.availability:
        if value.checked_at > instant:
            raise ValueError('processing.future_availability')
        previous = available.get(value.reference_identity)
        if previous is None or previous.checked_at < value.checked_at:
            available[value.reference_identity] = value
    def availability(reference=None, destination=None):
        key = destination if destination is not None else retained_reference_identity(reference)
        evidence = available.get(key)
        if evidence is None:
            return 'unknown'
        if policy.max_availability_age_seconds is not None and (instant - evidence.checked_at).total_seconds() > policy.max_availability_age_seconds:
            return 'unknown'
        return evidence.status
    original_identity = basis.input_identity or (candidate.material_identity if candidate else None)
    outputs = [value for value in state.outputs if matches(goal.key, value.key)]
    decisions = []
    for requirement in goal.requirements:
        wanted_basis = requirement.basis_identity or basis.stages.get(requirement.stage)
        def decision(action, reason, entrance=None, effects=(), restore_via=None):
            return ProcessingDecision(goal.key, requirement.stage, action, (reason,), wanted_basis, entrance, tuple(effects), restore_via,
                                      requirement.output_name)
        if policy.unknown_effect_ids:
            decisions.append(decision('reconcile', 'required_effect_uncertain', effects=policy.unknown_effect_ids))
            continue
        if not state.complete or not any(matches(key, goal.key) for key in state.keys):
            decisions.append(decision('index_catch_up', 'projection_coverage_insufficient'))
            continue
        if policy.max_observation_age_seconds is not None and (candidate is None or
                (instant - candidate.observed_at).total_seconds() > policy.max_observation_age_seconds):
            decisions.append(decision('observe', 'source_observation_stale'))
            continue
        eligible = [value for value in outputs if value.stage == requirement.stage
                    and (requirement.output_name is None or value.output_name == requirement.output_name)
                    and (wanted_basis is not None or requirement.stage in _BYTE_ONLY_STAGES)
                    and (wanted_basis is None or value.basis_identity == wanted_basis)
                    and (goal.selection_identity is None or value.selection_identity == goal.selection_identity)
                    and (requirement.destination_identity is None or value.destination_identity == requirement.destination_identity)
                    and _material_matches(value, original_identity)
                    and _qualified(value, allow_partial=requirement.allow_partial)]
        eligible.sort(key=lambda value: (value.accepted_at, value.sequence), reverse=True)
        if requirement.stage not in policy.force_stages:
            selected, uncertain = None, None
            for value in eligible:
                if value.stage == 'delivery':
                    status = availability(destination=requirement.destination_identity or value.destination_identity)
                    if not value.effect_ids or not set(value.effect_ids) <= set(policy.confirmed_effect_ids):
                        uncertain = value
                        continue
                elif value.retained_reference is not None and value.persistent:
                    status = availability(value.retained_reference)
                else:
                    continue  # Ephemeral events are diagnostics, never restored entrances.
                if status == 'available':
                    selected = value
                    break
                if status == 'unknown':
                    uncertain = value
            if selected is not None:
                decisions.append(decision('reuse', 'requested_result_fulfilled', selected.retained_reference, selected.effect_ids, selected.restore_via))
                continue
            if uncertain is not None:
                decisions.append(decision('verify', 'retained_result_availability_unproved', uncertain.retained_reference, uncertain.effect_ids))
                continue
        entrance, unverified, restoration = None, None, None
        for stage in _ANCESTORS[requirement.stage]:
            expected_basis = basis.stages.get(stage)
            ancestors = [value for value in outputs if value.stage == stage and value.persistent and value.retained_reference is not None
                         and (expected_basis is not None or stage in _BYTE_ONLY_STAGES)
                         and (expected_basis is None or value.basis_identity == expected_basis)
                         and _material_matches(value, original_identity)
                         and _qualified(value)]
            for value in sorted(ancestors, key=lambda value: (value.accepted_at, value.sequence), reverse=True):
                status = availability(value.retained_reference)
                if status == 'available':
                    entrance = value.retained_reference
                    restoration = value.restore_via
                    break
                if status == 'unknown':
                    unverified = value.retained_reference
            if entrance is not None:
                break
        if entrance is None and unverified is not None:
            decisions.append(decision('verify', 'upstream_retained_input_unverified', unverified))
        elif entrance is None and requirement.stage not in {'raw', 'delivery', 'retained'}:
            decisions.append(decision('acquire', 'required_admitted_input_missing'))
        else:
            reason = 'processing_basis_or_result_missing' if requirement.stage not in policy.force_stages else 'explicit_reprocessing_policy'
            decisions.append(decision(_ACTION[requirement.stage], reason, entrance, restore_via=restoration))
    return ProcessingAssessment(goal.identity, instant, tuple(decisions), state.checkpoint)


def source_state_read(inputs, settings, context):
    store = context.provider('source_state')
    keys = inputs.get('keys', _option(context, settings, 'keys'))
    stream_id = inputs.get('stream_id', _option(context, settings, 'stream_id'))
    if keys is None or not stream_id:
        raise ValueError('source_state.explicit_keys_and_stream_required')
    state = store.read(keys, stream_id=stream_id,
        minimum_applied_through=inputs.get('minimum_applied_through', _option(context, settings, 'minimum_applied_through', 0)),
        limit=_option(context, settings, 'limit', 1000), after=inputs.get('after'), view=_option(context, settings, 'view', 'current'))
    return {'state': state, 'checkpoint': state.checkpoint}


def processing_assess(inputs, settings, context):
    if 'evaluation_time' not in inputs:
        raise ValueError('processing.evaluation_time_required')
    result = assess_processing(inputs['goal'], inputs.get('candidate'), inputs['state'],
        inputs.get('basis', ProcessingBasis()), inputs.get('policy', ProcessingPolicy()),
        evaluation_time=inputs['evaluation_time'], observation_cutoff=inputs.get('observation_cutoff'))
    return {'assessment': result, 'decisions': result.decisions}
