"""Immutable authored metadata and canonical dependency evidence."""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from types import MappingProxyType


def freeze(value):
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError('metadata.string_keys_required')
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze(item) for item in value)
    if is_dataclass(value) and not isinstance(value, type):
        if not value.__dataclass_params__.frozen:
            raise TypeError('metadata.mutable_dataclass')
        changes = {f.name: freeze(getattr(value, f.name)) for f in fields(value) if f.init}
        return replace(value, **changes)
    return value


def canonical(value):
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
        return canonical(value.value)
    if type(value) is float:
        if value != value or value in (float('inf'), -float('inf')):
            raise ValueError('metadata.nonfinite')
        return {'float': value.hex()}
    if is_dataclass(value):
        return {'class': type(value).__module__ + ':' + type(value).__qualname__,
                'fields': {f.name: canonical(getattr(value, f.name)) for f in fields(value) if f.compare}}
    if isinstance(value, Mapping):
        return {key: canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [canonical(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((canonical(item) for item in value), key=lambda v: json.dumps(v, sort_keys=True))
    # Runtime objects with a competent retained identity need not serialize their payload.
    identity = getattr(value, 'identity', None)
    if identity is not None and identity is not value:
        return {'value_class': type(value).__module__ + ':' + type(value).__qualname__, 'identity': canonical(identity)}
    raise TypeError('metadata.opaque_identity:' + type(value).__name__)


def fingerprint(value):
    return sha256(json.dumps(canonical(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
