"""Source-profile selection for 01_04_A new loans.

The family algorithm is shared; the exact 26-code published layout and five
APK source ingredients follow the validated CBR publication reference profile.
"""

from __future__ import annotations

from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySelection
from stratbox.domains.cbr.tables.corporate_lending.industry.selection import SELECTION_METHOD, APK_COMPONENT_CODES
from stratbox.domains.cbr.tables.corporate_lending.industry.selection import resolve_industry_codes as _resolve_industry_codes
from stratbox.domains.cbr.tables.corporate_lending.industry.selection import selection_parameters as _selection_parameters
from stratbox.domains.cbr.tables.corporate_lending.industry.schema import CBR_0105A_DEBT_CORP_INDUSTRY_SPECS

_PUBLISHED = tuple(item.code for item in CBR_0105A_DEBT_CORP_INDUSTRY_SPECS)


def resolve_industry_codes(selection: IndustrySelection) -> tuple[str, ...] | None:
    return _resolve_industry_codes(
        selection, published_codes=_PUBLISHED, apk_ingredients=APK_COMPONENT_CODES
    )


def selection_parameters(selection: IndustrySelection) -> dict:
    return _selection_parameters(
        selection, published_codes=_PUBLISHED, apk_ingredients=APK_COMPONENT_CODES
    )
