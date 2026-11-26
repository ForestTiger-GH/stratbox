"""Separate escrow table geometry from source-local numerical interpretation."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from stratbox.domains.cbr.common.provenance import source_use
from stratbox.domains.cbr.common.issues import issue_parameters
from stratbox.shared.data.values import Assessment, DocumentEvidence, SourceDataset, TableEvidenceSet, WorkbookEvidence


@dataclass(frozen=True)
class EscrowTable:
    name: str
    header_row: int
    headers: tuple
    rows: tuple[tuple, ...]


def extract(inputs, settings, context):
    import pandas as pd
    from stratbox.domains.cbr.methods.tables.project_finance.parser import _find_header_row
    physical = inputs["physical"]
    if isinstance(physical, WorkbookEvidence):
        from stratbox.domains.cbr.methods.tables.decoded_workbooks import decoded_sheets
        material = physical.material
        candidates = tuple((name, tuple(rows)) for name, rows in decoded_sheets(
            physical.workbook, material.data, formulas=True, checkpoint=context.checkpoint))
    elif isinstance(physical, DocumentEvidence):
        material = physical.material
        blocks = getattr(physical.document, "blocks", ())
        candidates = tuple((f"table-{index}", tuple(block.rows))
            for index, block in enumerate(blocks) if getattr(block, "kind", None) == "table")
    else:
        raise ValueError("cbr.escrow_physical_evidence_required")
    if material.source_id not in {None, settings.series_id}:
        raise ValueError("cbr.escrow_source_mismatch")
    selected = []
    for name, rows in candidates:
        context.checkpoint()
        try:
            header_row, headers = _find_header_row(pd.DataFrame(rows, dtype=object))
        except ValueError:
            continue
        selected.append(EscrowTable(name, header_row, tuple(headers), tuple(rows[header_row + 1:])))
    if len(selected) != 1:
        raise ValueError("cbr.escrow_table_unresolved" if not selected else "cbr.escrow_table_ambiguous")
    tables = TableEvidenceSet(tuple(selected), material, settings.series_id,
        str(context.parameters.get("issue_id", material.metadata.get("issue_id", ""))))
    return {"tables": tables, "coverage": tables.assessment}


def interpret(inputs, settings, context):
    import pandas as pd
    from stratbox.domains.cbr.methods.tables.project_finance.columns import probe_indicator_columns
    from stratbox.domains.cbr.methods.tables.project_finance.parser import decode_cell
    from stratbox.domains.cbr.methods.tables.project_finance.rows import parse_escrow_rows
    tables = inputs["tables"]
    if not isinstance(tables, TableEvidenceSet) or tables.source_id != settings.series_id or tables.material is None:
        raise ValueError("cbr.escrow_table_evidence_required")
    parameters = issue_parameters(inputs, context, tables.issue_id)
    observed = str(parameters.get("as_of") or parameters.get("issue_id") or tables.issue_id)
    date.fromisoformat(observed)
    output, findings, unmapped = [], set(), set()
    for table in tables.tables:
        columns, unknown = probe_indicator_columns(table.headers, allow_unknown=True)
        unmapped.update(str(label) for _, label in unknown)
        findings.update("cbr.escrow.unmapped_header:" + str(label) for _, label in unknown)
        data = pd.DataFrame(table.rows, dtype=object)
        for region in parse_escrow_rows(data):
            context.checkpoint()
            for column in columns:
                token, kind, status, number = decode_cell(data.iat[region.source_row_index, column.source_index])
                if status == "unparsed" or status == "formula_unresolved":
                    findings.add("cbr.escrow.unparsed_cell")
                mapped_status = "reported" if number is not None else "dash" if status == "marker" else "blank" if status == "blank" else "missing"
                spec = column.spec
                output.append({"metric": spec.code, "subject": region.entity_name,
                    "subject_order": region.display_order,
                    "subject_namespace": "cbr.published_territory", "period": observed, "period_kind": "as_of",
                    "unit": spec.unit, "scale": Decimal(spec.scale), "measure_kind": spec.quantity_kind,
                    "perimeter": "national" if region.row_kind == "country" else "published_territory",
                    "value": number, "value_status": mapped_status, "raw_token": token,
                    "dimensions": (("row_kind", region.row_kind),
                        ("federal_district", region.federal_district_name or ""),
                        ("source_period_basis", "cumulative_start_unspecified" if spec.quantity_kind is None else "as_of")),
                    "evidence_ref": f"sha256:{tables.material.identity.sha256}#{table.name}!row={table.header_row + region.source_row_index + 2}&column={column.source_index + 1}"})
    if not output:
        raise ValueError("cbr.escrow_no_observations")
    assessment = Assessment("partial" if findings else "complete", tuple(sorted(findings)))
    dataset = SourceDataset(settings.series_id, tuple(output), {"source": "escrow", "unmapped_headers": tuple(sorted(unmapped))}, observed,
        (tables.material.identity,), assessment, source_uses=(source_use(settings.series_id, observed, tables.material.identity),))
    return {"dataset": dataset, "assessment": assessment}
