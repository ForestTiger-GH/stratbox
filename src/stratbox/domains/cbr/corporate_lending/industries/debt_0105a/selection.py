"""Source-profile selection for 01_05_A debt stock.

The family algorithm is shared; the exact 26-code published layout and five
APK source ingredients follow the validated CBR publication reference profile.
"""

from __future__ import annotations

from ..common.contracts import IndustrySelection
from ..common.selection import (
    SELECTION_METHOD,
    resolve_industry_codes as _resolve_industry_codes,
    selection_parameters as _selection_parameters,
)
from .schema import CBR_0105A_DEBT_CORP_INDUSTRY_SPECS

_PUBLISHED = tuple(item.code for item in CBR_0105A_DEBT_CORP_INDUSTRY_SPECS)


def _apk_ingredients() -> tuple[str, ...]:
    from .derived import CBR_0105A_DEBT_CORP_APK_SOURCE_INDUSTRY_CODES

    return CBR_0105A_DEBT_CORP_APK_SOURCE_INDUSTRY_CODES


def resolve_industry_codes(selection: IndustrySelection) -> tuple[str, ...] | None:
    return _resolve_industry_codes(
        selection, published_codes=_PUBLISHED, apk_ingredients=_apk_ingredients()
    )


def selection_parameters(selection: IndustrySelection) -> dict:
    return _selection_parameters(
        selection, published_codes=_PUBLISHED, apk_ingredients=_apk_ingredients()
    )
