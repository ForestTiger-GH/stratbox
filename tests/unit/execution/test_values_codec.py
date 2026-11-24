"""Portable value snapshots preserve semantic qualification and typed content."""
from datetime import date
from decimal import Decimal
import json

import pytest

from stratbox.core.execution.values.codec import decode_value, encode_value
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import (
    ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable,
)
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.workbook_cells import WorkbookCell, WorkbookCells, SheetCells
from stratbox.shared.identity import ByteIdentity


def test_typed_snapshot_preserves_role_units_periods_lineage_coverage_and_identity():
    contract = DataContract("test.observations", 2, DataRole.EXTRACTS)
    schema = TableSchema(contract, (
        ColumnSchema("period", ScalarType.DATE),
        ColumnSchema("amount", ScalarType.DECIMAL, unit="RUB million"),
    ))
    table = TypedTable(schema, ((date(2026, 9, 1), Decimal("17.25")),))
    payload = SourcePayload(b"source", source_id="test.source")
    snapshot = DatasetSnapshot.build("test.source", "2026-09", contract, (("rows", table),),
        coverage=SnapshotCoverage("partial", "One supplied region"),
        inputs=(UsedInputReceipt.for_payload(payload, "original"),))
    restored = decode_value(encode_value(snapshot, contract, qualifications=frozenset({"reported", "partial"}),
        coverage=frozenset({"region.1"})))
    assert restored.value == snapshot
    assert restored.identity == snapshot.identity
    assert restored.contract == contract
    assert restored.qualifications == frozenset({"reported", "partial"})
    assert restored.coverage == frozenset({"region.1"})


def test_scalar_collection_snapshot_keeps_tuple_decimal_bytes_and_signed_zero():
    value = {"parts": (Decimal("0.100"), b"binary", -0.0, [1, True])}
    restored = decode_value(encode_value(value, DataContract("test.collection")))
    assert restored.value == value
    assert type(restored.value["parts"]) is tuple
    assert str(restored.value["parts"][0]) == "0.100"
    assert restored.value["parts"][2].hex() == "-0x0.0p+0"


def test_snapshot_budget_and_identity_tampering_fail_explicitly():
    contract = DataContract("test.bytes")
    with pytest.raises(ValueError, match="snapshot_limit"):
        encode_value(b"a" * 1000, contract, max_bytes=100)
    data = encode_value(7, contract)
    with pytest.raises(ValueError, match="encoding_limit"):
        decode_value(data, max_bytes=10)
    raw = json.loads(data)
    raw["value"] = ["scalar", 8]
    with pytest.raises(ValueError, match="identity_mismatch"):
        decode_value(json.dumps(raw).encode())


def test_pilot_workbook_cells_preserve_formula_cache_tokens_styles_and_source_basis():
    cells = (WorkbookCell(1, 1, "A1", Decimal("1.20"), "1.20", "n", "SUM(B1:C1)", "0.00", 1, (("t", "shared"),)),
             WorkbookCell(1, 2, "B1", "reported", "reported", "str"))
    workbook = WorkbookCells((SheetCells("budget", 0, 1, 2, cells, ("A1:B1",)),), ByteIdentity.of(b"original workbook"))
    contract = DataContract("workbook.cells", 1, DataRole.READABLE)
    encoded = encode_value(workbook, contract)
    restored = decode_value(encoded)
    assert restored.value == workbook
    assert restored.value.identity == workbook.identity
    assert restored.identity != workbook.identity  # Original bytes and decoded evidence are separate identities.
    with pytest.raises(ValueError, match="cell_limit"):
        decode_value(encoded, max_cells=1)
    tampered = json.loads(encoded)
    tampered["value"][1]["sheets"][0]["cells"][0][3] = ["decimal", "9.00"]
    tampered["value"][1]["sheets"][0]["cells"][0][4] = "9.00"
    with pytest.raises(ValueError, match="identity_mismatch"):
        decode_value(json.dumps(tampered).encode())


def test_representation_and_original_roundtrip_retain_profile_and_source_semantics():
    representation = Representation("csv.banking", 2, "text/csv", b"region,value\nA,1\n", "utf-8")
    source = SourcePayload(b"original", "text/csv", "publisher.issue", charset="utf-8")
    for original, contract in ((representation, DataContract("product.csv", role=DataRole.PRODUCTS)),
                               (source, DataContract("source.payload", role=DataRole.ORIGINALS))):
        decoded = decode_value(encode_value(original, contract, qualifications=frozenset({"reported"})))
        assert decoded.value == original
        assert decoded.contract == contract


def test_collection_materialization_enforces_one_aggregate_cell_ceiling():
    contract = DataContract("test.small-table")
    table = TypedTable(TableSchema(contract, (ColumnSchema("value", ScalarType.INTEGER),)), ((1,),))
    encoded = encode_value((table, table), DataContract("test.table-collection"))
    with pytest.raises(ValueError, match="cell_limit"):
        decode_value(encoded, max_cells=1)
    assert decode_value(encoded, max_cells=2).value == (table, table)
