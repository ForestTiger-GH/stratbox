"""Short-term indicators: document editions are distinct from workbook periods."""
from .rules import FamilyRule

RULE = FamilyRule(
    "short_term_indicators", "rosstat-short-term-indicators-2", "monthly",
    "main_workbook", (
        ("историческ", "historical_workbook"),
        ("архивный", "historical_workbook"),
        ("таблиц", "tables"),
    ),
)
