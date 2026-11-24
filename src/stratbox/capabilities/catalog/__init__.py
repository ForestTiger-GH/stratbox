"""Canonical metadata snapshots; executable adapters belong to bootstrap."""
from .descriptors import (
    CatalogContribution, MethodDefinition, ProcessingGroup, ProfileDefinition,
    RecipeDefinition, ReferenceDefinition, SchemaDefinition,
)
from .snapshot import CatalogError, CatalogSnapshot, CatalogView, Readiness, ResolvedBinding
