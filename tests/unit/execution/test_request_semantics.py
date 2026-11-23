"""Every computational request field is captured and technical roles stay apart."""
from dataclasses import dataclass, replace

from stratbox.core.execution import OperationDefinition
from stratbox.core.execution.arguments import capture_arguments, filter_parameters
from stratbox.shared.data.operations import InputPort, OperationSemantics, OutputPort, ProcessingStage, RequestField
from stratbox.shared.data.processing import DataContract


@dataclass(frozen=True)
class Controls:
    factor: int = 2
    logger: object = None
    destination: str = "first"


@dataclass(frozen=True)
class Request:
    value: int
    controls: Controls
    hidden: int = 1


def definition(policies=()):
    return OperationDefinition("fixture.project", "project", Request, int,
        request_fields=policies, processing=OperationSemantics((ProcessingStage.CALCULATE,),
            inputs=(InputPort("request", DataContract("fixture.request")),),
            parameters=("controls",), outputs=(OutputPort("result", DataContract("fixture.result")),),
            summary="Compute from exact data and explicitly classified controls."))


def test_mixed_root_port_excludes_effect_runtime_and_observability_fields():
    operation = definition((RequestField("value", "input"), RequestField("controls.factor", "parameter"),
        RequestField("controls.logger", "runtime"), RequestField("controls.destination", "effect"),
        RequestField("hidden", "observability")))
    before = Request(1, Controls())
    changed_effects = replace(before, controls=replace(before.controls, destination="another", logger=object()), hidden=99)
    assert capture_arguments(operation, before) == capture_arguments(operation, changed_effects)
    changed_method = replace(before, controls=replace(before.controls, factor=3))
    assert capture_arguments(operation, before) != capture_arguments(operation, changed_method)


def test_direct_definition_without_policy_captures_fields_missing_from_ports_and_parameters():
    operation = definition()
    before = Request(1, Controls())
    assert capture_arguments(operation, before) != capture_arguments(operation, replace(before, hidden=9))


def test_handler_metadata_cannot_reintroduce_nested_technical_parameters():
    operation = definition((RequestField("value", "input"), RequestField("controls.factor", "parameter"),
        RequestField("controls.logger", "runtime"), RequestField("controls.destination", "effect"),
        RequestField("hidden", "observability")))
    assert filter_parameters(operation, {"controls": {"factor": 2, "destination": "first", "logger": "host"},
        "hidden": "trace", "derived_method_option": "strict"}) == {
            "controls": {"factor": 2}, "derived_method_option": "strict"}
