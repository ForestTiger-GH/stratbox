"""Socio-economic position of Russia: source-document identity, no PDF parsing."""
from .rules import FamilyRule

RULE = FamilyRule(
    "socioeconomic_russia", "rosstat-socioeconomic-russia-2", "monthly",
    "report", (
        ("таблиц", "tables"),
        ("table", "tables"),
        ("историческ", "historical_tables"),
    ),
)
