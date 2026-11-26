"""Exact cells, retained semantics and independent product rendering."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from openpyxl import Workbook, load_workbook

from stratbox.core.commands import standard
from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.domains.cbr.methods.actions.workbook_comparison import compare_workbooks, validate_workbook
from stratbox.shared.data.values import Material

SERIES="cbr.monetary_statistics.monetary_agg"
XLSX="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def context(**parameters):
    return SimpleNamespace(parameters=parameters,checkpoint=lambda:None)


def action(command,inputs,**parameters):
    spec=DOMAIN.series[SERIES].commands["command."+command]
    return spec.method.resolve()(inputs,spec.settings,context(**parameters))


def replay(value):
    representation=action("value.encode",{"value":value})["representation"]
    return action("value.decode",{"representation":representation})["value"]


def interpret(value,**parameters):
    return action("table.interpret",{"tables":value},**parameters)["dataset"]


def prepare(dataset,**parameters):
    spec=DOMAIN.products["cbr.statistics.table"].commands["command.view.prepare"]
    return spec.method.resolve()({"dataset":dataset},spec.settings,context(**parameters))["view"]


def render(view,**parameters):
    spec=DOMAIN.products["cbr.statistics.table"].commands["command.product.render"]
    return spec.method.resolve()({"view":view},spec.settings,context(**parameters))["product"]


def workbook(*, exact="9007199254740993.00", name="Денежные агрегаты"):
    book = Workbook()
    sheet = book.active
    sheet.title = name
    sheet.append(["Monetary aggregate, млрд руб.", date(2026, 1, 1), date(2026, 2, 1)])
    sheet.append(["M2", 123, 456])
    sheet.append(["Unavailable", "—", None])
    sheet.append(["Formula", "=SUM(B2:C2)", 0])
    sheet.merge_cells("A6:C6")
    sheet["A6"] = "Methodology stays attached"
    out = BytesIO(); book.save(out)
    return rewrite(out.getvalue(), lambda name, data: data.replace(b"<v>123</v>", ("<v>" + exact + "</v>").encode())
                   if name == "xl/worksheets/sheet1.xml" else data)


def rewrite(data, fn):
    out = BytesIO()
    with ZipFile(BytesIO(data)) as old, ZipFile(out, "w") as new:
        for name in old.namelist():
            new.writestr(name, fn(name, old.read(name)))
    return out.getvalue()


def flake(data=None,*,issue="capture-1",asset="main"):
    material=Material(data or workbook(),XLSX,SERIES,metadata={"issue_id":issue,"asset_id":asset})
    physical=standard.workbook_decode({"material":material},None,context())["physical"]
    physical=replace(physical,material=material)
    return action("table.extract",{"physical":physical},issue_id=issue,asset_id=asset)["tables"]


def test_exact_numeric_lexeme_formulas_blank_and_merges_survive_source_replay():
    value=flake();cell=value.tables[0].cell(2,2)
    assert cell.value==Decimal("9007199254740993.00") and cell.raw_token=="9007199254740993.00"
    assert value.tables[0].cell(4,2).formula=="SUM(B2:C2)" and value.tables[0].cell(4,2).value is None
    assert value.tables[0].merged_ranges==("A6:C6",)
    restored=replay(value)
    assert restored==value
    assert {item[0] for item in validate_workbook(restored)}=={"cbr.workbook.formula_cache_missing"}
    physical=standard.workbook_decode({"material":value.material},None,context())["physical"]
    readable=standard.publication_transcribe({"physical":physical},None,context())["publication"]
    assert "9007199254740993.00" in str(readable)


def test_retained_dataset_and_view_render_without_original_or_parser(monkeypatch):
    original=flake();data=interpret(replay(original));rebuilt=replay(data)
    assert rebuilt==data
    target=next(row["metric"] for row in rebuilt.rows if dict(row["dimensions"])["source_hierarchy"]=="M2")
    view=replay(prepare(rebuilt,metrics=(target,)))
    def forbidden(*args,**kwargs):
        raise AssertionError("Rendering must consume only a prepared view")
    monkeypatch.setattr("stratbox.core.formats.spreadsheets.cells.read_workbook_cells",forbidden)
    representation=render(view)
    opened=load_workbook(BytesIO(representation.data),data_only=False)
    try:
        sheet=opened["Statistics"];headers=[cell.value for cell in sheet[4]]
        assert sheet.cell(5,headers.index("value")+1).value=="9007199254740993.00"
        assert representation.lineage==view.lineage
    finally:
        opened.close()


def selected():
    dataset=interpret(flake(workbook(exact="123")))
    rows=tuple(row for row in dataset.rows if dict(row["dimensions"])["source_hierarchy"]=="M2")
    return replace(dataset,rows=rows),rows


def test_computed_growth_has_distinct_measure_basis_and_exact_input_vector():
    dataset,items=selected()
    result=standard.calculate_change({"observations":dataset},{"mode":"percent"},context())["dataset"]
    row,=result.rows
    assert row["value"] > Decimal(270) and row["value"] < Decimal(271)
    assert row["measure_kind"]=="rate" and row["metric"]!=items[0]["metric"]
    assert dataset.identity in result.lineage
    assert row["baseline_evidence_ref"]==items[0]["evidence_ref"]


def test_byte_revision_and_source_fact_change_are_separate():
    before=flake(workbook(exact="123"));after=flake(workbook(exact="124"))
    difference=compare_workbooks(before,after)
    assert difference.source_change=="facts_changed" and difference.issue_change=="same_issue"
    assert [item.coordinate for item in difference.changes]==["B2"]


@pytest.mark.parametrize("mutation,diagnostic",[
    (lambda name,data:data.replace(b"http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        b"http://purl.oclc.org/ooxml/spreadsheetml/main"),"namespace_unsupported"),
    (lambda name,data:data.replace(b'<c r="B2"',b'<c s="-1" r="B2"') if name.endswith("sheet1.xml") else data,"invalid_cell"),
])
def test_unreviewed_namespace_and_negative_style_index_fail_closed(mutation,diagnostic):
    with pytest.raises(ValueError,match=diagnostic):
        read_workbook_cells(rewrite(workbook(),mutation))


def test_forged_source_or_numeric_lexeme_cannot_be_retained_as_complete_evidence():
    value=flake()
    with pytest.raises(ValueError,match="source_mismatch"):
        action("value.encode",{"value":replace(value,source_id="cbr.other")})
    sheet=value.tables[0]
    cells=tuple(replace(cell,value=999) if cell.coordinate=="B2" else cell for cell in sheet.cells)
    with pytest.raises(ValueError,match="numeric_evidence_mismatch"):
        action("value.encode",{"value":replace(value,tables=(replace(sheet,cells=cells),))})
