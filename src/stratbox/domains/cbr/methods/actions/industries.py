"""Regional industry tables keep their published six-component semantics."""
from datetime import date
from dataclasses import replace
from decimal import Decimal

from stratbox.domains.cbr.common.provenance import source_use
from stratbox.domains.cbr.common.issues import issue_parameters
from stratbox.shared.data.values import Assessment, SourceDataset, TableEvidenceSet, WorkbookEvidence


def extract(inputs, settings, context):
    evidence = inputs["physical"]
    if not isinstance(evidence, WorkbookEvidence) or evidence.material.source_id not in {None, settings.series_id}:
        raise ValueError("cbr.industry_workbook_evidence_required")
    if evidence.workbook.identity != evidence.material.identity:
        raise ValueError("cbr.industry_original_identity_mismatch")
    tables = TableEvidenceSet((evidence.workbook,), evidence.material, settings.series_id,
        str(context.parameters.get("issue_id", evidence.material.metadata.get("issue_id", ""))))
    return {"tables": tables, "coverage": tables.assessment}


def interpret(inputs, settings, context):
    tables = inputs["tables"]
    if not isinstance(tables, TableEvidenceSet) or tables.source_id != settings.series_id or tables.material is None:
        raise ValueError("cbr.industry_table_evidence_required")
    workbook = tables.tables[0]
    parameters = issue_parameters(inputs, context, tables.issue_id)
    source_name = str(parameters.get("source_name") or tables.material.metadata.get("name") or "")
    if not source_name:
        raise ValueError("cbr.industry_source_name_required")
    if settings.kind == "industry_debt":
        from stratbox.domains.cbr.methods.tables.corporate_lending.debt.parser import parse_cbr_0105a_debt_corp_excel_bytes
        parsed = parse_cbr_0105a_debt_corp_excel_bytes(tables.material.data, source_name=source_name,
            decoded=workbook, checkpoint=context.checkpoint)
    else:
        from stratbox.domains.cbr.methods.tables.corporate_lending.issuance.parser import parse_workbook
        parsed = parse_workbook(tables.material.data, source_name=source_name,
            decoded=workbook, checkpoint=context.checkpoint)
    frame = parsed.df_stream
    from stratbox.domains.cbr.common.contracts import SourceContentEvidence
    from stratbox.shared.data.tables import table_identity
    from stratbox.shared.evidence import UsedInputReceipt
    seal = SourceContentEvidence(table_identity((("stream", frame),)), (
        UsedInputReceipt("source_workbook", tables.material.identity, tables.material.media_type,
            "inline", settings.series_id),))
    parsed = replace(parsed, evidence=seal)
    from stratbox.domains.cbr.methods.tables.corporate_lending.observations import cell_number
    cells = {sheet.name: {cell.coordinate: cell for cell in sheet.cells} for sheet in workbook.sheets}
    rows = []
    for source in frame.to_dict("records"):
        context.checkpoint()
        coordinate = str(source["source_column"]) + str(source["source_row"])
        cell = cells[str(source["source_sheet_name"])].get(coordinate)
        value, status = cell_number(cell)
        token = cell.raw_token if cell is not None else None
        if token is None and cell is not None and cell.value is not None:
            token = str(cell.value)
        parent = source.get("federal_district_name")
        parent = "" if parent is None or parent != parent else str(parent)
        point = str(source["report_date"])
        if settings.kind == "industry_issuance":
            import calendar
            year, month = map(int, str(source["reference_period"]).split("-"))
            period = (date(year, month, 1).isoformat(), date(year, month, calendar.monthrange(year, month)[1]).isoformat())
        else:
            period = point
        rows.append({"metric": str(source.get("industry_code")), "subject": str(source.get("region_code")),
            "subject_label": str(source.get("region_name")), "subject_order": int(source.get("region_order")),
            "subject_kind": str(source.get("region_kind")), "subject_parent": parent,
            "metric_label": str(source.get("industry_name_ru")), "metric_order": int(source.get("industry_order")),
            "reporting_date": point, "reference_period": str(source.get("reference_period") or point),
            "subject_namespace": "cbr.published_region", "period": period,
            "period_kind": "interval" if isinstance(period, tuple) else "as_of",
            "measure_kind": "flow" if settings.kind == "industry_issuance" else "stock",
            "unit": "RUB", "scale": Decimal(1000000), "perimeter": "CORPORATE_TOTAL",
            "value": Decimal(str(value)) if value is not None else None,
            "value_status": "reported" if value is not None else "blank" if status == "blank" else "dash" if status == "marker" else "missing",
            "raw_token": token,
            "dimensions": (("measure", str(source.get("measure"))), ("currency_scope", str(source.get("currency_scope")))),
            "evidence_ref": f"sha256:{tables.material.identity.sha256}#{source['source_sheet_name']}!{coordinate}"})
    diagnostics = getattr(parsed, "validation_issues", ())
    findings = tuple(sorted({str(getattr(item, "code", item)) for item in diagnostics}))
    assessment = Assessment("partial" if findings else "complete", findings)
    dataset = SourceDataset(settings.series_id, tuple(rows), {"source": settings.kind}, str(parameters.get("issue_id", parsed.report_date)),
        (tables.material.identity,), assessment, native=parsed, source_uses=(source_use(settings.series_id, parsed.report_date, tables.material.identity),))
    return {"dataset": dataset, "assessment": assessment}


def validate(inputs, settings, context):
    from stratbox.domains.cbr.methods.actions.observations import validate as validate_observations
    result = validate_observations(inputs, settings, context)
    native = result["dataset"].native
    issues = getattr(native, "validation_issues", ())
    if native is None or any(issue.severity == "error" for issue in issues):
        raise ValueError("cbr.industry_source_validation_failed")
    return result
