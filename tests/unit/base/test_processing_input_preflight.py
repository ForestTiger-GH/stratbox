"""The standard service admits inputs before invoking an amplifying encoder."""
from dataclasses import replace
from decimal import Decimal
import pytest

from stratbox.core.execution.service import ExecutionSettings
from stratbox.core.limits import ExecutionBudget
from stratbox.sdk import StrategyBox
from stratbox.shared.data.workbook_cells import WorkbookCells,SheetCells,WorkbookCell
from stratbox.shared.data.values import Assessment,Material,WorkbookEvidence,DocumentEvidence,DocumentStructure,DocumentBlock,SourceDataset


def workbook(count,text):
    material=Material(b"synthetic physical fixture")
    cells=tuple(WorkbookCell(row,1,f"A{row}",text,None,"str") for row in range(1,count+1))
    return WorkbookEvidence(material,WorkbookCells((SheetCells("Shared",0,count,1,cells),),material.identity))


def encoded(value,limits=None):
    with StrategyBox(settings=ExecutionSettings(run_limits=limits or ExecutionBudget())) as box:
        return box.invoke("command.value.encode",inputs={"value":value})


@pytest.mark.parametrize("resource,limit",(("input_bytes",8192),("cells",100)))
def test_shared_text_amplification_is_refused_before_the_encoder_runs(monkeypatch,resource,limit):
    value=workbook(1000,"x"*8192)
    assert value.workbook.sheets[0].cells[0].value is value.workbook.sheets[0].cells[-1].value
    def forbidden(*args,**kwargs):raise AssertionError("Encoder ran before input admission")
    monkeypatch.setattr("stratbox.core.commands.standard.canonical_tree",forbidden)
    result=encoded(value,ExecutionBudget(**{resource:limit}))
    assert result.outcome=="failed" and not result.outputs
    assert any("budget."+resource in str(item) for item in result.diagnostics)


def test_exact_input_and_output_boundary_limits_are_not_charged_twice():
    value=workbook(2,"A\nБ")
    baseline=encoded(value)
    assert baseline.outcome=="succeeded",baseline.diagnostics
    limits={key:baseline.resources[key] for key in ("input_bytes","output_bytes","cells")}
    bounded=encoded(value,ExecutionBudget(**limits))
    assert bounded.outcome=="succeeded",bounded.diagnostics
    assert bounded.output("representation").identity==baseline.output("representation").identity
    assert {key:bounded.resources[key] for key in limits}==limits


def test_empty_document_grid_still_has_a_real_boundary_cost(monkeypatch):
    material=Material(b"synthetic document fixture")
    value=DocumentEvidence(material,DocumentStructure("docx",(DocumentBlock(0,"table",rows=(("",)*100000,)),),material.identity,Assessment("unknown")))
    def forbidden(*args,**kwargs):raise AssertionError("Encoder ran before empty-cell admission")
    monkeypatch.setattr("stratbox.core.commands.standard.canonical_tree",forbidden)
    result=encoded(value,ExecutionBudget(input_bytes=128000))
    assert result.outcome=="failed" and any("budget.input_bytes" in str(item) for item in result.diagnostics)


def test_large_shared_decimal_rows_are_bounded_before_encoding(monkeypatch):
    number=Decimal("1"*8192)
    value=SourceDataset("example",tuple({"metric":"m","value":number,"raw_token":None} for _ in range(1000)))
    def forbidden(*args,**kwargs):raise AssertionError("Encoder ran before decimal admission")
    monkeypatch.setattr("stratbox.core.commands.standard.canonical_tree",forbidden)
    result=encoded(value,ExecutionBudget(input_bytes=8192))
    assert result.outcome=="failed" and any("budget.input_bytes" in str(item) for item in result.diagnostics)


def test_actual_encoded_boundary_overhead_is_enforced_before_exposing_an_output(monkeypatch):
    value=workbook(1,"small")
    baseline=encoded(value);assert baseline.outcome=="succeeded"
    from stratbox.core.commands import standard
    calls=[];canonical=standard.canonical_tree
    def recording(item):calls.append(1);return canonical(item)
    monkeypatch.setattr(standard,"canonical_tree",recording)
    result=encoded(value,ExecutionBudget(output_bytes=baseline.resources["output_bytes"]-1))
    assert calls and result.outcome=="failed" and not result.outputs
    assert any("budget.output_bytes" in str(item) for item in result.diagnostics)
