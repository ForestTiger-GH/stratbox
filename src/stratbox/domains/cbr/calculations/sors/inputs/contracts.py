"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass, field

from typing import Any

from stratbox.shared.evidence import SourcePayload, UsedInputReceipt

from stratbox.shared.data.coverage import SnapshotCoverage
from stratbox.shared.data.source_context import SourceUse


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pandas as pd
    from stratbox.domains.cbr.methods.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile
    from stratbox.domains.cbr.methods.tables.corporate_lending.observations import CorporateSourceDataset
    from stratbox.domains.cbr.methods.actions.statistics import SourceWorkbook


@dataclass(frozen=True, slots=True)
class SorsSourceInputs:
    regional_traditional: ParsedCbr0105ADebtCorpFile
    national_okved2: SourceWorkbook | CorporateSourceDataset
    federal_district_okved2: SourceWorkbook | CorporateSourceDataset
    national_traditional: SourceWorkbook | CorporateSourceDataset
    sme_national_totals: SourceWorkbook | CorporateSourceDataset
    sme_national_okved2: SourceWorkbook | CorporateSourceDataset
    sme_ie_national_okved2: SourceWorkbook | CorporateSourceDataset
    sme_federal_district_okved2: SourceWorkbook | CorporateSourceDataset
    sme_regional_totals: SourceWorkbook | CorporateSourceDataset
    sme_ie_regional_totals: SourceWorkbook | CorporateSourceDataset
    regional_totals_history: SourceWorkbook | CorporateSourceDataset | None = None


def _empty_frame():
    from pandas import DataFrame
    return DataFrame()


@dataclass(frozen=True)
class SorsSourceBundle:
    source_grid: pd.DataFrame
    regional_traditional_grid: pd.DataFrame
    national_traditional_grid: pd.DataFrame
    national_okved2_grid: pd.DataFrame
    federal_district_okved2_grid: pd.DataFrame
    sme_national_totals_grid: pd.DataFrame
    sme_national_okved2_grid: pd.DataFrame
    sme_ie_national_okved2_grid: pd.DataFrame
    sme_federal_district_okved2_grid: pd.DataFrame
    sme_regional_totals_grid: pd.DataFrame
    sme_ie_regional_totals_grid: pd.DataFrame
    regional_totals_history_grid: pd.DataFrame
    geography_nodes_grid: pd.DataFrame
    atomic_regions_grid: pd.DataFrame
    okved2_classes_grid: pd.DataFrame
    publication_categories_grid: pd.DataFrame
    observation_bindings_grid: pd.DataFrame
    source_manifest_grid: pd.DataFrame
    validation_grid: pd.DataFrame
    lineage: tuple[UsedInputReceipt, ...] = ()
    evidence: Any | None = None
    as_of_date: str | None = None
    publication_step: float | None = None
    dependency_manifest_grid: pd.DataFrame = field(default_factory=_empty_frame)
    coverage: SnapshotCoverage = SnapshotCoverage(
        "unknown", "Selected publication slice; publisher historical coverage is unspecified."
    )
    method_fingerprint: str = field(default_factory=lambda: _input_fingerprint())
    source_uses: tuple[SourceUse, ...] = ()

    @property
    def fingerprint(self):
        from stratbox.domains.cbr.calculations.sors.identity import retained_fingerprint
        return retained_fingerprint(self)


def _input_fingerprint():
    from stratbox.domains.cbr.calculations.sors.fingerprints import implementation_fingerprint
    return implementation_fingerprint("inputs")
