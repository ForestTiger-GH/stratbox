"""Reviewed document geometry and economic fields; conversion is upstream work."""
from datetime import date

from stratbox.shared.data.values import Assessment, DocumentEvidence, IntegratedDataset, SourceDataset, TableEvidenceSet
from ..common.numbers import numeric_value
from ..common.evidence import interpreted_use
from ..common.evidence import issue_id
from dataclasses import replace


def extract(inputs, settings, context):
    physical = inputs["physical"]
    if not isinstance(physical, DocumentEvidence):
        raise TypeError("minfin.document.evidence_required")
    if physical.material.source_id not in {None, settings.source_id}:
        raise ValueError("minfin.document.source_mismatch")
    document = physical.document
    if document.format != settings.format:
        raise ValueError("minfin.document.reviewed_geometry_required")
    blocks = tuple(document.blocks)
    if not any(block.kind == "table" and block.rows for block in blocks):
        raise ValueError("minfin.document.table_geometry_required")
    tables = TableEvidenceSet(blocks, physical.material, settings.source_id,
        str(physical.material.metadata.get("issue_id", "")), physical.assessment,
        {"format": document.format, **dict(physical.material.metadata)})
    return {"tables": tables, "coverage": tables.assessment}


def interpret(inputs, settings, context):
    tables = inputs["tables"]
    if not isinstance(tables, TableEvidenceSet) or tables.source_id != settings.source_id:
        raise ValueError("minfin.document.source_mismatch")
    tables = replace(tables, issue_id=issue_id(inputs, tables, context, settings.source_id))
    fields = tuple(getattr(context, "parameters", {}).get("fields", settings.fields))
    anchors = tuple(getattr(context, "parameters", {}).get("required_text", settings.required_text))
    if not fields or not anchors:
        raise ValueError("minfin.document.reviewed_fields_required")
    text = "\n".join(block.text if block.kind != "table" else "\n".join(" | ".join(row) for row in block.rows)
                     for block in tables.tables)
    if not all(anchor in text for anchor in anchors):
        raise ValueError("minfin.document.layout_unsupported")
    rows, keys = [], set()
    digest = tables.material.identity.sha256 if tables.material else "unretained"
    for field in fields:
        context.checkpoint()
        if min(field.block, field.row, field.column, field.label_column) < 0 or field.scale <= 0:
            raise ValueError("minfin.document.field_invalid")
        day = date.fromisoformat(field.as_of)
        try:
            block = tables.tables[field.block]
            if block.kind != "table":
                raise ValueError("minfin.document.table_geometry_required")
            source_row = block.rows[field.row]
            if " ".join(source_row[field.label_column].split()) != " ".join(field.row_label.split()):
                raise ValueError("minfin.document.row_label_mismatch")
            literal = source_row[field.column]
        except IndexError:
            raise ValueError("minfin.document.layout_unsupported") from None
        if field.measure_kind != "stock":
            raise ValueError("minfin.document.explicit_interval_rules_required")
        key = (field.metric, field.subject, day, field.perimeter)
        if key in keys:
            raise ValueError("minfin.document.duplicate_semantic_grain")
        keys.add(key)
        number, status = numeric_value(literal)
        rows.append({"metric": field.metric, "subject": field.subject, "subject_namespace": "geography",
            "period": day.isoformat(), "period_kind": "as_of", "frequency": "monthly",
            "measure_kind": field.measure_kind, "unit": field.unit, "scale": field.scale,
            "perimeter": field.perimeter, "value": number, "value_status": status,
            "raw_token": literal,
            "evidence_ref": f"sha256:{digest}#block={field.block}&row={field.row}&column={field.column}&issue={tables.issue_id}"})
    assessment = Assessment("partial", ("minfin.document.reviewed_fields_only",),
        expected=tuple(field.metric for field in fields), observed=tuple(row["metric"] for row in rows))
    dataset = SourceDataset(settings.source_id, tuple(rows),
        {"grain": ("metric", "subject", "period", "unit", "perimeter"), "scope": "reviewed_fields"},
        tables.issue_id, (tables.material.identity,) if tables.material else (), assessment,
        source_uses=interpreted_use(tables, settings.source_id, "minfin.nwf",
            tuple((block.kind, block.ordinal, tuple(len(row) for row in block.rows)) for block in tables.tables),
            (settings, fields, anchors)))
    return {"dataset": dataset, "assessment": assessment}


def validate(inputs, settings, context):
    dataset = inputs["dataset"]
    if dataset.source_id != settings.source_id:
        raise ValueError("minfin.document.source_mismatch")
    seen = set()
    for row in dataset.rows:
        key = tuple(row.get(name) for name in ("metric", "subject", "period", "unit", "perimeter"))
        if key in seen:
            raise ValueError("minfin.document.duplicate_semantic_grain")
        seen.add(key)
        if row["measure_kind"] != "stock" or row["period_kind"] != "as_of" or not row["unit"]:
            raise ValueError("minfin.document.semantic_basis_invalid")
    return {"dataset": dataset, "assessment": dataset.assessment}


def align(inputs, settings, context):
    dataset = validate(inputs, settings, context)["dataset"]
    value = IntegratedDataset(dataset.source_id, dataset.rows, dataset.semantics,
        dataset.issue_id, (*dataset.lineage, dataset.identity), dataset.assessment,
        source_uses=dataset.source_uses)
    return {"dataset": value, "assessment": value.assessment}
