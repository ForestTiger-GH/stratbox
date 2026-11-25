"""Common source and retained-product goals with independent stage outputs."""
from stratbox.capabilities.catalog import CatalogContribution, RecipeDefinition
from stratbox.capabilities.commands import MATERIAL_INPUT, MATERIAL, URL, RECEIPT, OBSERVATIONS, VIEW, REPRESENTATION
from stratbox.capabilities.model import OperationDefinition, ScenarioDefinition, GraphBody, Call, InputRef, OutputRef, ParameterRef


def contribution():
    accept = OperationDefinition("accept.original", GraphBody((
        Call("read", "material.read", {"material": InputRef("material")}),
        Call("attribute", "material.attribute", {"material": OutputRef("read")},
             {"source_id": ParameterRef("source_id")}),
    ), {"original": OutputRef("attribute")}),
        inputs={"material": MATERIAL_INPUT}, outputs={"original": MATERIAL},
        parameters={"source_id": None})
    original = ScenarioDefinition("scenario.source_original", GraphBody((
        Call("accept", "accept.original", {"material": InputRef("material")},
             {"source_id": ParameterRef("source_id")}),
    ), {"original": OutputRef("accept", "original")}),
        inputs={"material": MATERIAL_INPUT}, outputs={"original": MATERIAL},
        parameters={"source_id": None}, purpose="Admit supplied original bytes with an independent logical source use.")
    capture = ScenarioDefinition("scenario.capture_original", GraphBody((
        Call("acquire", "acquire.material", {"url": InputRef("url")},
             {"source_id": ParameterRef("source_id"), "max_bytes": ParameterRef("max_bytes")}),
        Call("preserve", "preserve.material", {"material": OutputRef("acquire", "material")},
             {"destination": ParameterRef("destination")}),
    ), {"original": OutputRef("acquire", "material"), "receipt": OutputRef("preserve", "receipt")},
        required_effects=("preserve",)),
        inputs={"url": URL}, outputs={"original": MATERIAL, "receipt": RECEIPT},
        parameters={"source_id": None, "max_bytes": 16 * 1024 * 1024},
        required_parameters=("destination",), effects=frozenset({"network.receive", "storage.write"}),
        purpose="Acquire once and preserve the publisher original with a confirmed storage receipt.")
    product = ScenarioDefinition("scenario.retained_product", GraphBody((
        Call("view", "view.table", {"observations": InputRef("observations")},
             {"view_id": ParameterRef("view_id"), "metric_ids": ParameterRef("metric_ids"),
              "subject_ids": ParameterRef("subject_ids")}),
        Call("render", "render.table", {"view": OutputRef("view", "view")},
             {"format": ParameterRef("format")}),
    ), {"view": OutputRef("view", "view"), "representation": OutputRef("render", "representation")}),
        inputs={"observations": OBSERVATIONS}, outputs={"view": VIEW, "representation": REPRESENTATION},
        parameters={"view_id": None, "metric_ids": (), "subject_ids": (), "format": "csv"},
        purpose="Prepare and render a product from retained observations without source reacquisition.")
    publish = ScenarioDefinition("scenario.save_retained_product", GraphBody((
        Call("product", "scenario.retained_product", {"observations": InputRef("observations")},
             {name: ParameterRef(name) for name in ("view_id", "metric_ids", "subject_ids", "format")}),
        Call("save", "save.product", {"material": OutputRef("product", "representation")},
             {name: ParameterRef(name) for name in ("destination", "mode", "expected_revision", "source_revision", "input_basis")}),
    ), {"view": OutputRef("product", "view"), "representation": OutputRef("product", "representation"),
        "receipt": OutputRef("save", "receipt")}, required_effects=("save",)),
        inputs={"observations": OBSERVATIONS}, outputs={"view": VIEW, "representation": REPRESENTATION, "receipt": RECEIPT},
        parameters={**dict(product.parameters), "mode": "immutable", "expected_revision": None,
                    "source_revision": None, "input_basis": None}, required_parameters=("destination",),
        effects=frozenset({"storage.write"}), purpose="Save a retained product under explicit revision and input-basis authority.")
    return CatalogContribution(definitions=(accept, original, capture, product, publish), recipes=(
        RecipeDefinition("recipe.source_original", "source.original", original.capability_id),
        RecipeDefinition("recipe.source_capture", "source.capture", capture.capability_id),
        RecipeDefinition("recipe.retained_product", "retained.product", product.capability_id),
        RecipeDefinition("recipe.save_retained_product", "retained.publish", publish.capability_id),
    ))
