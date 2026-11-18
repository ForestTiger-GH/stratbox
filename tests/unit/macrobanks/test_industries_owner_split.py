"""Series-owner symmetry and shared industry-family semantics."""

from pathlib import Path

from stratbox.domains.registry import domain_catalog
from stratbox.domains.cbr.corporate_lending.industries import (
    debt_0105a, issuance_0104,
)
from stratbox.domains.cbr.corporate_lending.industries.common import (
    operation_helpers, parsing, normalization, contracts, streams, rendering,
)
from stratbox.domains.cbr.corporate_lending.industries.debt_0105a import (
    operations as debt_operations,
)
from stratbox.domains.cbr.corporate_lending.industries.issuance_0104 import (
    operations as issuance_operations,
)


def test_industries_is_family_not_operation_owner():
    root = Path(__file__).resolve().parents[3] / (
        "src/stratbox/domains/cbr/corporate_lending/industries"
    )
    assert not (root / "_registration.py").exists()
    assert (root / "debt_0105a/_registration.py").is_file()
    assert (root / "issuance_0104/_registration.py").is_file()


def test_independent_series_keep_published_operation_contracts():
    refs = domain_catalog().list_refs()
    identities = {(r.operation_id, r.contract_version) for r in refs}
    assert ("cbr.industries.0105a.parse", 3) in identities
    assert ("cbr.industries.0104a.parse", 3) in identities
    assert debt_0105a.PARSE.operation_id == "cbr.industries.0105a.parse"
    assert issuance_0104.PARSE.operation_id == "cbr.industries.0104a.parse"


def test_shared_operations_are_owned_by_common_not_other_series():
    assert debt_operations._TABLE_LIMITS is operation_helpers._TABLE_LIMITS
    assert issuance_operations._TABLE_LIMITS is operation_helpers._TABLE_LIMITS
    assert debt_operations._seal_pivots is operation_helpers._seal_pivots
    assert issuance_operations._seal_pivots is operation_helpers._seal_pivots
    assert debt_operations._select_industry is issuance_operations._select_industry


def test_common_cell_normalization_preserves_debt_schema_semantics():
    from stratbox.domains.cbr.corporate_lending.industries.debt_0105a.schema import (
        normalize_cbr_0105a_text,
    )
    assert normalize_cbr_0105a_text is normalization.normalize_cbr_0105a_text
    assert normalization.normalize_cbr_0105a_text("СЕЛЬСКОЕ ХОЗЯЙСТВО, из них:") == (
        "сельское хозяйство"
    )
    assert callable(parsing._coerce_numeric_value)


def test_shared_selection_and_stream_schema_are_family_owned():
    assert debt_0105a.IndustrySelection is contracts.IndustrySelection
    assert issuance_0104.IndustrySelection is contracts.IndustrySelection
    from stratbox.domains.cbr.corporate_lending.industries.debt_0105a import (
        derived,
    )
    assert derived.STREAM_COLUMNS is streams.STREAM_COLUMNS
    assert "source_sha256" in streams.STREAM_COLUMNS

def test_excel_grid_renderer_is_shared_without_stock_private_imports():
    from stratbox.domains.cbr.corporate_lending.industries.debt_0105a import (
        export as debt_export,
    )
    from stratbox.domains.cbr.corporate_lending.industries.issuance_0104 import (
        export as issuance_export,
    )
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
    from stratbox.domains.cbr.corporate_lending.industries.common import (
        selection as shared_selection,
    )
    from stratbox.domains.cbr.corporate_lending.industries.debt_0105a import (
        selection as stock_selection,
    )
    from stratbox.domains.cbr.corporate_lending.industries.issuance_0104 import (
        selection as flow_selection,
    )

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
