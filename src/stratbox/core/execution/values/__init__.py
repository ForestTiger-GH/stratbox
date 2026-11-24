"""Common identity, snapshot and resource accounting for operation values.

Domains supply snapshot adapters and their admission checks. The execution
layer owns the identical evidence and resource mechanics around those values.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum
from pathlib import PurePath
import ast
from hashlib import sha256
import json
from functools import lru_cache
from types import UnionType
from typing import Callable
from zoneinfo import ZoneInfo

from stratbox.shared.data.documents import DocumentExtract, document_snapshot
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.observations import SubjectRef, MetricRef, PeriodRef
from stratbox.shared.data.snapshots import DatasetSnapshot, TypedTable
from stratbox.shared.data.views import ObservationView, view_snapshot
from stratbox.shared.data.workbooks import WorkbookExtract, workbook_snapshot
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

SNAPSHOT_MEDIA = "application/vnd.stratbox.dataset+json"
SnapshotFactory = Callable[[object, object], DatasetSnapshot | None]
_UNHANDLED = object()


def _scientific_value(value, convert, *, checkpoint=None, scalar_check=None):
    """Keep dataframe dependencies lazy while retaining their exact table schema."""
    modules = {kind.__module__.split(".", 1)[0] for kind in type(value).__mro__}
    if "pandas" in modules:
        import pandas
        from stratbox.shared.data.tables import table_identity
        if isinstance(value, pandas.DataFrame):
            identity = table_identity((("value", value),), allow_infinite=True, checkpoint=checkpoint,
                                      scalar_check=scalar_check)
            return {"type": "dataframe", "identity": plain(identity), "attrs": convert(value.attrs)}
        if isinstance(value, pandas.Series):
            identity = table_identity((("value", value.to_frame()),), allow_infinite=True, checkpoint=checkpoint,
                                      scalar_check=scalar_check)
            return {"type": "series", "name": convert(value.name), "identity": plain(identity),
                    "attrs": convert(value.attrs)}
        if isinstance(value, pandas.Index):
            identity = table_identity((("value", pandas.DataFrame(index=value)),), allow_infinite=True, checkpoint=checkpoint,
                                      scalar_check=scalar_check)
            return {"type": "index", "identity": plain(identity)}
        if value is pandas.NA:
            return {"type": "pandas_na"}
        if value is pandas.NaT:
            return {"type": "pandas_nat"}
        if isinstance(value, pandas.Timestamp):
            return {"type": "timestamp", "literal": value.isoformat()}
        if isinstance(value, pandas.Timedelta):
            return {"type": "timedelta", "literal": value.isoformat()}
    if "numpy" in modules:
        import numpy
        if isinstance(value, numpy.ndarray):
            return {"type": "ndarray", "dtype": value.dtype.descr if value.dtype.names else value.dtype.str, "shape": list(value.shape),
                    "values": convert(value.tolist())}
        if isinstance(value, numpy.generic):
            if value.dtype.kind in {"M", "m"}:
                return {"type": "numpy_scalar", "dtype": value.dtype.str, "literal": str(value)}
            item = value.item()
            if isinstance(item, numpy.generic):
                return {"type": "numpy_scalar", "dtype": value.dtype.str,
                        "bytes": plain(ByteIdentity.of(value.tobytes()))}
            return {"type": "numpy_scalar", "dtype": value.dtype.str, "value": convert(item)}
    return _UNHANDLED


def plain(value):
    """Encode exact control values deterministically without expanding decimals."""
    if isinstance(value, Enum):
        return plain(value.value)
    if value is None or type(value) in {bool, int, str}:
        return value
    if isinstance(value, ByteIdentity):
        return {"sha256": value.sha256, "size": value.size}
    if isinstance(value, SourcePayload):
        return {"type": "source_payload", "identity": plain(value.identity),
                "media_type": value.media_type, "source_id": value.source_id,
                "charset": value.charset}
    scientific = _scientific_value(value, plain)
    if scientific is not _UNHANDLED:
        return scientific
    if isinstance(value, Decimal):
        return {"type": "decimal", "literal": str(value)}
    if isinstance(value, ZoneInfo):
        return {"type": "timezone", "key": value.key}
    if isinstance(value, timezone):
        return {"type": "timezone", "offset_seconds": int(value.utcoffset(None).total_seconds()),
                "name": value.tzname(None)}
    if isinstance(value, (date, datetime, time)):
        return {"type": type(value).__name__, "literal": value.isoformat()}
    if isinstance(value, timedelta):
        return {"type": "duration", "days": value.days,
                "seconds": value.seconds, "microseconds": value.microseconds}
    if isinstance(value, float):
        return {"type": "float64", "literal": value.hex()}
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"type": "bytes", "identity": plain(ByteIdentity.of(bytes(value)))}
    if isinstance(value, PurePath):
        return {"type": "path", "literal": str(value)}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((plain(item) for item in value),
                      key=lambda item: canonical_manifest_bytes({"item": item}))
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("processing.control_key_unsupported")
        return {key: plain(item) for key, item in value.items()}
    if is_dataclass(value):
        return {item.name: plain(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, str):
        return str(value)
    raise ValueError("processing.control_value_unsupported")


@lru_cache(maxsize=4096)
def _trace_annotation(annotation):
    """Identify explicitly typed provenance, including postponed annotations."""
    from stratbox.shared.data.datasets import ComputationReceipt
    from typing import Union, get_args, get_origin
    trace_types = {ComputationReceipt, UsedInputReceipt}
    if annotation in trace_types:
        return True
    if isinstance(annotation, str):
        names = {"ComputationReceipt", "UsedInputReceipt"}
        def pure(node):
            if isinstance(node, ast.Name):
                return node.id in names
            if isinstance(node, ast.Constant):
                return node.value is None or node.value is Ellipsis
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                return pure(node.left) and pure(node.right)
            if isinstance(node, ast.Subscript):
                name = node.value.id if isinstance(node.value, ast.Name) else (
                    node.value.attr if isinstance(node.value, ast.Attribute) else "")
                if name in {"tuple", "list", "set", "frozenset", "Tuple", "List", "Set", "FrozenSet", "Optional", "Union"}:
                    arguments = node.slice.elts if isinstance(node.slice, ast.Tuple) else (node.slice,)
                    return all(pure(item) for item in arguments)
            return False
        try:
            tree = ast.parse(annotation, mode="eval").body
        except SyntaxError:
            return False
        return pure(tree) and any(isinstance(item, ast.Name) and item.id in names for item in ast.walk(tree))
    arguments = get_args(annotation)
    return get_origin(annotation) in {Union, UnionType, tuple, list, set, frozenset} and bool(arguments) and all(
        item is type(None) or item is Ellipsis or _trace_annotation(item) for item in arguments)


@lru_cache(maxsize=4096)
def _argument_fields(kind):
    return tuple(sorted((field for field in fields(kind) if not _trace_annotation(field.type)),
                        key=lambda field: field.name))


def argument_value(value):
    """Encode consumed content while keeping typed execution ancestry separate."""
    from stratbox.shared.data.datasets import ComputationReceipt
    from stratbox.shared.evidence import AcquisitionReceipt
    from stratbox.shared.materials import MaterialArtifact
    from stratbox.shared.data.source_context import SourceUse
    sealed = _sealed_argument(value)
    if sealed is not _UNHANDLED:
        return sealed
    if isinstance(value, ComputationReceipt):
        return None
    if isinstance(value, SourceUse):
        return {"coordinate": argument_value(value.coordinate), "input_role": value.input_role}
    if isinstance(value, AcquisitionReceipt):
        return {"type": "acquisition", **{item.name: argument_value(getattr(value, item.name))
                for item in fields(value) if item.name not in {"observed_at_utc", "shared_work_id"}}}
    if isinstance(value, MaterialArtifact):
        return {"type": "material_artifact", "contract": argument_value(value.contract),
                "representation": argument_value(value.representation),
                "series_id": value.series_id, "source_asset": argument_value(value.source_asset)}
    scientific = _scientific_value(value, argument_value)
    if scientific is not _UNHANDLED:
        return scientific
    if isinstance(value, SourcePayload):
        return plain(value)
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("processing.control_key_unsupported")
        return {key: argument_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [argument_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((argument_value(item) for item in value),
                      key=lambda item: canonical_manifest_bytes({"item": item}))
    if is_dataclass(value) and not isinstance(value, ByteIdentity):
        return {item.name: argument_value(getattr(value, item.name)) for item in _argument_fields(type(value))}
    return plain(value)


def _sealed_argument(value):
    """Use core-owned seals only where construction verified deep immutability."""
    if isinstance(value, TypedTable):
        return {"type": "typed_table", "contract": plain(value.schema),
                "identity": plain(value.identity), "row_count": len(value.rows)}
    if isinstance(value, DatasetSnapshot):
        manifest = value.manifest
        return {"type": "dataset_snapshot", "dataset_id": manifest.dataset_id,
                "version_id": manifest.version_id, "contract": plain(manifest.contract),
                "coverage": plain(manifest.coverage),
                "components": [{"name": part.name, "schema": plain(part.schema),
                    "identity": plain(part.identity), "row_count": part.row_count}
                    for part in manifest.components],
                "tables": [{"name": name, "identity": plain(table.identity)} for name, table in value.tables]}
    return _UNHANDLED


def argument_identity(value, *, checkpoint=None, budget=None, cache=None) -> ByteIdentity:
    """Stream exact semantic content with bounded memory and cancellation.

    An invocation may retain signatures of deeply immutable values. Mutable
    dataframes, lists, mappings and dataclasses containing them are scanned on
    every call, so a later mutation cannot reuse an earlier signature. Core
    typed tables and snapshots use constructor-verified content seals.
    """
    from stratbox.shared.data.datasets import ComputationReceipt
    from stratbox.shared.evidence import AcquisitionReceipt
    from stratbox.shared.materials import MaterialArtifact
    from stratbox.shared.data.source_context import SourceUse

    def check():
        if checkpoint is not None:
            checkpoint()
        elif budget is not None:
            budget.checkpoint()

    def bound(resource, amount):
        # Signing observes already-owned values; it never consumes them twice.
        if budget is not None:
            limit = getattr(budget.limits, resource)
            if limit is not None and amount > limit:
                from stratbox.core.limits import BudgetExceeded
                raise BudgetExceeded(resource)

    check()
    if isinstance(value, SourcePayload):
        bound("input_bytes", value.identity.size)
    elif isinstance(value, DatasetSnapshot):
        bound("cells", snapshot_cells(value))
    elif isinstance(value, TypedTable):
        bound("cells", len(value.rows) * len(value.schema.columns))
    elif isinstance(value, ObservationBatch):
        bound("cells", len(value.observations))
    elif type(value) is str:
        bound("input_bytes", len(value))
    metrics = None if cache is None else cache.setdefault("signature_metrics", {"scans": 0, "hits": 0})
    key = ("argument", id(value))
    retained = None if cache is None else cache.get(key)
    if retained is not None and retained[0] is value:
        if metrics is not None:
            metrics["hits"] += 1
        return retained[1]
    if metrics is not None:
        metrics["scans"] += 1
    digest, size, visits = sha256(), 0, 0
    active = set()
    leaf_encodings = {}
    quoted_encodings = {}
    encoding_size = 0
    encoding_limit = 65536 if budget is None or budget.limits.temporary_bytes is None else min(
        65536, budget.limits.temporary_bytes // 2)

    def feed(token):
        nonlocal size
        data = token.encode("utf-8")
        bound("temporary_bytes", len(data))
        digest.update(data)
        size += len(data)

    def quoted(text):
        nonlocal size, encoding_size
        # Avoid a second full encoded copy even for one large text value.
        retained = quoted_encodings.get(text) if len(text) <= 256 else None
        if retained is not None:
            digest.update(retained)
            size += len(retained)
            return
        if len(text) <= 256 and len(quoted_encodings) < 1024:
            encoded = json.dumps(text, ensure_ascii=False).encode("utf-8")
            if encoding_size + len(encoded) <= encoding_limit:
                bound("temporary_bytes", len(encoded))
                quoted_encodings[text] = encoded
                encoding_size += len(encoded)
                digest.update(encoded)
                size += len(encoded)
                return
        feed('"')
        for start in range(0, len(text), 4096):
            check()
            feed(json.dumps(text[start:start + 4096], ensure_ascii=False)[1:-1])
        feed('"')

    def scientific_scalar(item):
        if isinstance(item, (str, bytes)):
            bound("input_bytes", len(item))

    def mapping(items, depth, metadata=False, ordered=False):
        immutable = True
        feed("{")
        for index, (name, item) in enumerate(items if ordered else sorted(items)):
            if index:
                feed(",")
            quoted(name)
            feed(":")
            immutable = walk(item, depth + 1, metadata=metadata) and immutable
        feed("}")
        return immutable

    def walk(item, depth=0, *, metadata=False):
        nonlocal visits, size, encoding_size
        visits += 1
        if visits % 256 == 0:
            check()
        if depth > 64:
            raise ValueError("processing.input_structure_invalid")
        if item is None:
            feed("null")
            return True
        if type(item) is bool:
            feed("true" if item else "false")
            return True
        if type(item) is int:
            if not metadata:
                bound("input_bytes", max(1, (item.bit_length() - 1) * 30102 // 100000 + 1))
            feed(str(item))
            return True
        if type(item) is str:
            if not metadata:
                bound("input_bytes", len(item))
            quoted(item)
            return True
        if isinstance(item, Enum):
            return walk(item.value, depth + 1, metadata=metadata)
        if isinstance(item, (SubjectRef, MetricRef, PeriodRef)):
            retained = leaf_encodings.get(id(item))
            if retained is not None and retained[0] is item:
                digest.update(retained[1])
                size += len(retained[1])
                return True
            leaf_values = tuple(getattr(item, field.name) for field in fields(item))
            if (len(leaf_encodings) < 256
                    and all(value is None or isinstance(value, (str, int, bool, Decimal, date)) for value in leaf_values)
                    and sum(len(value) for value in leaf_values if isinstance(value, str)) <= 1024):
                encoded = canonical_manifest_bytes(argument_value(item))
                temporary = None if budget is None else budget.limits.temporary_bytes
                if (len(encoded) <= 4096 and encoding_size + len(encoded) <= encoding_limit
                        and (temporary is None or len(encoded) <= temporary)):
                    leaf_encodings[id(item)] = (item, encoded)
                    encoding_size += len(encoded)
                    digest.update(encoded)
                    size += len(encoded)
                    return True
        if isinstance(item, ComputationReceipt):
            return walk(None, depth + 1)
        if isinstance(item, SourceUse):
            walk({"coordinate": item.coordinate, "input_role": item.input_role}, depth + 1)
            return True
        sealed = _sealed_argument(item)
        if sealed is not _UNHANDLED:
            if isinstance(item, TypedTable):
                bound("cells", len(item.rows) * len(item.schema.columns))
            elif isinstance(item, DatasetSnapshot):
                bound("cells", snapshot_cells(item))
            walk(sealed, depth + 1, metadata=True)
            return True
        if isinstance(item, AcquisitionReceipt):
            walk({"type": "acquisition", **{field.name: getattr(item, field.name)
                for field in fields(item) if field.name not in {"observed_at_utc", "shared_work_id"}}}, depth + 1)
            return True
        if isinstance(item, SourcePayload):
            bound("input_bytes", item.identity.size)
            walk(plain(item), depth + 1, metadata=True)
            return True
        if isinstance(item, MaterialArtifact):
            walk({"type": "material_artifact", "contract": item.contract,
                "representation": item.representation, "series_id": item.series_id,
                "source_asset": item.source_asset}, depth + 1)
            return True
        modules = {kind.__module__.split(".", 1)[0] for kind in type(item).__mro__}
        if "pandas" in modules:
            import pandas
            if isinstance(item, (pandas.DataFrame, pandas.Series)):
                bound("cells", int(item.size))
                bound("input_bytes", int(item.size))
            scientific = _scientific_value(item, lambda nested: nested, checkpoint=check,
                                           scalar_check=scientific_scalar)
            if scientific is not _UNHANDLED:
                walk(scientific, depth + 1, metadata=True)
                return False  # attrs and frames remain caller-mutable.
        if "numpy" in modules:
            import numpy
            if isinstance(item, numpy.ndarray):
                bound("cells", int(item.size))
                feed('{"dtype":')
                walk(item.dtype.descr if item.dtype.names else item.dtype.str, depth + 1, metadata=True)
                feed(',"shape":')
                walk(tuple(item.shape), depth + 1)
                feed(',"type":"ndarray","values":[')
                for index, scalar in enumerate(item.flat):
                    if index:
                        feed(",")
                    walk(scalar, depth + 1)
                feed("]}")
                return False
            scientific = _scientific_value(item, lambda nested: nested, checkpoint=check)
            if scientific is not _UNHANDLED:
                return walk(scientific, depth + 1, metadata=True)
        if isinstance(item, (tuple, list, set, frozenset)):
            if id(item) in active:
                raise ValueError("processing.input_structure_invalid")
            active.add(id(item))
            members = item
            if isinstance(item, (set, frozenset)):
                bound("temporary_bytes", len(item) * 32)
                members = sorted(item, key=lambda nested: argument_identity(nested, checkpoint=check).sha256)
            feed("[")
            immutable = type(item) in {tuple, frozenset}
            for index, nested in enumerate(members):
                if index:
                    feed(",")
                immutable = walk(nested, depth + 1, metadata=metadata) and immutable
            feed("]")
            active.remove(id(item))
            return immutable
        if isinstance(item, Mapping):
            if id(item) in active or any(not isinstance(name, str) for name in item):
                raise ValueError("processing.control_key_unsupported")
            active.add(id(item))
            mapping(item.items(), depth, metadata=metadata)
            active.remove(id(item))
            return False
        if is_dataclass(item) and not isinstance(item, ByteIdentity):
            if id(item) in active:
                raise ValueError("processing.input_structure_invalid")
            active.add(id(item))
            if isinstance(item, ObservationBatch):
                bound("cells", len(item.observations))
            immutable = mapping(((field.name, getattr(item, field.name)) for field in _argument_fields(type(item))),
                                depth, metadata=metadata, ordered=True)
            active.remove(id(item))
            return bool(getattr(type(item), "__dataclass_params__").frozen) and immutable
        walk(plain(item), depth + 1, metadata=True)
        return isinstance(item, (ByteIdentity, Decimal, date, time, timedelta, timezone, ZoneInfo,
                                 float, bytes, PurePath))

    feed('{"value":')
    immutable = walk(value)
    feed("}")
    check()
    identity = ByteIdentity(digest.hexdigest(), size)
    if cache is not None and immutable:
        cache[key] = (value, identity)
    return identity


def snapshot_of(value, invocation=None, *, snapshot_factory: SnapshotFactory | None = None):
    """Resolve an optional domain adapter once per retained value and invocation."""
    cache = None
    if invocation is not None:
        cache = getattr(invocation, "_value_snapshots", None)
        if cache is None:
            cache = invocation._value_snapshots = {}
        key = (id(value), snapshot_factory)
        retained = cache.get(key)
        if retained is not None and retained[0] is value:
            return retained[1]
    snapshot = snapshot_factory(value, invocation) if snapshot_factory is not None else None
    if snapshot is None:
        if isinstance(value, DatasetSnapshot):
            snapshot = value
        elif isinstance(value, WorkbookExtract):
            snapshot = workbook_snapshot(value)
        elif isinstance(value, DocumentExtract):
            snapshot = document_snapshot(value)
        elif isinstance(value, ObservationView):
            snapshot = view_snapshot(value)
        elif isinstance(value, ObservationBatch):
            snapshot = observation_snapshot(value)
    if snapshot is not None and not isinstance(snapshot, DatasetSnapshot):
        raise ValueError("processing.snapshot_adapter_invalid")
    if cache is not None and snapshot is not None:
        cache[key] = (value, snapshot)
    return snapshot


def snapshot_size(snapshot: DatasetSnapshot) -> int:
    return snapshot.identity.size + sum(table.identity.size for _, table in snapshot.tables)


def snapshot_cells(snapshot: DatasetSnapshot) -> int:
    return sum(len(table.rows) * max(1, len(table.schema.columns)) for _, table in snapshot.tables)


def value_identity(value) -> ByteIdentity:
    """Identify the supplied value, preserving collection position and count."""
    identity = getattr(value, "identity", None)
    if isinstance(identity, ByteIdentity):
        return identity
    snapshot = snapshot_of(value)
    if snapshot is not None:
        return snapshot.identity
    return argument_identity(value)


@dataclass(frozen=True, slots=True)
class ValueDescriptor:
    identity: ByteIdentity
    media_type: str
    source_id: str | None
    size: int
    cells: int
    snapshot: DatasetSnapshot | None = None


def describe_value(value, invocation=None, *, snapshot_factory: SnapshotFactory | None = None):
    snapshot = snapshot_of(value, invocation, snapshot_factory=snapshot_factory)
    if snapshot is not None:
        return ValueDescriptor(snapshot.identity, SNAPSHOT_MEDIA, snapshot.manifest.dataset_id,
                               snapshot_size(snapshot), snapshot_cells(snapshot), snapshot)
    identity = value_identity(value)
    return ValueDescriptor(identity,
        value.media_type if isinstance(value, SourcePayload) else "application/json",
        value.source_id if isinstance(value, SourcePayload) else None,
        identity.size, 0)


def use_value(value, invocation, role, *, snapshot_factory: SnapshotFactory | None = None,
              include_lineage=False, charge_cells=True):
    """Retain exact evidence and charge every collection occurrence separately."""
    invocation.check_cancelled()
    if isinstance(value, (tuple, list)):
        for index, member in enumerate(value):
            use_value(member, invocation, f"{role}.{index}", snapshot_factory=snapshot_factory,
                      include_lineage=include_lineage, charge_cells=charge_cells)
        return
    descriptor = describe_value(value, invocation, snapshot_factory=snapshot_factory)
    invocation.budget.charge("input_bytes", descriptor.size)
    if charge_cells and descriptor.cells:
        invocation.budget.charge("cells", descriptor.cells)
    invocation.use(UsedInputReceipt(role, descriptor.identity, descriptor.media_type, "inline",
        descriptor.source_id, version=descriptor.identity if descriptor.snapshot is not None else None))
    if include_lineage:
        lineage = descriptor.snapshot.manifest.inputs if descriptor.snapshot is not None else getattr(value, "lineage", ())
        for receipt in lineage:
            invocation.use(receipt)


def account_snapshot(snapshot, invocation, *, table_prefix="component:",
                     manifest_key="manifest", charge_cells=True):
    if charge_cells:
        invocation.budget.charge("cells", snapshot_cells(snapshot))
    for name, table in snapshot.tables:
        invocation.check_cancelled()
        invocation.account_output(table.identity, key=table_prefix + name)
    if manifest_key is not None:
        invocation.account_output(snapshot.identity, key=manifest_key)
    return snapshot.identity


def account_value(value, invocation, *, snapshot_factory: SnapshotFactory | None = None,
                  table_prefix="component:", manifest_key="manifest", key="returned",
                  charge_cells=True):
    invocation.check_cancelled()
    descriptor = describe_value(value, invocation, snapshot_factory=snapshot_factory)
    if descriptor.snapshot is not None:
        return account_snapshot(descriptor.snapshot, invocation, table_prefix=table_prefix,
                                manifest_key=manifest_key, charge_cells=charge_cells)
    invocation.account_output(descriptor.identity, key=key)
    return descriptor.identity


def record_value(value, request, definition, invocation, *, snapshot_factory: SnapshotFactory | None = None,
                 table_prefix="component:", manifest_key="manifest", key="returned",
                 charge_cells=True, resources=None):
    identity = account_value(value, invocation, snapshot_factory=snapshot_factory,
        table_prefix=table_prefix, manifest_key=manifest_key, key=key, charge_cells=charge_cells)
    parameters = {name: plain(getattr(request, name)) for name in definition.processing.parameters}
    return invocation.record(identity, parameters=parameters, resources=resources)
