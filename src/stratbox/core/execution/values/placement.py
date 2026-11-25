"""One accepted result owner shared by all graph and scope projections.

Projections retain logical ownership rather than the payload. A placement change
therefore removes every internal RAM alias at once. Reads of a spilled value
hold an explicitly accounted materialization lease for their complete use.
"""
from __future__ import annotations

from contextvars import ContextVar
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass, replace
from threading import RLock
from uuid import uuid4


_read_scope = ContextVar("stratbox_value_read_scope", default=None)
_EVIDENCE = ("definition", "invocation_id", "outcome", "diagnostics", "used_inputs",
             "effects", "observability", "computation", "resources_used")


class ValueReadScope:
    """Keep all core materializations alive until a handler/check completes."""
    def __init__(self):
        self._leases = []
        self._results = {}
        self._collections = {}
        self._token = None

    def __enter__(self):
        self._token = _read_scope.set(self)
        return self

    def hold(self, lease):
        self._leases.append(lease)
        return lease.value

    def result(self, owner):
        if owner not in self._results:
            self._results[owner] = self.hold(owner.read())
        return self._results[owner]

    def collection(self, value):
        from stratbox.core.execution.handoff import collect_inputs, PreparedInput
        key = id(value)
        if key not in self._collections:
            members = tuple(_resolve_with_scope(item, self) for item in value.items)
            if not members:
                if not value.allow_empty:
                    raise ValueError("execution.collection_empty")
                prepared = PreparedInput(value.contract, (), outcome=value.outcome)
            else:
                prepared = collect_inputs(members, contract=value.contract, element_contract=value.element_contract)
                if value.outcome == "partial":
                    prepared = replace(prepared, outcome="partial")
            self._collections[key] = value, prepared
        return self._collections[key][1]

    def isolate(self, value, ledger, *, resource="retained_bytes"):
        """Admit a mutable worker copy before allocating its payload buffers."""
        from .ownership import isolate_value
        size = _copy_size(value)
        owner = "consumer-copy:" + uuid4().hex
        if ledger is not None and not ledger.reserve(owner, {resource: size}):
            raise ValueError("resource." + resource)
        try:
            isolated = isolate_value(value)
        except BaseException:
            if ledger is not None:
                ledger.release(owner)
            raise
        self._leases.append(_CapacityLease(ledger, owner))
        return isolated

    def close(self):
        self._results.clear()
        self._collections.clear()
        for lease in reversed(self._leases):
            lease.close()
        self._leases.clear()

    def __exit__(self, *exc):
        try:
            self.close()
        finally:
            _read_scope.reset(self._token)


def resolve_managed(value):
    """Resolve into the active core read scope, or hand a detached copy out."""
    return _resolve_with_scope(value, _read_scope.get())


def _resolve_with_scope(value, scope):
    if isinstance(value, (ManagedResult, ManagedProjection)):
        if scope is None:
            return value.copy()
        if isinstance(value, ManagedResult):
            return scope.result(value)
        from stratbox.core.execution.handoff import project_output
        projected = project_output(scope.result(value.owner), value.port)
        return projected.value if value.unwrap else projected
    if isinstance(value, ManagedCollection):
        return value.copy() if scope is None else scope.collection(value)
    if isinstance(value, Mapping):
        items = {name: _resolve_with_scope(item, scope) for name, item in value.items()}
        return value if all(items[name] is item for name, item in value.items()) else items
    if isinstance(value, (tuple, list)):
        items = [_resolve_with_scope(item, scope) for item in value]
        return value if all(a is b for a, b in zip(items, value)) else tuple(items) if isinstance(value, tuple) else items
    if is_dataclass(value) and not isinstance(value, type):
        items = {member.name: _resolve_with_scope(getattr(value, member.name), scope) for member in fields(value) if member.init}
        return value if all(item is getattr(value, name) for name, item in items.items()) else replace(value, **items)
    return value


def isolate_managed(value, ledger, *, resource="retained_bytes"):
    """Use the active handler read scope for worker-owned mutable copies."""
    from .ownership import isolate_value
    scope = _read_scope.get()
    return isolate_value(value) if scope is None else scope.isolate(value, ledger, resource=resource)


def _copy_size(value, *, root=True):
    from .ownership import _immutable
    from stratbox.core.execution.retention import retained_size
    from stratbox.core.execution.handoff import PreparedInput, ProjectedOutput
    if _immutable(value) or isinstance(value, (ManagedResult, ManagedProjection, ManagedCollection)):
        return 0
    if isinstance(value, (PreparedInput, ProjectedOutput)):
        return _copy_size(value.value, root=False)
    if isinstance(value, Mapping):
        # The outer request mapping is control metadata. Nested payload maps
        # allocate key/value references even when their scalar members share.
        return (0 if root else len(value) * 16) + sum(_copy_size(item, root=False) for item in value.values())
    if isinstance(value, (tuple, list)):
        return len(value) * 8 + sum(_copy_size(item, root=False) for item in value)
    if is_dataclass(value) and not isinstance(value, type):
        return sum(_copy_size(getattr(value, member.name), root=False) for member in fields(value) if member.init)
    return retained_size(value)


class _CapacityLease:
    def __init__(self, ledger, owner):
        self.ledger, self.owner = ledger, owner

    def close(self):
        if self.ledger is not None:
            self.ledger.release(self.owner)
            self.ledger = None


class ManagedResult:
    def __init__(self, result, *, ledger=None, reservation_owner=None,
                 resource="retained_bytes"):
        from stratbox.core.execution.contracts import OperationResult
        from stratbox.core.execution.retention import retained_size
        if not isinstance(result, OperationResult):
            raise TypeError("execution.result_required")
        self._evidence = {name: getattr(result, name) for name in _EVIDENCE}
        self._has_value = result.value is not None
        self._resident = result
        self._spilled = None
        self._spill_pin = None
        self._ledger, self._owner = ledger, reservation_owner
        self._resource = resource
        self._size = retained_size(result.value)
        self._readers = 0
        self._pins = 0
        self._closed = False
        self._released = False
        self._lock = RLock()

    def __getattr__(self, name):
        evidence = self.__dict__.get("_evidence", {})
        if name in evidence:
            return evidence[name]
        raise AttributeError(name)

    @property
    def operation_id(self):
        return self.definition.operation_id

    @property
    def has_value(self):
        return self._has_value

    @property
    def placement(self):
        with self._lock:
            return "closed" if self._released else "temporary" if self._spilled is not None else "resident"

    @property
    def reservation_owner(self):
        with self._lock:
            return self._owner

    @property
    def value(self):
        # Explicit access is a caller-owned copy, never an internal RAM alias.
        return self.copy().value

    def project(self, port="value", *, unwrap=False):
        return ManagedProjection(self, port, unwrap)

    def read(self, *, _pinned=False):
        from stratbox.core.execution.retention import retained_size
        with self._lock:
            if self._released or self._closed and not _pinned:
                raise ValueError("execution.retention_closed")
            materialization = None
            if self._resident is not None:
                result = self._resident
            else:
                materialization = "materialization:" + uuid4().hex
                if self._ledger is not None and not self._ledger.reserve(materialization, {"retained_bytes": self._size}):
                    raise ValueError("resource.retained_bytes")
                try:
                    result = self._spilled.resolve()
                    actual = retained_size(result.value)
                    if self._ledger is not None and actual != self._size and not self._ledger.replace(materialization, {"retained_bytes": actual}):
                        raise ValueError("resource.retained_bytes")
                except BaseException:
                    if self._ledger is not None:
                        self._ledger.release(materialization)
                    raise
            self._readers += 1
            return ManagedReadLease(self, result, materialization)

    def copy(self):
        from .ownership import isolate_value
        with self.read() as result:
            value = isolate_value(result.value)
            return result if value is result.value else replace(result, value=value)

    resolve = copy

    def spill(self, store):
        """Change the placement without changing any graph/scope reference."""
        with self._lock:
            if self._released or self._closed:
                raise ValueError("execution.retention_closed")
            if self._spilled is not None:
                return False
            pin = store.pin()
            try:
                spilled = store.put(self._resident)
            except BaseException:
                pin.close()
                raise
            self._spilled, self._spill_pin = spilled, pin
            self._resident = None
            # A resident read lease still owns the old object. Its reservation
            # stays occupied until that reader releases the actual last alias.
            self._release_resident_if_unused()
            return True

    def pin(self):
        with self._lock:
            if self._closed or self._released:
                raise ValueError("execution.retention_closed")
            self._pins += 1
        return ManagedDemandPin(self)

    def close(self):
        with self._lock:
            self._closed = True
            self._collect()

    def _release_resident_if_unused(self):
        if self._spilled is not None and not self._readers and self._owner is not None:
            if self._ledger is not None:
                self._ledger.release(self._owner)
            self._owner = None

    def _reader_closed(self, materialization):
        with self._lock:
            if materialization is not None and self._ledger is not None:
                self._ledger.release(materialization)
            self._readers -= 1
            self._release_resident_if_unused()
            self._collect()

    def _collect(self):
        if not self._closed or self._readers or self._pins or self._released:
            return
        self._resident, self._spilled = None, None
        if self._owner is not None and self._ledger is not None:
            self._ledger.release(self._owner)
        self._owner = None
        if self._spill_pin is not None:
            self._spill_pin.close()
            self._spill_pin = None
        self._released = True

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class ManagedReadLease:
    def __init__(self, owner, result, materialization):
        self._owner, self._result, self._materialization = owner, result, materialization
        self._lock = RLock()
        self._closed = False

    @property
    def value(self):
        with self._lock:
            if self._closed:
                raise ValueError("execution.read_lease_closed")
            return self._result

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed, self._result = True, None
            self._owner._reader_closed(self._materialization)
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


@dataclass(frozen=True, slots=True)
class ManagedProjection:
    owner: ManagedResult
    port: str = "value"
    unwrap: bool = False

    def read(self):
        from stratbox.core.execution.handoff import project_output
        lease = self.owner.read()
        try:
            projected = project_output(lease.value, self.port)
            value = projected.value if self.unwrap else projected
            return ProjectionReadLease(lease, value)
        except BaseException:
            lease.close()
            raise

    def copy(self):
        from .ownership import isolate_value
        with self.read() as value:
            return isolate_value(value)

    resolve = copy


class ProjectionReadLease:
    def __init__(self, lease, value):
        self._lease, self._value = lease, value
        self._lock = RLock()

    @property
    def value(self):
        with self._lock:
            if self._lease is None:
                raise ValueError("execution.read_lease_closed")
            return self._value

    def close(self):
        with self._lock:
            if self._lease is None:
                return
            lease, self._lease, self._value = self._lease, None, None
            lease.close()

    def __enter__(self):
        return self.value

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class ManagedDemandPin:
    def __init__(self, owner):
        self._owner = owner
        self._lock = RLock()

    def read(self):
        with self._lock:
            if self._owner is None:
                raise ValueError("value.pin_closed")
            return self._owner.read(_pinned=True)

    def close(self):
        with self._lock:
            owner = self._owner
            if owner is None:
                return
            self._owner = None
            with owner._lock:
                owner._pins -= 1
                owner._collect()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


@dataclass(frozen=True, slots=True)
class ManagedCollection:
    """A structural collection holds member projections, never raw payloads."""
    items: tuple
    contract: object
    element_contract: object
    outcome: str = "succeeded"
    allow_empty: bool = False

    def __post_init__(self):
        if not isinstance(self.items, tuple) or self.outcome not in {"succeeded", "partial"} or type(self.allow_empty) is not bool:
            raise ValueError("execution.collection_invalid")

    def read(self):
        scope = ValueReadScope()
        try:
            value = scope.collection(self)
            return CompositeReadLease(scope, value)
        except BaseException:
            scope.close()
            raise

    def copy(self):
        from .ownership import isolate_value
        with self.read() as value:
            return isolate_value(value)

    resolve = copy


class CompositeReadLease:
    def __init__(self, scope, value):
        self._scope, self._value = scope, value
        self._lock = RLock()

    @property
    def value(self):
        with self._lock:
            if self._scope is None:
                raise ValueError("execution.read_lease_closed")
            return self._value

    def close(self):
        with self._lock:
            if self._scope is None:
                return
            scope, self._scope, self._value = self._scope, None, None
            scope.close()

    def __enter__(self):
        return self.value

    def __exit__(self, *exc):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
