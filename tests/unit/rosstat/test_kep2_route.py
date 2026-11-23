"""The notebook's source selection replays independently through every layer."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO
import json
import pytest

from stratbox.shared.evidence import SourcePayload
from stratbox.shared.data.workbooks import workbook_snapshot,workbook_from_snapshot
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.core.formats.spreadsheets.extracts import extract_workbook
from stratbox.domains.rosstat.tables.contracts import Kep2Request
from stratbox.domains.rosstat.tables.kep2 import extract_kep2,numeric_token
from stratbox.domains.rosstat.tables.profiles import KEP2_INDICATORS
from stratbox.domains.rosstat.tables.snapshots import flake_snapshot,flake_from_snapshot
from stratbox.domains.rosstat.integration.datasets import integrate_flakes,dataset_snapshot,dataset_from_snapshot
from stratbox.domains.rosstat.products.views import prepare_kep2_monthly
from stratbox.domains.rosstat.products.xlsx import render_kep2_xlsx
from stratbox.shared.data.views import view_snapshot,view_from_snapshot
from stratbox.domains.rosstat.analytics.indicators import derive_index_growth


@pytest.fixture
def native_workbook():
    openpyxl=pytest.importorskip("openpyxl")
    book=openpyxl.Workbook()
    contents=book.active
    contents.title="Содержание"
    names={"investment":"1.6 ","wages":"4.2 ","construction":"1.7 ","freight_turnover":"1.5 ",
        "retail":"1.12 ","retail_food":"1.12 ","retail_nonfood":"1.12 ","catering":"1.12 ",
        "wholesale":"1.15","paid_services":"1.13 ","agriculture":"1.3"}
    months=("Янв.","Фев.","Март","Апр.","Май","Июнь","Июль","Август","Сент.","Окт.","Нояб.","Дек.")
    sheets={}
    for name in dict.fromkeys(names.values()):
        sheet=book.create_sheet(name)
        sheets[name]=sheet
        sheet.cell(1,2,"Год")
        sheet.cell(2,2,"Year")
        sheet.cell(1,3,"Кварталы / Quarters")
        for col,quarter in enumerate(("I","II","III","IV"),3):sheet.cell(2,col,quarter)
        for col,month in enumerate(months,7):sheet.cell(1,col,month)
    next_row={name:3 for name in sheets}
    toc=0
    for indicator in KEP2_INDICATORS:
        name=names[indicator.id]
        if indicator.parent is None:
            col=1 if toc<4 else 5
            row=3+toc%4
            contents.cell(row,col,name.strip()+".")
            contents.cell(row,col+1,indicator.titles[0])
            toc+=1
        sheet=sheets[name]
        start=next_row[name]
        title=indicator.titles[0]
        if indicator.id=="wages":title=indicator.titles[1]
        unit="млрд тонно-км" if indicator.id=="freight_turnover" else "рублей1)" if indicator.id=="wages" else "млрд рублей"
        sheet.cell(start,1,title+("1), " if indicator.id=="investment" else ", ")+unit)
        cursor=start+1
        if indicator.absolute:
            sheet.cell(cursor,1,"/ English source title")
            sheet.cell(cursor+1,1,2024)
            sheet.cell(cursor+1,2,1000)
            sheet.cell(cursor+1,3,200)
            sheet.cell(cursor+1,7,100.1)
            sheet.cell(cursor+2,7,"110,2 1)")
            sheet.cell(cursor+2,8,"—")
            sheet.cell(cursor+2,9,"…2)")
            sheet.cell(cursor+3,1,2025)
            sheet.cell(cursor+3,7,0)
            cursor+=4
        for measure,marker in (("yoy","в % к соответствующему периоду предыдущего года"),("previous","в % к предыдущему периоду")):
            if indicator.id=="agriculture" and measure=="previous":continue
            sheet.cell(cursor,1,marker)
            sheet.cell(cursor+1,1,"/ English index marker")
            sheet.cell(cursor+2,1,2024)
            sheet.cell(cursor+2,2,105)
            sheet.cell(cursor+2,3,103)
            sheet.cell(cursor+2,7,105.1 if measure=="yoy" else 102.5)
            sheet.cell(cursor+3,1,2025)
            sheet.cell(cursor+3,7,101)
            cursor+=4
        sheet.cell(cursor,1,"1) Preliminary estimate.")
        next_row[name]=cursor+2
    # A different quantity on the transport sheet must not donate its indices.
    freight=sheets[names["freight_turnover"]]
    r=next_row[names["freight_turnover"]]
    freight.cell(r,1,"Перевозка грузов транспортом, млн тонн")
    freight.cell(r+1,1,2024)
    freight.cell(r+1,7,999)
    freight.cell(r+2,1,"в % к соответствующему периоду предыдущего года")
    freight.cell(r+3,1,2024)
    freight.cell(r+3,7,777)
    stream=BytesIO();book.save(stream)
    return stream.getvalue()


@pytest.fixture
def physical(native_workbook):
    return extract_workbook(SourcePayload(native_workbook,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        series_id="rosstat.short_term_indicators",issue_id="2025-01",asset_id="main_workbook")


def test_kep2_all_frequencies_indices_source_row_policy_and_complete_replay(physical,monkeypatch):
    physical_saved=workbook_snapshot(physical)
    # No decoder can be needed after a stored physical snapshot has been read.
    monkeypatch.setattr("stratbox.core.formats.spreadsheets.extracts.extract_workbook",lambda *a,**k:pytest.fail("decoder invoked during replay"))
    restored_physical=workbook_from_snapshot(physical_saved)
    flake=extract_kep2(Kep2Request(restored_physical))
    assert flake.coverage.status=="complete",flake.diagnostics
    assert len({row.indicator_id for row in flake.values})==11
    assert {row.frequency for row in flake.values}=={"monthly","quarterly","annual"}
    source=next(row for row in flake.values if row.indicator_id=="investment" and row.measure=="absolute" and row.period_start==date(2024,1,1) and row.frequency=="monthly")
    assert source.value==Decimal("110.2") and source.raw_token=="110,2 1)" and source.footnotes==("1)",)
    assert source.period_end==date(2024,1,31) and source.display_date==date(2024,2,1)
    assert source.source_sheet=="1.6 " and source.unit=="RUB" and source.scale==Decimal(10)**9
    rejected=next(row for row in flake.row_decisions if not row.selected and row.indicator_id=="investment")
    assert rejected.reason=="last_source_row"
    rejected_cells=json.loads(rejected.source_cells)["cells"]
    assert rejected_cells[1]["raw_token"]=="1000"  # Discarded annual evidence is retained in the flake itself.
    assert not any(row.indicator_id=="agriculture" and row.measure!="year_on_year_index" for row in flake.values)
    freight=next(row for row in flake.values if row.indicator_id=="freight_turnover" and row.measure=="year_on_year_index" and row.frequency=="monthly" and row.period_start.year==2024)
    assert freight.value==Decimal("105.1")
    assert freight.unit=="percent" and freight.quantity_kind=="index"
    saved=flake_snapshot(flake)
    assert flake_from_snapshot(saved)==flake
    dataset=integrate_flakes((flake_from_snapshot(saved),),dataset_id="rosstat.kep2",release_id="v1")
    dataset_saved=dataset_snapshot(dataset)
    replayed=dataset_from_snapshot(dataset_saved)
    assert replayed==dataset
    monthly=prepare_kep2_monthly(replayed)
    view_saved=view_snapshot(monthly)
    assert view_from_snapshot(view_saved)==monthly
    assert {dict(row.dimensions)["frequency"] for row in monthly.batch.observations}=={"monthly"}
    growth=derive_index_growth(replayed,release_id="growth-v1")
    assert any(row.value==Decimal("5.1") and row.value_status=="derived" for row in growth.observations)
    assert any(row.value==Decimal("105.1") and row.value_status=="reported" for row in dataset.batch.observations)
    product=render_kep2_xlsx(view_from_snapshot(view_saved))
    assert render_kep2_xlsx(view_from_snapshot(view_saved)).data==product.data
    openpyxl=pytest.importorskip("openpyxl")
    book=openpyxl.load_workbook(BytesIO(product.data),read_only=False,data_only=True)
    assert book["Росстат"]["A3"].value=="Ежемесячные показатели"
    assert book["Росстат"].freeze_panes=="C5"
    assert book["Росстат"]["C4"].value=="2024-02-01"
    assert book["Росстат"]["C5"].value==110.2
    assert book["Росстат"]["D5"].value==0
    assert book["Evidence"].max_row==len(monthly.batch.observations)+1
    assert book["Metadata"]["B2"].value==monthly.source_identity.sha256


def test_duplicate_year_can_be_rejected_and_semantic_duplicates_never_average(physical):
    with pytest.raises(ValueError,match="duplicate_year"):
        extract_kep2(Kep2Request(physical,duplicate_year_policy="reject"))
    flake=extract_kep2(Kep2Request(physical))
    with pytest.raises(ValueError,match="duplicate_observation"):
        integrate_flakes((flake,flake),dataset_id="test",release_id="v1")
    dataset=integrate_flakes((flake,),dataset_id="test",release_id="v1")
    view=prepare_kep2_monthly(dataset)
    duplicate=replace(view,batch=replace(view.batch,observations=(*view.batch.observations,view.batch.observations[0])))
    with pytest.raises(ValueError,match="product_duplicate_cell"):
        render_kep2_xlsx(duplicate)


def test_month_layout_drift_and_ambiguous_sheets_fail_closed(physical):
    sheet=next(s for s in physical.sheets if s.name=="1.6 ")
    changed=replace(sheet,cells=tuple(replace(c,value="Январь-февраль") if c.row==1 and c.column==8 else c for c in sheet.cells))
    wrong=replace(physical,sheets=tuple(changed if s.name==sheet.name else s for s in physical.sheets))
    with pytest.raises(ValueError,match="period_layout_unreviewed"):
        extract_kep2(Kep2Request(wrong))
    extra=replace(sheet,name="1.6",index=len(physical.sheets))
    wrong=replace(physical,sheets=(*physical.sheets,extra))
    with pytest.raises(ValueError,match="sheet_ambiguous"):
        extract_kep2(Kep2Request(wrong))


def test_missing_marker_does_not_escape_section_and_partial_is_explicit(physical):
    sheet=next(s for s in physical.sheets if s.name=="1.12 ")
    markers=[c for c in sheet.cells if c.column==1 and c.value=="в % к предыдущему периоду"]
    first=markers[0]
    changed=replace(sheet,cells=tuple(replace(c,value="Unknown publication marker") if c==first else c for c in sheet.cells))
    wrong=replace(physical,sheets=tuple(changed if s.name==sheet.name else s for s in physical.sheets))
    flake=extract_kep2(Kep2Request(wrong))
    assert flake.coverage.status=="partial"
    assert "rosstat.kep2.marker_missing:retail:previous_period_index" in flake.diagnostics
    assert not any(v.indicator_id=="retail" and v.measure=="previous_period_index" for v in flake.values)
    with pytest.raises(ValueError,match="integration_unresolved_source"):
        integrate_flakes((flake,),dataset_id="test",release_id="v1")


def test_numeric_tokens_keep_special_states_and_footnotes():
    assert numeric_token("0")== (Decimal(0),"reported",())
    assert numeric_token("…2)")== (None,"missing",("2)",))
    assert numeric_token("—")== (None,"dash",())
    assert numeric_token("20262)")== (Decimal(2026),"reported",("2)",))
    assert numeric_token("157 0014)")== (Decimal(157001),"reported",("4)",))
    assert numeric_token("bad token")== (None,"unparsed",())
    assert numeric_token(None,formula_without_cache=True)== (None,"unparsed",())


def test_offline_example_preserves_original_snapshots_and_product_descriptor(native_workbook,tmp_path):
    import importlib.util
    from pathlib import Path
    from stratbox.shared.identity import ByteIdentity
    path=Path(__file__).resolve().parents[3]/"examples"/"rosstat_kep2_offline.py"
    spec=importlib.util.spec_from_file_location("rosstat_example",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source=tmp_path/"source.xlsx"
    source.write_bytes(native_workbook)
    output=tmp_path/"output"
    result=module.build(source,"2025-01",output)
    assert result["source_sha256"]==ByteIdentity.of(native_workbook).sha256
    assert (output/"originals"/"2025-01.xlsx").read_bytes()==native_workbook
    assert (output/"products"/"2025-01-monthly.xlsx").is_file()
    assert (output/"products"/"2025-01-monthly.xlsx.stratbox.json").is_file()
    assert len(tuple((output/"datasets"/"versions").rglob("*.json")))==4


def test_operation_boundaries_pin_complete_values_parameters_and_budgets(physical):
    from stratbox.core.execution import ExecutionContext
    from stratbox.core.limits import ExecutionBudget
    from stratbox.domains.rosstat.operations import handlers as H
    from stratbox.domains.rosstat.operations.contracts import SnapshotRequest,FlakeRequest
    from stratbox.domains.rosstat.operations.evidence import snapshot_size
    request=Kep2Request(physical)
    result=H.extract_kep2(request)
    assert result.outcome=="succeeded",result.diagnostics
    assert result.computation is not None
    assert result.computation.inputs==result.used_inputs
    assert physical.identity in {receipt.identity for receipt in result.used_inputs}
    assert result.computation.output==result.value.identity
    assert dict(result.resources_used)["input_bytes"]>=snapshot_size(workbook_snapshot(physical))
    saved=flake_snapshot(result.value)
    assert dict(result.resources_used)["output_bytes"]>=snapshot_size(saved)
    again=H.extract_kep2(request)
    assert again.computation.computation_id==result.computation.computation_id
    selected=H.extract_kep2(Kep2Request(physical,required_indicators=("retail",)))
    assert selected.outcome=="succeeded"
    assert selected.computation.computation_id!=result.computation.computation_id
    manifest=json.loads(selected.computation.version.manifest)
    assert manifest["parameters"]["required_indicators"]==["retail"]
    replay=H.read_flake(SnapshotRequest(saved))
    assert replay.outcome=="succeeded" and replay.computation.output==saved.identity
    assert dict(replay.resources_used)["input_bytes"]>=snapshot_size(saved)
    validation=H.validate_flake(FlakeRequest(result.value))
    assert validation.outcome=="succeeded" and validation.computation.output!=saved.identity
    for resource in ("input_bytes","output_bytes","cells"):
        failed=H.read_flake(SnapshotRequest(saved),context=ExecutionContext(budget=ExecutionBudget(**{resource:1})))
        assert failed.outcome=="failed" and failed.value is None
        assert any(d.code=="budget."+resource for d in failed.diagnostics)
