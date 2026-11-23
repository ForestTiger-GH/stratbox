"""Reviewed workbook specializations share one explicit outer workflow."""
from __future__ import annotations

from stratbox.composition.models import (
    CollectSpec, CollectStep, OperationStep, PlanOutputRef, ScenarioDefinition,
)
from stratbox.shared.data.processing import DataContract, DataRole
from .common import value_input


def rosstat_workflow(series_id, *, payload, issue_id, asset_id="main", profile=None,
                     format="csv", kep2_options=None):
    physical = OperationStep("physical", "rosstat.tables.extract_workbook",
        {"payload": value_input(payload, "source.payload", "originals")},
        {"series_id": series_id, "issue_id": issue_id, "asset_id": asset_id})
    if series_id == "rosstat.short_term_indicators":
        interpret = OperationStep("interpret", "rosstat.tables.extract_kep2",
            {"workbook": PlanOutputRef("physical", "workbook")}, dict(kep2_options or {}))
    else:
        if profile is None:
            raise ValueError("workflow.reviewed_profile_required")
        interpret = OperationStep("interpret", "rosstat.tables.map_reviewed_cells",
            {"physical": PlanOutputRef("physical", "workbook")}, {"profile": profile})
    flake_contract = DataContract("rosstat.source_flake", role=DataRole.EXTRACTS)
    collect = CollectStep("flakes", CollectSpec((PlanOutputRef("interpret", "flake"),),
                          contract=flake_contract, element_contract=flake_contract))
    integrate = OperationStep("integrate", "rosstat.integration.integrate",
        {"flakes": PlanOutputRef("flakes", "value")},
        {"dataset_id": series_id, "release_id": issue_id})
    view = OperationStep("view", "rosstat.products.prepare_view",
        {"dataset": PlanOutputRef("integrate", "dataset")})
    render = OperationStep("render", "rosstat.products.render_view",
        {"view": PlanOutputRef("view", "view")}, {"format": format})
    return ScenarioDefinition(series_id + ".processing", (physical, interpret, collect, integrate, view, render),
        {"workbook": PlanOutputRef("physical", "workbook"), "flake": PlanOutputRef("interpret", "flake"),
         "dataset": PlanOutputRef("integrate", "dataset"), "view": PlanOutputRef("view", "view"),
         "representation": PlanOutputRef("render", "representation")})
