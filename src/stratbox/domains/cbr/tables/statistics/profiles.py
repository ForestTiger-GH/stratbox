"""Explicit profile binding across statistical families; no inference from URLs."""
from functools import lru_cache
from importlib import import_module
import re

_MODULES = ("funding", "household_lending", "household_finance", "monetary_statistics",
            "banking_sector_structure", "securities", "external_debt", "exchange_rates")


@lru_cache(maxsize=1)
def profiles():
    modules = tuple("stratbox.domains.cbr.tables." + family + ".profiles" for family in _MODULES)
    modules += ("stratbox.domains.cbr.tables.statistics.corporate_profiles",)
    result = tuple(profile for name in modules for profile in import_module(name).PROFILES)
    if len({profile.profile_id for profile in result}) != len(result):
        raise ValueError("cbr.tables.duplicate_profile")
    return result


def table_profile(profile_id):
    for profile in profiles():
        if profile.profile_id == profile_id:
            return profile
    raise ValueError("cbr.tables.profile_unknown")


def sheet_variant(profile, sheet_name):
    matches = tuple(variant for variant in profile.variants
                    if re.fullmatch(variant.sheet_pattern, sheet_name, re.I))
    if len(matches) > 1:
        raise ValueError("cbr.tables.variant_ambiguous")
    return matches[0] if matches else None
