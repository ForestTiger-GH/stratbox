"""Independent FNS source, interpretation, alignment and presentation steps."""
from __future__ import annotations

from stratbox.composition.models import OperationStep, PlanOutputRef, ScenarioDefinition
from .common import network_retry, value_input


def fns_workflow(family, *, release, payload=None, url=None, format="csv"):
    if family not in {"fns.sme", "fns.1yur"}:
        raise ValueError("workflow.fns_family_unknown")
    if release.series_id != family:
        raise ValueError("workflow.fns_release_mismatch")
    steps = []
    if payload is None:
        parameters = {"as_of": release.observation_date}
        if family == "fns.1yur":
            parameters["url"] = url
        elif url is not None:
            raise ValueError("fns.sme.fixed_endpoint_required")
        steps.append(OperationStep("acquire", family + ".acquire", parameters=parameters, retry=network_retry()))
        original = PlanOutputRef("acquire", "source")
    else:
        original = value_input(payload, family + ".original", "originals")
    steps.extend((
        OperationStep("extract", family + ".extract", {"source": original}, {"release": release}),
        OperationStep("project", family + ".project", {"flake": PlanOutputRef("extract", "flake")}),
        OperationStep("align", family + ".align", {"projection": PlanOutputRef("project", "projection")}),
        OperationStep("view", family + ".view", {"dataset": PlanOutputRef("align", "dataset")}),
        OperationStep("render", family + ".render", {"view": PlanOutputRef("view", "view")}, {"format": format}),
    ))
    outputs = {"flake": PlanOutputRef("extract", "flake"),
               "projection": PlanOutputRef("project", "projection"),
               "dataset": PlanOutputRef("align", "dataset"),
               "view": PlanOutputRef("view", "view"),
               "representation": PlanOutputRef("render", "representation")}
    if payload is None:
        outputs.update(original=PlanOutputRef("acquire", "source"), payload=PlanOutputRef("acquire", "payload"))
    else:
        outputs.update(original=original, payload=value_input(payload, "source.payload", "originals"))
    return ScenarioDefinition(family + ".processing", tuple(steps), outputs)


def fns_capture_workflow(family, request):
    """The regional CSV product keeps its explicit publication date."""
    parameters = {"as_of": request.as_of}
    if family == "fns.1yur":
        parameters["url"] = request.url
    return ScenarioDefinition(family + ".capture", (
        OperationStep("acquire", family + ".acquire", parameters=parameters, retry=network_retry()),
        OperationStep("parse", family + ".parse", {"source": PlanOutputRef("acquire", "source")},
                      {"as_of": request.as_of}),
    ), {"release": PlanOutputRef("parse", "release"),
        "representation": PlanOutputRef("parse", "representation")})
