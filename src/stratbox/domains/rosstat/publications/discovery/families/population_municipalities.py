"""Municipal population releases: edition year is not a publication timestamp."""
from .rules import FamilyRule

RULE = FamilyRule(
    "population_municipalities", "rosstat-population-municipalities-2", "annual",
    "population_workbook", (
        ("историческ", "historical_workbook"),
        ("таблиц", "tables"),
    ),
)
