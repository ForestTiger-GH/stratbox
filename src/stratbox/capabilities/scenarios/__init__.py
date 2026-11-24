"""Independently useful source-view and two-source ratio tasks."""
from stratbox.capabilities.model import ScenarioDefinition, GraphBody, Call, InputRef, OutputRef, ParameterRef
from stratbox.capabilities.commands import MATERIAL_INPUT, VIEW, REPRESENTATION


def definitions():
    return (
        ScenarioDefinition("scenario.observation_view", GraphBody((
            Call("extract", "extract.observations", {"material": InputRef("material")}, {"profile": ParameterRef("profile")}, method_id="extract.rows"),
            Call("readable", "convert.readable", {"material": InputRef("material")}),
            Call("view", "view.table", {"observations": OutputRef("extract", "observations")}),
            Call("render", "render.table", {"view": OutputRef("view", "view")}),
        ), {"view": OutputRef("view", "view"), "representation": OutputRef("render", "representation"),
            "readable": OutputRef("readable", "readable")}),
            inputs={"material": MATERIAL_INPUT}, outputs={"view": VIEW, "representation": REPRESENTATION, "readable": REPRESENTATION}, parameters={"profile": {}},
            purpose="Prepare a source observation view and an independently reusable CSV representation."),
        ScenarioDefinition("scenario.observation_ratio", GraphBody((
            Call("numerator", "extract.observations", {"material": InputRef("numerator")},
                {"profile": ParameterRef("numerator_profile")}, method_id="extract.rows"),
            Call("denominator", "extract.observations", {"material": InputRef("denominator")},
                {"profile": ParameterRef("denominator_profile")}, method_id="extract.rows"),
            Call("calculate", "calculate.ratio", {"numerator": OutputRef("numerator", "observations"),
                "denominator": OutputRef("denominator", "observations")}),
            Call("view", "view.table", {"observations": OutputRef("calculate", "observations")}),
            Call("render", "render.table", {"view": OutputRef("view", "view")}),
            Call("save", "save.product", {"material": OutputRef("render", "representation")},
                {"destination": ParameterRef("destination")}),
        ), {"view": OutputRef("view", "view"), "representation": OutputRef("render", "representation")},
            required_effects=("save",)), inputs={"numerator": MATERIAL_INPUT, "denominator": MATERIAL_INPUT},
            outputs={"view": VIEW, "representation": REPRESENTATION},
            parameters={"numerator_profile": {}, "denominator_profile": {}}, required_parameters=("destination",),
            effects=frozenset({"storage.write"}), purpose="Calculate, render and conditionally save a ratio from two aligned source tables."),
    )
