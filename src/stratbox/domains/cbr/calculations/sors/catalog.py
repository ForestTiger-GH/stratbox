"""Static coupled SORS model; standard definitions own all executable graphs."""
from stratbox.capabilities.model.domains import CalculationSpec, CommandSpec, Applicability, ProductSpec
from stratbox.capabilities.model.methods import MethodRef
from .inputs.dependencies import DEPENDENCIES


SORS = CalculationSpec(
    id="cbr.sors",
    input_topology="coupled",
    settings={"primary_portfolio_scope": "CORPORATE_TOTAL", "publication_unit": "million_rubles"},
    semantics={"measure_kind": "stock", "input_scope": "full_coupled_model",
               "evidence": "publication_intervals_and_global_feasibility"},
    inputs={item.input_name: {"source_id": item.series_id, "required": item.required,
                              "purpose": item.source_role} for item in DEPENDENCIES},
    commands={
        "command.value.encode": CommandSpec(
            MethodRef("stratbox.domains.cbr.calculations.sors.serialization:value_encode"),
            applicability=Applicability()),
        "command.value.decode": CommandSpec(
            MethodRef("stratbox.domains.cbr.calculations.sors.serialization:value_decode"),
            applicability=Applicability()),
        "command.model.inputs": CommandSpec(
            MethodRef("stratbox.domains.cbr.calculations.sors.stages:model_inputs"),
            applicability=Applicability()),
        "command.constraints.build": CommandSpec(
            MethodRef("stratbox.domains.cbr.calculations.sors.stages:constraints_build"),
            applicability=Applicability()),
        "command.bounds.propagate": CommandSpec(
            MethodRef("stratbox.domains.cbr.calculations.sors.stages:bounds_propagate"),
            applicability=Applicability()),
        "command.facts.inherit": CommandSpec(
            MethodRef("stratbox.domains.cbr.calculations.sors.stages:facts_inherit"),
            applicability=Applicability()),
        "command.facts.reconcile": CommandSpec(
            MethodRef("stratbox.domains.cbr.calculations.sors.stages:facts_reconcile"),
            applicability=Applicability()),
        "command.model.compile": CommandSpec(
            MethodRef("stratbox.domains.cbr.calculations.sors.stages:model_compile"),
            applicability=Applicability()),
        "command.model.feasibility": CommandSpec(
            MethodRef("stratbox.domains.cbr.calculations.sors.stages:model_feasibility"),
            applicability=Applicability()),
        "command.bounds.optimize": CommandSpec(
            MethodRef("stratbox.domains.cbr.calculations.sors.stages:bounds_optimize"),
            applicability=Applicability()),
        "command.values.certify": CommandSpec(
            MethodRef("stratbox.domains.cbr.calculations.sors.stages:values_certify"),
            applicability=Applicability()),
        "command.observations.assemble": CommandSpec(
            MethodRef("stratbox.domains.cbr.calculations.sors.stages:observations_assemble"),
            applicability=Applicability()),
    },
)


SORS_WORKBOOK = ProductSpec(
    id="cbr.sors.workbook",
    inputs={"dataset": {"calculation": "cbr.sors", "scope": "certified_full_result"}},
    commands={
        "command.view.prepare": CommandSpec(MethodRef(
            "stratbox.domains.cbr.calculations.sors.products:view_prepare")),
        "command.product.render": CommandSpec(MethodRef(
            "stratbox.domains.cbr.calculations.sors.products:product_render")),
        "command.value.encode": CommandSpec(MethodRef(
            "stratbox.domains.cbr.calculations.sors.serialization:value_encode")),
        "command.value.decode": CommandSpec(MethodRef(
            "stratbox.domains.cbr.calculations.sors.serialization:value_decode")),
    },
)


SORS_CROSSWALK = CalculationSpec(
    id="cbr.sors.crosswalk", input_topology="coupled",
    inputs={"strict_result": {"calculation": "cbr.sors", "required": True}},
    semantics={"evidence_layer": "conditional_crosswalk", "input_scope": "full_coupled_model"},
    commands={
        "command.model.inputs": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.sors.crosswalk.stages:model_inputs")),
        "command.constraints.build": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.sors.crosswalk.stages:constraints_build")),
        "command.bounds.propagate": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.sors.crosswalk.stages:bounds_propagate")),
        "command.facts.inherit": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.sors.crosswalk.stages:facts_inherit")),
        "command.facts.reconcile": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.sors.crosswalk.stages:facts_reconcile")),
        "command.model.compile": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.sors.crosswalk.stages:model_compile")),
        "command.model.feasibility": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.sors.crosswalk.stages:model_feasibility")),
        "command.bounds.optimize": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.sors.crosswalk.stages:bounds_optimize")),
        "command.values.certify": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.sors.crosswalk.stages:values_certify")),
        "command.observations.assemble": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.sors.crosswalk.stages:observations_assemble")),
        "command.value.encode": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.sors.serialization:value_encode")),
        "command.value.decode": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.sors.serialization:value_decode")),
    },
)
