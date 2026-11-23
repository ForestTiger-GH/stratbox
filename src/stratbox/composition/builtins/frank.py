"""Frank RG file admission and independent workbook interpretation."""
from __future__ import annotations

from stratbox.composition.models import OperationStep, PlanOutputRef, ScenarioDefinition
from .common import value_input


def frank_workflow(series_id, *, payload=None, asset=None, period=None, format="xlsx", profile=None,
                   dataset_id=None, release_id=None):
    if payload is None:
        if asset is None:
            raise ValueError("workflow.asset_required")
        if asset.source_id != series_id:
            raise ValueError("workflow.source_mismatch")
        first = OperationStep("original", "frg.acquire", {"asset": value_input(asset, "frg.asset")})
    else:
        if period is None:
            raise ValueError("workflow.period_required")
        first = OperationStep("original", "frg.capture", {"payload": value_input(payload, "source.payload", "originals")},
                              {"source_id": series_id, "period": period, "format": format})
    steps = [first, OperationStep("extract", "frg.extract", {"report": PlanOutputRef("original", "report")})]
    outputs = {"original": PlanOutputRef("original", "report"), "payload": PlanOutputRef("original", "payload"),
               "extract": PlanOutputRef("extract", "value")}
    if profile is not None:
        steps.append(OperationStep("interpret", "frg.build_flake",
            {"extract": PlanOutputRef("extract", "value"), "profile": value_input(profile, "frg.semantic_profile")}))
        steps.append(OperationStep("integrate", "frg.integrate", {"flake": PlanOutputRef("interpret", "value")},
            {"dataset_id": dataset_id or series_id, "release_id": release_id or period.issue_id}))
        outputs.update(flake=PlanOutputRef("interpret", "value"), dataset=PlanOutputRef("integrate", "value"))
    return ScenarioDefinition(series_id + ".processing", tuple(steps), outputs)
