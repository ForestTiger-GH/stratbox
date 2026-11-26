"""Physical fidelity, independent retention and bounded cross-domain processing."""
from dataclasses import replace
from datetime import date
from decimal import Decimal,localcontext
from io import BytesIO
import json
import pytest

from stratbox.core.execution.service import ExecutionFailure
from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.observability import MemoryJournal
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Assessment,Material,SourceDataset,canonical_tree,restore_tree,fingerprint
from stratbox.shared.data.coverage import CoverageDimension,SnapshotCoverage


def checked(result,port):
    assert result.outcome=="succeeded",result.diagnostics
    return result.output(port)

def workbook(sparse=False):
    from openpyxl import Workbook
    book = Workbook()
    sheet = book.active
    sheet.title = "Source "
    sheet.append(["Label", 1.25, "1,25*", "=B1*2"])
    sheet.merge_cells("A2:C2")
    if sparse:
        sheet.cell(1000, 16384).number_format = "0.00"
    stream = BytesIO()
    book.save(stream)
    return Material(stream.getvalue(), source_id="example.table")


def test_sparse_source_geometry_survives_cold_artifact_replay(tmp_path):
    store=LocalFileStore(tmp_path)
    with StrategyBox(providers={"filestore":store}) as box:
        value=checked(box.invoke("command.workbook.decode",inputs={"material":workbook(sparse=True)}),"physical")
        sheet=value.workbook.sheets[0]
        assert sheet.columns==16384 and sheet.cell(1,2).value==Decimal("1.25")
        assert sheet.cell(1,2).raw_token=="1.25" and sheet.cell(1,4).formula=="B1*2"
        with pytest.raises(ValueError,match="dense_materialization"):sheet.values()
        scope=SnapshotCoverage("partial","Explicit represented sheets",(CoverageDimension("sheets",requested=("Source ","Absent"),materialized=("Source ",),output=("Source ",),missing=("Absent",)),))
        value=replace(value,assessment=Assessment("partial",coverage=scope))
        encoded=checked(box.invoke("command.value.encode",inputs={"value":value}),"representation")
        reference=checked(box.invoke("command.artifact.commit",inputs={"material":encoded,"destination":"physical"}),"reference")
    with StrategyBox(providers={"filestore":LocalFileStore(tmp_path)}) as box:
        raw=checked(box.invoke("command.material.read",inputs={"location":reference}),"material")
        restored=checked(box.invoke("command.value.decode",inputs={"representation":raw.data}),"value")
        assert restored==value and restored.assessment.coverage==scope
        assert b"B1*2" in raw.data and b"Source " in raw.data


def test_binary_xls_keeps_decoded_precision_without_claiming_source_numeric_text():
    import xlwt
    book=xlwt.Workbook();sheet=book.add_sheet("Binary");sheet.write(0,0,0.1);sheet.write_merge(1,1,0,2,"Merged")
    stream=BytesIO();book.save(stream)
    with StrategyBox() as box:
        physical=checked(box.invoke("command.workbook.decode",inputs={"material":Material(stream.getvalue())}),"physical")
    cell=physical.workbook.sheets[0].cell(1,1)
    assert cell.value==Decimal.from_float(0.1) and cell.evidence_kind=="decoded_binary"
    assert physical.workbook.sheets[0].merged_ranges==("A2:C2",)
    assert physical.assessment.status=="partial" and "decoded_binary" in physical.assessment.qualifications
    assert restore_tree(canonical_tree(physical))==physical


def test_empty_cached_strings_and_unpopulated_geometry_are_retained():
    from zipfile import ZipFile
    original=workbook();stream=BytesIO()
    with ZipFile(BytesIO(original.data)) as before,ZipFile(stream,"w") as after:
        for name in before.namelist():
            raw=before.read(name)
            if name=="xl/worksheets/sheet1.xml":
                raw=raw.replace(b'<c r="D1"><f>B1*2</f><v></v></c>',b'<c r="D1" t="str"><f>B1*2</f><v/></c>')
                raw=raw.replace(b'ref="A1:D2"',b'ref="A1:F9"')
            after.writestr(name,raw)
    with StrategyBox() as box:
        physical=checked(box.invoke("command.workbook.decode",inputs={"material":Material(stream.getvalue())}),"physical")
    assert physical.workbook.sheets[0].cell(1,4).value==""
    assert (physical.workbook.sheets[0].rows,physical.workbook.sheets[0].columns)==(9,6)
    assert restore_tree(canonical_tree(physical))==physical


def test_compact_decimal_exponents_cannot_force_unbounded_manifest_expansion():
    from stratbox.shared.identity import canonical_manifest_bytes
    with pytest.raises(ValueError,match="decimal_expansion_limit"):
        canonical_manifest_bytes({"scale":Decimal("1e1000000000")})


def test_docx_body_order_and_table_grid_survive_independent_replay():
    from docx import Document
    doc=Document();doc.add_paragraph("Before");table=doc.add_table(rows=1,cols=2)
    table.cell(0,0).text="A";table.cell(0,1).text="12";doc.add_paragraph("After")
    stream=BytesIO();doc.save(stream)
    with StrategyBox() as box:
        physical=checked(box.invoke("command.document.decode",inputs={"material":Material(stream.getvalue())}),"physical")
    value=physical.document
    assert [block.kind for block in value.blocks]==["paragraph","table","paragraph"]
    assert value.blocks[1].rows==(("A","12"),) and value.blocks[2].text=="After"
    assert value.assessment.status=="partial"
    assert restore_tree(canonical_tree(physical))==physical


def test_pdf_page_failure_remains_explicit_partial_evidence(monkeypatch):
    import pypdf
    class Page:
        def extract_text(self):raise ValueError("broken text")
    class Reader:
        is_encrypted=False;pages=[Page()]
        def __init__(self,*args,**kwargs):pass
    monkeypatch.setattr(pypdf,"PdfReader",Reader)
    with StrategyBox() as box:
        physical=checked(box.invoke("command.document.decode",inputs={"material":Material(b"%PDF-1.7\n")}),"physical")
    assert physical.document.blocks[0].kind=="error" and physical.document.blocks[0].page==1
    assert physical.assessment.status=="partial"
    assert any("extraction_failed" in finding for finding in physical.assessment.findings)


def batch(value):
    return SourceDataset("example.population",({"subject_namespace":"source.region","subject":"001","metric":"population",
        "unit":"person","scale":Decimal(1),"measure_kind":"stock","period_kind":"as_of","period":"2026-01-01",
        "dimensions":(),"perimeter":"source-perimeter","value":value,"value_status":"reported","raw_token":str(value),"evidence_ref":"sheet:1!B2"},))


def test_calculation_exactness_duplicate_detection_and_semantic_perimeter_barriers():
    from stratbox.core.commands.calculations import observations_compare
    from types import SimpleNamespace
    with localcontext() as precision:
        precision.prec=3
        compared=observations_compare({"before":batch(Decimal("1000000000000000000000000000000.01")),
            "after":batch(Decimal("1000000000000000000000000000000.03"))},{},SimpleNamespace())["changes"]
    assert compared[0]["delta"]==Decimal("0.02")
    changed=replace(batch(Decimal(1)),rows=({**dict(batch(Decimal(1)).rows[0]),"perimeter":"different"},))
    result=observations_compare({"before":batch(Decimal(1)),"after":changed},{},SimpleNamespace())["changes"]
    assert {row["kind"] for row in result}=={"added","removed"} and all(row["delta"] is None for row in result)
    with pytest.raises(ExecutionFailure,match="duplicate"):
        observations_compare({"before":changed,"after":replace(changed,rows=changed.rows*2)},{},SimpleNamespace())


def test_prepared_view_replays_independently_of_source_and_writer(monkeypatch):
    with StrategyBox() as box:
        view=checked(box.invoke("command.view.prepare",inputs={"dataset":batch(Decimal("1.2300"))}),"view")
        encoded=checked(box.invoke("command.value.encode",inputs={"value":view}),"representation")
    def forbidden(*args,**kwargs):raise AssertionError("A prepared view does not repeat source processing")
    monkeypatch.setattr("stratbox.core.formats.spreadsheets.cells.read_workbook_cells",forbidden)
    with StrategyBox() as box:
        restored=checked(box.invoke("command.value.decode",inputs={"representation":encoded}),"value")
        product=checked(box.invoke("command.product.render",inputs={"view":restored},parameters={"format":"json"}),"product")
    assert restored==view and json.loads(product.data)[0]["value"]=="1.2300"


def test_bounded_query_pins_actual_snapshot_and_preserves_source_coordinates(tmp_path):
    store=FileDatasetStore(tmp_path);value=batch(Decimal(5))
    reference=store.ingest(value,destination="source",identity=value.identity)
    result=store.query(reference,{"filters":{"metric":"population"},"limit":1})
    assert result.rows[0]["value"]==Decimal(5) and result.rows[0]["evidence_ref"]=="sheet:1!B2"
    with pytest.raises(ValueError,match="conflict"):
        store.query(replace(reference,identity="f"*64),{})


def test_changed_reference_content_changes_semantic_work_without_changing_source_bytes():
    from stratbox.shared.identity import ByteIdentity
    original=ByteIdentity.of(b"publisher-original")
    a=replace(batch(Decimal(5)),lineage=(original,ByteIdentity.of(b"reference-A")))
    b=replace(a,lineage=(original,ByteIdentity.of(b"reference-B")))
    assert a.identity!=b.identity and a.lineage[0]==b.lineage[0]


def test_machine_projection_is_bounded_and_never_invents_release_contract_fields():
    from stratbox.sdk.machine import project,invoke
    with StrategyBox() as box:
        with pytest.raises(ValueError,match="unknown_request_fields"):
            invoke(box,{"capability_id":"command.value.encode","inputs":{"value":1},"grant_effects":True})
        result=invoke(box,{"capability_id":"command.value.encode","inputs":{"value":Decimal("1.2300")}})
        assert result.outcome=="succeeded"
        projection=project(result.output("representation"),max_items=3)
        assert "__truncated__" in projection
        assert "contract_version" not in projection


def test_work_identity_pins_parameters_while_values_keep_exact_content():
    journal=MemoryJournal()
    with StrategyBox(journal=journal) as box:
        outputs=[checked(box.invoke("command.value.encode",inputs={"value":batch(Decimal(5))},parameters={"purpose":name}),"representation") for name in ("first","second")]
    assert outputs[0].data==outputs[1].data
    started=[fact for fact in journal.read() if fact.kind=="work.started"]
    assert len(started)==2 and len({fact.physical_work_id for fact in started})==2
