"""Reviewed Rosstat table procedures over supplied physical evidence only."""
from __future__ import annotations

from dataclasses import dataclass, replace

from stratbox.shared.data.values import Assessment, IntegratedDataset, SourceDataset, TableEvidenceSet, WorkbookEvidence
from .types import TableRules, Kep2Settings, bind_workbook, as_dataset


def extract(inputs, settings: TableRules, context):
    physical = inputs.get("physical", inputs.get("workbook"))
    if not isinstance(physical, WorkbookEvidence):
        raise TypeError("rosstat.workbook_evidence_required")
    if physical.workbook.identity != physical.material.identity:
        raise ValueError("rosstat.physical_material_identity_conflict")
    source = physical.material.source_id
    if source not in {None, settings.source_id, settings.publication_id}:
        raise ValueError("rosstat.source_context_conflict")
    context.checkpoint()
    issue = str(context.parameters.get("issue_id", physical.material.metadata.get("issue_id", "")))
    tables = TableEvidenceSet((physical,), physical.material, settings.source_id, issue,
        physical.assessment, {"publication_id": settings.publication_id, "table_kind": settings.kind})
    return {"tables": tables, "coverage": physical.assessment}


def interpret(inputs, settings: TableRules, context):
    workbook = bind_workbook(inputs["tables"], settings, context.parameters)
    context.checkpoint()
    if settings.kind == "kep2":
        from .kep2 import extract_kep2
        table = extract_kep2(Kep2Settings(workbook,
            str(context.parameters.get("duplicate_year_policy", settings.duplicate_year_policy)),
            tuple(context.parameters.get("required_indicators", settings.required_indicators))),
            checkpoint=context.checkpoint)
    elif settings.kind == "population":
        from .editions import extract_population
        table = extract_population(workbook, selected_rows=tuple(context.parameters.get("selected_rows", settings.selected_rows)),
            checkpoint=context.checkpoint)
    elif settings.kind == "regional_industry":
        from .editions import extract_regional_industrial_indices
        table = extract_regional_industrial_indices(workbook,
            selected_rows=tuple(context.parameters.get("selected_rows", settings.selected_rows)),
            selected_years=tuple(context.parameters.get("selected_years", settings.selected_years)), checkpoint=context.checkpoint)
    else:
        raise ValueError("rosstat.reviewed_table_rules_missing")
    context.checkpoint()
    dataset = as_dataset(table, source_id=settings.source_id)
    return {"dataset": dataset, "assessment": dataset.assessment}


def validate(inputs, settings, context):
    dataset = inputs["dataset"]
    if not isinstance(dataset, SourceDataset) or dataset.source_id != settings.source_id:
        raise ValueError("rosstat.dataset_source_conflict")
    seen = set()
    for row in dataset.rows:
        context.checkpoint()
        key = (row["metric"], row["subject_namespace"], row["subject"], row["period"],
            row["frequency"], row["perimeter"], tuple(row.get("dimensions", ())))
        if key in seen:
            raise ValueError("rosstat.duplicate_semantic_key")
        seen.add(key)
        if row["measure_kind"] == "index" and row["unit"] != "percent":
            raise ValueError("rosstat.index_unit_invalid")
        if row["value_status"] == "unparsed" or row["unit"] is None:
            raise ValueError("rosstat.unresolved_semantics")
        if settings.kind == "population" and (row["period_kind"] != "as_of" or row["unit"] != "person"):
            raise ValueError("rosstat.population_stock_semantics_required")
    return {"dataset": dataset, "assessment": dataset.assessment}


def align(inputs, settings, context):
    dataset = inputs["dataset"]
    if not isinstance(dataset, SourceDataset) or dataset.source_id != settings.source_id:
        raise ValueError("rosstat.dataset_source_conflict")
    # Source-native addressing is explicit. No TERSON-MO/OKTMO equivalence is
    # implied by placing the observations in a shared queryable dataset.
    if context.parameters.get("require_canonical_geography") and any(
            row.get("subject_namespace", "").startswith("rosstat.") for row in dataset.rows):
        raise ValueError("rosstat.reviewed_geography_crosswalk_required")
    assessment = replace(dataset.assessment,
        qualifications=dataset.assessment.qualifications | {"source_native_addressing"})
    result = IntegratedDataset(dataset.source_id, dataset.rows,
        {**dataset.semantics, "geography_mode": "source_native"}, dataset.issue_id,
        dataset.lineage, assessment, dataset.native, source_uses=dataset.source_uses)
    return {"dataset": result, "assessment": assessment}
