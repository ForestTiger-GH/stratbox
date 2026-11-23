"""SORS dependency roles reference the shared CBR publication catalogue.

The program declares ten required publications and one optional validation
history. URLs and file locations belong to acquisition profiles and callers.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from math import isfinite

from stratbox.domains.cbr.publications.catalog import source
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt


@dataclass(frozen=True, slots=True)
class SorsDependency:
    input_name: str
    source_series: str
    series_id: str
    source_role: str
    required: bool = True
    method_version: str = "sors-published-observation-1"
    accepted_contracts: tuple[DataContract, ...] = (
        DataContract("source.payload", 1, DataRole.ORIGINALS), DataContract("material.payload", 1),
        DataContract("cbr.workbook.flake", 1, DataRole.EXTRACTS),
        DataContract("cbr.corporate_lending.source_observations", 1, DataRole.EXTRACTS),
    )
    compatibility_rule: str = "same_report_date_and_publication_step"


def _declared_dependencies():
    from stratbox.core.registry.requirements import declared_requirements
    return tuple(SorsDependency(
        item.input_name, item.source_label, item.source_ids[0], item.role,
        required=item.required, accepted_contracts=item.accepted_contracts,
    ) for item in declared_requirements("cbr.sors.prepare_inputs"))


DEPENDENCIES = _declared_dependencies()


def dependencies():
    for dependency in DEPENDENCIES:
        source(dependency.series_id)
    return DEPENDENCIES


def contract_coordinates(dependency):
    return tuple((item.schema_id, item.version, item.role.value if item.role else None)
                 for item in dependency.accepted_contracts)


def original_input(value, role):
    """Resolve exact original evidence from original bytes or a complete debt flake."""
    if isinstance(value, SourcePayload):
        return UsedInputReceipt.for_payload(value, role)
    from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake
    from stratbox.domains.cbr.tables.corporate_lending.observations import CorporateSourceDataset
    if isinstance(value, (WorkbookFlake, CorporateSourceDataset)):
        source_id = next((item.source_id for item in value.lineage if item.identity == value.source_identity and item.source_id), value.series_id)
        return UsedInputReceipt(role, value.source_identity,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only", source_id)
    from stratbox.domains.cbr.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile
    if not isinstance(value, ParsedCbr0105ADebtCorpFile) or value.evidence is None:
        raise ValueError("sors.input_original_identity_missing")
    matches = tuple(item for item in value.evidence.inputs if item.role == "source_workbook" and item.identity.sha256 == value.source_sha256)
    if len(matches) != 1:
        raise ValueError("sors.input_original_identity_ambiguous")
    receipt = matches[0]
    return UsedInputReceipt(role, receipt.identity, receipt.media_type, "reference_only", value.source_id,
                            receipt.container, receipt.member, receipt.version)


def dependency_manifest(inputs, as_of_date, publication_step):
    import pandas as pd
    date.fromisoformat(as_of_date)
    if not isfinite(publication_step) or publication_step <= 0:
        raise ValueError("sors.publication_policy_invalid")
    records = []
    for item in dependencies():
        value = getattr(inputs, item.input_name)
        if value is None and item.required:
            raise ValueError("sors.required_source_missing")
        receipt = original_input(value, item.source_series) if value is not None else None
        records.append({
            "input_name": item.input_name, "source_series": item.source_series, "series_id": item.series_id,
            "source_role": item.source_role, "required": item.required,
            "status": "resolved" if receipt else "not_supplied", "as_of_date": as_of_date,
            "publication_step": float(publication_step), "method_version": item.method_version,
            "accepted_contracts": contract_coordinates(item), "compatibility_rule": item.compatibility_rule,
            "original_sha256": receipt.identity.sha256 if receipt else None,
            "original_size": receipt.identity.size if receipt else None,
            "source_id": receipt.source_id if receipt else None,
            "input_kind": "original" if isinstance(value, SourcePayload) else "flake" if value is not None else None,
        })
    return pd.DataFrame(records, dtype=object)
