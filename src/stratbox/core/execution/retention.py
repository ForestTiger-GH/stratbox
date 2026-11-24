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
        self._store_id = uuid4().hex
        self._directory = TemporaryDirectory(prefix="stratbox-results-")
        self._lock = RLock()
        self._keys = {}

    def put(self, result):
        if not isinstance(result, OperationResult):
            raise TypeError("execution.result_required")
        key = result.invocation_id
        with self._lock:
            if self._closed:
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
            if self._closed:
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
            with path.open("rb") as stream:
                data = stream.read(self._sizes[reference.key] + 1)
            if sha256(data).hexdigest() != reference.digest:
                raise ValueError("execution.retained_content_changed")
            result = pickle.loads(data)
        if not isinstance(result, OperationResult) or result.invocation_id != reference.invocation_id:
            raise ValueError("execution.retained_result_invalid")
        return result


class ResultMapping(Mapping):
    """Read detached operation values while keeping qualified receipts resident."""
    def __init__(self, entries):
        self._entries = MappingProxyType(dict(entries))

    def __getitem__(self, key):
        value = self._entries[key]
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
        return tuple(_detached_result(value.resolve() if isinstance(value, SpilledResult) else value)
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
    def __init__(self, entries):
        self._entries = MappingProxyType(dict(entries))

    def __getitem__(self, key):
        from stratbox.core.execution.values.ownership import isolate_value
        return isolate_value(self._entries[key])

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

    def __init__(self, ledger, owners=(), spill=None):
        self._ledger, self._owners, self._spill = ledger, tuple(owners), spill
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
        with self._lock:
            if self._closed:
                raise ValueError("execution.retention_closed")
            owner = "result-reader:" + uuid4().hex
            size = 0 if isinstance(value, SpilledResult) or _immutable(value) else retained_size(value)
            if self._ledger is not None and not self._ledger.reserve(owner, {"retained_bytes": size}):
                raise ValueError("resource.retained_bytes")
            try:
                isolated = isolate_value(value)
                actual_size = 0 if isolated is value else retained_size(isolated)
                if self._ledger is not None and actual_size != size and not self._ledger.replace(owner, {"retained_bytes": actual_size}):
                    raise ValueError("resource.retained_bytes")
            except BaseException:
                if self._ledger is not None:
                    self._ledger.release(owner)
                raise
            self._readers += 1
        return ResultReadLease(self, isolated, owner)

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
        if self._spill is not None:
            self._spill.close()
        if self._ledger is not None:
            for owner in self._owners:
                self._ledger.release(owner)
        self._owners, self._ledger, self._spill = (), None, None
        self._released = True

    def __del__(self):
        # GC is a fallback; explicit close gives deterministic capacity release.
        try:
            self.close()
        except Exception:
            pass


class ResultReadLease:
    def __init__(self, owner, value, reservation):
        self._owner, self._value = owner, value
        self._reservation = reservation
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
