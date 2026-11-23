"""Functional ownership and shared stock/flow industry semantics."""

from pathlib import Path

from stratbox.operations import domain_catalog
from stratbox.domains.cbr.operations.corporate_lending import (
    debt as debt_0105a, issuance as issuance_0104,
)
import stratbox.domains.cbr.operations.corporate_lending.industry.operation_helpers as operation_helpers
import stratbox.domains.cbr.tables.corporate_lending.industry.parsing as parsing
import stratbox.domains.cbr.tables.corporate_lending.industry.normalization as normalization
import stratbox.domains.cbr.tables.corporate_lending.industry.contracts as contracts
import stratbox.domains.cbr.tables.corporate_lending.industry.streams as streams
import stratbox.domains.cbr.products.corporate_lending.industry.rendering as rendering
import stratbox.domains.cbr.operations.corporate_lending.debt.operations as debt_operations
import stratbox.domains.cbr.operations.corporate_lending.issuance.operations as issuance_operations


def test_cbr_is_one_registered_owner_with_functional_operation_references():
    root = Path(__file__).resolve().parents[3] / "src/stratbox/domains/cbr"
    from stratbox.core.resources import owner_directory, read_document
    catalog = domain_catalog()
    assert read_document(owner_directory("cbr").joinpath("OWNER.yaml"))["owner_id"] == "cbr"
    assert {item.owner_id for item in catalog.registrations
            if item.owner_id == "cbr" or item.owner_id.startswith("cbr.")} == {"cbr"}
    for operation_id in ("cbr.industries.0105a.parse", "cbr.industries.0104a.parse"):
        assert catalog.owner_of(operation_id) == "cbr"
    assert not tuple(root.rglob("_registration.py"))
    assert not tuple(root.rglob("registration.py"))
    assert not (root / "corporate_lending/industries").exists()


def test_independent_series_keep_published_operation_contracts():
    refs = domain_catalog().list_refs()
    identities = {r.operation_id for r in refs}
    assert "cbr.industries.0105a.parse" in identities
    assert "cbr.industries.0104a.parse" in identities
    assert debt_0105a.PARSE.operation_id == "cbr.industries.0105a.parse"
    assert issuance_0104.PARSE.operation_id == "cbr.industries.0104a.parse"


def test_shared_operations_are_owned_by_common_not_other_series():
    assert debt_operations.PARSE.limits == operation_helpers._TABLE_LIMITS
    assert issuance_operations.PARSE.limits == operation_helpers._TABLE_LIMITS
    assert debt_operations._seal_pivots is operation_helpers._seal_pivots
    assert issuance_operations._seal_pivots is operation_helpers._seal_pivots
    assert debt_operations._select_industry is issuance_operations._select_industry


def test_common_cell_normalization_is_owned_by_industry_family():
    assert normalization.normalize_industry_text("СЕЛЬСКОЕ ХОЗЯЙСТВО, из них:") == (
        "сельское хозяйство"
    )
    assert callable(parsing._coerce_numeric_value)


def test_shared_selection_and_stream_schema_are_family_owned():
    assert debt_0105a.IndustrySelection is contracts.IndustrySelection
    assert issuance_0104.IndustrySelection is contracts.IndustrySelection
    import stratbox.domains.cbr.analytics.corporate_lending.industry.apk as derived
    assert derived.STREAM_COLUMNS is streams.STREAM_COLUMNS
    assert "source_sha256" in streams.STREAM_COLUMNS

def test_excel_grid_renderer_is_shared_without_stock_private_imports():
    import stratbox.domains.cbr.products.corporate_lending.debt.rendering as debt_export
    import stratbox.domains.cbr.products.corporate_lending.issuance.rendering as issuance_export
    assert debt_export._write_cbr_industry_sheet is rendering._write_cbr_industry_sheet
    assert issuance_export._write_cbr_industry_sheet is rendering._write_cbr_industry_sheet
    assert debt_export._industry_table_dates is rendering._industry_table_dates
    assert issuance_export._industry_table_dates is rendering._industry_table_dates


def test_shared_grid_date_columns_reject_ambiguous_multi_value_columns():
    from types import SimpleNamespace

    import pandas as pd
    from pytest import raises

    sheet = SimpleNamespace(
        data_columns=2,
        df_table=pd.DataFrame({
            "region_name": ["Россия"],
            "2026-06-01": [1.0],
            "2026-07-01": [2.0],
        }),
    )
    assert rendering._industry_table_dates(sheet) == ("2026-06-01", "2026-07-01")
    sheet.data_columns = 0
    with raises(ValueError, match="no date columns"):
        rendering._industry_table_dates(sheet)

def test_both_series_share_exact_industry_selection_semantics():
    import stratbox.domains.cbr.tables.corporate_lending.industry.selection as shared_selection
    import stratbox.domains.cbr.tables.corporate_lending.debt.selection as stock_selection
    import stratbox.domains.cbr.tables.corporate_lending.issuance.selection as flow_selection

    chosen = contracts.IndustrySelection(("apk", "total"))
    assert stock_selection.resolve_industry_codes(chosen) == (
        flow_selection.resolve_industry_codes(chosen)
    )
    assert stock_selection.selection_parameters(chosen) == (
        flow_selection.selection_parameters(chosen)
    )
    assert stock_selection.SELECTION_METHOD == shared_selection.SELECTION_METHOD
    for invalid in (("total", "total"), ("unknown",)):
        from pytest import raises
        with raises(ValueError, match="Invalid industry selection"):
            stock_selection.resolve_industry_codes(contracts.IndustrySelection(invalid))
        with raises(ValueError, match="Invalid industry selection"):
            flow_selection.resolve_industry_codes(contracts.IndustrySelection(invalid))


def test_common_structural_types_are_owned_by_family_not_by_stock_series():
    import stratbox.domains.cbr.tables.corporate_lending.debt.contracts as stock
    import stratbox.domains.cbr.tables.corporate_lending.issuance.contracts as flow

    assert stock.Cbr0105ADebtCorpIndustrySpec is contracts.IndustrySpec
    assert stock.Cbr0105ADebtCorpRegionSpec is contracts.IndustryRegionSpec
    assert stock.Cbr0105ADebtCorpValidationIssue is contracts.IndustryValidationIssue
    from stratbox.domains.cbr.analytics.corporate_lending.industry.contracts import IndustryApkCalculationResult
    from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotRequest, IndustryPivotSetResult
    assert IndustryApkCalculationResult.__module__ == "stratbox.domains.cbr.analytics.corporate_lending.industry.contracts"
    assert IndustryPivotRequest.__module__ == IndustryPivotSetResult.__module__ == "stratbox.domains.cbr.products.corporate_lending.industry.contracts"
    assert not hasattr(stock, "Cbr0105ADebtCorpApkCalculationResult")
    assert not hasattr(stock, "Cbr0105ADebtCorpPivotRequest")
    assert flow.IndustrySpec is contracts.IndustrySpec
    assert flow.RegionSpec is contracts.IndustryRegionSpec
    assert flow.ValidationIssue is contracts.IndustryValidationIssue
    assert not hasattr(flow, "IndustryPivotRequest")


def test_issuance_uses_shared_contracts_without_debt_private_types():
    import ast
    root = Path(__file__).resolve().parents[3] / "src/stratbox/domains/cbr"
    for relative in ("tables/corporate_lending/issuance/contracts.py",
                     "tables/corporate_lending/issuance/parser.py",
                     "operations/corporate_lending/issuance/operations.py"):
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        assert "stratbox.domains.cbr.tables.corporate_lending.debt.contracts" not in imports


def test_series_implementations_use_direct_family_helpers():
    import stratbox.domains.cbr.tables.corporate_lending.debt.parser as stock_parser
    import stratbox.domains.cbr.analytics.corporate_lending.industry.apk as stock_derived
    import stratbox.domains.cbr.tables.corporate_lending.issuance.parser as flow_parser

    assert stock_parser.optimize_industry_stream_dtypes is streams.optimize_industry_stream_dtypes
    assert stock_derived.concat_industry_streams is streams.concat_industry_streams
    assert flow_parser.optimize_industry_stream_dtypes is streams.optimize_industry_stream_dtypes
    assert stock_parser.normalize_industry_text is normalization.normalize_industry_text
