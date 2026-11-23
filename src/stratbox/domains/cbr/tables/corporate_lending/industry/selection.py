"""Selection of published industry dimensions shared by loan stock and flow.

Source validation always covers the complete original publication; this layer
only controls which validated observations are materialized in the result.
"""

from __future__ import annotations

from stratbox.domains.cbr.tables.corporate_lending.industry.contracts import IndustrySelection

SELECTION_METHOD = "cbr-industries-selection-1"
APK_COMPONENT_CODES = (
    "agriculture_hunting_services", "agriculture_hunting_forestry",
    "manufacturing_food_beverages_tobacco", "manufacturing_machinery_agriculture_forestry",
    "manufacturing_wood_products",
)


def resolve_industry_codes(
    selection: IndustrySelection,
    *,
    published_codes: tuple[str, ...],
    apk_ingredients: tuple[str, ...],
) -> tuple[str, ...] | None:
    """Expand the APK aggregate while retaining the published code order."""
    if not isinstance(selection, IndustrySelection):
        raise ValueError("Industry selection requires IndustrySelection")
    requested = selection.industry_codes
    if requested is None:
        return None
    if (type(requested) is not tuple or not requested
            or any(type(value) is not str for value in requested)
            or len(set(requested)) != len(requested)
            or set(requested) - (set(published_codes) | {"apk"})):
        raise ValueError("Invalid industry selection")
    needed = set(requested) - {"apk"}
    if "apk" in requested:
        needed.update(apk_ingredients)
    return tuple(code for code in published_codes if code in needed)


def selection_parameters(
    selection: IndustrySelection,
    *,
    published_codes: tuple[str, ...],
    apk_ingredients: tuple[str, ...],
) -> dict:
    materialized = resolve_industry_codes(
        selection,
        published_codes=published_codes,
        apk_ingredients=apk_ingredients,
    )
    return {
        "selection_method": SELECTION_METHOD,
        "requested_industries": selection.industry_codes,
        "materialized_source_industries": materialized,
        "source_validation_scope": "full",
        "observation_scope": "full" if materialized is None else "selected",
    }
