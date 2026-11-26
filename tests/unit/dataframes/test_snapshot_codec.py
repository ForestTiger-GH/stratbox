"""Portable dataframe values preserve scientific axes, dtypes and scalar evidence."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from stratbox.core.commands.standard import value_decode, value_encode
from stratbox.core.execution.service import ExecutionFailure, ExecutionSettings
from stratbox.core.limits import ExecutionBudget
from stratbox.sdk import StrategyBox
from stratbox.shared.data.frame_codec import _axis_from, _dtype_from, _unatom
from stratbox.shared.data.values import canonical_tree, restore_tree


def _context():
    return SimpleNamespace(parameters={},checkpoint=lambda:None)


def _replay(frame):
    # Real JSON transfer separates retained data from the live pandas object.
    encoded=value_encode({"value":frame},None,_context())["representation"]
    restored=value_decode({"representation":encoded},None,_context())["value"]
    tree_restored=restore_tree(json.loads(json.dumps(canonical_tree(frame))))
    pd.testing.assert_frame_equal(restored,tree_restored)
    return restored


def test_nullable_categories_decimal_and_mixed_scalars_replay_exactly():
    frame=pd.DataFrame({
        "category":pd.Categorical(["a",None,"b"],categories=["b","a","unused"],ordered=True),
        "value":pd.array([1.0,None,-0.0],dtype="Float64"),
        "small":pd.Series([1,2,3],dtype="int16"),
        "amount":[Decimal("1.2300"),None,Decimal("0.00")],
        "mixed":[("x",2),pd.NA,None],
        "object_nulls":pd.Series([None,float("nan"),pd.NA],dtype="object"),
    })
    frame.index=pd.MultiIndex.from_tuples([("a",1),("b",2),("c",3)],names=["name","id"])
    pd.testing.assert_frame_equal(frame,_replay(frame))


def test_pivot_axes_nanosecond_time_and_unbounded_values_replay():
    frame=pd.DataFrame([[1.0,float("inf")],[float("nan"),-float("inf")]],
        columns=pd.MultiIndex.from_tuples([("value","2026-01"),("value","2026-02")],names=[None,"period"]))
    frame.index=pd.DatetimeIndex([pd.Timestamp("2026-01-01T00:00:00.000000001Z"),datetime(2026,2,1,tzinfo=timezone.utc)])
    pd.testing.assert_frame_equal(frame,_replay(frame))


def test_named_dst_fold_and_nanoseconds_survive_object_cells_and_datetime_axis():
    from zoneinfo import ZoneInfo
    zone=ZoneInfo("America/New_York")
    first=datetime(2026,11,1,1,30,tzinfo=zone,fold=0)
    second=datetime(2026,11,1,1,30,tzinfo=zone,fold=1)
    stamps=(pd.Timestamp(first)+pd.Timedelta(1,unit="ns"),
        pd.Timestamp(second)+pd.Timedelta(2,unit="ns"))
    assert first.utcoffset()!=second.utcoffset()
    frame=pd.DataFrame({"wall":pd.Series((first,second),dtype=object),
        "stamp":pd.Series(stamps,dtype=object),"amount":pd.array((10,20),dtype="Int64")})
    frame.index=pd.DatetimeIndex(stamps,name="source_clock")
    restored=_replay(frame)
    assert str(restored.index.dtype)==str(frame.index.dtype)
    assert restored.index.name==frame.index.name
    assert restored.index.asi8.tolist()==frame.index.asi8.tolist()
    assert restored["amount"].dtype==frame["amount"].dtype
    for column in ("wall","stamp"):
        for before,after in zip(frame[column],restored[column]):
            assert getattr(after.tzinfo,"key",getattr(after.tzinfo,"zone",None))=="America/New_York"
            assert after.fold==before.fold and after.utcoffset()==before.utcoffset()
            assert after.isoformat()==before.isoformat()
    assert [value.nanosecond for value in restored["stamp"]]==[1,2]


def test_empty_axes_and_duplicate_columns_are_preserved():
    for frame in (pd.DataFrame(index=pd.Index(["a","b"],name="rows")),
        pd.DataFrame(columns=pd.Index(["a","a"],name="columns")),
        pd.DataFrame([[1,2]],columns=["a","a"])):
        pd.testing.assert_frame_equal(frame,_replay(frame))


def test_changed_retained_dtype_descriptor_cannot_reuse_original_content_identity():
    frame=pd.DataFrame({"a":[1.0]})
    encoded=value_encode({"value":frame},None,_context())["representation"]
    tree=json.loads(encoded.data)
    tree["dataframe"]["dtypes"][0]={"kind":"scalar","dtype":"float32"}
    altered=replace(encoded,data=json.dumps(tree).encode())
    with pytest.raises((ValueError,ExecutionFailure),match="identity|descriptor|dataframe"):
        value_decode({"representation":altered},None,_context())


def test_unsupported_objects_fail_and_real_cell_budget_is_enforced():
    with pytest.raises(TypeError,match="scalar_unsupported"):
        value_encode({"value":pd.DataFrame({"a":[object()]})},None,_context())
    with StrategyBox(settings=ExecutionSettings(run_limits=ExecutionBudget(cells=1))) as box:
        result=box.invoke("command.value.encode",inputs={"value":pd.DataFrame({"a":[1,2]})})
        assert result.outcome=="failed" and not result.outputs
        assert any("budget.cells" in str(item) for item in result.diagnostics)


@pytest.mark.parametrize("alter",[
    lambda frame:frame.update(dtypes=[]),
    lambda frame:frame.update(rows=[[]]),
    lambda frame:frame.update(executor="caller.module:callable"),
])
def test_malformed_frame_shape_and_unknown_descriptor_fields_fail(alter):
    tree=deepcopy(canonical_tree(pd.DataFrame({"a":[1.0]})))
    alter(tree["dataframe"])
    with pytest.raises(ValueError,match="dataframe|descriptor"):
        restore_tree(tree)


@pytest.mark.parametrize("payload",[["int","001"],["bool",1],["class","caller.module:callable"]])
def test_hostile_or_noncanonical_scalar_descriptors_fail(payload):
    with pytest.raises(ValueError,match="scalar"):
        _unatom(payload)


def test_dtype_and_axis_descriptors_do_not_select_arbitrary_code():
    with pytest.raises(ValueError,match="dtype_unsupported"):
        _dtype_from({"kind":"scalar","dtype":"caller.module:Arbitrary"})
    axis=deepcopy(canonical_tree(pd.DataFrame({"a":[1.0]}))["dataframe"]["columns"])
    axis["factory"]="caller.module:callable"
    with pytest.raises(ValueError,match="axis_invalid"):
        _axis_from(axis)
