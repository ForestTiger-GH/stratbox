"""Bounded source-state projection storage; effects retain their own authority."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Protocol

from stratbox.shared.data.journal import JournalPage
from stratbox.shared.data.processing import SourceStateKey, StateProjectionCheckpoint
from stratbox.shared.data.values import canonical_tree, restore_tree, fingerprint


class SourceStateStore(Protocol):
    def checkpoint(self, stream_id: str) -> StateProjectionCheckpoint | None: ...
    def apply_page(self, page: JournalPage, records: tuple, authority: tuple, retention_links: tuple): ...
    def read(self, keys, *, stream_id: str, minimum_applied_through=0, limit=1000, after=None, view='current'): ...
    def has_validation_certificate(self, identity: str) -> bool: ...
    def has_source_use(self, identity: str) -> bool: ...
    def has_acquisition_evidence(self, identity: str) -> bool: ...


def normalize_keys(keys):
    keys = tuple(keys)
    if len(keys) > 1000:
        raise ValueError('source_state.key_limit')
    values = tuple(value if isinstance(value, SourceStateKey) else SourceStateKey(value) if isinstance(value, str)
                   else SourceStateKey(**value) if isinstance(value, Mapping) else None for value in keys)
    if any(value is None for value in values) or len(set(values)) != len(values):
        raise ValueError('source_state.keys_invalid')
    return values


def matches(pattern, key):
    return (pattern.source_id == key.source_id and (pattern.issue_id is None or pattern.issue_id == key.issue_id)
            and (pattern.asset_id is None or pattern.asset_id == key.asset_id))


def validate_page(page, checkpoint):
    if not isinstance(page, JournalPage) or page.filters:
        raise ValueError('source_state.unfiltered_page_required')
    if checkpoint is None:
        if page.after != 0 or page.retained_after != 0:
            raise ValueError('source_state.history_missing')
        applied = 0
    else:
        if page.stream_id != checkpoint.stream_id:
            raise ValueError('source_state.stream_conflict')
        applied = checkpoint.applied_through
        if page.after > applied:
            raise ValueError('source_state.coverage_gap')
    return applied


def next_checkpoint(page, previous):
    applied = max(page.scanned_through, previous.applied_through if previous else 0)
    return StateProjectionCheckpoint(page.stream_id, applied, page.retained_after,
        max(page.tail, previous.observed_tail if previous else 0), previous.coverage_complete if previous else True)


def record_id(value):
    from stratbox.shared.data.processing import SourceObservation
    if isinstance(value, SourceObservation):
        return fingerprint(('source_observation', value.key, value.observation_id, value.evidence_identity))
    return fingerprint((type(value).__name__, value.sequence, value.key,
                        getattr(value, 'accepted_value_id', getattr(value, 'observation_id', None))))


def current_key(value):
    """Physical revisions and effective rules differ; poll occurrence does not."""
    from stratbox.shared.data.processing import SourceObservation
    if isinstance(value, SourceObservation):
        return fingerprint(('observation', value.key))
    materials = tuple(sorted({fingerprint(use.coordinate) for use in value.source_uses
                              if getattr(use.coordinate, 'material_identity', None) is not None}))
    return fingerprint(('output', value.key, value.stage, value.output_name, materials, value.processing_basis, value.selection_identity,
                        value.destination_identity, value.represents_value_identity))


def current_order(value):
    return (getattr(value, 'observed_at', getattr(value, 'accepted_at', None)), value.sequence)


def detached(value):
    return restore_tree(canonical_tree(value))


def linked_output(value, links, representations=()):
    reference = links.get(getattr(value, 'accepted_value_id', None))
    restore_via = value.restore_via
    if reference is None and value.retained_reference is None:
        for representation in sorted(representations, key=lambda item: item.sequence, reverse=True):
            if representation.represents_value_identity != value.value_identity:
                continue
            reference = representation.retained_reference or links.get(representation.accepted_value_id)
            if reference is not None:
                from stratbox.shared.data.values import SnapshotRef
                restore_via = 'command.dataset.query' if isinstance(reference, SnapshotRef) else 'command.value.decode'
                break
    if reference is None:
        return value
    return replace(value, retained_reference=reference, persistent=True, restore_via=restore_via,
        effect_ids=tuple(dict.fromkeys((*value.effect_ids, *((reference.effect_id,) if getattr(reference, 'effect_id', None) else ())))))
