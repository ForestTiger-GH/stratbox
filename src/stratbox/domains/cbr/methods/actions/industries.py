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
    source_name = str(parameters.get("source_name") or tables.material.metadata.get("filename")
        or tables.material.metadata.get("name") or "")
    if not source_name:
        raise ValueError("cbr.industry_source_name_required")
    if settings.kind == "industry_debt":
        from stratbox.domains.cbr.methods.tables.corporate_lending.debt.parser import parse_cbr_0105a_debt_corp_excel_bytes
        parsed = parse_cbr_0105a_debt_corp_excel_bytes(tables.material.identity, source_name=source_name,
            decoded=workbook, checkpoint=context.checkpoint)
    else:
        from stratbox.domains.cbr.methods.tables.corporate_lending.issuance.parser import parse_workbook
        parsed = parse_workbook(tables.material.identity, source_name=source_name,
            decoded=workbook, checkpoint=context.checkpoint)
    if parameters.get("issue_id") not in {None, "", parsed.report_date}:
        raise ValueError("cbr.industry_issue_date_mismatch")
    frame = parsed.df_stream
    from stratbox.domains.cbr.common.contracts import SourceContentEvidence
    from stratbox.shared.data.tables import table_identity
    from stratbox.shared.evidence import UsedInputReceipt
    seal = SourceContentEvidence(table_identity((("stream", frame),)), (
        UsedInputReceipt("source_workbook", tables.material.identity, tables.material.media_type,
            "inline" if hasattr(tables.material, "data") else "reference_only", settings.series_id),))
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
    from collections.abc import Mapping
    from stratbox import __version__
    from stratbox.shared.data.history import make_validation_certificate, verify_history_certificates
    from stratbox.shared.data.values import fingerprint
    from stratbox.domains.cbr.methods.actions.observations import validate as validate_observations
    result = validate_observations(inputs, settings, context)
    dataset = result["dataset"]
    native = dataset.native
    method = getattr(context, "method_identity", fingerprint((__name__ + ":validate", settings)))
    build = getattr(context, "build_identity", __version__)
    rule = "cbr.industry.source"
    if native is None or dataset.validation_certificates:
        verifier = getattr(context, "verify_validation_certificate", None)
        def competent(certificate):
            return (certificate.rule_id == rule and certificate.method_identity == method
                and certificate.build_identity == build and certificate.source_id == settings.series_id
                and verifier is not None and verifier(certificate))
        if not verify_history_certificates(dataset, competent):
            raise ValueError("cbr.industry_source_validation_evidence_required")
        return {"dataset": replace(dataset, native=None), "assessment": dataset.assessment}
    issues = getattr(native, "validation_issues", ())
    if any(issue.severity == "error" for issue in issues):
        raise ValueError("cbr.industry_source_validation_failed")
    accepted = getattr(context, "accepted_input", None)
    if accepted is not None:
        evidence = accepted("dataset")
        producer = evidence.get("produced_by") if isinstance(evidence, Mapping) else getattr(evidence, "produced_by", None)
        if producer != "command.table.interpret":
            raise ValueError("cbr.industry_source_validation_evidence_required")
    identities = tuple(dict.fromkeys(use.coordinate.material_identity for use in dataset.source_uses
        if use.coordinate.material_identity is not None))
    certificate = make_validation_certificate(dataset, rule_id=rule,
        method_identity=method, build_identity=build, material_identities=identities)
    qualified = replace(dataset, validation_certificates=(certificate,))
    return {"dataset": qualified, "assessment": qualified.assessment}
