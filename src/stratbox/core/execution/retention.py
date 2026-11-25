"""Private, process-local spill leases for completed intermediate results.

Only bytes written by this instance are decoded. These files are temporary
implementation storage, never an interchange format or a reusable input API.
"""
from __future__ import annotations

import copyreg
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
import pickle
from tempfile import TemporaryDirectory
from threading import RLock
from types import MappingProxyType
from collections.abc import Mapping
from uuid import uuid4

from stratbox.core.execution.contracts import OperationResult


def _mapping(value):
    return MappingProxyType(value)


def _reduce_mapping(value):
    return _mapping, (dict(value),)


@dataclass(frozen=True, slots=True)
class SpilledResult:
    store: object
    key: str
    digest: str
    invocation_id: str
    outcome: str
    definition: object
    diagnostics: tuple
    used_inputs: tuple
    effects: tuple
    observability: object
    computation: object
    resources_used: tuple

    def resolve(self):
        return self.store.resolve(self)


class _BoundedSpillWriter:
    """Write private pickle frames directly to disk under the byte reservation."""

    def __init__(self, stream, limit, ledger, owner):
        self.stream, self.limit, self.ledger, self.owner = stream, limit, ledger, owner
        self.digest, self.size = sha256(), 0

    def write(self, data):
        size = self.size + len(data)
        if size > self.limit:
            raise ValueError("resource.temporary_bytes")
        if self.ledger is not None and not self.ledger.replace(self.owner, {"temporary_bytes": size}):
            raise ValueError("resource.temporary_bytes")
        self.stream.write(data)
        self.digest.update(data)
        self.size = size
        return len(data)


class ResultSpillStore:
    def __init__(self, *, max_bytes=1024 * 1024 * 1024, ledger=None):
        if type(max_bytes) is not int or max_bytes < 0:
            raise ValueError("resource.invalid_limit")
        self.max_bytes = max_bytes
        self.ledger = ledger
        self._sizes = {}
        self._total_size = 0
        self._owners = []
        self._closed = False
        self._close_requested = False
        self._pins = 0
        self._store_id = uuid4().hex
        self._directory = TemporaryDirectory(prefix="stratbox-results-")
        self._lock = RLock()
        self._keys = {}

    def put(self, result):
        if not isinstance(result, OperationResult):
            raise TypeError("execution.result_required")
        key = result.invocation_id
        with self._lock:
            if self._closed or self._close_requested:
                raise ValueError("execution.retention_closed")
            # A private result may be requested repeatedly while several readers
            # still hold its immutable reference. Never replace their file.
            if key in self._keys:
                return self._reference(result, key, self._keys[key])
            owner = "spill:" + self._store_id + ":" + key
            partial = Path(self._directory.name, key + ".part")
            target = Path(self._directory.name, key)
            available = self.max_bytes - self._total_size
            try:
                with partial.open("wb") as stream:
                    sink = _BoundedSpillWriter(stream, available, self.ledger, owner)
                    writer = pickle.Pickler(sink, protocol=pickle.HIGHEST_PROTOCOL)
                    writer.dispatch_table = copyreg.dispatch_table.copy()
                    writer.dispatch_table[MappingProxyType] = _reduce_mapping
                    writer.dump(result)
                    stream.flush()
                partial.replace(target)
            except BaseException:
                partial.unlink(missing_ok=True)
                if self.ledger is not None:
                    self.ledger.release(owner)
                raise
            self._owners.append(owner)
            self._total_size += sink.size
            self._sizes[key] = sink.size
            self._keys[key] = sink.digest.hexdigest()
            return self._reference(result, key, self._keys[key])

    def _reference(self, result, key, digest):
        return SpilledResult(self, key, digest, result.invocation_id, result.outcome,
            result.definition, result.diagnostics, result.used_inputs, result.effects,
            result.observability, result.computation, result.resources_used)

    def release_capacity(self):
        with self._lock:
            if self.ledger is not None:
                for owner in self._owners:
                    self.ledger.release(owner)
                self.ledger = None

    def close(self):
        with self._lock:
            self._close_requested = True
            self._collect()

    def pin(self):
        """Keep temporary placement available to its accepted owner/readers."""
        with self._lock:
            if self._closed or self._close_requested:
                raise ValueError("execution.retention_closed")
            self._pins += 1
        return _SpillPin(self)

    def _collect(self):
        if self._closed or not self._close_requested or self._pins:
            return
        self.release_capacity()
        self._directory.cleanup()
        self._closed = True

    def resolve(self, reference):
        with self._lock:
            if self._closed:
                raise ValueError("execution.retention_closed")
            if reference.store is not self or self._keys.get(reference.key) != reference.digest:
                raise ValueError("execution.retained_reference_invalid")
            path = Path(self._directory.name, reference.key)
            if path.stat().st_size != self._sizes[reference.key]:
                raise ValueError("execution.retained_content_changed")
            staging_owner = "spill-read:" + uuid4().hex
            staged = self.ledger is not None and "staging_bytes" in self.ledger.capacities
            if staged and not self.ledger.reserve(staging_owner, {"staging_bytes": self._sizes[reference.key]}):
                raise ValueError("resource.staging_bytes")
            try:
                with path.open("rb") as stream:
                    digest = sha256()
                    while data := stream.read(65536):
                        digest.update(data)
                    if digest.hexdigest() != reference.digest:
                        raise ValueError("execution.retained_content_changed")
                    stream.seek(0)
                    # Decode only this instance's integrity-checked private
                    # stream. No whole serialized copy remains beside payload.
                    result = pickle.load(stream)
            finally:
                if staged:
                    self.ledger.release(staging_owner)
        if not isinstance(result, OperationResult) or result.invocation_id != reference.invocation_id:
            raise ValueError("execution.retained_result_invalid")
        return result


class ResultMapping(Mapping):
    """Read detached operation values while keeping qualified receipts resident."""
    def __init__(self, entries):
        self._entries = MappingProxyType(dict(entries))

    def __getitem__(self, key):
        from stratbox.core.execution.values.placement import ManagedResult
        value = self._entries[key]
        if isinstance(value, ManagedResult):
            return value.copy()
        value = value.resolve() if isinstance(value, SpilledResult) else value
        return _detached_result(value)

    def __iter__(self):
        return iter(self._entries)

    def __len__(self):
        return len(self._entries)

    @property
    def effects(self):
        return tuple(effect for value in self._entries.values() for effect in value.effects)


class AttemptMapping(Mapping):
    def __init__(self, entries):
        self._entries = MappingProxyType(dict(entries))

    def __getitem__(self, key):
        from stratbox.core.execution.values.placement import ManagedResult
        return tuple(value.copy() if isinstance(value, ManagedResult) else _detached_result(value.resolve() if isinstance(value, SpilledResult) else value)
                     for value in self._entries[key])

    def __iter__(self):
        return iter(self._entries)

    def __len__(self):
        return len(self._entries)


def _detached_result(value):
    from stratbox.core.execution.values.ownership import isolate_value
    detached = isolate_value(value.value)
    return value if detached is value.value else replace(value, value=detached)


class ValueMapping(Mapping):
    """Named accepted outputs expose independent mutable consumer values."""
    def __init__(self, entries, *, unwrap=False):
        self._entries = MappingProxyType(dict(entries))
        self._unwrap = unwrap

    def __getitem__(self, key):
        from stratbox.core.execution.values.ownership import isolate_value
        from stratbox.core.execution.values.placement import resolve_managed
        value = resolve_managed(self._entries[key])
        if self._unwrap:
            from stratbox.core.execution.handoff import PreparedInput, ProjectedOutput
            if isinstance(value, (PreparedInput, ProjectedOutput)):
                value = value.value
        return isolate_value(value)

    def _owned(self, key):
        """Core-only projection before obtaining an accounted read lease."""
        return self._entries[key]

    def __iter__(self):
        return iter(self._entries)

    def __len__(self):
        return len(self._entries)


def retained_size(value):
    """Measure resident payloads, never the size of their digest descriptors.

    This accounts known Python containers and scientific buffers; it is a
    retained-material budget, not a hard cap on interpreter or native RSS.
    """
    from dataclasses import fields, is_dataclass
    from sys import getsizeof
    seen = set()

    def measure(item):
        if item is None or id(item) in seen:
            return 0
        seen.add(id(item))
        if isinstance(item, (bytes, bytearray, memoryview)):
            return len(item)
        if isinstance(item, str):
            return len(item.encode("utf-8"))
        if isinstance(item, (bool, int, float)):
            return max(8, (item.bit_length() + 7) // 8) if isinstance(item, int) else 8
        modules = {kind.__module__.split(".", 1)[0] for kind in type(item).__mro__}
        if "pandas" in modules and hasattr(item, "memory_usage"):
            usage = item.memory_usage(deep=True)
            return int(usage.sum() if hasattr(usage, "sum") else usage)
        if "numpy" in modules and hasattr(item, "nbytes"):
            return int(item.nbytes)
        if isinstance(item, Mapping):
            return sum(measure(key) + measure(member) for key, member in item.items())
        if isinstance(item, (tuple, list, set, frozenset)):
            return sum(measure(member) for member in item)
        if is_dataclass(item):
            return sum(measure(getattr(item, member.name)) for member in fields(item))
        return getsizeof(item)

    return measure(value)


class ResultOwnership:
    """Transfer live-result capacity to the returned handle, beyond run completion.

    Closing prevents new readers. Existing leases delay the actual cleanup.
    The object deliberately keeps the ledger alive when a convenience session
    closes, so accounting follows the promised result rather than the executor.
    """

    def __init__(self, ledger, owners=(), spill=None, *, managed=(), on_close=None):
        self._managed = tuple(dict.fromkeys(managed))
        managed_owners = {item.reservation_owner for item in self._managed}
        self._ledger, self._owners, self._spill = ledger, tuple(owner for owner in owners if owner not in managed_owners), spill
        self._on_close = on_close
        self._readers = 0
        self._closed = False
        self._released = False
        self._lock = RLock()

    @property
    def closed(self):
        with self._lock:
            return self._closed

    def lease(self, value=None):
        from stratbox.core.execution.values.ownership import isolate_value, _immutable
        from stratbox.core.execution.values.placement import ManagedResult, ManagedProjection, ManagedCollection
        with self._lock:
            if self._closed:
                raise ValueError("execution.retention_closed")
            managed_lease = None
            if isinstance(value, (ManagedResult, ManagedProjection, ManagedCollection)):
                managed_lease = value.read()
                value = managed_lease.value
                from stratbox.core.execution.handoff import PreparedInput, ProjectedOutput
                if isinstance(value, (PreparedInput, ProjectedOutput)):
                    value = value.value
            owner = "result-reader:" + uuid4().hex
            size = 0 if isinstance(value, SpilledResult) or _immutable(value) else retained_size(value)
            try:
                if self._ledger is not None and not self._ledger.reserve(owner, {"retained_bytes": size}):
                    raise ValueError("resource.retained_bytes")
                isolated = isolate_value(value)
                actual_size = 0 if isolated is value else retained_size(isolated)
                if self._ledger is not None and actual_size != size and not self._ledger.replace(owner, {"retained_bytes": actual_size}):
                    raise ValueError("resource.retained_bytes")
            except BaseException:
                if self._ledger is not None:
                    self._ledger.release(owner)
                if managed_lease is not None:
                    managed_lease.close()
                raise
            self._readers += 1
        return ResultReadLease(self, isolated, owner, managed_lease)

    def close(self):
        with self._lock:
            self._closed = True
            self._cleanup()

    release = close

    def _reader_closed(self, owner):
        with self._lock:
            if self._ledger is not None:
                self._ledger.release(owner)
            self._readers -= 1
            self._cleanup()

    def _cleanup(self):
        if not self._closed or self._readers or self._released:
            return
        for managed in self._managed:
            managed.close()
        self._managed = ()
        if self._spill is not None:
            self._spill.close()
        if self._ledger is not None:
            for owner in self._owners:
                self._ledger.release(owner)
        self._owners, self._ledger, self._spill = (), None, None
        self._released = True
        callback, self._on_close = self._on_close, None
        if callback is not None:
            callback()

    def __del__(self):
        # GC is a fallback; explicit close gives deterministic capacity release.
        try:
            self.close()
        except Exception:
            pass


class ResultReadLease:
    def __init__(self, owner, value, reservation, managed_lease=None):
        self._owner, self._value = owner, value
        self._reservation = reservation
        self._managed_lease = managed_lease
        self._closed = False
        self._lock = RLock()

    @property
    def value(self):
        with self._lock:
            if self._closed:
                raise ValueError("execution.read_lease_closed")
            return self._value

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._value = None
            if self._managed_lease is not None:
                self._managed_lease.close()
                self._managed_lease = None
            self._owner._reader_closed(self._reservation)
            self._owner = None

    def __enter__(self):
        return self.value

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class _SpillPin:
    def __init__(self, store):
        self._store = store

    def close(self):
        store = self._store
        if store is None:
            return
        with store._lock:
            if self._store is None:
                return
            self._store = None
            store._pins -= 1
            store._collect()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
