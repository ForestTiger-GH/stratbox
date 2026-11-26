"""Fiscal periods, raw statuses and reviewed statistical meanings."""
from decimal import Decimal
import pytest

from stratbox.domains.minfin.common.numbers import numeric_value
from stratbox.domains.minfin.common.periods import normalize_period
from stratbox.domains.minfin.methods.budget import period_details


@pytest.mark.parametrize("label,frequency,expected", [
    ("окт.26 **", "monthly", "2026-10"), ("Январь 2008¹", "monthly", "2008-01"),
    ("2025-08-31T00:00:00", "monthly", "2025-08"), ("45869", "monthly", "2025-07"),
    ("2 кв.2026 ***", "quarterly", "2026-Q2"), ("2025", "annual", "2025"),
])
def test_publisher_period_spellings(label, frequency, expected):
    assert normalize_period(label, frequency) == expected


def test_ytd_quarter_and_actual_stock_date_remain_distinct():
    assert period_details("2026-Q2", "quarterly", "ytd")["period"] == ("2026-01-01", "2026-06-30")
    assert period_details("2026-Q2", "quarterly", "period_flow")["period"] == ("2026-04-01", "2026-06-30")
    assert period_details("2026-10", "monthly", "stock", "01.10.2026")["period"] == "2026-10-01"
    with pytest.raises(ValueError, match="basis_mismatch"):
        period_details("2026-10", "monthly", "annual")


@pytest.mark.parametrize("token", ["NaN", "Infinity", "12x", "1,2,3"])
def test_ambiguous_or_nonfinite_numeric_text_is_rejected(token):
    with pytest.raises(ValueError):
        numeric_value(token)


def test_precision_sign_dash_and_blank_preserve_their_meaning():
    assert numeric_value("100.00000000000000000000001") == (Decimal("100.00000000000000000000001"), "reported")
    assert numeric_value("-25") == (Decimal(-25), "reported")
    assert numeric_value("—") == (None, "dash")
    assert numeric_value("") == (None, "blank")
    assert numeric_value(None) == (None, "missing")
