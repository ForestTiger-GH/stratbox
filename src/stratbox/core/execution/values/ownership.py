"""Coherent candidate acceptance, demand pins and independent read leases.

This is a process-local value owner. Portable encoding belongs to ``codec``;
temporary spill never grants durability. A caller obtains named handles only
after every declared output has passed the same acceptance boundary.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass, replace
from threading import RLock
from types import MappingProxyType
from uuid import uuid4

from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.snapshots import DatasetSnapshot, TypedTable
from stratbox.shared.identity import ByteIdentity


def _immutable(value, active=None):
    from datetime import date, datetime, time, timedelta, timezone
    from decimal import Decimal
    from pathlib import PurePath
    from enum import Enum
    if value is None or type(value) in {bool, int, float, str, bytes, type}:
        return True
    if isinstance(value, (DatasetSnapshot, TypedTable, ByteIdentity, date, datetime, time, timedelta, timezone, Decimal, PurePath)):
        return True
    active = set() if active is None else active
    if id(value) in active:
        return False
    active.add(id(value))
    try:
        if isinstance(value, Enum):
            return _immutable(value.value, active)
        if isinstance(value, (tuple, frozenset)):
            return all(_immutable(item, active) for item in value)
        if is_dataclass(value) and not isinstance(value, type) and value.__dataclass_params__.frozen:
            return all(_immutable(getattr(value, member.name), active) for member in fields(value))
        return False
    finally:
        active.remove(id(value))


def isolate_value(value):
    """Detach mutable payloads while preserving core sealed immutable tables."""
    from stratbox.core.execution.retention import SpilledResult
    if isinstance(value, SpilledResult):
        # A descriptor is immutable and retains its owning store. Copying the
        # store would split locks and ownership without creating new content.
        return value
    if _immutable(value):
        return value
    if isinstance(value, Mapping):
        return {name: isolate_value(item) for name, item in value.items()}
    if isinstance(value, tuple):
        return tuple(isolate_value(item) for item in value)
    if isinstance(value, list):
        return [isolate_value(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return replace(value, **{member.name: isolate_value(getattr(value, member.name))
                                 for member in fields(value) if member.init})
    return deepcopy(value)


@dataclass(frozen=True, slots=True)
class AcceptedDescriptor:
    identity: ByteIdentity
    contract: DataContract
    qualifications: frozenset[str]
    coverage: frozenset[str]
    resident_bytes: int
    availability: str = "process_local"


@dataclass(frozen=True, slots=True)
class AcceptedTransfer:
    """An exclusive value and its reservation handed to another core owner."""
    value: object
    descriptor: AcceptedDescriptor
    owner: str


@dataclass
class _Entry:
    value: object
    descriptor: AcceptedDescriptor
    owner: str
    handles: int = 1
    readers: int = 0
    pins: int = 0
    obligations: set | None = None


class CandidateGroup:
    def __init__(self, store, contracts, obligations):
        self._store, self.contracts = store, MappingProxyType(dict(contracts))
        self._obligations = frozenset(obligations)
        self._outputs = {}
        self._state = "staging"
        self._owner = "candidate:" + uuid4().hex

    @property
    def state(self):
        return self._state

    def write(self, name, value, *, qualifications=frozenset(), coverage=frozenset()):
        from stratbox.core.execution.retention import retained_size
        from . import value_identity
        if self._state != "staging":
            raise ValueError("value.writer_closed")
        if name not in self.contracts or name in self._outputs or value is None:
            raise ValueError("value.output_invalid")
        if not isinstance(qualifications, frozenset) or not isinstance(coverage, frozenset):
            raise ValueError("value.qualification_invalid")
        with self._store._lock:
            previous = sum(item[1].resident_bytes for item in self._outputs.values())
            # Admit the copy before allocating it. A result too large for the
            # stage never briefly becomes an unbounded second resident value.
            self._store._reserve_staging(self._owner, previous + retained_size(value))
            try:
                # No candidate aliases a producer's mutable object after this call.
                value = isolate_value(value)
                descriptor = AcceptedDescriptor(value_identity(value), self.contracts[name],
                    qualifications, coverage, retained_size(value))
                self._store._reserve_staging(self._owner, previous + descriptor.resident_bytes)
            except BaseException:
                if previous:
                    self._store._reserve_staging(self._owner, previous)
                else:
                    self._store._release_staging(self._owner)
                raise
            self._outputs[name] = value, descriptor

    def close_writer(self):
        if self._state != "staging":
            raise ValueError("value.writer_closed")
        self._state = "closed"

    def validate(self, checks=()):
        if self._state != "closed":
            raise ValueError("value.writer_not_closed")
        if set(self._outputs) != set(self.contracts):
            raise ValueError("value.output_set_incomplete")
        if checks:
            # The validator's private copy is another actual staging owner.
            # Admission happens before copying, and its bytes are released even
            # when a predicate raises or rejects the coherent output group.
            owner = "validation:" + uuid4().hex
            size = sum(item[1].resident_bytes for item in self._outputs.values() if not _immutable(item[0]))
            with self._store._lock:
                self._store._reserve_staging(owner, size)
            try:
                values = MappingProxyType({name: isolate_value(item[0]) for name, item in self._outputs.items()})
                for check in checks:
                    if check(values) is False:
                        raise ValueError("value.semantic_check_failed")
            finally:
                with self._store._lock:
                    self._store._release_staging(owner)
        self._state = "validated"
        return self

    def accept(self):
        if self._state != "validated":
            raise ValueError("value.acceptance_not_validated")
        handles = self._store._accept(self)
        self._state = "accepted"
        self._outputs = {}
        return handles

    def abort(self):
        if self._state == "accepted":
            return
        with self._store._lock:
            self._store._release_staging(self._owner)
        self._outputs = {}
        self._state = "aborted"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.abort()

    def __del__(self):
        try:
            self.abort()
        except Exception:
            pass


class AcceptedValueStore:
    """Keep resident, staging and cached bytes as independent capacity domains.

    Handles own demand; pins represent a downstream obligation; leases own an
    active read. Closing a scope releases its handles while existing leases and
    unresolved recovery obligations keep their actual capacity reserved.
    """

    def __init__(self, *, max_resident_bytes=256 * 1024 * 1024,
                 max_staging_bytes=64 * 1024 * 1024, ledger=None):
        if any(type(value) is not int or value < 0 for value in (max_resident_bytes, max_staging_bytes)):
            raise ValueError("value.invalid_limit")
        self.max_resident_bytes, self.max_staging_bytes = max_resident_bytes, max_staging_bytes
        self.ledger = ledger
        self._entries, self._staging = {}, {}
        self._lease_bytes = 0
        self._lock = RLock()
        self._closed = False

    def begin(self, contracts, *, obligations=()):
        if (not isinstance(contracts, Mapping) or not contracts
                or any(not isinstance(name, str) or not name or not isinstance(contract, DataContract)
                       for name, contract in contracts.items())):
            raise ValueError("value.contracts_invalid")
        with self._lock:
            if self._closed:
                raise ValueError("value.store_closed")
        return CandidateGroup(self, contracts, obligations)

    def _reserve_staging(self, owner, size):
        if self._closed:
            raise ValueError("value.store_closed")
        if sum(self._staging.values()) - self._staging.get(owner, 0) + size > self.max_staging_bytes:
            raise ValueError("resource.staging_bytes")
        if self.ledger is not None and "staging_bytes" in self.ledger.capacities:
            if not self.ledger.replace(owner, {"staging_bytes": size}):
                raise ValueError("resource.staging_bytes")
        self._staging[owner] = size

    def _release_staging(self, owner):
        self._staging.pop(owner, None)
        if self.ledger is not None:
            self.ledger.release(owner)

    def _accept(self, candidate):
        with self._lock:
            if self._closed:
                raise ValueError("value.store_closed")
            size = sum(item[1].resident_bytes for item in candidate._outputs.values())
            if self.resident_bytes + size > self.max_resident_bytes:
                raise ValueError("resource.retained_bytes")
            owner = "accepted:" + uuid4().hex
            if self.ledger is not None and not self.ledger.reserve(owner, {"retained_bytes": size}):
                raise ValueError("resource.retained_bytes")
            # Reserve the complete group before exposing even its first handle.
            entries = {}
            for name, (value, descriptor) in candidate._outputs.items():
                key = owner + ":" + name
                entries[key] = _Entry(value, descriptor, owner, obligations=set(candidate._obligations))
            self._entries.update(entries)
            self._release_staging(candidate._owner)
            return MappingProxyType({name: RetainedValue(self, owner + ":" + name)
                                     for name in candidate._outputs})

    @property
    def resident_bytes(self):
        with self._lock:
            return sum(entry.descriptor.resident_bytes for entry in self._entries.values()) + self._lease_bytes

    @property
    def staging_bytes(self):
        with self._lock:
            return sum(self._staging.values())

    def _collect(self, key):
        entry = self._entries.get(key)
        if entry is None or entry.handles or entry.readers or entry.pins or entry.obligations:
            return
        owner = entry.owner
        del self._entries[key]
        if self.ledger is not None:
            remaining = sum(item.descriptor.resident_bytes for item in self._entries.values() if item.owner == owner)
            if remaining:
                self.ledger.replace(owner, {"retained_bytes": remaining})
            else:
                self.ledger.release(owner)

    def resolve_obligation(self, key, obligation):
        with self._lock:
            entry = self._entries[key]
            entry.obligations.discard(obligation)
            self._collect(key)

    def close(self):
        with self._lock:
            self._closed = True
            for owner in tuple(self._staging):
                self._release_staging(owner)
            # A store close stops new admission. Its handles, readers and
            # recovery obligations continue to own their promised values.


class RetainedValue:
    def __init__(self, store, key):
        self._store, self.key = store, key
        self._closed = False

    def _entry(self):
        if self._closed:
            raise ValueError("value.handle_closed")
        return self._store._entries[self.key]

    @property
    def descriptor(self):
        with self._store._lock:
            return self._entry().descriptor

    def read(self):
        from stratbox.core.execution.retention import retained_size
        with self._store._lock:
            entry = self._entry()
            entry.readers += 1
            try:
                # A lease receives its own mutable copy. Sealed snapshots can
                # be shared without changing the next consumer's observations.
                value = isolate_value(entry.value)
                size = 0 if value is entry.value else retained_size(value)
                if self._store.resident_bytes + size > self._store.max_resident_bytes:
                    raise ValueError("resource.retained_bytes")
                owner = "reader:" + uuid4().hex
                if self._store.ledger is not None and not self._store.ledger.reserve(owner, {"retained_bytes": size}):
                    raise ValueError("resource.retained_bytes")
                self._store._lease_bytes += size
            except BaseException:
                entry.readers -= 1
                raise
            return ValueLease(self._store, self.key, value, owner, size)

    def pin(self):
        with self._store._lock:
            self._entry().pins += 1
        return DemandPin(self._store, self.key)

    def clone(self):
        with self._store._lock:
            self._entry().handles += 1
        return RetainedValue(self._store, self.key)

    def transfer(self):
        """Hand an exclusive singleton group to the enclosing run/result owner.

        The recipient must release ``owner`` on the same ledger. This operation
        performs no deserialization or payload copy and retains the reservation
        continuously across the ownership boundary.
        """
        with self._store._lock:
            entry = self._entry()
            if (entry.handles != 1 or entry.readers or entry.pins or entry.obligations
                    or any(other_key != self.key and other.owner == entry.owner
                           for other_key, other in self._store._entries.items())):
                raise ValueError("value.exclusive_transfer_required")
            self._closed = True
            del self._store._entries[self.key]
            return AcceptedTransfer(entry.value, entry.descriptor, entry.owner)

    def close(self):
        with self._store._lock:
            if self._closed:
                return
            self._closed = True
            self._store._entries[self.key].handles -= 1
            self._store._collect(self.key)

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class ValueLease:
    def __init__(self, store, key, value, owner, size):
        self._store, self.key, self._value = store, key, value
        self._owner, self._size = owner, size
        self._closed = False

    @property
    def value(self):
        if self._closed:
            raise ValueError("value.lease_closed")
        return self._value

    def close(self):
        with self._store._lock:
            if self._closed:
                return
            self._closed, self._value = True, None
            self._store._lease_bytes -= self._size
            if self._store.ledger is not None:
                self._store.ledger.release(self._owner)
            self._store._entries[self.key].readers -= 1
            self._store._collect(self.key)

    def __enter__(self):
        return self.value

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class DemandPin:
    def __init__(self, store, key):
        self._store, self.key, self._closed = store, key, False

    def close(self):
        with self._store._lock:
            if self._closed:
                return
            self._closed = True
            self._store._entries[self.key].pins -= 1
            self._store._collect(self.key)

    def retain(self):
        """Admit the pinned downstream consumer after its producer scope closes."""
        with self._store._lock:
            if self._closed:
                raise ValueError("value.pin_closed")
            self._store._entries[self.key].handles += 1
        return RetainedValue(self._store, self.key)

    def read(self):
        handle = self.retain()
        try:
            return handle.read()
        finally:
            handle.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def accept_owned_value(value, contract, *, ledger, max_resident_bytes,
                       max_staging_bytes, checks=(), qualifications=frozenset(),
                       coverage=frozenset()):
    """Admit one command result before the coordinator exposes its named ports.

    Commands may return a typed envelope with several named outputs. Validators
    check that whole envelope before its one coherent acceptance. The run takes
    the accepted reservation and later transfers it to ``ResultOwnership``.
    """
    store = AcceptedValueStore(max_resident_bytes=max_resident_bytes,
        max_staging_bytes=max_staging_bytes, ledger=ledger)
    with store.begin({"value": contract}) as candidate:
        candidate.write("value", value, qualifications=qualifications, coverage=coverage)
        candidate.close_writer()
        candidate.validate(tuple(lambda values, check=check: check(values["value"]) for check in checks))
        handle = candidate.accept()["value"]
        return handle.transfer()
