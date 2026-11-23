"""Private, process-local spill leases for completed intermediate results.

Only bytes written by this instance are decoded. These files are temporary
implementation storage, never an interchange format or a reusable input API.
"""
from __future__ import annotations

import copyreg
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import pickle
from tempfile import TemporaryDirectory
from threading import RLock
from types import MappingProxyType
from collections.abc import Mapping

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


class ResultSpillStore:
    def __init__(self, *, max_bytes=1024 * 1024 * 1024, ledger=None):
        self.max_bytes = max_bytes
        self.ledger = ledger
        self._sizes = {}
        self._total_size = 0
        self._owners = []
        self._closed = False
        self._directory = TemporaryDirectory(prefix="stratbox-results-")
        self._lock = RLock()
        self._keys = {}

    def put(self, result):
        if not isinstance(result, OperationResult):
            raise TypeError("execution.result_required")
        target = BytesIO()
        writer = pickle.Pickler(target, protocol=pickle.HIGHEST_PROTOCOL)
        writer.dispatch_table = copyreg.dispatch_table.copy()
        writer.dispatch_table[MappingProxyType] = _reduce_mapping
        writer.dump(result)
        data = target.getvalue()
        digest = sha256(data).hexdigest()
        key = result.invocation_id
        with self._lock:
            if self._closed:
                raise ValueError("execution.retention_closed")
            if self._total_size - self._sizes.get(key, 0) + len(data) > self.max_bytes:
                raise ValueError("resource.temporary_bytes")
            owner = "spill:" + key
            if self.ledger is not None and not self.ledger.reserve(owner, {"temporary_bytes": len(data)}):
                raise ValueError("resource.temporary_bytes")
            try:
                Path(self._directory.name, key).write_bytes(data)
            except Exception:
                if self.ledger is not None:
                    self.ledger.release(owner)
                raise
            self._owners.append(owner)
            self._total_size += len(data) - self._sizes.get(key, 0)
            self._sizes[key] = len(data)
            self._keys[key] = digest
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
            data = Path(self._directory.name, reference.key).read_bytes()
            if sha256(data).hexdigest() != reference.digest:
                raise ValueError("execution.retained_content_changed")
            result = pickle.loads(data)
        if not isinstance(result, OperationResult) or result.invocation_id != reference.invocation_id:
            raise ValueError("execution.retained_result_invalid")
        return result


class ResultMapping(Mapping):
    """Read operation results lazily while keeping qualified receipts resident."""
    def __init__(self, entries):
        self._entries = MappingProxyType(dict(entries))

    def __getitem__(self, key):
        value = self._entries[key]
        return value.resolve() if isinstance(value, SpilledResult) else value

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
        return tuple(value.resolve() if isinstance(value, SpilledResult) else value for value in self._entries[key])

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
