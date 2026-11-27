"""Bounded streaming of the canonical typed identity representation.

The byte stream matches the canonical JSON representation for admitted values.
No caller-provided digest substitutes for content, and large byte bodies never
become a full hexadecimal string or a complete temporary JSON tree.
"""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from hashlib import sha256
import json


def exact_fingerprint(value, *, max_nodes=10000000, max_depth=128):
    from .values import canonical_tree
    active = set()
    nodes = 0
    dumps = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))

    def sequence(values, depth):
        yield '['
        first = True
        for item in values:
            if not first:
                yield ','
            first = False
            yield from emit(item, depth + 1)
        yield ']'

    def emit(item, depth=0):
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes or depth > max_depth:
            raise ValueError('identity.structure_limit')
        if item is None or type(item) in {str, int, bool}:
            yield dumps(item)
            return
        if isinstance(item, bytes):
            yield '{"bytes":"'
            for offset in range(0, len(item), 32768):
                yield item[offset:offset + 32768].hex()
            yield '"}'
            return
        key = id(item)
        if key in active:
            raise ValueError('identity.cyclic_value')
        active.add(key)
        try:
            if isinstance(item, Mapping):
                # Keys are metadata, not a second retained copy of the values.
                keys = [(json.dumps(canonical_tree(name), sort_keys=True), name) for name in item]
                keys.sort(key=lambda pair: pair[0])
                yield '{"mapping":['
                for index, (_, name) in enumerate(keys):
                    if index:
                        yield ','
                    yield '['
                    yield from emit(name, depth + 1)
                    yield ','
                    yield from emit(item[name], depth + 1)
                    yield ']'
                yield ']}'
            elif isinstance(item, (tuple, list)):
                yield '{"tuple":'
                yield from sequence(item, depth)
                yield '}'
            elif isinstance(item, (set, frozenset)):
                ordered = sorted(item, key=lambda part: json.dumps(canonical_tree(part), sort_keys=True))
                yield '{"set":'
                yield from sequence(ordered, depth)
                yield '}'
            elif is_dataclass(item) and not isinstance(item, type):
                yield '{"fields":{'
                for index, field in enumerate(sorted(fields(item), key=lambda field: field.name)):
                    if index:
                        yield ','
                    yield dumps(field.name) + ':'
                    yield from emit(object.__getattribute__(item, field.name), depth + 1)
                yield '},"type":' + dumps(type(item).__module__ + ':' + type(item).__qualname__) + '}'
            elif type(item).__module__.startswith('numpy') and type(item).__name__ == 'ndarray':
                if item.dtype.hasobject or item.dtype.kind not in 'biufcmM':
                    raise ValueError('codec.ndarray_dtype_not_admitted')
                yield '{"ndarray":{"bytes":"'
                # nditer bounds materialization even for a strided array.
                import numpy as np
                for block in np.nditer(item, flags=['external_loop', 'buffered', 'zerosize_ok'],
                        order='C', buffersize=32768):
                    yield block.tobytes().hex()
                yield '","dtype":' + dumps(item.dtype.str) + ',"shape":' + dumps(tuple(item.shape)) + '}}'
            elif type(item).__module__.startswith('pandas') and hasattr(item, 'columns') and hasattr(item, 'itertuples'):
                from .frame_codec import _atom, _axis_value, _dtype_value
                yield '{"dataframe":{"columns":' + dumps(_axis_value(item.columns))
                yield ',"dtypes":' + dumps([_dtype_value(dtype) for dtype in item.dtypes])
                yield ',"index":' + dumps(_axis_value(item.index)) + ',"rows":['
                rows = item.itertuples(index=False, name=None) if len(item.columns) else (() for _ in item.index)
                for index, row in enumerate(rows):
                    if index:
                        yield ','
                    encoded = []
                    for cell in row:
                        try:
                            encoded.append(_atom(cell))
                        except TypeError:
                            # Runtime ownership admits nested object cells even
                            # where the portable scalar-frame codec is narrower.
                            encoded.append(['owned_value', exact_fingerprint(cell,
                                max_nodes=max_nodes - nodes, max_depth=max_depth - depth - 1)])
                    yield dumps(encoded)
                yield ']}}'
            else:
                yield dumps(canonical_tree(item))
        finally:
            active.remove(key)

    digest, buffer, size = sha256(), [], 0
    for piece in emit(value):
        buffer.append(piece)
        size += len(piece)
        if size >= 65536:
            digest.update(''.join(buffer).encode())
            buffer, size = [], 0
    if buffer:
        digest.update(''.join(buffer).encode())
    return digest.hexdigest()
