"""Regional socio-economic editions: archive identity, not archive extraction."""
from .rules import FamilyRule

RULE = FamilyRule(
    "socioeconomic_regions", "rosstat-socioeconomic-regions-2", "monthly",
    "regional_archive", (
        ("таблиц", "tables"),
        ("историческ", "historical_archive"),
    ),
)
