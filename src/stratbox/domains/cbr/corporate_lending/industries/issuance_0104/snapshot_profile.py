"""Explicit domain types admitted by the portable snapshot codec."""
from .contracts import ParsedIssuanceFile, IssuanceStreamResult, IssuanceSheetSpec, IssuanceSourceFailure, IssuanceSourceLink
from ..common.contracts import (IndustrySelection, IndustrySpec, IndustryRegionSpec, IndustryValidationIssue,
    IndustryApkCalculationResult, IndustryPivotSetResult, IndustryPivotTable)

TYPES = {"selection": IndustrySelection, "industry": IndustrySpec, "region": IndustryRegionSpec,
    "issue": IndustryValidationIssue, "calculation": IndustryApkCalculationResult,
    "view": IndustryPivotSetResult, "view_table": IndustryPivotTable,
    "sheet": IssuanceSheetSpec, "failure": IssuanceSourceFailure, "link": IssuanceSourceLink,
    "stream": IssuanceStreamResult, "flake": ParsedIssuanceFile}
