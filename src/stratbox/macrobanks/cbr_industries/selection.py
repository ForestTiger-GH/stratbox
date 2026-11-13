"""Select only needed published observations; source validation always covers all cells."""

from __future__ import annotations

from .contracts import IndustrySelection
from .schema import CBR_0105A_DEBT_CORP_INDUSTRY_SPECS

SELECTION_METHOD = "cbr-industries-selection-1"
_PUBLISHED = tuple(item.code for item in CBR_0105A_DEBT_CORP_INDUSTRY_SPECS)


def resolve_industry_codes(selection: IndustrySelection) -> tuple[str, ...] | None:
    """Expand derived APK to five published ingredients in source schema order."""
    from .derived import CBR_0105A_DEBT_CORP_APK_SOURCE_INDUSTRY_CODES

    if not isinstance(selection, IndustrySelection):
        raise ValueError("Industry selection requires IndustrySelection")
    requested = selection.industry_codes
    if requested is None:
        return None
    if (type(requested) is not tuple or not requested
            or any(type(value) is not str for value in requested)
            or len(set(requested)) != len(requested)
            or set(requested) - (set(_PUBLISHED) | {"apk"})):
        raise ValueError("Invalid industry selection")
    needed = set(requested) - {"apk"}
    if "apk" in requested:
        needed.update(CBR_0105A_DEBT_CORP_APK_SOURCE_INDUSTRY_CODES)
    return tuple(code for code in _PUBLISHED if code in needed)


def selection_parameters(selection: IndustrySelection) -> dict:
    materialized = resolve_industry_codes(selection)
    return {
        "selection_method": SELECTION_METHOD,
        "requested_industries": selection.industry_codes,
        "materialized_source_industries": materialized,
        "source_validation_scope": "full",
        "observation_scope": "full" if materialized is None else "selected",
    }
