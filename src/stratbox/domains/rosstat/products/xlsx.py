"""Notebook-style monthly XLSX; presentation only, no statistical aggregation."""
from __future__ import annotations
from datetime import date,timedelta
from stratbox.core.runtime.dependencies import require_extra
from stratbox.core.formats.spreadsheets.workbook_bytes import openpyxl_bytes
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.views import ObservationView
from ..tables.profiles import KEP2_INDICATORS, KEP2_MEASURES


def render_kep2_xlsx(view: ObservationView) -> Representation:
    if view.view_id != "rosstat.kep2.monthly":
        raise ValueError("rosstat.kep2.monthly_view_required")
    index,dates={},set()
    for value in view.batch.observations:
        dims=dict(value.dimensions)
        if dims.get("frequency") != "monthly" or value.period.kind != "interval":
            raise ValueError("rosstat.kep2.view_frequency_mismatch")
        display=date.fromisoformat(dims["display_date"])
        if display != value.period.end + timedelta(days=1) or value.period.start.day != 1 or display.day != 1:
            raise ValueError("rosstat.kep2.view_display_date_invalid")
        key=(dims["indicator_id"],dims["measure"],display)
        if key in index:
            raise ValueError("rosstat.kep2.product_duplicate_cell")
        index[key]=value
        if value.value is not None:
            dates.add(display)
    periods=tuple(sorted(dates))
    if not periods:
        raise ValueError("rosstat.kep2.product_empty")
    openpyxl=require_extra("openpyxl","excel")
    from openpyxl.styles import Font,PatternFill,Border,Side,Alignment
    from openpyxl.utils import get_column_letter
    book=openpyxl.Workbook()
    sheet=book.active
    sheet.title="Росстат"
    sheet.sheet_view.showGridLines=False
    sheet["A2"]="КРАТКОСРОЧНАЯ СТАТИСТИКА РОССТАТА"
    sheet["A3"]="Ежемесячные показатели"
    sheet["A2"].font=Font(name="Arial",size=12,bold=True)
    sheet["A3"].font=Font(name="Arial",size=10,bold=True)
    fill=PatternFill("solid",fgColor="DAE3F3")
    border=Border(left=Side(style="thin",color="DDDDDD"),right=Side(style="thin",color="DDDDDD"),
        top=Side(style="thin",color="DDDDDD"),bottom=Side(style="thin",color="DDDDDD"))
    for col,period in enumerate(periods,3):
        cell=sheet.cell(4,col,period.isoformat())
        cell.fill=fill
        cell.font=Font(name="Arial",size=10,bold=True)
        cell.border=border
    row=5
    for measure,label,_ in KEP2_MEASURES:
        for indicator in KEP2_INDICATORS:
            sheet.cell(row,1,indicator.label)
            sheet.cell(row,2,label)
            for col,period in enumerate(periods,3):
                source=index.get((indicator.id,measure,period))
                cell=sheet.cell(row,col)
                if source is not None and source.value is not None:
                    # XLSX is a display product. The exact Decimal and source
                    # token remain text columns in Evidence, independent of its
                    # one-decimal presentation format.
                    cell.value=source.value
                cell.number_format="#,##0.0"
            for cell in sheet[row]:
                cell.font=Font(name="Arial",size=10,bold=cell.column <= 2)
                cell.border=border
                cell.alignment=Alignment(vertical="top",wrap_text=cell.column <= 2)
            sheet.row_dimensions[row].height=30
            row+=1
        row+=2
    sheet.column_dimensions["A"].width=34
    sheet.column_dimensions["B"].width=23
    for col in range(3,len(periods)+3):
        sheet.column_dimensions[get_column_letter(col)].width=13
    sheet.freeze_panes="C5"
    evidence=book.create_sheet("Evidence")
    evidence.append(("indicator_id","measure","period_start","period_end","display_date","value_exact",
        "value_status","unit","scale","unit_literal","raw_token","footnotes","number_format","source_evidence"))
    for value in view.batch.observations:
        dims=dict(value.dimensions)
        evidence.append((dims["indicator_id"],dims["measure"],value.period.start.isoformat(),value.period.end.isoformat(),
            dims["display_date"],str(value.value) if value.value is not None else None,value.value_status,value.metric.unit,
            str(value.metric.scale),dims.get("unit_literal"),value.raw_token,dims.get("source_footnotes"),
            dims.get("source_number_format"),value.evidence_ref))
    evidence.freeze_panes="F2"
    evidence.auto_filter.ref=evidence.dimensions
    for cell in evidence[1]:
        cell.font=Font(name="Arial",bold=True)
        cell.fill=fill
    for col in range(1,15):
        evidence.column_dimensions[get_column_letter(col)].width=20 if col<10 else 42
    metadata=book.create_sheet("Metadata")
    for pair in (("view_id",view.view_id),("dataset_sha256",view.source_identity.sha256),
        ("coverage",view.coverage.status),("scope",view.coverage.description),
        ("date_convention","First day after the actual source month; actual intervals are in Evidence."),
        ("index_basis","Published percent-of-baseline indices. 100 is the comparison baseline; no subtraction is applied."),
        ("agriculture","The reviewed source publishes its year-on-year index only; empty absolute and previous-period rows are retained.")):
        metadata.append(pair)
    for receipt in view.batch.lineage:
        metadata.append((receipt.role,receipt.identity.sha256))
    metadata.column_dimensions["A"].width=24
    metadata.column_dimensions["B"].width=100
    for row in metadata:
        for cell in row:
            cell.alignment=Alignment(vertical="top",wrap_text=True)
    return Representation("rosstat.kep2.monthly.xlsx",1,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",openpyxl_bytes(book,literal_text=True))
