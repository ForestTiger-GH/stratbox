"""The four publisher-specific release profiles share one bounded link parser."""

from . import (
    socioeconomic_russia, socioeconomic_regions,
    short_term_indicators, population_municipalities,
)

RULES = {
    profile.RULE.profile_id: profile.RULE
    for profile in (
        socioeconomic_russia, socioeconomic_regions,
        short_term_indicators, population_municipalities,
    )
}
