"""Versioned identities of tables and the computations that produced them."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
import math
from typing import Callable, TYPE_CHECKING

from .evidence import ByteIdentity, UsedInputReceipt
from .identity import DatasetVersion

if TYPE_CHECKING:
    from pandas import DataFrame


TABLE_ENCODING = "stratbox.tables.v1"
TABLE_MEDIA_TYPE = "application/vnd.stratbox.tables"


@dataclass(frozen=True, slots=True)
class ComputationReceipt:
    version: DatasetVersion
    output: ByteIdentity
    inputs: tuple[UsedInputReceipt, ...]
    computation_id: ByteIdentity
    parents: tuple[tuple[str, ComputationReceipt], ...] = ()


def _scalar(value, pandas, numpy, allow_infinite):
    if value is None:
        return ["none"]
    if value is pandas.NA:
        return ["na"]
    if value is pandas.NaT:
        return ["nat"]
    if isinstance(value, numpy.datetime64):
        return _scalar(pandas.Timestamp(value), pandas, numpy, allow_infinite)
    if isinstance(value, numpy.timedelta64):
        return _scalar(pandas.Timedelta(value), pandas, numpy, allow_infinite)
    if isinstance(value, numpy.generic):
        value = value.item()
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        if math.isnan(value):
            return ["nan"]
        if math.isfinite(value):
            return ["float", value.hex()]
        if allow_infinite:
            return ["unbounded", "+" if value > 0 else "-"]
    if isinstance(value, Decimal) and value.is_finite():
        return ["decimal", str(value)]
    if isinstance(value, datetime):
        if value.utcoffset() is not None:
            return ["instant", value.astimezone(timezone.utc).isoformat()]
        return ["local_datetime", value.isoformat()]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, time):
        return ["time", value.isoformat()]
    if isinstance(value, pandas.Timedelta):
        return ["timedelta", value.isoformat()]
    if isinstance(value, timedelta):
        return ["timedelta", pandas.Timedelta(value).isoformat()]
    if isinstance(value, str):
        return ["text", value]
    if isinstance(value, tuple):
        return ["tuple", [_scalar(item, pandas, numpy, allow_infinite) for item in value]]
    raise TypeError("Unsupported table value")


def table_identity(
    tables: tuple[tuple[str, DataFrame], ...],
    *,
    checkpoint: Callable[[], None] | None = None,
    allow_infinite: bool = False,
) -> ByteIdentity:
    """Hash the ordered schema and rows without building a second table encoding."""
    import numpy
    import pandas

    digest = sha256()
    size = 0

    def scalar(value):
        return _scalar(value, pandas, numpy, allow_infinite)

    def feed(value):
        nonlocal size
        line = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        digest.update(line)
        digest.update(b"\n")
        size += len(line) + 1

    def dtype(value):
        if isinstance(value, pandas.CategoricalDtype):
            return ["category", dtype(value.categories.dtype), value.ordered, [scalar(x) for x in value.categories]]
        return str(value)

    feed([TABLE_ENCODING, len(tables)])
    for role, frame in tables:
        if not isinstance(frame, pandas.DataFrame):
            raise TypeError("Expected a pandas DataFrame")
        if checkpoint is not None:
            checkpoint()
        feed([role, *frame.shape])
        feed([[scalar(x) for x in axis.names] for axis in (frame.index, frame.columns)])
        feed([[dtype(x) for x in axis.dtypes] if isinstance(axis, pandas.MultiIndex)
              else [dtype(axis.dtype)] for axis in (frame.index, frame.columns)])
        feed([scalar(x) for x in frame.columns])
        feed([dtype(x) for x in frame.dtypes])
        for number, (label, *values) in enumerate(frame.itertuples(index=True, name=None)):
            if checkpoint is not None and number % 1024 == 0:
                checkpoint()
            feed([scalar(label), *[scalar(value) for value in values]])
    return ByteIdentity(digest.hexdigest(), size)
