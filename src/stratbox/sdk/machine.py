"""Bounded data projections and invocation through the ordinary SDK service."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from math import isfinite


def project(value, *, max_items=100, max_depth=10):
    if type(max_items) is not int or max_items < 1 or type(max_depth) is not int or max_depth < 1:
        raise ValueError('machine.invalid_projection_limit')
    budget = [max_items]
    def convert(item, depth):
        if depth > max_depth:
            return {'truncated': 'depth', 'type': type(item).__name__}
        if item is None or type(item) in (str, int, bool):
            return item
        if isinstance(item, float):
            if not isfinite(item):
                raise ValueError('machine.nonfinite')
            return item
        if isinstance(item, Decimal):
            if not item.is_finite():
                raise ValueError('machine.nonfinite')
            return {'decimal': str(item)}
        if isinstance(item, bytes):
            return {'sha256': sha256(item).hexdigest(), 'size': len(item)}
        if isinstance(item, (date, datetime)):
            return item.isoformat()
        if isinstance(item, type):
            return {'python_type': item.__module__ + ':' + item.__qualname__}
        if is_dataclass(item):
            item = {field.name: getattr(item, field.name) for field in fields(item) if not field.name.startswith('_')}
        if isinstance(item, Mapping):
            result = {}
            for key, member in item.items():
                if budget[0] <= 0:
                    result['__truncated__'] = True
                    break
                if not isinstance(key, str):
                    raise TypeError('machine.string_keys_required')
                budget[0] -= 1
                result[key] = convert(member, depth + 1)
            return result
        if isinstance(item, (tuple, list, set, frozenset)):
            source = sorted(item, key=repr) if isinstance(item, (set, frozenset)) else item
            result = []
            for member in source:
                if budget[0] <= 0:
                    result.append({'truncated': 'items'})
                    break
                budget[0] -= 1
                result.append(convert(member, depth + 1))
            return result
        raise TypeError('machine.unsupported_projection:' + type(item).__name__)
    return convert(value, 0)


def invoke(box, request):
    if not isinstance(request, Mapping) or not isinstance(request.get('capability_id'), str):
        raise TypeError('machine.invocation_required')
    allowed = {'capability_id', 'inputs', 'parameters', 'target', 'outputs', 'timeout'}
    if request.keys() - allowed:
        raise ValueError('machine.unknown_request_fields')
    return box.invoke(request['capability_id'], inputs=request.get('inputs'), parameters=request.get('parameters'),
                      target=request.get('target'), outputs=request.get('outputs'), timeout=request.get('timeout'))
