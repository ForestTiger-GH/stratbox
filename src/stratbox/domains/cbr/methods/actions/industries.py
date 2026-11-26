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
    rows = []
    for source in frame.to_dict("records"):
        context.checkpoint()
        value = source.get("value")
        missing = value is None or value != value
        point = str(source["report_date"])
        if settings.kind == "industry_issuance":
            import calendar
            year, month = map(int, str(source["reference_period"]).split("-"))
            period = (date(year, month, 1).isoformat(), date(year, month, calendar.monthrange(year, month)[1]).isoformat())
        else:
            period = point
        rows.append({"metric": str(source.get("industry_code")), "subject": str(source.get("region_code")),
            "subject_namespace": "cbr.published_region", "period": period,
            "period_kind": "interval" if isinstance(period, tuple) else "as_of",
            "measure_kind": "flow" if settings.kind == "industry_issuance" else "stock",
            "unit": "RUB", "scale": Decimal(1000000), "perimeter": "CORPORATE_TOTAL",
            "value": None if missing else Decimal(str(value)), "value_status": "blank" if missing else "reported",
            "raw_token": None if missing else str(value),
            "dimensions": (("measure", str(source.get("measure"))), ("currency_scope", str(source.get("currency_scope")))),
            "evidence_ref": f"sha256:{tables.material.identity.sha256}#region={source.get('region_code')}&industry={source.get('industry_code')}"})
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
