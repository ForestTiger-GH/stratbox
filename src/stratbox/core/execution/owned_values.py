"""Owned payload measurement, scientific cell counts and private reader copies."""
from dataclasses import dataclass, fields, is_dataclass, replace
from typing import Mapping
import copy
import sys
import re
from types import MemberDescriptorType, MappingProxyType
from datetime import date,datetime,time,timedelta
from decimal import Decimal
from enum import Enum

from stratbox.shared.data.values import fingerprint

_COPY_BUDGET = object()


class _CopyBudget:
    def __init__(self, max_bytes, max_nodes=1000000):
        self.remaining, self.nodes = max_bytes, max_nodes

    def reserve(self, value):
        self.nodes -= 1
        if self.nodes < 0:
            raise ValueError('value.copy_object_limit')
        if type(value).__module__.startswith('numpy') and hasattr(value, 'nbytes'):
            amount = int(value.nbytes) + 64
        elif type(value).__module__.startswith('pandas') and hasattr(value, 'memory_usage'):
            usage = value.memory_usage(deep=False)
            amount = int(usage.sum() if hasattr(usage, 'sum') else usage) + 256
        elif isinstance(value, Mapping):
            amount = 64 + len(value) * 48
        elif isinstance(value, (tuple, list, set, frozenset)):
            amount = 64 + len(value) * 16
        else:
            amount = sys.getsizeof(value) + 16
        self.remaining -= amount
        if self.remaining < 0:
            raise ValueError('value.copy_bytes_limit')


def copy_memo(max_bytes):
    return {_COPY_BUDGET: _CopyBudget(max_bytes)}

def _size(value, seen=None):
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    if isinstance(value, (bytes, bytearray)):
        return len(value)
    if isinstance(value, memoryview):
        return value.nbytes
    if type(value).__module__.startswith('numpy') and type(value).__name__ == 'ndarray':
        return int(value.nbytes) + (sum(_size(item, seen) for item in value.flat)
            if value.dtype.hasobject else 0)
    if isinstance(value, Mapping):
        return sys.getsizeof(value) + sum(_size(k, seen) + _size(x, seen) for k, x in value.items())
    if isinstance(value, (tuple, list)):
        return sys.getsizeof(value) + sum(_size(x, seen) for x in value)
    if isinstance(value,(set,frozenset)):
        return sys.getsizeof(value)+sum(_size(x,seen) for x in value)
    if type(value).__module__.startswith('pandas') and hasattr(value, "memory_usage"):
        try:
            usage = value.memory_usage(deep=False)
            total = int(usage.sum() if hasattr(usage, 'sum') else usage)
            if hasattr(value, 'columns'):
                for position, dtype in enumerate(value.dtypes):
                    if dtype.kind == 'O':
                        total += sum(_size(item, seen) for item in value.iloc[:, position].array)
            elif value.dtype.kind == 'O':
                total += sum(_size(item, seen) for item in value.array)
            if getattr(value.index.dtype, 'kind', None) == 'O':
                total += sum(_size(item, seen) for item in value.index)
            return total
        except Exception:
            pass
    if is_dataclass(value) and not isinstance(value,type):
        return sys.getsizeof(value) + sum(_size(getattr(value, item.name), seen) for item in fields(value))
    total=sys.getsizeof(value)
    if not isinstance(value,type):
        try: attributes=object.__getattribute__(value,'__dict__')
        except AttributeError: attributes=None
        if attributes is not None: total+=_size(attributes,seen)
        for cls in type(value).__mro__:
            for name,descriptor in vars(cls).items():
                if isinstance(descriptor,MemberDescriptorType) and name not in {'__dict__','__weakref__'}:
                    try: item=object.__getattribute__(value,name)
                    except AttributeError: continue
                    total+=_size(item,seen)
    return total


def _cells(value):
    """Count actual supplied semantic cells, without inferring Cartesian coverage."""
    from stratbox.shared.data.values import SourceDataset, TableEvidenceSet, WorkbookEvidence
    from stratbox.shared.data.workbook_cells import WorkbookCells, WorkbookCell
    if isinstance(value, WorkbookCell): return 1
    if isinstance(value, SourceDataset): return sum(len(row) for row in value.rows)
    if isinstance(value, WorkbookEvidence): return _cells(value.workbook)
    if isinstance(value, WorkbookCells): return sum(len(sheet.cells) for sheet in value.sheets)
    if isinstance(value, TableEvidenceSet): return sum(_cells(item) for item in value.tables)
    if isinstance(value, Mapping): return sum(_cells(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return sum(_cells(item) if isinstance(item, (Mapping, tuple, list)) or is_dataclass(item) or hasattr(item,"shape") else 1 for item in value)
    if hasattr(value, "shape") and len(value.shape) == 2: return int(value.shape[0] * value.shape[1])
    if is_dataclass(value) and not isinstance(value,type): return sum(_cells(getattr(value, field.name)) for field in fields(value))
    return 0


def _isolate(value, memo=None, *, max_bytes=None):
    """Give mutable tabular payloads a private owner without copying immutable bytes."""
    memo = (copy_memo(max_bytes) if max_bytes is not None else {}) if memo is None else memo
    if id(value) in memo: return memo[id(value)]
    if value is None or type(value) in {str, bytes, bool, int, float, complex, type, range, object}:
        return value
    if type(value) in {date, datetime, time, timedelta, Decimal, re.Pattern}:
        return value
    if isinstance(value, Enum):
        if type(value.value) not in {str, bytes, bool, int, float, type(None)}:
            raise ValueError('value.mutable_enum_not_admitted')
        return value
    if type(value).__module__.startswith('numpy'):
        import numpy as np
        # NumPy scalars also expose .flat. Numeric/text/time scalar kinds are
        # immutable; structured void scalars and object storage are not.
        if isinstance(value, np.generic) and value.dtype.kind in 'biufcmMSU':
            return value
    if type(value).__module__.startswith('pandas') and type(value).__name__ in {'Timestamp', 'Timedelta', 'Period', 'Interval', 'NaTType', 'NAType'}:
        return value
    # Immutable leaves are retained by reference, so repeated labels and small
    # scalar cells do not spend the copy budget or its compound-object limit.
    if _COPY_BUDGET in memo:
        memo[_COPY_BUDGET].reserve(value)
    from array import array
    from collections import deque
    if isinstance(value, (array, deque)):
        # Unsupported native container semantics must not bypass recursive
        # ownership, staged-reference discovery or the portable value boundary.
        raise ValueError('value.native_container_not_admitted:' + type(value).__name__)
    if isinstance(value,bytearray):
        result = bytearray(value); memo[id(value)] = result; return result
    if isinstance(value,memoryview):
        result = memoryview(value.tobytes()).cast(value.format,shape=value.shape)
        memo[id(value)] = result; return result
    if type(value).__module__.startswith('pandas') and hasattr(value, 'memory_usage') and hasattr(value, 'copy'):
        # Pandas deep-copy owns numeric blocks and object cells below. Axis
        # labels must belong to its admitted scalar vocabulary; arbitrary
        # mutable hashable labels otherwise remain aliased inside Index.
        from stratbox.shared.data.frame_codec import _axis_value
        try:
            _axis_value(value.index)
            if hasattr(value, 'columns'):
                _axis_value(value.columns)
        except (TypeError, ValueError) as error:
            raise ValueError('value.axis_not_admitted') from error
        result = value.copy(deep=True); memo[id(value)] = result
        if hasattr(result,"columns"):
            for position,dtype in enumerate(result.dtypes):
                if dtype.kind == "O":
                    for index in range(len(result.index)):
                        result.iat[index,position] = _isolate(result.iat[index,position],memo)
        elif getattr(result.dtype,"kind",None) == "O":
            for index in range(len(result)): result.iat[index] = _isolate(result.iat[index],memo)
        return result
    if type(value).__module__.startswith("numpy") and type(value).__name__ == "ndarray":
        result = value.copy(order="K"); memo[id(value)] = result
        if result.dtype.hasobject:
            for index in range(result.size): result.flat[index] = _isolate(result.flat[index],memo)
        return result
    if isinstance(value, Mapping):
        result = {}; memo[id(value)] = result
        result.update({_isolate(key, memo): _isolate(item, memo) for key, item in value.items()})
        if isinstance(value, MappingProxyType):
            result = MappingProxyType(result); memo[id(value)] = result
        return result
    if isinstance(value, tuple):
        result = tuple(_isolate(item, memo) for item in value); memo[id(value)] = result; return result
    if isinstance(value, list):
        result = []; memo[id(value)] = result
        result.extend(_isolate(item, memo) for item in value); return result
    if isinstance(value,(set,frozenset)):
        result=type(value)(_isolate(item,memo) for item in value)
        memo[id(value)]=result
        return result
    if is_dataclass(value) and not isinstance(value,type):
        result = object.__new__(type(value)); memo[id(value)] = result
        for item in fields(value):
            object.__setattr__(result, item.name, _isolate(getattr(value, item.name), memo))
        return result
    if type(value).__module__ not in {"builtins","datetime","decimal","enum","zoneinfo"}:
        try: attributes = object.__getattribute__(value,"__dict__")
        except AttributeError: attributes = None
        slots = [(name,descriptor) for cls in type(value).__mro__ for name,descriptor in vars(cls).items()
            if isinstance(descriptor,MemberDescriptorType) and name not in {"__dict__","__weakref__"}]
        if attributes or slots:
            try: result = object.__new__(type(value))
            except TypeError: raise ValueError("value.opaque_owner_not_admitted") from None
            memo[id(value)] = result
            if attributes is not None:
                for name,item in attributes.items(): object.__setattr__(result,name,_isolate(item,memo))
            for name,_ in slots:
                try: item = object.__getattribute__(value,name)
                except AttributeError: continue
                object.__setattr__(result,name,_isolate(item,memo))
            return result
    if type(value).__module__ in {'zoneinfo', 'datetime'}:
        return value
    raise ValueError('value.opaque_owner_not_admitted:' + type(value).__name__)



def input_values(values, *, max_nodes=100000):
    """Visit only graph containers, keeping scientific payloads as one value."""
    seen, pending = set(), list(values)
    visited = 0
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value)); visited += 1
        if visited > max_nodes:
            raise ValueError('value.input_metadata_limit')
        yield value
        if isinstance(value, Mapping):
            pending.extend(value.values())
        elif isinstance(value,(tuple,list)):
            pending.extend(value)


def _value_keys(values):
    keys = set()
    for value in input_values(values):
        try: keys.add(fingerprint(value))
        except (ValueError,TypeError): pass
    return keys


@dataclass(frozen=True)
class OwnedValueDescriptor:
    value_id: str
    exact_identity: str | None
    processing_identity: str | None
    resident_bytes: int
    cells: int
    staged_references: tuple
    input_material_bytes: int
    expressions: bool = False
    physical_identity: object = None


@dataclass
class _OwnedEntry:
    payload: object
    descriptor: OwnedValueDescriptor
    children: tuple[int, ...]
    own_bytes: int
    owners: set


class OwnedValues:
    """Private, sealed payloads with cached identities and exact owner release.

    Object addresses are used only to locate payloads already detached and held
    by this registry. Public object identities and arbitrary digest attributes
    never grant admission. Mutable working copies are deliberately unregistered.
    """
    def __init__(self, *, max_bytes, max_objects=1000000):
        from threading import RLock
        self._lock = RLock()
        self._entries, self._owners = {}, {}
        self._working = {}
        self.max_bytes, self.max_objects = max_bytes, max_objects
        self.resident_bytes = self.working_bytes = 0
        self.identity_passes = self.sealed_values = 0

    def descriptor(self, value):
        with self._lock:
            entry = self._entries.get(id(value))
            return entry.descriptor if entry is not None and entry.payload is value else None

    def reserve_working(self, owner, amount):
        with self._lock:
            if self.resident_bytes + self.working_bytes + amount > self.max_bytes:
                raise ValueError('value.retention_capacity_exhausted')
            if owner in self._working:
                raise ValueError('value.duplicate_working_owner')
            self._working[owner] = amount
            self.working_bytes += amount

    def release_working(self, owner):
        with self._lock:
            self.working_bytes -= self._working.pop(owner, 0)

    def identity(self, value):
        descriptor = self.descriptor(value)
        return descriptor.exact_identity if descriptor is not None else None

    def processing_identity(self, value):
        descriptor = self.descriptor(value)
        if descriptor is None or descriptor.processing_identity is None:
            raise ValueError('value.unsealed_processing_input')
        return descriptor.processing_identity

    def keys(self, values):
        return {key for value in input_values(values) if (key := self.identity(value)) is not None}

    def described(self, value):
        """Inspect graph metadata only, leaving unknown typed projections opaque."""
        if self.descriptor(value) is not None:
            return True
        if isinstance(value, Mapping):
            return all(self.described(part) for pair in value.items() for part in pair)
        if isinstance(value, (tuple, list)):
            return all(self.described(part) for part in value)
        return value is None or type(value) in {str, bytes, bool, int, float}

    def work_identity(self, value):
        """A compact work basis over named/ordered graph containers."""
        known = self.identity(value)
        if known is not None:
            return known
        if isinstance(value, Mapping):
            return ('mapping', tuple(sorted((self.work_identity(key), self.work_identity(item)) for key, item in value.items())))
        if isinstance(value, (tuple, list)):
            return ('tuple', tuple(self.work_identity(item) for item in value))
        if known is None:
            # Only bounded control literals may bypass a payload descriptor.
            if value is None or type(value) in {str, int, float, bool, bytes}:
                return fingerprint(value)
            raise ValueError('value.unsealed_work_input')
        return known

    def seal(self, value, owner, *, detach=False, as_bundle=False):
        """Compute descriptors off the coordinator, then publish one owner.

        The caller has reserved the snapshot/working-set budget. Opaque values
        retain ownership and isolation but never acquire fabricated hash keys.
        """
        from uuid import uuid4
        from stratbox.shared.data.materials import staged_references
        from stratbox.shared.data.processing import processing_input_identity
        from .boundary_accounting import _input_materials
        if detach:
            value = _isolate(value, max_bytes=self.max_bytes)
        candidates, active = {}, set()

        def visit(item, *, bundle=False):
            key = id(item)
            with self._lock:
                previous = self._entries.get(key)
                if previous is not None and previous.payload is item:
                    return previous.descriptor
            if key in candidates:
                return candidates[key].descriptor
            if key in active:
                raise ValueError('value.cyclic_owner')
            if len(candidates) >= self.max_objects:
                raise ValueError('value.owner_objects_exhausted')
            active.add(key)
            children = tuple(part for pair in item.items() for part in pair) if isinstance(item, Mapping) else tuple(item) if isinstance(item, (tuple, list)) else ()
            child_descriptors = tuple(visit(child) for child in children)
            # Graph containers have additive ownership; a scientific carrier is
            # one sealed payload and is inspected once at its own boundary.
            child_sizes = {id(child): descriptor.resident_bytes for child, descriptor in zip(children, child_descriptors)}
            size = _size(item) if not children else sys.getsizeof(item) + sum(child_sizes.values())
            if size > self.max_bytes:
                raise ValueError('value.retention_capacity_exhausted')
            try:
                exact = None if bundle else fingerprint(item)
                if not bundle:
                    self.identity_passes += 1
            except (ValueError, TypeError):
                exact = None
            try:
                processing = None if bundle else processing_input_identity(item)
            except (ValueError, TypeError):
                processing = exact
            from stratbox.shared.data.values import Material, EncodedProduct, IdentifiedMaterial, ImmutableMaterialRef, RequestSpec, request_identity
            from stratbox.shared.data.materials import StagedMaterialRef
            physical = item.material if isinstance(item, IdentifiedMaterial) else item
            physical_identity = (physical.identity if isinstance(physical, (Material, EncodedProduct, ImmutableMaterialRef, StagedMaterialRef))
                else request_identity(item) if isinstance(item, RequestSpec) else None)
            descriptor = OwnedValueDescriptor(uuid4().hex, exact, processing, size,
                _cells(item), tuple(staged_references(item)),
                sum(reference.identity.size for reference in _input_materials(item)),
                type(item).__module__ == 'stratbox.capabilities.plan.models' and type(item).__name__ in {'ValueRef', 'TemplateInput'}
                    or any(descriptor.expressions for descriptor in child_descriptors), physical_identity)
            own = max(0, size - sum(child_sizes.values()))
            candidates[key] = _OwnedEntry(item, descriptor, tuple(id(child) for child in children), own, set())
            active.remove(key)
            return descriptor

        visit(value, bundle=as_bundle)
        with self._lock:
            incoming = {key: entry for key, entry in candidates.items() if key not in self._entries}
            if len(self._entries) + len(incoming) > self.max_objects:
                raise ValueError('value.owner_objects_exhausted')
            amount = sum(entry.own_bytes for entry in incoming.values())
            if self.resident_bytes + self.working_bytes + amount > self.max_bytes:
                raise ValueError('value.retention_capacity_exhausted')
            self._entries.update(incoming)
            self.resident_bytes += amount
            self.sealed_values += len(incoming)
            self._pin(value, owner)
        return value

    def _pin(self, value, owner):
        owned = self._owners.setdefault(owner, set())
        pending = [id(value)]
        while pending:
            key = pending.pop()
            if key in owned:
                continue
            entry = self._entries.get(key)
            if entry is None:
                raise ValueError('value.unsealed_owner')
            owned.add(key)
            entry.owners.add(owner)
            pending.extend(entry.children)

    def pin(self, value, owner):
        with self._lock:
            self._pin(value, owner)

    def pin_graph(self, value, owner):
        with self._lock:
            if self.descriptor(value) is not None:
                self._pin(value, owner)
            elif isinstance(value, Mapping):
                for item in value.values(): self.pin_graph(item, owner)
            elif isinstance(value, (tuple, list)):
                for item in value: self.pin_graph(item, owner)
    def release(self, owner):
        with self._lock:
            for key in self._owners.pop(owner, ()):
                entry = self._entries.get(key)
                if entry is not None:
                    entry.owners.discard(owner)
                    if not entry.owners:
                        self.resident_bytes -= entry.own_bytes
                        self._entries.pop(key)

    def size(self, value):
        descriptor = self.descriptor(value)
        if descriptor is not None:
            return descriptor.resident_bytes
        if isinstance(value, Mapping):
            return sys.getsizeof(value) + sum(self.size(part) for pair in value.items() for part in pair)
        if isinstance(value, (tuple, list)):
            return sys.getsizeof(value) + sum(self.size(item) for item in value)
        if value is None or type(value) in {str, int, float, bool, bytes}:
            return _size(value)
        from stratbox.shared.data.selection import MemberOutcome
        if isinstance(value, MemberOutcome):
            return _size(value)
        raise ValueError('value.unsealed_owner')

    def references(self, value):
        descriptor = self.descriptor(value)
        if descriptor is not None:
            return descriptor.staged_references
        from stratbox.shared.data.selection import MemberOutcome
        if isinstance(value, MemberOutcome):
            from stratbox.shared.data.materials import staged_references
            return tuple(staged_references(value.references))
        values = value.values() if isinstance(value, Mapping) else value if isinstance(value, (tuple, list)) else ()
        return tuple(reference for item in values for reference in self.references(item))


def seal_plan_inputs(registry, plan, owner):
    """Seal literals once while a submitted plan is still private to admission."""
    seen = set()
    def visit(current):
        if id(current) in seen:
            return
        seen.add(id(current))
        registry.seal(current.outputs, owner, as_bundle=True)
        registry.seal(current.target, owner)
        for task in current.tasks:
            for name in ('inputs', 'items', 'initial', 'selector', 'forwarded'):
                if hasattr(task, name):
                    value = getattr(task, name)
                    registry.seal(value, owner, as_bundle=name == 'inputs')
            if hasattr(task, 'command'):
                registry.seal(task.command.parameters, owner)
                registry.seal(task.command.settings, owner)
                registry.seal(task.command.target, owner)
            if getattr(task, 'template', None) is not None:
                visit(task.template)
            for template in getattr(task, 'alternatives', {}).values():
                visit(template)
    visit(plan)
