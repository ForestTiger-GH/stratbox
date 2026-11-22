"""Explicit, portable pandas frames carried by typed dataset tables.

The companion descriptor preserves axes, categorical dictionaries, nullable
sentinels and dtypes. It contains data only; decoding never imports a class named
by the descriptor. Homogeneous scalar columns use native table types. Mixed
object columns use an explicit tagged scalar encoding within TEXT columns.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
import json
import re

from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.snapshots import ColumnSchema, ScalarType, TableSchema, TypedTable
from stratbox.shared.data.tables import table_identity
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

_SCHEMA = "stratbox.dataframe.v1"
_DTYPES = frozenset({
    "object", "bool", "boolean", "string", "str", "int8", "int16", "int32", "int64",
    "uint8", "uint16", "uint32", "uint64", "float32", "float64",
    "Int8", "Int16", "Int32", "Int64", "UInt8", "UInt16", "UInt32", "UInt64",
    "Float32", "Float64", "datetime64[ns]", "datetime64[us]", "datetime64[ms]",
    "datetime64[s]", "timedelta64[ns]", "timedelta64[us]", "timedelta64[ms]", "timedelta64[s]",
})
_NATIVE = {
    "bool": ScalarType.BOOLEAN, "int": ScalarType.INTEGER, "float": ScalarType.FLOAT64,
    "decimal": ScalarType.DECIMAL, "text": ScalarType.TEXT, "date": ScalarType.DATE,
}


def _atom(value):
    import numpy as np
    import pandas as pd

    if value is None:
        return ["none"]
    if value is pd.NA:
        return ["na"]
    if value is pd.NaT:
        return ["nat"]
    if isinstance(value, np.datetime64):
        return _atom(pd.Timestamp(value))
    if isinstance(value, np.timedelta64):
        return _atom(pd.Timedelta(value))
    if isinstance(value, np.generic):
        value = value.item()
    if type(value) is bool:
        return ["bool", value]
    if type(value) is int:
        return ["int", str(value)]
    if type(value) is float:
        return ["float", value.hex()]
    if isinstance(value, Decimal) and value.is_finite():
        return ["decimal", str(value)]
    if isinstance(value, pd.Timestamp):
        return ["timestamp", value.isoformat()]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat()]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, time):
        return ["time", value.isoformat()]
    if isinstance(value, pd.Timedelta):
        return ["timedelta_ns", str(value.value)]
    if isinstance(value, timedelta):
        return ["timedelta_us", str((value.days * 86400 + value.seconds) * 1_000_000 + value.microseconds)]
    if type(value) is str:
        return ["text", value]
    if isinstance(value, tuple):
        return ["tuple", [_atom(item) for item in value]]
    raise TypeError("dataframe.scalar_unsupported")


def _unatom(value):
    import pandas as pd

    if not isinstance(value, list) or not value or len(value) > 2:
        raise ValueError("dataframe.scalar_invalid")
    tag = value[0]
    if tag in {"none", "na", "nat"} and len(value) == 1:
        return {"none": None, "na": pd.NA, "nat": pd.NaT}[tag]
    if len(value) != 2:
        raise ValueError("dataframe.scalar_invalid")
    item = value[1]
    if tag == "bool" and type(item) is bool:
        result = item
    elif tag == "int" and isinstance(item, str):
        result = int(item)
    elif tag == "float" and isinstance(item, str):
        result = float.fromhex(item)
    elif tag == "decimal" and isinstance(item, str):
        result = Decimal(item)
    elif tag == "text" and isinstance(item, str):
        result = item
    elif tag == "date" and isinstance(item, str):
        result = date.fromisoformat(item)
    elif tag == "time" and isinstance(item, str):
        result = time.fromisoformat(item)
    elif tag == "datetime" and isinstance(item, str):
        result = datetime.fromisoformat(item)
    elif tag == "timestamp" and isinstance(item, str):
        result = pd.Timestamp(item)
    elif tag == "timedelta_ns" and isinstance(item, str):
        result = pd.Timedelta(int(item), unit="ns")
    elif tag == "timedelta_us" and isinstance(item, str):
        result = timedelta(microseconds=int(item))
    elif tag == "tuple" and isinstance(item, list):
        result = tuple(_unatom(x) for x in item)
    else:
        raise ValueError("dataframe.scalar_invalid")
    if _atom(result) != value:
        raise ValueError("dataframe.scalar_noncanonical")
    return result


def _dtype_value(dtype):
    import pandas as pd

    if isinstance(dtype, pd.CategoricalDtype):
        return {"kind": "category", "dtype": _dtype_value(dtype.categories.dtype),
                "ordered": dtype.ordered, "categories": [_atom(x) for x in dtype.categories]}
    text = str(dtype)
    if text not in _DTYPES and not re.fullmatch(r"datetime64\[(?:ns|us|ms|s), [A-Za-z0-9_+/:. -]+\]", text):
        raise ValueError("dataframe.dtype_unsupported")
    return {"kind": "scalar", "dtype": text}


def _dtype_from(value):
    import pandas as pd

    if not isinstance(value, dict):
        raise ValueError("dataframe.dtype_invalid")
    if value.get("kind") == "category" and set(value) == {"kind", "dtype", "ordered", "categories"}:
        if type(value["ordered"]) is not bool or not isinstance(value["categories"], list):
            raise ValueError("dataframe.dtype_invalid")
        categories = pd.Index([_unatom(x) for x in value["categories"]],
                              dtype=_dtype_from(value["dtype"]), tupleize_cols=False)
        result = pd.CategoricalDtype(categories, ordered=value["ordered"])
    elif value.get("kind") == "scalar" and set(value) == {"kind", "dtype"}:
        text = value["dtype"]
        if not isinstance(text, str) or (text not in _DTYPES and not re.fullmatch(
                r"datetime64\[(?:ns|us|ms|s), [A-Za-z0-9_+/:. -]+\]", text)):
            raise ValueError("dataframe.dtype_unsupported")
        result = pd.api.types.pandas_dtype(text)
    else:
        raise ValueError("dataframe.dtype_invalid")
    if _dtype_value(result) != value:
        raise ValueError("dataframe.dtype_noncanonical")
    return result


def _axis_value(axis):
    import pandas as pd

    multi = isinstance(axis, pd.MultiIndex)
    dtypes = tuple(axis.dtypes) if multi else (axis.dtype,)
    return {"multi": multi, "names": [_atom(x) for x in axis.names],
            "dtypes": [_dtype_value(dtype) for dtype in dtypes],
            "values": [_atom(x) for x in axis]}


def _axis_from(value):
    import pandas as pd

    if not isinstance(value, dict) or set(value) != {"multi", "names", "dtypes", "values"}:
        raise ValueError("dataframe.axis_invalid")
    if type(value["multi"]) is not bool or any(not isinstance(value[key], list) for key in ("names", "dtypes", "values")):
        raise ValueError("dataframe.axis_invalid")
    names = [_unatom(x) for x in value["names"]]
    dtypes = [_dtype_from(x) for x in value["dtypes"]]
    labels = [_unatom(x) for x in value["values"]]
    if not names or len(names) != len(dtypes):
        raise ValueError("dataframe.axis_invalid")
    if value["multi"]:
        if any(not isinstance(x, tuple) or len(x) != len(names) for x in labels):
            raise ValueError("dataframe.axis_invalid")
        arrays = [pd.Index([x[index] for x in labels], dtype=dtype, tupleize_cols=False)
                  for index, dtype in enumerate(dtypes)]
        result = pd.MultiIndex.from_arrays(arrays, names=names)
    else:
        if len(names) != 1:
            raise ValueError("dataframe.axis_invalid")
        result = pd.Index(labels, dtype=dtypes[0], name=names[0], tupleize_cols=False)
    if _axis_value(result) != value:
        raise ValueError("dataframe.axis_noncanonical")
    return result


def _column(values, name):
    atoms = tuple(_atom(value) for value in values)
    missing = [(index, atom) for index, atom in enumerate(atoms)
               if atom[0] in {"none", "na", "nat"} or atom == ["float", "nan"]]
    tags = {atom[0] for atom in atoms if atom[0] not in {"none", "na", "nat"} and atom != ["float", "nan"]}
    if len(tags) == 1 and next(iter(tags)) in _NATIVE:
        tag = next(iter(tags))
        kind = _NATIVE[tag]
        absent = {index for index, _ in missing}
        data = tuple(None if index in absent else _unatom(atom) for index, atom in enumerate(atoms))
        return ColumnSchema(name, kind, nullable=bool(missing)), data, {"encoding": "native", "missing": missing}
    data = tuple(canonical_manifest_bytes(atom).decode("utf-8") for atom in atoms)
    return ColumnSchema(name, ScalarType.TEXT), data, {"encoding": "tagged", "missing": []}


def _values(column, rows, descriptor):
    if not isinstance(descriptor, dict) or set(descriptor) != {"encoding", "missing"} or not isinstance(descriptor["missing"], list):
        raise ValueError("dataframe.column_invalid")
    if descriptor["encoding"] == "tagged":
        if descriptor["missing"] or column.scalar_type is not ScalarType.TEXT:
            raise ValueError("dataframe.column_invalid")
        return [_unatom(json.loads(value)) for value in rows]
    if descriptor["encoding"] != "native":
        raise ValueError("dataframe.column_invalid")
    values = list(rows)
    seen = set()
    for pair in descriptor["missing"]:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("dataframe.missing_invalid")
        index, atom = pair
        if type(index) is not int or index in seen or not 0 <= index < len(values) or values[index] is not None:
            raise ValueError("dataframe.missing_invalid")
        if atom[0] not in {"none", "na", "nat"} and atom != ["float", "nan"]:
            raise ValueError("dataframe.missing_invalid")
        values[index] = _unatom(atom)
        seen.add(index)
    return values


def frame_to_table(frame, *, contract: DataContract, max_cells: int = 5_000_000, checkpoint=None):
    """Return a typed value table and a JSON-safe, versioned frame descriptor."""
    import pandas as pd

    if not isinstance(frame, pd.DataFrame) or type(max_cells) is not int or max_cells < 0:
        raise ValueError("dataframe.invalid")
    if max(1, len(frame)) * max(1, len(frame.columns)) > max_cells:
        raise ValueError("dataframe.cell_limit")
    if checkpoint is not None:
        checkpoint()
    columns, values, fields = [], [], []
    for index in range(frame.shape[1]):
        if checkpoint is not None:
            checkpoint()
        column, data, descriptor = _column(frame.iloc[:, index].tolist(), f"column_{index}")
        columns.append(column)
        values.append(data)
        fields.append(descriptor)
    # A row ordinal retains row count for zero-column frames.
    schema = TableSchema(contract, (ColumnSchema("row", ScalarType.INT64), *columns), ("row",))
    table = TypedTable(schema, tuple((index, *(value[index] for value in values)) for index in range(len(frame))))
    identity = table_identity((("frame", frame),), checkpoint=checkpoint, allow_infinite=True)
    descriptor = {"schema": _SCHEMA, "index": _axis_value(frame.index), "columns": _axis_value(frame.columns),
                  "dtypes": [_dtype_value(dtype) for dtype in frame.dtypes], "fields": fields,
                  "frame_identity": {"sha256": identity.sha256, "size": identity.size},
                  "table_identity": {"sha256": table.identity.sha256, "size": table.identity.size}}
    # Tuples in missing masks are normalized to JSON lists for stable replay.
    return table, json.loads(canonical_manifest_bytes(descriptor))


def frame_from_table(table: TypedTable, metadata: dict, *, max_cells: int = 5_000_000, checkpoint=None):
    """Restore and verify the complete frame, including its original fingerprint."""
    import pandas as pd

    keys = {"schema", "index", "columns", "dtypes", "fields", "frame_identity", "table_identity"}
    if not isinstance(table, TypedTable) or not isinstance(metadata, dict) or set(metadata) != keys or metadata["schema"] != _SCHEMA:
        raise ValueError("dataframe.descriptor_invalid")
    if type(max_cells) is not int or max_cells < 0 or max(1, len(table.rows)) * max(1, len(table.schema.columns) - 1) > max_cells:
        raise ValueError("dataframe.cell_limit")
    if table.identity != ByteIdentity(**metadata["table_identity"]):
        raise ValueError("dataframe.table_identity_mismatch")
    if checkpoint is not None:
        checkpoint()
    width = len(table.schema.columns) - 1
    if (width < 0 or table.schema.primary_key != ("row",)
            or tuple(column.name for column in table.schema.columns) != ("row", *(f"column_{i}" for i in range(width)))
            or [row[0] for row in table.rows] != list(range(len(table.rows)))
            or any(not isinstance(metadata[key], list) or len(metadata[key]) != width for key in ("dtypes", "fields"))):
        raise ValueError("dataframe.table_invalid")
    columns = {}
    for index, (dtype, descriptor) in enumerate(zip(metadata["dtypes"], metadata["fields"])):
        if checkpoint is not None:
            checkpoint()
        values = _values(table.schema.columns[index + 1], [row[index + 1] for row in table.rows], descriptor)
        columns[index] = pd.Series(values, dtype=_dtype_from(dtype))
    result = pd.DataFrame(columns, index=pd.RangeIndex(len(table.rows)))
    result.index = _axis_from(metadata["index"])
    result.columns = _axis_from(metadata["columns"])
    if table_identity((("frame", result),), checkpoint=checkpoint, allow_infinite=True) != ByteIdentity(**metadata["frame_identity"]):
        raise ValueError("dataframe.frame_identity_mismatch")
    return result


scalar_to_value = _atom
scalar_from_value = _unatom

__all__ = ("frame_to_table", "frame_from_table", "scalar_to_value", "scalar_from_value")
