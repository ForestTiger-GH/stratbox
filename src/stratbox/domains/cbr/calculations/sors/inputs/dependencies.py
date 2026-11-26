"""SORS dependency roles reference the shared CBR publication catalogue.

The program declares ten required publications and one optional validation
history. URLs and file locations belong to publication specifications and callers.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from math import isfinite

from stratbox.shared.evidence import SourcePayload, UsedInputReceipt


@dataclass(frozen=True, slots=True)
class SorsDependency:
    input_name: str
    source_series: str
    series_id: str
    source_role: str
    required: bool = True
    accepted_contracts: tuple[str, ...] = (
        "source.payload", "material.payload", "cbr.workbook.flake",
        "cbr.corporate_lending.source_observations",
    )

    @property
    def method_fingerprint(self):
        from stratbox.domains.cbr.calculations.sors.fingerprints import implementation_fingerprint
        return implementation_fingerprint("inputs")

    compatibility_rule: str = "same_report_date_and_publication_step"


DEPENDENCIES = (
    SorsDependency('regional_traditional', '01_05_A', 'cbr.corporate_lending.debt_0105a', 'STRICT_REGIONAL_TOTALS_AND_CROSSWALK_LEGACY', required=True),
    SorsDependency('national_traditional', '01_02_A', 'cbr.corporate_lending.corp_debt_a', 'STRICT_NATIONAL_TOTAL_AND_CROSSWALK_LEGACY', required=True),
    SorsDependency('national_okved2', '01_02_C', 'cbr.corporate_lending.corp_debt_c', 'STRICT_NATIONAL_OKVED2', required=True),
    SorsDependency('federal_district_okved2', '01_03_C', 'cbr.corporate_lending.fd_okved2', 'STRICT_FD_OKVED2', required=True),
    SorsDependency('sme_national_totals', '01_11', 'cbr.corporate_lending.sme_debt', 'STRICT_NATIONAL_SME_TOTALS', required=True),
    SorsDependency('sme_national_okved2', '01_11_F', 'cbr.corporate_lending.sme_debt_activity', 'STRICT_NATIONAL_OKVED2_SME', required=True),
    SorsDependency('sme_ie_national_okved2', '01_11_I', 'cbr.corporate_lending.sme_ie_debt_activity', 'STRICT_NATIONAL_OKVED2_SME_IE', required=True),
    SorsDependency('sme_federal_district_okved2', '01_12_A', 'cbr.corporate_lending.sme_fd_okved2', 'STRICT_FD_OKVED2_SME', required=True),
    SorsDependency('sme_regional_totals', '01_13_F', 'cbr.corporate_lending.sme_debt_subj_f', 'STRICT_REGIONAL_TOTALS_SME', required=True),
    SorsDependency('sme_ie_regional_totals', '01_13_I', 'cbr.corporate_lending.sme_debt_subj_i', 'STRICT_REGIONAL_TOTALS_SME_IE', required=True),
    SorsDependency('regional_totals_history', '01_05_D', 'cbr.corporate_lending.corp_debt_subj', 'OPTIONAL_VALIDATION_AND_HISTORY', required=False),
)

def dependencies():
    return DEPENDENCIES


def source_uses(inputs):
    """Preserve admitted source identity without a second profile registry."""
    from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
    uses = []
    for dependency in DEPENDENCIES:
        value = getattr(inputs, dependency.input_name)
        if value is None:
            continue
        receipt = original_input(value, dependency.source_series)
        coordinate = SourceCoordinate(
            dependency.series_id,
            issue_id=getattr(value, "issue_id", None),
            asset_id=getattr(value, "asset_id", None),
            material_identity=receipt.identity,
        )
        uses.append(SourceUse(coordinate, dependency.input_name, "domain_validated",
                              "sha256:" + receipt.identity.sha256))
    return tuple(uses)


def contract_coordinates(dependency):
    return tuple(dependency.accepted_contracts)


def original_input(value, role):
    """Resolve exact original evidence from original bytes or a complete debt flake."""
    if isinstance(value, SourcePayload):
        return UsedInputReceipt.for_payload(value, role)
    from stratbox.domains.cbr.methods.actions.statistics import SourceWorkbook
    from stratbox.domains.cbr.methods.tables.corporate_lending.observations import CorporateSourceDataset
    if isinstance(value, (SourceWorkbook, CorporateSourceDataset)):
        source_id = next((item.source_id for item in value.lineage if item.identity == value.source_identity and item.source_id), value.series_id)
        return UsedInputReceipt(role, value.source_identity,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "reference_only", source_id)
    from stratbox.domains.cbr.methods.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile
    if not isinstance(value, ParsedCbr0105ADebtCorpFile) or value.evidence is None:
        raise ValueError("sors.input_original_identity_missing")
    matches = tuple(item for item in value.evidence.inputs if item.role == "source_workbook" and item.identity.sha256 == value.source_sha256)
    if len(matches) != 1:
        raise ValueError("sors.input_original_identity_ambiguous")
    receipt = matches[0]
    return UsedInputReceipt(role, receipt.identity, receipt.media_type, "reference_only", value.source_id,
                            receipt.container, receipt.member, receipt.content_basis)


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
            "publication_step": float(publication_step), "method_fingerprint": item.method_fingerprint,
            "accepted_contracts": contract_coordinates(item), "compatibility_rule": item.compatibility_rule,
            "original_sha256": receipt.identity.sha256 if receipt else None,
            "original_size": receipt.identity.size if receipt else None,
            "source_id": receipt.source_id if receipt else None,
            "input_kind": "original" if isinstance(value, SourcePayload) else "flake" if value is not None else None,
        })
    return pd.DataFrame(records, dtype=object)
