"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass, field

from pathlib import Path

from stratbox.shared.data.datasets import ComputationReceipt

from stratbox.shared.evidence import SourcePayload, UsedInputReceipt

from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.data.source_context import SourceUse

from stratbox.domains.cbr.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile
from stratbox.domains.cbr.tables.corporate_lending.observations import CorporateSourceDataset
from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pandas as pd


@dataclass(frozen=True, slots=True)
class SorsSourceFiles:
    regional_traditional: str | Path
    national_okved2: str | Path
    federal_district_okved2: str | Path
    national_traditional: str | Path
    sme_national_totals: str | Path
    sme_national_okved2: str | Path
    sme_ie_national_okved2: str | Path
    sme_federal_district_okved2: str | Path
    sme_regional_totals: str | Path
    sme_ie_regional_totals: str | Path
    regional_totals_history: str | Path | None = None


@dataclass(frozen=True, slots=True)
class SorsSourceInputs:
    regional_traditional: SourcePayload | ParsedCbr0105ADebtCorpFile
    national_okved2: SourcePayload | WorkbookFlake | CorporateSourceDataset
    federal_district_okved2: SourcePayload | WorkbookFlake | CorporateSourceDataset
    national_traditional: SourcePayload | WorkbookFlake | CorporateSourceDataset
    sme_national_totals: SourcePayload | WorkbookFlake | CorporateSourceDataset
    sme_national_okved2: SourcePayload | WorkbookFlake | CorporateSourceDataset
    sme_ie_national_okved2: SourcePayload | WorkbookFlake | CorporateSourceDataset
    sme_federal_district_okved2: SourcePayload | WorkbookFlake | CorporateSourceDataset
    sme_regional_totals: SourcePayload | WorkbookFlake | CorporateSourceDataset
    sme_ie_regional_totals: SourcePayload | WorkbookFlake | CorporateSourceDataset
    regional_totals_history: SourcePayload | WorkbookFlake | CorporateSourceDataset | None = None


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
    evidence: ComputationReceipt | None = None
    as_of_date: str | None = None
    publication_step: float | None = None
    dependency_manifest_grid: pd.DataFrame = field(default_factory=_empty_frame)
    coverage: SnapshotCoverage = SnapshotCoverage(
        "unknown", "Selected publication slice; publisher historical coverage is unspecified."
    )
    method_version: str = "sors-source-bundle-2"
    source_uses: tuple[SourceUse, ...] = ()
