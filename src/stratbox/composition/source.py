"""Bind source-goal recipes against an explicitly supplied capability catalog."""
from __future__ import annotations


def source_workflow(series_id, *, payload=None, issue_id=None, format=None, asset=None,
                    parameters=None, inputs=None, selection=None, output="extract", catalog):
    """Bind a source recipe to explicit values using the common request contract.

    Publication contexts and reviewed profiles are caller inputs. No context is
    manufactured from a date string. A supplied material starts at extraction;
    acquisition occurs only when the chosen recipe explicitly includes it.
    """
    from stratbox.composition.requests import InvocationRequest
    from stratbox.capabilities.catalog import CatalogSnapshot
    snapshot = catalog if isinstance(catalog, CatalogSnapshot) else getattr(catalog, "snapshot", None)
    if snapshot is None:
        raise ValueError("workflow.capability_catalog_required")
    sources = catalog.source_catalog() if hasattr(catalog, "source_catalog") else None
    if sources is None:
        from stratbox.domains.registry import source_catalog
        sources = source_catalog()
    card = sources.source(series_id)
    if card is None:
        raise ValueError("registry.source_unknown")
    selected = {**dict(selection or {}), "source_id": series_id}
    representation = format or getattr(asset, "format", None) or getattr(asset, "declared_format", None)
    if representation is not None:
        if representation not in card.formats:
            raise ValueError("source.operation_format_unavailable")
        selected["representation"] = representation
    goals = {"extract": "source.extract", "product": "source.product",
             "original": "source.original", "capture": "source.capture"}
    if output not in goals:
        raise ValueError("workflow.goal_unknown")
    recipe = snapshot.resolve_goal(goals[output], selection=selected)
    target = snapshot.definition(recipe.capability_id)
    values, options = dict(inputs or {}), dict(parameters or {})
    if payload is not None:
        ports = [name for name in ("payload", "material", "source") if name in target.inputs]
        if len(ports) != 1 or ports[0] in values:
            raise ValueError("workflow.explicit_material_input_required")
        values[ports[0]] = payload
    if asset is not None:
        if "asset" not in target.inputs or "asset" in values:
            raise ValueError("workflow.explicit_asset_input_required")
        values["asset"] = asset
    declared = set(target.parameters) | set(target.fixed) | set(target.required_parameters) | set(recipe.defaults)
    if "source_id" in declared:
        if "source_id" in options and options["source_id"] != series_id:
            raise ValueError("workflow.source_mismatch")
        options["source_id"] = series_id
    if issue_id is not None:
        if "issue_id" not in declared:
            raise ValueError("workflow.explicit_publication_context_required")
        if "issue_id" in options and options["issue_id"] != issue_id:
            raise ValueError("workflow.issue_mismatch")
        options["issue_id"] = issue_id
    return InvocationRequest(target.capability_id, values, options,
        selection=selected, recipe_id=recipe.recipe_id)

