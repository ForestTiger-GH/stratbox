"""Prepared office-count tables independent of source acquisition and calculation."""
from dataclasses import dataclass
from decimal import Decimal
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.identity import canonical_manifest_bytes
from stratbox.shared.evidence import UsedInputReceipt

@dataclass(frozen=True, slots=True)
class OfficeViewRequest:
    batch: ObservationBatch
    dataset_id: str
    version_id: str
    subjects: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class RenderOfficeViewRequest:
    view: DatasetSnapshot
    format: str = "xlsx"

VIEW = DataContract("cbr.service_network.view", 1, DataRole.PRODUCTS)
_T, _D, _N = ScalarType.TEXT, ScalarType.DATE, ScalarType.DECIMAL
_SCHEMA = TableSchema(DataContract("cbr.service_network.view.rows", 1, DataRole.PRODUCTS), tuple(ColumnSchema(*item) for item in (
    ("subject_namespace", _T), ("subject", _T), ("metric", _T), ("unit", _T), ("scale", _N, True),
    ("period_kind", _T), ("as_of", _D, True), ("start", _D, True), ("end", _D, True),
    ("dimensions", _T), ("perimeter", _T), ("value", _N, True), ("status", _T), ("evidence", _T),
)))


def build_view(request):
    dependency = UsedInputReceipt("view_observations", observation_snapshot(request.batch).identity,
        "application/vnd.stratbox.dataset+json", "inline", request.batch.dataset_id)
    rows=[]
    for item in request.batch.observations:
        if request.subjects and item.subject.id not in request.subjects or request.metrics and item.metric.id not in request.metrics:
            continue
        if item.value is not None and type(item.value) not in {int, Decimal}:
            raise ValueError("cbr.offices.view_numeric_value_required")
        rows.append((item.subject.namespace, item.subject.id, item.metric.id, item.metric.unit, item.metric.scale,
            item.period.kind, item.period.as_of, item.period.start, item.period.end,
            canonical_manifest_bytes(dict(item.dimensions)).decode("utf-8"), item.perimeter,
            Decimal(item.value) if item.value is not None else None, item.value_status, item.evidence_ref))
    return DatasetSnapshot.build(request.dataset_id, request.version_id, VIEW, (("observations", TypedTable(_SCHEMA, tuple(rows))),),
        coverage=SnapshotCoverage("complete", "Selected admitted office observations; source-wide coverage is inherited from the supplied batch."),
        inputs=tuple(dict.fromkeys((*request.batch.lineage, dependency))))


def render_view(request, budget):
    import csv
    from io import StringIO
    from stratbox.shared.data.representation import Representation, CSV, XLSX
    from stratbox.core.formats.spreadsheets.workbook_bytes import openpyxl_bytes
    if (not request.view.complete or request.view.manifest.contract != VIEW
            or tuple(name for name, _ in request.view.tables) != ("observations",)
            or request.view.table("observations").schema != _SCHEMA):
        raise ValueError("cbr.offices.view_invalid")
    table = request.view.table("observations")
    header = tuple(column.name for column in table.schema.columns)
    if request.format == "csv":
        stream=StringIO(newline="");writer=csv.writer(stream,lineterminator="\n")
        writer.writerow(header);writer.writerows(table.rows)
        data=stream.getvalue().encode("utf-8")
        budget.charge("output_bytes",len(data))
        return Representation("cbr.service_network.csv",1,CSV,data,"utf-8")
    if request.format != "xlsx":
        raise ValueError("request.office_output_format_invalid")
    from openpyxl import Workbook
    book=Workbook();sheet=book.active;sheet.title="Office counts"
    try:
        sheet.append(header)
        for row in table.rows:
            sheet.append(row)
        sheet.freeze_panes="C2";sheet.auto_filter.ref=sheet.dimensions
        for column in ("A","B","C","J","K","N"):
            sheet.column_dimensions[column].width=28 if column != "J" else 48
        return Representation("cbr.service_network.xlsx",1,XLSX,openpyxl_bytes(book,literal_text=True,budget=budget))
    finally:
        book.close()
