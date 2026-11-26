"""Exact scalar, dtype and axis data for portable scientific pandas values.

The vocabulary is explicit data. Descriptors never import classes or select a
component release. The Stratbox repository build owns this encoding.
"""
from __future__ import annotations
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import re


_DTYPES = frozenset({
    "object", "bool", "boolean", "string", "str", "int8", "int16", "int32", "int64",
    "uint8", "uint16", "uint32", "uint64", "float32", "float64",
    "Int8", "Int16", "Int32", "Int64", "UInt8", "UInt16", "UInt32", "UInt64",
    "Float32", "Float64", "datetime64[ns]", "datetime64[us]", "datetime64[ms]",
    "datetime64[s]", "timedelta64[ns]", "timedelta64[us]", "timedelta64[ms]", "timedelta64[s]",
})


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
