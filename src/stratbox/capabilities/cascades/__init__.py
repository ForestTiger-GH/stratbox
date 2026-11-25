"""Canonical coordination of independently accepted analytical scenarios."""
from stratbox.capabilities.model import CascadeDefinition, CollectionMembership, GraphBody, Call, InputRef, OutputRef, ParameterRef
from stratbox.capabilities.commands import MATERIAL_INPUT, VIEW, REPRESENTATION, READABLE


def definitions():
    return (CascadeDefinition("cascade.observation_package", GraphBody((
        Call("source", "scenario.observation_view", {"material": InputRef("material")}, {"profile": ParameterRef("numerator_profile")}),
        Call("ratio", "scenario.observation_ratio", {"numerator": InputRef("material"), "denominator": InputRef("material")},
            {"numerator_profile": ParameterRef("numerator_profile"), "denominator_profile": ParameterRef("denominator_profile"),
             "destination": ParameterRef("destination"), "pair": ParameterRef("pair")}),
    ), {"source": OutputRef("source", "view"), "ratio": OutputRef("ratio", "view"),
        "representation": OutputRef("ratio", "representation"), "readable": OutputRef("source", "readable")}, required_effects=("ratio",)),
        inputs={"material": MATERIAL_INPUT}, outputs={"source": VIEW, "ratio": VIEW, "representation": REPRESENTATION, "readable": READABLE},
        parameters={"numerator_profile": {}, "denominator_profile": {}}, required_parameters=("destination", "pair"),
        effects=frozenset({"storage.write"}),
        membership=CollectionMembership(("source", "ratio"), True,
            frozenset({"source", "ratio"}), frozenset({"source", "ratio"}))),)
