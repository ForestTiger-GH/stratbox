"""Explicit domain types admitted by the portable snapshot codec."""
from .contracts import ParsedCbr0105ADebtCorpFile, Cbr0105ADebtCorpStreamResult, Cbr0105ADebtCorpSheetSpec, Cbr0105ADebtCorpSourceFailure, Cbr0105ADebtCorpSourceLink
from ..common.contracts import (IndustrySelection, IndustrySpec, IndustryRegionSpec, IndustryValidationIssue,
    IndustryApkCalculationResult, IndustryPivotSetResult, IndustryPivotTable)

TYPES = {"selection": IndustrySelection, "industry": IndustrySpec, "region": IndustryRegionSpec,
    "issue": IndustryValidationIssue, "calculation": IndustryApkCalculationResult,
    "view": IndustryPivotSetResult, "view_table": IndustryPivotTable,
    "sheet": Cbr0105ADebtCorpSheetSpec, "failure": Cbr0105ADebtCorpSourceFailure, "link": Cbr0105ADebtCorpSourceLink,
    "stream": Cbr0105ADebtCorpStreamResult, "flake": ParsedCbr0105ADebtCorpFile}
