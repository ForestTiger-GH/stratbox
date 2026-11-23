"""Typed territory-name matching without source-specific statistical aggregation."""

from .models import RegionNameContext, RegionNameMatch, RegionNameRule
from .names import normalize_region_label
from .resolver import RegionNameResolver
from .editions import TerritoryUnit, TerritoryTransition, TerritoryEdition, territory_snapshot, territory_from_snapshot
