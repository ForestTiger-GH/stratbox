"""Explicit domain types admitted by the portable snapshot codec."""
from stratbox.domains.cbr.tables.corporate_lending.issuance.contracts import ParsedIssuanceFile
from stratbox.domains.cbr.integration.corporate_lending.issuance.contracts import IssuanceStreamResult
from stratbox.domains.cbr.tables.corporate_lending.issuance.contracts import IssuanceSheetSpec
from stratbox.domains.cbr.tables.corporate_lending.issuance.contracts import IssuanceSourceFailure
from stratbox.domains.cbr.publications.corporate_lending.contracts import IssuanceSourceLink
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySelection
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySpec
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustryRegionSpec
from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustryValidationIssue
from stratbox.domains.cbr.analytics.corporate_lending.industry.contracts import IndustryApkCalculationResult
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotSetResult
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotTable

TYPES = {"selection": IndustrySelection, "industry": IndustrySpec, "region": IndustryRegionSpec,
    "issue": IndustryValidationIssue, "calculation": IndustryApkCalculationResult,
    "view": IndustryPivotSetResult, "view_table": IndustryPivotTable,
    "sheet": IssuanceSheetSpec, "failure": IssuanceSourceFailure, "link": IssuanceSourceLink,
    "stream": IssuanceStreamResult, "flake": ParsedIssuanceFile}
