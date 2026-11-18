"""Series-owner symmetry and shared industry-family semantics."""

from pathlib import Path

from stratbox.domains.registry import domain_catalog
from stratbox.domains.cbr.corporate_lending.industries import (
    debt_0105a, issuance_0104,
)
from stratbox.domains.cbr.corporate_lending.industries.common import (
    operation_helpers, parsing, normalization, contracts, streams,
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
