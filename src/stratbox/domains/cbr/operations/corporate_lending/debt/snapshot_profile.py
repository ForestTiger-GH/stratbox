"""Explicit domain types admitted by the portable snapshot codec."""
from stratbox.domains.cbr.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile
from stratbox.domains.cbr.integration.corporate_lending.debt.contracts import Cbr0105ADebtCorpStreamResult
from stratbox.domains.cbr.tables.corporate_lending.debt.contracts import Cbr0105ADebtCorpSheetSpec
from stratbox.domains.cbr.tables.corporate_lending.debt.contracts import Cbr0105ADebtCorpSourceFailure
from stratbox.domains.cbr.publications.corporate_lending.contracts import Cbr0105ADebtCorpSourceLink
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
    "sheet": Cbr0105ADebtCorpSheetSpec, "failure": Cbr0105ADebtCorpSourceFailure, "link": Cbr0105ADebtCorpSourceLink,
    "stream": Cbr0105ADebtCorpStreamResult, "flake": ParsedCbr0105ADebtCorpFile}
