"""Office tables consume existing physical HTML or workbook evidence."""
from datetime import date
from xml.etree.ElementTree import Element, SubElement

from stratbox.domains.cbr.common.provenance import source_use
from stratbox.domains.cbr.common.issues import issue_parameters
from stratbox.shared.data.values import Assessment, DocumentEvidence, Material, SourceDataset, TableEvidenceSet, WorkbookEvidence


def decode_document(inputs, settings, context):
    from stratbox.core.commands._physical import bounded_material_bytes, physical_material
    from stratbox.domains.cbr.methods.tables.service_network.bank_offices.parser import MAX_HTML, SourceScanner
    from stratbox.shared.data.values import IdentifiedMaterial, ImmutableMaterialRef
    from stratbox.shared.data.materials import StagedMaterialRef
    original = inputs["material"]
    carrier = physical_material(original)
    material = original if isinstance(original, IdentifiedMaterial) else carrier
    if not isinstance(carrier, (Material, ImmutableMaterialRef, StagedMaterialRef)) or material.source_id not in {None, settings.series_id}:
        raise ValueError("cbr.office_material_required")
    limit = context.parameters.get("max_materialized_bytes", 32 * 1024 * 1024)
    if type(limit) is not int or limit < 1:
        raise ValueError("cbr.office_html_limit")
    if material.identity.size > MAX_HTML:
        raise ValueError("cbr.office_html_limit")
    data = bounded_material_bytes(original, context, max_bytes=min(limit, MAX_HTML))
    scanner = SourceScanner()
    scanner.feed(data.decode(material.charset or "utf-8"))
    scanner.close()
    context.checkpoint()
    return {"physical": DocumentEvidence(material, scanner.snapshot())}


def _territorial_sheets(workbook, context):
    from stratbox.domains.cbr.methods.tables.service_network.territorial_offices.parser import XML
    result = []
    for sheet in workbook.sheets:
        context.checkpoint()
        by_row, formulas = {}, {}
        for cell in sheet.cells:
            value = cell.raw_token if cell.kind in {"n", "e"} and cell.raw_token is not None else cell.value
            token = "" if value is None else str(value)
            if token:
                by_row.setdefault(cell.row, {})[cell.column] = token
            if cell.formula is not None:
                formulas[cell.row, cell.column] = {"formula": cell.formula, "attributes": dict(cell.formula_attributes),
                    **({"cache_missing": True} if cell.value is None else {})}
            if cell.kind == "e":
                formulas.setdefault((cell.row, cell.column), {})["error_value"] = True
        merges = Element(XML + "worksheet")
        for reference in sheet.merged_ranges:
            SubElement(merges, XML + "mergeCell", {"ref": reference})
        result.append((sheet.name, sorted(by_row.items()), formulas, merges))
    return result


def extract(inputs, settings, context):
    physical = inputs["physical"]
    if settings.kind == "bank_offices":
        from stratbox.domains.cbr.methods.tables.service_network.bank_offices.parser import extract_records
        if not isinstance(physical, DocumentEvidence):
            raise ValueError("cbr.office_document_evidence_required")
        records, count = extract_records(scanned=physical.document)
        selected = tuple(tuple(row) for row in records)
        metadata = {"data_rows": count}
    else:
        from stratbox.domains.cbr.methods.tables.service_network.territorial_offices.parser import convert_xlsx
        from stratbox.domains.cbr.common.csv import csv_rows
        if not isinstance(physical, WorkbookEvidence):
            raise ValueError("cbr.office_workbook_evidence_required")
        if physical.workbook.identity != physical.material.identity:
            raise ValueError("cbr.office_workbook_identity_mismatch")
        metadata = {}
        observed = context.parameters.get("as_of") or context.parameters.get("issue_id")
        if observed is None:
            raise ValueError("cbr.office_as_of_required")
        decoded = _territorial_sheets(physical.workbook, context)
        csv, formula_lineage = convert_xlsx(None, return_formula_lineage=True, expected_date=date.fromisoformat(str(observed)),
            sheet_name=context.parameters.get("sheet"), national_row=context.parameters.get("national_row"),
            last_row=context.parameters.get("last_row"), evidence=metadata, decoded_sheets=decoded,
            checkpoint=context.checkpoint)
        selected = tuple(tuple(row) for row in csv_rows(csv))
        metadata["csv"] = csv
        metadata["formula_lineage"] = formula_lineage
    material = physical.material
    if material.source_id not in {None, settings.series_id}:
        raise ValueError("cbr.office_source_mismatch")
    tables = TableEvidenceSet(selected, material, settings.series_id,
        str(context.parameters.get("issue_id", "")), metadata=metadata)
    return {"tables": tables, "coverage": tables.assessment}


def interpret(inputs, settings, context):
    from stratbox.domains.cbr.methods.actions.statistics import observation_row
    tables = inputs["tables"]
    if not isinstance(tables, TableEvidenceSet) or tables.source_id != settings.series_id or tables.material is None:
        raise ValueError("cbr.office_table_evidence_required")
    parameters = issue_parameters(inputs, context, tables.issue_id)
    if settings.kind == "bank_offices":
        from stratbox.domains.cbr.methods.tables.service_network.bank_offices.observations import _observations
        captured = parameters.get("captured_on")
        official = parameters.get("official_as_of")
        if captured is None:
            raise ValueError("cbr.office_capture_date_required")
        captured = date.fromisoformat(str(captured))
        official = date.fromisoformat(str(official)) if official is not None else None
        observations = _observations(tables.tables, captured, official)
        excluded = ()
    else:
        from stratbox.domains.cbr.methods.tables.service_network.territorial_offices.observations import _observations
        observed = parameters.get("as_of") or tables.issue_id
        observations, excluded = _observations(tables.metadata["csv"], date.fromisoformat(str(observed)),
            unresolved=tuple(tables.metadata.get("unresolved_fields", ())))
        if observations is None:
            raise ValueError("cbr.office_indicators_unresolved")
    rows = []
    for value in observations:
        row = observation_row(value)
        row["measure_kind"] = "count"
        row["evidence_ref"] = "sha256:" + tables.material.identity.sha256 + "#" + row["evidence_ref"]
        rows.append(row)
    qualifications = set(tables.assessment.qualifications)
    if settings.kind == "bank_offices" and official is None:
        qualifications.add("capture_date_is_not_official_as_of")
    assessment = Assessment("partial" if excluded else tables.assessment.status,
        (*tables.assessment.findings, *(str(item) for item in excluded)),
        qualifications=frozenset(qualifications))
    semantics = {"source": settings.kind, "measure_kind": "count",
        "source_scope": dict(tables.metadata), "excluded_fields": tuple(excluded)}
    if settings.kind == "bank_offices":
        semantics.update(captured_on=captured.isoformat(),
            official_as_of=official.isoformat() if official is not None else None,
            period_basis="official_as_of" if official is not None else "capture")
    else:
        semantics.update(official_as_of=date.fromisoformat(str(observed)).isoformat(),
            period_basis="official_as_of")
    dataset = SourceDataset(settings.series_id, tuple(rows), semantics, str(parameters.get("issue_id", tables.issue_id)),
        (tables.material.identity,), assessment, source_uses=(source_use(settings.series_id, tables.issue_id or semantics.get("official_as_of") or semantics.get("captured_on"), tables.material.identity),))
    return {"dataset": dataset, "assessment": assessment}
