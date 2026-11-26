"""Direct source declarations and independently retained physical and semantic values."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO
from struct import pack

import pytest
from openpyxl import Workbook

from stratbox.capabilities.catalog import standard_catalog
from stratbox.capabilities.model import OperationDefinition, GraphBody, Call, InputRef, OutputRef
from stratbox.capabilities.model.contracts import PortContract
from stratbox.capabilities.model.targets import SeriesTarget, CalculationTarget, ProductTarget
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material, SourceDataset, View, EncodedProduct

SERIES="cbr.monetary_statistics.monetary_agg"


def workbook():
    book=Workbook();sheet=book.active;sheet.title="Денежные агрегаты"
    sheet.append(["Денежные агрегаты, млрд руб.",date(2026,1,1),date(2026,2,1)])
    sheet.append(["M2",123,456]);sheet.append(["Notes","source footnote","—"])
    stream=BytesIO();book.save(stream);book.close()
    return Material(stream.getvalue(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",SERIES)


def dbf(columns,rows):
    header=pack("<BBBBIHH20x",3,126,4,1,len(rows),33+32*len(columns),1+sum(c[2] for c in columns))
    descriptors=b"".join(pack("<11sc4xBB14x",n.encode(),k.encode(),size,decimals) for n,k,size,decimals in columns)
    records=b"".join(flag+b"".join(str(value).encode().ljust(column[2]) for value,column in zip(values,columns)) for flag,values in rows)
    return header+descriptors+b"\r"+records+b"\x1a"


def checked(result,port):
    assert result.outcome=="succeeded",result.diagnostics
    return result.output(port)


def test_complete_source_inventory_has_static_standard_routes():
    assert len(DOMAIN.series)==57
    assert len(DOMAIN.calculations)==12
    for source in DOMAIN.series.values():
        assert source.id==source.publication.series_id
        for command, spec in source.commands.items():
            assert standard_catalog().get(command).kind=="command"
            assert callable(spec.method.resolve())
        assert not hasattr(source,"version")
    assert "cbr.sors" in DOMAIN.calculations
    assert "cbr.sors.crosswalk" in DOMAIN.calculations
    with pytest.raises(TypeError):DOMAIN.series["forged"]=None


def test_original_physical_evidence_replays_without_decoding_again(monkeypatch):
    target=SeriesTarget(SERIES)
    with StrategyBox() as box:
        physical=checked(box.invoke("command.workbook.decode",inputs={"material":workbook()}),"physical")
        assert physical.workbook.sheets[0].cell(2,2).value==123
        encoded=checked(box.invoke("command.value.encode",inputs={"value":physical},target=target),"representation")
        def forbidden(*args,**kwargs):raise AssertionError("A retained physical value must not re-decode")
        monkeypatch.setattr("stratbox.core.formats.spreadsheets.cells.read_workbook_cells",forbidden)
        restored=checked(box.invoke("command.value.decode",inputs={"representation":encoded},target=target),"value")
        assert restored==physical
        assert restored.workbook.sheets[0].cell(3,2).value=="source footnote"
        dataset=checked(box.invoke("operation.series.extract_workbook",inputs={"physical":restored,"issue":"2026-04-01"},target=target),"dataset")
        assert dataset.rows and dataset.source_uses[0].coordinate.material_identity==physical.material.identity


def test_lossless_dbf_keeps_deleted_records_leading_zeros_precision_and_blank():
    columns=(("REGN","C",8,0),("ROW","C",8,0),("VALUE","N",18,4))
    content=dbf(columns,((b" ",("0012","011","000001.2300")),(b"*",("0012","012","99")),(b" ",("0012","013","0")),(b" ",("0012","014",""))))
    with StrategyBox() as box:
        physical=checked(box.invoke("command.dbf.decode",inputs={"material":Material(content,"application/x-dbf")}),"physical")
        assert len(physical.records)==4 and physical.records[1].deleted
        assert physical.records[0].values==("0012","011","000001.2300")
        assert physical.records[-1].values[-1]==""
        encoded=checked(box.invoke("command.value.encode",inputs={"value":physical}),"representation")
        assert checked(box.invoke("command.value.decode",inputs={"representation":encoded}),"value")==physical
        # A physically readable arbitrary DBF does not establish reviewed Form134 semantics.
        rejected=box.invoke("operation.series.extract_structured.dbf",inputs={"physical":physical,"issue":"2014-04-01"},parameters={"period":"2014-04-01","unit":"RUB","scale":1000},target=SeriesTarget("cbr.reporting_forms.f134"))
        assert rejected.outcome=="failed" and any("fields_unsupported" in str(item) for item in rejected.diagnostics)


@pytest.mark.parametrize("code,columns,values,period,issue",(
    ("134",(("REGN","N",4,0),("C1","C",15,0),("C3","N",16,4)),("0012","U104.2.2.1","123.2300"),"2014-04-01","2014-04-01"),
    ("803",(("REGN_GKO","N",4,0),("RAZDEL","C",3,0),("STR","C",5,0),("KORR_P","N",16,4),("KORR_M","N",16,4),("VSEGO","N",16,4)),("0012","001","00014","1.2300","0",""),("2024-01-01","2024-03-31"),"2024-04-01"),
))
def test_published_134_803_geometry_has_explicit_measurement_without_invented_financial_model(code,columns,values,period,issue):
    source="cbr.reporting_forms.f"+code
    with StrategyBox() as box:
        dataset=checked(box.invoke("operation.series.extract_structured.dbf",inputs={"material":Material(dbf(columns,((b" ",values),)),source_id=source),"issue":issue},parameters={"period":period,"unit":"RUB","scale":Decimal(1000)},target=SeriesTarget(source)),"dataset")
        assert len(dataset.rows)==(1 if code=="134" else 3)
        assert all(row["period"]==period and row["scale"]==Decimal(1000) and row["subject"]=="12" for row in dataset.rows)
        if code=="803":
            assert [row["value"] for row in dataset.rows]==[Decimal("1.2300"),Decimal(0),None]
            assert [row["value_status"] for row in dataset.rows]==["reported","reported","blank"]
        encoded=checked(box.invoke("command.value.encode",inputs={"value":dataset},target=SeriesTarget(source)),"representation")
        assert checked(box.invoke("command.value.decode",inputs={"representation":encoded},target=SeriesTarget(source)),"value")==dataset
        result=box.invoke("command.calculate.formula",inputs={"dataset":dataset},target=CalculationTarget("cbr.forms.f"+code+".model"))
        assert result.outcome=="failed" and any("requires_publisher_evidence" in str(item) for item in result.diagnostics)


def test_product_failure_keeps_accepted_source_dataset_and_prepared_view():
    definition=OperationDefinition("fixture.cbr.product",inputs={"material":PortContract("material",Material)},
        outputs={"dataset":PortContract("dataset",SourceDataset),"view":PortContract("view",View),"product":PortContract("product",EncodedProduct)},
        body=GraphBody((
            Call("extract","operation.series.extract_workbook",{"material":InputRef("material"),"issue":"2026-04-01"},target=SeriesTarget(SERIES)),
            Call("view","command.view.prepare",{"dataset":OutputRef("extract","dataset")},target=ProductTarget("cbr.statistics.table")),
            Call("render","command.product.render",{"view":OutputRef("view","view")},{"format":"unsupported"},target=ProductTarget("cbr.statistics.table")),
        ),{"dataset":OutputRef("extract","dataset"),"view":OutputRef("view","view"),"product":OutputRef("render","product")}))
    with StrategyBox() as box:
        result=box.invoke(definition,inputs={"material":workbook()})
        assert result.outcome=="failed"
        assert result.output("dataset").rows
        assert result.output("view").value
        with pytest.raises((KeyError,ValueError)):result.output("product")


def test_retained_dbf_content_cannot_disagree_with_its_original_byte_evidence():
    content=dbf((("REGN","C",8,0),("ROW","C",8,0),("VALUE","N",18,4)),((b" ",("0012","011","1.2300")),))
    with StrategyBox() as box:
        physical=checked(box.invoke("command.dbf.decode",inputs={"material":Material(content)}),"physical")
        assert physical.decoded_identity is not None
        record=replace(physical.records[0],values=("0012","011","9999"))
        with pytest.raises(ValueError,match="decoded_content_mismatch"):
            replace(physical,records=(record,))
        encoded=checked(box.invoke("command.value.encode",inputs={"value":physical}),"representation")
        assert checked(box.invoke("command.value.decode",inputs={"representation":encoded}),"value")==physical
