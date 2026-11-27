"""Bounded inspection and private snapshots before accepting prepared plans."""
from dataclasses import dataclass, fields, is_dataclass
from collections.abc import Mapping
from types import MappingProxyType
import sys
from types import FunctionType, BuiltinFunctionType, MethodType, MemberDescriptorType

from .owned_values import _isolate, copy_memo


class AdmissionRejected(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PlanFootprint:
    nodes: int
    bytes: int


def inspect_plan(plan, *, max_nodes, max_bytes, max_objects=1000000, max_depth=128, owned_descriptor=None):
    """Count the whole retained object graph, stopping before allocating a copy.

    Shared immutable referents count once within a plan. Scientific arrays get a
    cheap storage lower bound before object-valued cells are inspected.
    """
    from stratbox.capabilities.plan.models import PreparedPlan
    if not isinstance(plan,PreparedPlan): raise AdmissionRejected("admission.prepared_plan_required")
    total = objects = nodes = 0
    seen, active = set(), set()
    def charge(amount):
        nonlocal total
        total += amount
        if total > max_bytes: raise AdmissionRejected("admission.plan_bytes")
    def visit(value,depth=0):
        nonlocal objects,nodes
        if depth > max_depth: raise AdmissionRejected("admission.plan_depth")
        key = id(value)
        if key in active: raise AdmissionRejected("admission.cyclic_plan_value")
        if key in seen: return
        seen.add(key); objects += 1
        if objects > max_objects: raise AdmissionRejected("admission.plan_objects")
        if owned_descriptor is not None:
            descriptor = owned_descriptor(value)
            if descriptor is not None and not descriptor.expressions:
                charge(64)
                return
        if isinstance(value,type): charge(64); return
        if isinstance(value,(FunctionType,BuiltinFunctionType,MethodType)):
            raise AdmissionRejected("admission.opaque_callable")
        if isinstance(value,memoryview):
            charge(value.nbytes+sys.getsizeof(value)); return
        if isinstance(value,(str,bytes,bytearray)):
            charge(sys.getsizeof(value)); return
        module = type(value).__module__
        if module == "stratbox.capabilities.plan.models" and (hasattr(type(value),"kind") or isinstance(value,PreparedPlan) or type(value).__name__ == "PreparedScope"):
            nodes += 1
            if nodes > max_nodes: raise AdmissionRejected("admission.plan_nodes")
        if isinstance(value,PreparedPlan):
            if len(value.tasks)+len(value.scopes)+1 > max_nodes-nodes+1:
                raise AdmissionRejected("admission.plan_nodes")
        active.add(key)
        try:
            if module.startswith("numpy") and type(value).__name__ == "ndarray":
                charge(int(value.nbytes)+128)
                if value.dtype.hasobject:
                    for item in value.flat: visit(item,depth+1)
            elif module.startswith("pandas") and hasattr(value,"columns"):
                import pandas as pd
                charge(int(pd.DataFrame.memory_usage(value,index=True,deep=False).sum())+256)
                for position,dtype in enumerate(value.dtypes):
                    if dtype.kind == "O":
                        for item in value.iloc[:,position].array: visit(item,depth+1)
                visit(tuple(value.columns),depth+1)
                if value.index.dtype.kind == "O":
                    for item in value.index: visit(item,depth+1)
            elif isinstance(value,Mapping):
                charge(64+len(value)*32)
                for name,item in value.items(): visit(name,depth+1); visit(item,depth+1)
            elif isinstance(value,(tuple,list,set,frozenset)):
                charge(64+len(value)*8)
                for item in value: visit(item,depth+1)
            elif is_dataclass(value):
                charge(64+len(fields(value))*8)
                for item in fields(value): visit(object.__getattribute__(value,item.name),depth+1)
            else:
                charge(sys.getsizeof(value))
                try: attributes = object.__getattribute__(value,"__dict__")
                except AttributeError: attributes = None
                if attributes is not None: visit(attributes,depth+1)
                for cls in type(value).__mro__:
                    for name,descriptor in vars(cls).items():
                        if isinstance(descriptor,MemberDescriptorType) and name not in {"__dict__","__weakref__"}:
                            try: item = object.__getattribute__(value,name)
                            except AttributeError: continue
                            visit(item,depth+1)
        finally: active.remove(key)
    visit(plan)
    return PlanFootprint(nodes,total)


def replace_record(record, **updates):
    """Clone an already validated plan record without running authoring hooks."""
    copied = object.__new__(type(record))
    for item in fields(record): object.__setattr__(copied,item.name,updates.get(item.name,getattr(record,item.name)))
    return copied


def snapshot_plan(plan, *, max_bytes=None):
    """Detach queued literals without reconstructing or resolving definitions."""
    memo = copy_memo(max_bytes) if max_bytes is not None else {}
    def snapshot(value):
        if id(value) in memo: return memo[id(value)]
        if isinstance(value,type): return value
        if is_dataclass(value) and type(value).__module__.startswith("stratbox.capabilities."):
            copied = object.__new__(type(value)); memo[id(value)] = copied
            for item in fields(value): object.__setattr__(copied,item.name,snapshot(getattr(value,item.name)))
            return copied
        if isinstance(value,Mapping):
            copied = MappingProxyType({snapshot(key):snapshot(item) for key,item in value.items()})
            memo[id(value)] = copied; return copied
        if isinstance(value,(tuple,list)):
            copied = tuple(snapshot(item) for item in value); memo[id(value)] = copied; return copied
        if isinstance(value,(set,frozenset)):
            copied = frozenset(snapshot(item) for item in value); memo[id(value)] = copied; return copied
        copied = _isolate(value,memo)
        memo[id(value)] = copied
        return copied
    return snapshot(plan)
