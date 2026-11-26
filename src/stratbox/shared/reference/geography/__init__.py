"""Typed territory-name matching without source-specific statistical aggregation."""
from .models import RegionNameContext, RegionNameMatch, RegionNameRule
from .names import normalize_region_label
from .resolver import RegionNameResolver
from .territories import TerritoryUnit, TerritoryTransition, TerritoryDataset, territory_snapshot, territory_from_snapshot
