"""Retained input admission precedes potentially amplified snapshot encoding."""

from datetime import date
from decimal import Decimal

import pytest

from stratbox.core.execution import ExecutionBudget, ExecutionContext
from stratbox.core.operations.processing import definitions as C, handlers as H
from stratbox.shared.data.workbook_cells import SheetCells, WorkbookCell
from stratbox.shared.data.workbooks import WorkbookExtract, workbook_snapshot
from stratbox.shared.data.documents import DocumentBlock, DocumentExtract
from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt


def shared_text_workbook(count, text):
    source = SourcePayload(b"synthetic workbook evidence")
    cells = tuple(WorkbookCell(row, 1, f"A{row}", text, None, "str")
                  for row in range(1, count + 1))
    return WorkbookExtract("example.shared", "2026", "main", source.identity,
        "xlsx", "workbook.cells.v1", 1, (SheetCells("Shared", 0, count, 1, cells),),
        (UsedInputReceipt.for_payload(source, "source"),))


@pytest.mark.parametrize("resource", ("input_bytes", "cells"))
def test_shared_text_amplification_is_refused_before_snapshot_encoding(monkeypatch, resource):
    text = "x" * 32767
    value = shared_text_workbook(10000, text)
    assert value.sheets[0].cells[0].value is value.sheets[0].cells[-1].value

    def forbidden_encoder(*args, **kwargs):
        raise AssertionError("Snapshot encoder ran before input admission")

    monkeypatch.setattr(H.W, "workbook_snapshot", forbidden_encoder)
    limit = 128000 if resource == "input_bytes" else 100
    result = H.snapshot_workbook(C.WorkbookRequest(value), context=ExecutionContext(
        budget=ExecutionBudget(**{resource: limit})))
    assert result.outcome == "failed"
    assert result.value is None and result.computation is None
    assert any(d.code == f"budget.{resource}" for d in result.diagnostics)


def test_preflight_does_not_double_charge_real_snapshot_size():
    value = shared_text_workbook(2, "A\nБ")
    snapshot = workbook_snapshot(value)
    size = snapshot.identity.size + sum(table.identity.size for _, table in snapshot.tables)
    cells = sum(len(table.rows) * len(table.schema.columns) for _, table in snapshot.tables)
    result = H.snapshot_workbook(C.WorkbookRequest(value), context=ExecutionContext(
        budget=ExecutionBudget(input_bytes=size, cells=cells)))
    assert result.outcome == "succeeded", result.diagnostics
    assert result.value.identity == snapshot.identity
    assert dict(result.resources_used)["input_bytes"] == size
    assert dict(result.resources_used)["cells"] == cells


def test_empty_document_cells_still_have_an_encoding_cost(monkeypatch):
    source = SourcePayload(b"synthetic document evidence")
    value = DocumentExtract("example.shared", "2026", "main", source.identity,
        "docx", "document.blocks.v1", 1,
        (DocumentBlock(0, "table", "", rows=(("",) * 100000,)),),
        (UsedInputReceipt.for_payload(source, "source"),), SnapshotCoverage("unknown"))

    def forbidden_encoder(*args, **kwargs):
        raise AssertionError("Document encoder ran before empty-cell admission")

    monkeypatch.setattr(H.D, "document_snapshot", forbidden_encoder)
    result = H.snapshot_document(C.DocumentRequest(value), context=ExecutionContext(
        budget=ExecutionBudget(input_bytes=128000)))
    assert result.outcome == "failed"
    assert any(d.code == "budget.input_bytes" for d in result.diagnostics)


def test_shared_decimal_amplification_without_raw_tokens_is_bounded(monkeypatch):
    value = Decimal("1" * 32767)
    item = Observation(SubjectRef("s", "s"), MetricRef("m", "u", "stock", "v1", Decimal(1)),
        PeriodRef("as_of", date(2026, 1, 1)), (), "p", value, "reported", "e")
    batch = ObservationBatch("example.shared", 1, "2026", (item,) * 1000, ())

    def forbidden_encoder(*args, **kwargs):
        raise AssertionError("Observation encoder ran before decimal admission")

    monkeypatch.setattr(H, "observation_snapshot", forbidden_encoder)
    result = H.prepare_view(C.PrepareViewRequest(batch, "example.view"), context=ExecutionContext(
        budget=ExecutionBudget(input_bytes=128000)))
    assert result.outcome == "failed"
    assert any(d.code == "budget.input_bytes" for d in result.diagnostics)


def test_actual_encoded_overhead_still_enforces_input_budget(monkeypatch):
    value = shared_text_workbook(1, "small")
    snapshot = workbook_snapshot(value)
    size = snapshot.identity.size + sum(table.identity.size for _, table in snapshot.tables)
    encoded = []

    def encoder(workbook, **kwargs):
        encoded.append(workbook)
        return workbook_snapshot(workbook, **kwargs)

    monkeypatch.setattr(H.W, "workbook_snapshot", encoder)
    result = H.snapshot_workbook(C.WorkbookRequest(value), context=ExecutionContext(
        budget=ExecutionBudget(input_bytes=size - 1)))
    assert encoded == [value]
    assert result.outcome == "failed"
    assert any(d.code == "budget.input_bytes" for d in result.diagnostics)
