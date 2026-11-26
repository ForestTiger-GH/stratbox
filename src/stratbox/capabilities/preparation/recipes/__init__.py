"""Resolve the pure graph strategy declared by a capability definition."""
from stratbox.capabilities.model import GraphBody


def resolve_recipe(definition, values, parameters, record, catalog=None):
    reference = definition.recipe
    if reference is None:
        return definition
    resolved = reference.resolve()(definition, values, parameters, record, catalog)
    if type(resolved) is not type(definition) or resolved.id != definition.id:
        raise ValueError("recipe.definition_identity_changed")
    if not isinstance(getattr(resolved, "body", None), GraphBody):
        raise TypeError("recipe.graph_required")
    return resolved
