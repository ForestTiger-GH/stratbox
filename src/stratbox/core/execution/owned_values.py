"""Owned payload measurement, scientific cell counts and private reader copies."""
from dataclasses import fields, is_dataclass, replace
from typing import Mapping
import copy
import sys
import re
from types import MemberDescriptorType
from datetime import date,time,timedelta
from decimal import Decimal
from enum import Enum

from stratbox.shared.data.values import fingerprint

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


def _isolate(value, memo=None):
    """Give mutable tabular payloads a private owner without copying immutable bytes."""
    memo = {} if memo is None else memo
    if id(value) in memo: return memo[id(value)]
    if isinstance(value,(date,time,timedelta,Decimal,Enum,re.Pattern)): return value
    if isinstance(value,bytearray):
        result = bytearray(value); memo[id(value)] = result; return result
    if isinstance(value,memoryview):
        result = memoryview(value.tobytes()).cast(value.format,shape=value.shape)
        memo[id(value)] = result; return result
    if hasattr(value, "memory_usage") and hasattr(value, "copy"):
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
        result.update({key: _isolate(item, memo) for key, item in value.items()}); return result
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
        updates = {item.name: _isolate(getattr(value, item.name), memo) for item in fields(value)}
        try:
            result = replace(value, **updates); memo[id(value)] = result; return result
        except (TypeError, ValueError):
            return copy.deepcopy(value)
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
    return value



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
