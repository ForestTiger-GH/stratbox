"""Bounded transactional in-memory projection for finite application sessions."""
from __future__ import annotations

import json
from threading import RLock

from stratbox.shared.data.values import canonical_tree
from stratbox.shared.data.processing import RetainedOutput, SourceObservation, SourceStateSnapshot, StateProjectionCheckpoint
from .ports import normalize_keys, matches, validate_page, next_checkpoint, record_id, current_key, current_order, detached, linked_output


class MemorySourceState:
    provider_id = 'source_state.memory'

    def __init__(self, *, max_records=100000, max_bytes=64 * 1024 * 1024):
        if type(max_records) is not int or max_records < 1 or type(max_bytes) is not int or max_bytes < 1:
            raise ValueError('source_state.limits_invalid')
        self.max_records, self.max_bytes = max_records, max_bytes
        self._checkpoints, self._records, self._authority, self._links, self._current = {}, {}, {}, {}, {}
        self._lock = RLock()

    def checkpoint(self, stream_id):
        with self._lock:
            return self._checkpoints.get(stream_id)

    def apply_page(self, page, records=(), authority=(), retention_links=()):
        with self._lock:
            previous = self._checkpoints.get(page.stream_id)
            applied = validate_page(page, previous)
            rows, authorities, links, current = dict(self._records), dict(self._authority), dict(self._links), dict(self._current)
            for value in records:
                if value.sequence <= applied:
                    continue
                if not page.after < value.sequence <= page.scanned_through:
                    raise ValueError('source_state.record_outside_page')
                rows[(page.stream_id, record_id(value))] = detached(value)
                pointer = (page.stream_id, current_key(value))
                previous_id = current.get(pointer)
                if previous_id is None or current_order(rows[(page.stream_id, previous_id)]) <= current_order(value):
                    current[pointer] = record_id(value)
            for kind, identity, sequence in authority:
                if sequence > applied:
                    if not page.after < sequence <= page.scanned_through or kind not in {'certificate', 'source_use', 'acquisition'}:
                        raise ValueError('source_state.authority_outside_page')
                    authorities[(page.stream_id, kind, identity)] = sequence
            for accepted_id, reference, sequence in retention_links:
                if sequence > applied:
                    links[(page.stream_id, accepted_id)] = detached(reference)
            if len(rows) + len(authorities) + len(links) > self.max_records:
                raise ValueError('source_state.capacity_exhausted')
            size = len(json.dumps(canonical_tree((tuple(rows.values()), tuple(authorities), tuple(links.values()))), separators=(',', ':')).encode())
            if size > self.max_bytes:
                raise ValueError('source_state.byte_capacity_exhausted')
            self._records, self._authority, self._links, self._current = rows, authorities, links, current
            checkpoint = next_checkpoint(page, previous)
            self._checkpoints[page.stream_id] = checkpoint
            return checkpoint

    def read(self, keys, *, stream_id, minimum_applied_through=0, limit=1000, after=None, view='current'):
        keys = normalize_keys(keys)
        if type(limit) is not int or not 1 <= limit <= 10000 or view not in {'current', 'history'}:
            raise ValueError('source_state.page_invalid')
        with self._lock:
            checkpoint = self._checkpoints.get(stream_id) or StateProjectionCheckpoint(stream_id, 0, coverage_complete=False)
            selected_ids = {key for (stream, _), key in self._current.items() if stream == stream_id} if view == 'current' else None
            entries = sorted(((value.sequence, key[1], value) for key, value in self._records.items()
                              if key[0] == stream_id and any(matches(pattern, value.key) for pattern in keys)
                              and (selected_ids is None or key[1] in selected_ids)
                              and (after is None or (value.sequence, key[1]) > tuple(after))), key=lambda row: row[:2])
            chosen, truncated = entries[:limit], len(entries) > limit
            links = {accepted: reference for (stream, accepted), reference in self._links.items() if stream == stream_id}
            representations = tuple(value for (stream, _), value in self._records.items() if stream == stream_id
                                    and isinstance(value, RetainedOutput) and value.represents_value_identity)
            equivalents = {}
            if view == 'current':
                for (stream, _), value in self._records.items():
                    if stream == stream_id and isinstance(value, RetainedOutput):
                        equivalents.setdefault(current_key(value), []).append(value)
            outputs = []
            for _, _, value in chosen:
                if not isinstance(value, RetainedOutput):
                    continue
                resolved = linked_output(value, links, representations)
                if view == 'current' and not resolved.persistent:
                    for candidate in sorted(equivalents.get(current_key(value), ()), key=current_order, reverse=True):
                        retained = linked_output(candidate, links, representations)
                        if retained.persistent:
                            resolved = retained
                            break
                outputs.append(detached(resolved))
            observations = tuple(detached(value) for _, _, value in chosen if isinstance(value, SourceObservation))
            return SourceStateSnapshot(keys, checkpoint, tuple(outputs), observations, minimum_applied_through, truncated,
                chosen[-1][:2] if truncated else None, tuple(after) if after is not None else None, view)

    def has_validation_certificate(self, identity):
        with self._lock:
            return any(kind == 'certificate' and key == identity for _, kind, key in self._authority)

    def has_source_use(self, identity):
        with self._lock:
            return any(kind == 'source_use' and key == identity for _, kind, key in self._authority)

    def has_acquisition_evidence(self, identity):
        with self._lock:
            return any(kind == 'acquisition' and key == identity for _, kind, key in self._authority)

    def compact(self, *, stream_id, through):
        """Discard old unretained outputs only; observation history stays explicit."""
        with self._lock:
            checkpoint = self._checkpoints.get(stream_id)
            if checkpoint is None or type(through) is not int or not 0 <= through <= checkpoint.applied_through:
                raise ValueError('source_state.compaction_cursor_invalid')
            removed = 0
            affected = set()
            represented_values = {value.represents_value_identity for (stream, _), value in self._records.items()
                                  if stream == stream_id and isinstance(value, RetainedOutput) and value.represents_value_identity}
            for key, value in tuple(self._records.items()):
                if (key[0] == stream_id and isinstance(value, RetainedOutput) and value.sequence <= through
                        and not value.persistent and (stream_id, value.accepted_value_id) not in self._links
                        and value.value_identity not in represented_values):
                    del self._records[key]
                    pointer = (stream_id, current_key(value))
                    if self._current.get(pointer) == key[1]:
                        del self._current[pointer]
                        affected.add(pointer)
                    removed += 1
            for key, value in self._records.items():
                pointer = (key[0], current_key(value))
                if pointer not in affected:
                    continue
                previous = self._current.get(pointer)
                if previous is None or current_order(self._records[(stream_id, previous)]) <= current_order(value):
                    self._current[pointer] = key[1]
            return removed
