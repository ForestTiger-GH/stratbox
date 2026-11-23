"""Signature scans are bounded, interruptible and safe around mutable inputs."""
from dataclasses import dataclass

import pytest

from stratbox.core.execution import OperationFailure
from stratbox.core.execution.values import argument_identity
from stratbox.core.limits import BudgetExceeded, BudgetMeter, ExecutionBudget
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.evidence import SourcePayload


def snapshot():
    table = TypedTable(TableSchema(DataContract("fixture.values"),
        (ColumnSchema("value", ScalarType.INTEGER),)), tuple((number,) for number in range(1000)))
    return DatasetSnapshot.build("fixture", "capture", DataContract("fixture.snapshot"),
        (("values", table),), coverage=SnapshotCoverage("complete"))


def test_constructor_sealed_snapshot_reuses_one_invocation_signature():
    value = snapshot()
    cache = {}
    assert argument_identity(value, cache=cache) == argument_identity(value, cache=cache)
    assert cache["signature_metrics"] == {"scans": 1, "hits": 1}
    with pytest.raises(BudgetExceeded, match="budget.cells"):
        argument_identity(value, cache=cache, budget=BudgetMeter(ExecutionBudget(cells=10)))


def test_mutating_a_dataframe_or_its_enclosing_frozen_dataclass_invalidates_signature():
    pd = pytest.importorskip("pandas")
    @dataclass(frozen=True)
    class Value:
        frame: object
    frame = pd.DataFrame({"value": [1, 2]})
    value = Value(frame)
    cache = {}
    original = argument_identity(value, cache=cache)
    frame.loc[0, "value"] = 3
    assert original != argument_identity(value, cache=cache)
    assert cache["signature_metrics"]["hits"] == 0


def test_resource_lower_bound_rejects_dataframe_before_its_hash_scan(monkeypatch):
    pd = pytest.importorskip("pandas")
    from stratbox.shared.data import tables
    frame = pd.DataFrame({"value": range(100)})
    monkeypatch.setattr(tables, "table_identity", lambda *args, **kwargs: pytest.fail("Hashing started after failed preflight"))
    with pytest.raises(BudgetExceeded, match="budget.cells"):
        argument_identity(frame, budget=BudgetMeter(ExecutionBudget(cells=10)))


def test_signature_metadata_digests_do_not_count_as_original_payload_bytes():
    value = SourcePayload(b"data", "text/plain", "original")
    assert argument_identity(value, budget=BudgetMeter(ExecutionBudget(input_bytes=16)))


def test_one_oversized_text_cell_is_rejected_before_escaping_its_contents(monkeypatch):
    pd = pytest.importorskip("pandas")
    from stratbox.shared.data import tables
    import json
    frame = pd.DataFrame({"value": ["x" * 100_000]})
    original = json.dumps
    def guarded(value, *args, **kwargs):
        if isinstance(value, str) and len(value) > 4096:
            pytest.fail("Unbounded scalar escaping started")
        return original(value, *args, **kwargs)
    monkeypatch.setattr(tables.json, "dumps", guarded)
    with pytest.raises(BudgetExceeded, match="budget.input_bytes"):
        argument_identity(frame, budget=BudgetMeter(ExecutionBudget(input_bytes=100)))


def test_streamed_table_identity_preserves_the_previous_exact_json_bytes(monkeypatch):
    pd = pytest.importorskip("pandas")
    from stratbox.shared.data import tables
    import json
    from hashlib import sha256
    from stratbox.shared.identity import ByteIdentity
    frame = pd.DataFrame({"value": ["é\\\n\"" * 3000, "", None]})
    calls = []
    original = json.dumps
    def bounded(value, *args, **kwargs):
        assert not isinstance(value, str) or len(value) <= 4096
        return original(value, *args, **kwargs)
    monkeypatch.setattr(tables.json, "dumps", bounded)
    streamed = tables.table_identity((("values", frame),))
    # Exact schema/row serialization is an external content contract. Its
    # existing bytes remain stable when only the encoder's allocation changes.
    import numpy
    scalar = lambda value: tables._scalar(value, pd, numpy, False)
    records = [[tables.TABLE_ENCODING, 1], ["values", *frame.shape],
        [[scalar(x) for x in axis.names] for axis in (frame.index, frame.columns)],
        [[str(axis.dtype)] for axis in (frame.index, frame.columns)],
        [scalar(x) for x in frame.columns], [str(dtype) for dtype in frame.dtypes],
        *[[scalar(index), *[scalar(value) for value in values]]
          for index, *values in frame.itertuples(index=True, name=None)]]
    encoded = b"".join(original(record, ensure_ascii=False, allow_nan=False,
        separators=(",", ":")).encode() + b"\n" for record in records)
    assert streamed == ByteIdentity.of(encoded)


def test_cancellation_stops_before_hash_and_during_a_large_collection():
    def cancelled():
        raise OperationFailure("operation.cancelled", outcome="cancelled")
    with pytest.raises(OperationFailure, match="operation.cancelled"):
        argument_identity(tuple(range(10000)), checkpoint=cancelled)
    checks = 0
    def during():
        nonlocal checks
        checks += 1
        if checks == 2:
            cancelled()
    with pytest.raises(OperationFailure, match="operation.cancelled"):
        argument_identity(tuple(range(10000)), checkpoint=during)
    assert checks == 2
