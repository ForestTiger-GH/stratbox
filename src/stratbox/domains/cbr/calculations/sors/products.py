"""SORS presentation methods; standard operations own rendering and persistence."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from stratbox.shared.data.values import SourceDataset, View
from stratbox.domains.cbr.products.corporate_lending.sors.contracts import SorsWorkbookRequest
from stratbox.domains.cbr.products.corporate_lending.sors.results import SorsViewPack
from stratbox.domains.cbr.calculations.sors.results import SorsRestorationResult, SorsCrosswalkResult


def _checkpoint(context):
    if context is not None and hasattr(context, "checkpoint"):
        context.checkpoint()


def view_prepare(inputs, settings, context):
    from stratbox.domains.cbr.products.corporate_lending.sors.pack import build_sors_views
    value = inputs["dataset"]
    lineage = getattr(value, "lineage", ())
    result = value.native if isinstance(value, SourceDataset) else value
    if not isinstance(result, (SorsRestorationResult, SorsCrosswalkResult)):
        raise TypeError("sors.product_certified_result_required")
    parameters = getattr(context, "parameters", {}) if context is not None else {}
    request = parameters.get("request", SorsWorkbookRequest())
    if isinstance(request, Mapping):
        request = SorsWorkbookRequest(**request)
    if not isinstance(request, SorsWorkbookRequest):
        raise TypeError("sors.product_request_invalid")
    pack = build_sors_views(result, request, checkpoint=lambda: _checkpoint(context),
                            budget=getattr(context, "budget", None))
    return {"view": View(pack, lineage=lineage, source_uses=tuple(pack.source_uses))}


def product_render(inputs, settings, context):
    from stratbox.domains.cbr.products.corporate_lending.sors.rendering import render_sors_views
    value = inputs["view"]
    if not isinstance(value, View) or not isinstance(value.value, SorsViewPack):
        raise TypeError("sors.prepared_view_required")
    rendered = render_sors_views(value.value, checkpoint=lambda: _checkpoint(context),
                                 budget=getattr(context, "budget", None))
    return {"product": replace(rendered.representation, lineage=value.lineage, source_uses=value.source_uses,
        descriptor={"scientific_view": value.value.fingerprint, "sheets": rendered.sheet_names})}
