"""Physical fidelity, independent replay and bounded cross-domain processing."""
from dataclasses import replace
from datetime import date
from decimal import Decimal, localcontext
from io import BytesIO
import json

import pytest

from stratbox.core.formats.spreadsheets.extracts import extract_workbook
from stratbox.core.formats.documents import extract_document
from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.shared.data.documents import document_snapshot, document_from_snapshot
from stratbox.shared.data.workbooks import workbook_snapshot, workbook_from_snapshot, readable_workbook
from stratbox.shared.data.snapshots import CoverageDimension, SnapshotCoverage
from stratbox.shared.evidence import SourcePayload


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
    return SourcePayload(stream.getvalue(), source_id="example.table")


def test_sparse_source_geometry_survives_file_store_cold_replay(tmp_path):
    value = extract_workbook(workbook(sparse=True), series_id="example.table", issue_id="2026-11")
    assert value.sheets[0].columns == 16384
    assert value.sheets[0].cell(1,2).value == Decimal("1.25")
    assert value.sheets[0].cell(1,2).raw_token == "1.25"
    assert value.sheets[0].cell(1,4).formula == "B1*2"
    with pytest.raises(ValueError, match="dense_materialization"):
        value.sheets[0].values()
    scope = SnapshotCoverage("partial", "Explicit represented sheets", (
        CoverageDimension("sheets", requested=("Source ", "Absent"), materialized=("Source ",),
                          output=("Source ",), missing=("Absent",)),))
    value = replace(value, coverage=scope)
    snapshot = workbook_snapshot(value)
    store = FileDatasetStore(LocalFileStore(str(tmp_path)), "data", provider_id="files", scope_id="test")
    reference = store.write_snapshot(snapshot).reference
    restored = workbook_from_snapshot(store.read_snapshot(reference))
    assert restored == value
    assert restored.identity == value.identity
    assert b'"formula":"B1*2"' in readable_workbook(restored).data
    assert b'"name":"Source "' in readable_workbook(restored).data


def test_binary_xls_retains_decoded_precision_and_does_not_claim_source_lexeme():
    import xlwt
    book = xlwt.Workbook()
    sheet = book.add_sheet("Binary")
    sheet.write(0,0,0.1)
    sheet.write_merge(1,1,0,2,"Merged")
    stream = BytesIO(); book.save(stream)
    value = extract_workbook(SourcePayload(stream.getvalue()), series_id="example.legacy", issue_id="2012-01")
    cell = value.sheets[0].cell(1,1)
    assert cell.value == Decimal.from_float(0.1)
    assert cell.evidence_kind == "decoded_binary"
    assert value.sheets[0].merged_ranges == ("A2:C2",)
    assert any("formula" in q.lower() for q in value.qualifications)
    assert workbook_from_snapshot(workbook_snapshot(value)) == value


def test_empty_cached_strings_and_unpopulated_geometry_are_retained():
    from zipfile import ZipFile
    source=workbook(); stream=BytesIO()
    with ZipFile(BytesIO(source.data)) as before, ZipFile(stream,"w") as after:
        for name in before.namelist():
            raw=before.read(name)
            if name=="xl/worksheets/sheet1.xml":
                raw=raw.replace(b'<c r="D1"><f>B1*2</f><v></v></c>',
                    b'<c r="D1" t="str"><f>B1*2</f><v/></c>')
                raw=raw.replace(b'ref="A1:D2"',b'ref="A1:F9"')
            after.writestr(name,raw)
    value=extract_workbook(SourcePayload(stream.getvalue()),series_id="example.table",issue_id="2026")
    assert value.sheets[0].cell(1,4).value==""
    assert (value.sheets[0].rows,value.sheets[0].columns)==(9,6)
    assert workbook_from_snapshot(workbook_snapshot(value))==value


def test_compact_decimal_exponents_cannot_force_unbounded_manifest_expansion():
    from stratbox.shared.identity import canonical_manifest_bytes
    with pytest.raises(ValueError,match="decimal_expansion_limit"):
        canonical_manifest_bytes({"scale":Decimal("1e1000000000")})


def test_docx_body_order_and_grid_replay():
    from docx import Document
    doc = Document(); doc.add_paragraph("Before")
    table = doc.add_table(rows=1, cols=2); table.cell(0,0).text="A";table.cell(0,1).text="12"
    doc.add_paragraph("After")
    stream=BytesIO();doc.save(stream)
    value=extract_document(SourcePayload(stream.getvalue()),series_id="example.document",issue_id="2026")
    assert [b.kind for b in value.blocks] == ["paragraph","table","paragraph"]
    assert value.blocks[1].rows == (("A","12"),)
    assert value.blocks[2].text == "After"
    assert value.coverage.status == "partial"
    assert document_from_snapshot(document_snapshot(value)) == value


def test_pdf_page_failure_is_an_explicit_block(monkeypatch):
    import pypdf
    class Page:
        def extract_text(self): raise ValueError("broken text")
    class Reader:
        is_encrypted=False
        pages=[Page()]
        def __init__(self,*args,**kwargs): pass
    monkeypatch.setattr(pypdf,"PdfReader",Reader)
    value=extract_document(SourcePayload(b"%PDF-1.7\n"),series_id="example.pdf",issue_id="2026")
    assert value.blocks[0].kind == "error"
    assert value.blocks[0].page == 1
    assert any("text_extraction_failed" in q for q in value.qualifications)


def batch(value):
    from stratbox.shared.data.observations import Observation, ObservationBatch, MetricRef, PeriodRef, SubjectRef
    row=Observation(SubjectRef("source.region","001"),MetricRef("population","person","stock","v1",Decimal(1)),
        PeriodRef("as_of",date(2026,1,1)),(),"source-perimeter",value,"reported","sheet:1!B2",str(value))
    return ObservationBatch("example.population",1,"2026",(row,),())


def test_calculation_exactness_and_semantic_barriers():
    from stratbox.shared.data.calculations import compare_observations
    with localcontext() as context:
        context.prec=3
        result=compare_observations(batch(Decimal("1000000000000000000000000000000.01")),
                                    batch(Decimal("1000000000000000000000000000000.03")))
    assert result.changes[0].delta == Decimal("0.02")
    changed=batch(Decimal(1))
    changed=replace(changed,observations=(replace(changed.observations[0],perimeter="different"),))
    result=compare_observations(batch(Decimal(1)),changed)
    assert {c.kind for c in result.changes} == {"added","removed"}
    assert all(c.delta is None for c in result.changes)
    duplicated=replace(changed,observations=changed.observations*2)
    with pytest.raises(ValueError,match="ambiguous_duplicate"):
        compare_observations(changed,duplicated)


def test_prepared_view_snapshot_is_independent_of_source_and_writer():
    from stratbox.shared.data.views import prepare_observation_view,view_snapshot,view_from_snapshot,render_observation_view
    view=prepare_observation_view(batch(Decimal("1.2300")),view_id="example.view")
    restored=view_from_snapshot(view_snapshot(view))
    assert restored==view
    product=render_observation_view(restored,format="json")
    assert json.loads(product.data)["observations"][0]["value"]=="1.2300"


def test_bounded_query_has_a_pinned_cursor_and_retains_row_positions():
    from stratbox.shared.data.query import TableQuery,TablePredicate,query_snapshot
    from stratbox.shared.data.observation_snapshots import observation_snapshot
    snapshot=observation_snapshot(batch(Decimal(5)))
    query=TableQuery("observations",columns=("metric_id","decimal_value"),
        predicates=(TablePredicate("metric_id","eq","population"),),limit=1,scan_limit=1)
    result=query_snapshot(snapshot,query,expected_identity=snapshot.identity)
    assert result.table.rows==(("population",Decimal(5)),)
    assert result.source_rows==(0,) and not result.has_more
    from stratbox.shared.identity import ByteIdentity
    with pytest.raises(ValueError,match="snapshot_changed"):
        query_snapshot(snapshot,query,expected_identity=ByteIdentity.of(b"wrong"))


def test_update_plan_distinguishes_recompute_from_destination_copy():
    from stratbox.shared.data.processing import DataContract
    from stratbox.shared.data.updates import ProcessingTarget,RetainedProcessing,plan_updates
    from stratbox.shared.source_publications import SourceAssetIdentity
    from stratbox.shared.identity import ByteIdentity
    target=ProcessingTarget(SourceAssetIdentity("example.a","2026","main"),DataContract("example.schema"),
        ByteIdentity.of(b"source"),"v1",destinations=("archive","network"))
    previous=RetainedProcessing(target,ByteIdentity.of(b"result"),("archive",))
    decision=plan_updates((target,),(previous,)).decisions[0]
    assert not decision.recompute and decision.destinations_to_write==("network",)
    changed=replace(target,references=(("geography",ByteIdentity.of(b"new edition")),))
    decision=plan_updates((changed,),(previous,)).decisions[0]
    assert decision.source_state=="same" and decision.recompute
    assert decision.reasons==("reference_edition_changed",)


def test_reference_invocation_uses_real_definition_and_refuses_ungranted_effects():
    from stratbox.core.execution.machine.references import MemoryValueResolver,invoke_reference,reference_schemas
    from stratbox.core.operations.processing.definitions import ExtractRequest
    from stratbox.core.registry import core_catalog
    vault=MemoryValueResolver()
    reference=vault.retain(ExtractRequest(workbook(),"example.table","2026"))
    catalog=core_catalog()
    response=json.loads(invoke_reference(json.dumps({"operation_id":"workbook.extract","request_ref":reference,"preview_bytes":256}).encode(),catalog=catalog,values=vault))
    assert response["outcome"]=="succeeded" and response["value_ref"]
    assert response["preview"]["bounded"]
    schema,_=reference_schemas("dataset.write_snapshot",catalog=catalog)
    assert "dataset.write" in schema["x-effects-requiring-host-grant"]
    assert set(schema["required"]) == {"operation_id", "request_ref"}
    assert "contract_version" not in response
    assert "method_id" in response
    with pytest.raises(ValueError,match="effects_not_granted"):
        invoke_reference(json.dumps({"operation_id":"dataset.write_snapshot","request_ref":reference}).encode(),catalog=catalog,values=vault)


def test_reference_capacity_is_reserved_before_any_handler_and_preview_never_loses_receipt():
    from stratbox.core.execution.machine.references import MemoryValueResolver,invoke_reference,preview_value
    from stratbox.core.operations.processing.definitions import ExtractRequest,WORKBOOK
    vault=MemoryValueResolver(max_values=2)
    reference=vault.retain(ExtractRequest(workbook(),"example.table","2026"))
    class Catalog:
        called=False
        def get(self,*args): return WORKBOOK
        def resolve(self,*args):
            self.called=True
            raise AssertionError("No resolution or execution before capacity admission")
    catalog=Catalog()
    with pytest.raises(ValueError,match="capacity_exhausted"):
        invoke_reference(json.dumps({"operation_id":"workbook.extract","request_ref":reference}).encode(),catalog=catalog,values=vault)
    assert not catalog.called
    assert preview_value(10**5000,max_bytes=256)["value_omitted"]=="magnitude"


def test_processing_receipts_pin_inputs_parameters_and_control_results():
    from stratbox.core.operations.processing import handlers as h, definitions as d
    first=h.extract_workbook(d.ExtractRequest(workbook(),"example.table","first"))
    second=h.extract_workbook(d.ExtractRequest(workbook(),"example.table","second"))
    assert first.outcome==second.outcome=="succeeded"
    assert first.computation.computation_id!=second.computation.computation_id
    encoded=h.snapshot_workbook(d.WorkbookRequest(first.value))
    assert any(r.role=="input_workbook" for r in encoded.used_inputs)
    comparison=h.compare_workbooks(d.CompareWorkbooksRequest(first.value,second.value))
    assert comparison.outcome=="succeeded" and comparison.computation is not None
    assert comparison.resources_used and any(n=="output_bytes" for n,_ in comparison.resources_used)
    plan=h.plan_update(d.UpdatePlanRequest(()))
    assert plan.outcome=="succeeded" and plan.computation is not None
