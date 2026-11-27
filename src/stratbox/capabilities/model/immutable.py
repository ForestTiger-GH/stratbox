"""Immutable authored metadata and canonical dependency evidence."""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from types import MappingProxyType


def freeze(value, *, _typed=False, _memo=None):
    memo = {} if _memo is None else _memo
    key = (id(value), _typed)
    if key in memo: return memo[key]
    if type(value).__module__.startswith('pandas.') and hasattr(value, 'copy') and hasattr(value, 'columns'):
        copied = value.copy(deep=True)
        memo[key] = copied
        return copied
    if type(value).__module__.startswith('numpy') and type(value).__name__ == 'ndarray':
        copied = value.copy()
        memo[key] = copied
        return copied
    # Scientific runtime carriers own their internal lifecycle and expose a
    # competent content identity. Authored definitions still undergo recursive
    # normalization, so mutable settings cannot hide behind a plan fingerprint.
    if not getattr(type(value), '__authored_definition__', False):
        exact = getattr(value, 'fingerprint', None)
        if isinstance(exact, str) and exact:
            return value
    if isinstance(value, Mapping):
        if not _typed and any(not isinstance(key, str) for key in value):
            raise TypeError('metadata.string_keys_required')
        copied = MappingProxyType({name: freeze(item, _typed=_typed, _memo=memo) for name, item in value.items()})
        memo[key] = copied
        return copied
    if isinstance(value, (tuple, list)):
        copied = tuple(freeze(item, _typed=_typed, _memo=memo) for item in value)
        memo[key] = copied
        return copied
    if isinstance(value, (set, frozenset)):
        copied = frozenset(freeze(item, _typed=_typed, _memo=memo) for item in value)
        memo[key] = copied
        return copied
    if is_dataclass(value) and not isinstance(value, type):
        if not value.__dataclass_params__.frozen:
            raise TypeError('metadata.mutable_dataclass')
        # A typed data record can legitimately carry coordinate-keyed maps
        # (JSON token paths, numerical matrices). Metadata map names remain
        # strings; mapping payloads are detached without changing their keys.
        changes = {f.name: freeze(getattr(value, f.name), _typed=f.name not in {'metadata', 'settings'}, _memo=memo)
                   for f in fields(value) if f.init}
        copied = replace(value, **changes)
        memo[key] = copied
        return copied
    return value


def freeze_bindings(values):
    """Freeze named invocation bindings while retaining typed payload map keys."""
    if not isinstance(values, Mapping) or any(not isinstance(name, str) for name in values):
        raise TypeError('metadata.string_keys_required')
    return freeze(values, _typed=True)


def canonical(value, *, _runtime=False):
    if not getattr(type(value),'__authored_definition__',False):
        exact=getattr(value,'fingerprint',None)
        if isinstance(exact,str) and exact:
            return {'runtime_type':type(value).__module__+':'+type(value).__qualname__,'fingerprint':exact}
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, bytes):
        return {'bytes': sha256(value).hexdigest(), 'size': len(value)}
    if isinstance(value, (date, datetime)):
        return {'date': value.isoformat()}
    if isinstance(value, Decimal):
        return {'decimal': str(value)}
    if isinstance(value, type):
        return {'type': value.__module__ + ':' + value.__qualname__}
    if isinstance(value, Enum):
        return canonical(value.value, _runtime=_runtime)
    if type(value) is float:
        if _runtime:
            from stratbox.shared.data.values import canonical_tree
            return canonical_tree(value)
        if value != value or value in (float('inf'), -float('inf')):
            raise ValueError('metadata.nonfinite')
        return {'float': value.hex()}
    if type(value).__module__.startswith(('pandas.', 'numpy.')):
        from stratbox.shared.data.values import fingerprint as value_fingerprint
        return {'runtime_value': type(value).__module__ + ':' + type(value).__qualname__,
                'content_identity': value_fingerprint(value)}
    if is_dataclass(value) and type(value).__module__.startswith('stratbox.shared.data.'):
        # Shared data carriers have their own exact runtime canonicalization,
        # including typed coordinate maps and scientific missing values.
        from stratbox.shared.data.values import fingerprint as value_fingerprint
        return {'runtime_value': type(value).__module__ + ':' + type(value).__qualname__,
                'content_identity': value_fingerprint(value)}
    if is_dataclass(value):
        runtime_fields = {
            'CommandTask': {'inputs'}, 'InputGuard': {'value'},
            'MapTask': {'items'}, 'RepeatTask': {'initial'},
            'CollectTask': {'items'}, 'DispatchTask': {'selector'},
            'PreparedScope': {'outputs'}, 'PreparedPlan': {'outputs'},
            'InvocationRequest': {'inputs'}, 'Call': {'inputs'},
            'MapCall': {'items', 'inputs'}, 'CollectCall': {'items'},
            'RepeatUntil': {'initial', 'inputs'}, 'DispatchCall': {'selector', 'inputs'},
            'GraphBody': {'outputs'},
        }.get(type(value).__name__, set()) if type(value).__module__.startswith('stratbox.capabilities.') else set()
        return {'class': type(value).__module__ + ':' + type(value).__qualname__,
                'fields': {f.name: canonical(getattr(value, f.name), _runtime=_runtime or f.name in runtime_fields)
                           for f in fields(value) if f.compare}}
    if isinstance(value, Mapping):
        if all(isinstance(key, str) for key in value):
            return {key: canonical(item, _runtime=_runtime) for key, item in sorted(value.items())}
        pairs = [(canonical(key, _runtime=_runtime), canonical(item, _runtime=_runtime)) for key, item in value.items()]
        return {'mapping': sorted(pairs, key=lambda pair: json.dumps(pair[0], sort_keys=True))}
    if isinstance(value, (tuple, list)):
        return [canonical(item, _runtime=_runtime) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((canonical(item, _runtime=_runtime) for item in value), key=lambda v: json.dumps(v, sort_keys=True))
    # Runtime objects with a competent retained identity need not serialize their payload.
    identity = getattr(value, 'identity', None)
    if identity is not None and identity is not value:
        return {'value_class': type(value).__module__ + ':' + type(value).__qualname__, 'identity': canonical(identity, _runtime=_runtime)}
    raise TypeError('metadata.opaque_identity:' + type(value).__name__)


def fingerprint(value):
    return sha256(json.dumps(canonical(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
