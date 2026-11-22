from datetime import datetime, timezone
from decimal import Decimal
import json

import pandas as pd
import pytest

from stratbox.core.formats.dataframes import frame_from_table, frame_to_table
from stratbox.core.storage.datasets.codec import decode_table, encode_table
from stratbox.shared.data.processing import DataContract, DataRole


def _replay(frame):
    table, descriptor = frame_to_table(frame, contract=DataContract("test.frame", 1, DataRole.EXTRACTS))
    return frame_from_table(decode_table(encode_table(table)), json.loads(json.dumps(descriptor)))


def test_nullable_categories_decimal_and_mixed_scalars_replay_exactly():
    frame = pd.DataFrame({
        "category": pd.Categorical(["a", None, "b"], categories=["b", "a", "unused"], ordered=True),
        "value": pd.array([1.0, None, -0.0], dtype="Float64"),
        "small": pd.Series([1, 2, 3], dtype="int16"),
        "amount": [Decimal("1.2300"), None, Decimal("0.00")],
        "mixed": [("x", 2), pd.NA, None],
        "object_nulls": pd.Series([None, float("nan"), pd.NA], dtype="object"),
    })
    frame.index = pd.MultiIndex.from_tuples([("a", 1), ("b", 2), ("c", 3)], names=["name", "id"])
    pd.testing.assert_frame_equal(frame, _replay(frame))


def test_pivot_axes_nanosecond_time_and_unbounded_values_replay():
    frame = pd.DataFrame([[1.0, float("inf")], [float("nan"), -float("inf")]],
        columns=pd.MultiIndex.from_tuples([("value", "2026-01"), ("value", "2026-02")], names=[None, "period"]))
    frame.index = pd.DatetimeIndex([pd.Timestamp("2026-01-01T00:00:00.000000001Z"), datetime(2026, 2, 1, tzinfo=timezone.utc)])
    pd.testing.assert_frame_equal(frame, _replay(frame))


def test_empty_axes_and_duplicate_columns_are_preserved():
    for frame in (pd.DataFrame(index=pd.Index(["a", "b"], name="rows")),
                  pd.DataFrame(columns=pd.Index(["a", "a"], name="columns")),
                  pd.DataFrame([[1, 2]], columns=["a", "a"])):
        pd.testing.assert_frame_equal(frame, _replay(frame))


def test_changed_descriptor_and_unsupported_objects_fail():
    table, metadata = frame_to_table(pd.DataFrame({"a": [1.0]}), contract=DataContract("test.frame", 1, DataRole.EXTRACTS))
    metadata["dtypes"][0] = {"kind": "scalar", "dtype": "float32"}
    with pytest.raises(ValueError, match="frame_identity_mismatch"):
        frame_from_table(table, metadata)
    with pytest.raises(TypeError, match="scalar_unsupported"):
        frame_to_table(pd.DataFrame({"a": [object()]}), contract=DataContract("test.frame", 1, DataRole.EXTRACTS))
    with pytest.raises(ValueError, match="cell_limit"):
        frame_to_table(pd.DataFrame({"a": [1, 2]}), contract=DataContract("test.frame", 1, DataRole.EXTRACTS), max_cells=1)
