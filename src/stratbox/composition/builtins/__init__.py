"""Library-supplied workflows use the same graph contracts as client workflows."""
from __future__ import annotations

from .cbr import CbrSelection, cbr_workflow, multi_cbr_workflow
from .expansion import CompositionDisposition, composition_dispositions, expand_operation
from .fns import fns_workflow
from .frank import frank_workflow
from .minfin import minfin_workflow
from .rosstat import rosstat_workflow


def source_workflow(series_id, *, payload=None, issue_id=None, format=None, asset=None,
                    parameters=None, output="extract", catalog=None):
    """Construct an explicit graph for a registered source.

    Publisher identity determines the reviewed method family. ``parameters``
    holds publication context and method-specific choices; no parser is guessed
    from cell contents. Unsupported legacy document decoding remains a qualified
    absence rather than a successful empty extraction.
    """
    from dataclasses import replace
    from datetime import date
    from stratbox.composition.models import OperationStep, PlanOutputRef, ScenarioDefinition
    from .common import network_retry, selected_output, value_input
    if catalog is None:
        from stratbox.domains.registry import source_catalog
        catalog = source_catalog()
    if hasattr(catalog, "source_catalog"):
        catalog = catalog.source_catalog()
    card = catalog.source(series_id)
    if card is None:
        raise ValueError("registry.source_unknown")
    parameters = dict(parameters or {})
    source_format = format or getattr(asset, "format", None) or getattr(asset, "declared_format", None) or card.formats[0]
    if source_format not in card.formats:
        raise ValueError("source.operation_format_unavailable")
    if card.publisher_id == "cbr":
        if issue_id is None:
            raise ValueError("workflow.issue_required")
        scenario = cbr_workflow(series_id, payload=payload, issue_id=issue_id, format=source_format,
            asset_id=parameters.get("asset_id", "main"), url=parameters.get("url"), extract=output != "original")
    elif card.publisher_id == "fns":
        from stratbox.domains.fns.publications.contracts import ReleaseContext
        release = parameters.get("release")
        if release is None:
            if issue_id is None:
                raise ValueError("workflow.issue_required")
            release = ReleaseContext(series_id, issue_id, date.fromisoformat(issue_id))
        scenario = fns_workflow(series_id, release=release, payload=payload,
                               url=parameters.get("url"), format=parameters.get("render_format", "csv"))
        scenario = replace(scenario, outputs={**scenario.outputs, "extract": scenario.outputs["flake"]})
    elif card.publisher_id == "rosstat":
        steps = []
        if payload is None:
            if asset is None:
                raise ValueError("workflow.asset_required")
            if asset.series_id != series_id:
                raise ValueError("workflow.source_mismatch")
            issue_id = issue_id or asset.key.issue.issue_id
            asset_id = asset.key.asset_id
            steps.append(OperationStep("acquire", "rosstat.publications.acquire",
                {"asset": value_input(asset, "rosstat.publications.asset")}, retry=network_retry()))
            material = PlanOutputRef("acquire", "payload")
        else:
            material = value_input(payload, "source.payload", "originals")
            asset_id = parameters.get("asset_id", "main")
        if issue_id is None:
            raise ValueError("workflow.issue_required")
        if output == "original":
            scenario = ScenarioDefinition(series_id + ".original", tuple(steps), {"original": material})
        elif source_format == "xlsx" and (series_id == "rosstat.short_term_indicators" or parameters.get("profile") is not None):
            scenario = rosstat_workflow(series_id, payload=material, issue_id=issue_id, asset_id=asset_id,
                profile=parameters.get("profile"), format=parameters.get("render_format", "csv"),
                kep2_options=parameters.get("kep2_options"))
            scenario = replace(scenario, steps=tuple(steps) + scenario.steps,
                outputs={**scenario.outputs, "original": material, "extract": scenario.outputs["flake"]})
        elif source_format in {"xlsx", "pdf"}:
            kind = "document" if source_format == "pdf" else "workbook"
            steps.append(OperationStep("physical", "rosstat.tables.extract_" + kind, {"payload": material},
                {"series_id": series_id, "issue_id": issue_id, "asset_id": asset_id,
                 **{key: parameters[key] for key in ("container_identity", "member") if key in parameters}}))
            scenario = ScenarioDefinition(series_id + ".physical", tuple(steps),
                {"original": material, "extract": PlanOutputRef("physical", kind)})
        elif source_format in {"zip", "rar"}:
            steps.append(OperationStep("inspect", "rosstat.publications.inspect_archive", {"payload": material}))
            outputs = {"original": material, "inventory": PlanOutputRef("inspect", "inventory")}
            if parameters.get("member_names"):
                steps.append(OperationStep("members", "rosstat.publications.extract_members",
                    {"payload": material, "inventory": PlanOutputRef("inspect", "inventory")},
                    {"names": tuple(parameters["member_names"])}))
                outputs["extract"] = PlanOutputRef("members", "members")
            elif output == "extract":
                raise ValueError("workflow.archive_member_selection_required")
            scenario = ScenarioDefinition(series_id + ".archive", tuple(steps),
                                          outputs)
        else:
            raise ValueError("workflow.source_format_unsupported")
    elif card.publisher_id == "minfin":
        publication = parameters.get("publication")
        if publication is None and issue_id is not None:
            from stratbox.domains.minfin.publications.context import PublicationContext
            publication = PublicationContext(series_id, issue_id, parameters.get("asset_id", "main"))
        scenario = minfin_workflow(series_id, family_id=card.family_id, format=source_format,
            payload=payload, asset=asset, publication=publication, parameters=parameters,
            extract=output != "original")
    elif card.publisher_id == "frank_rg":
        from stratbox.domains.frank_rg.publications.contracts import ReportPeriod
        period = parameters.get("period")
        if period is None and issue_id is not None:
            period = ReportPeriod(date.fromisoformat(issue_id))
        scenario = frank_workflow(series_id, payload=payload, asset=asset, period=period, format=source_format,
            profile=parameters.get("profile"), dataset_id=parameters.get("dataset_id"), release_id=parameters.get("release_id"))
    else:
        raise ValueError("workflow.publisher_unsupported")
    return selected_output(scenario, output)


__all__ = ["source_workflow", "multi_cbr_workflow", "CbrSelection", "cbr_workflow", "fns_workflow",
           "rosstat_workflow", "minfin_workflow", "frank_workflow", "expand_operation",
           "composition_dispositions", "CompositionDisposition"]
