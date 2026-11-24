"""Exact functional transitions with inspectable command bodies."""
from stratbox.capabilities.model import AcceptanceContract, OperationDefinition, PortContract, GraphBody, Call, InputRef, OutputRef, ParameterRef
from stratbox.capabilities.commands import ANY, MATERIAL_INPUT, URL, MATERIAL, OBSERVATIONS, VIEW, REPRESENTATION, RECEIPT
from stratbox.shared.data.processing import DataContract


def extraction_body(interpreter="fields.interpret"):
    return GraphBody((
        Call("read", "material.read", {"material": InputRef("material")}),
        Call("decode", "workbook.decode", {"material": OutputRef("read")}),
        Call("select", "table.select", {"workbook": OutputRef("decode")}, {"profile": ParameterRef("profile")}),
        Call("interpret", interpreter, {"table": OutputRef("select")}, {"profile": ParameterRef("profile")}),
        Call("check", "schema.check", {"value": OutputRef("interpret")}),
    ), {"observations": OutputRef("check")}, required_checks=("check",))


def definitions():
    return (
        OperationDefinition("extract.observations", method_slot="interpretation", inputs={"material": MATERIAL_INPUT},
            outputs={"observations": OBSERVATIONS}, parameters={"profile": {}},
            acceptance=AcceptanceContract(coherent_outputs=("observations",))),
        OperationDefinition("convert.readable", GraphBody((
            Call("read", "material.read", {"material": InputRef("material")}),
            Call("decode", "workbook.decode", {"material": OutputRef("read")}),
            Call("readable", "workbook.readable", {"workbook": OutputRef("decode")}),
        ), {"readable": OutputRef("readable")}), inputs={"material": MATERIAL_INPUT}, outputs={"readable": REPRESENTATION}),
        OperationDefinition("calculate.ratio", GraphBody((
            Call("evaluate", "numbers.evaluate", {"numerator": InputRef("numerator"), "denominator": InputRef("denominator")},
                {name: ParameterRef(name) for name in ("metric_id", "unit", "multiplier", "dataset_id")}),
            Call("check", "schema.check", {"value": OutputRef("evaluate")}),
        ), {"observations": OutputRef("check")}, required_checks=("check",)),
            inputs={"numerator": OBSERVATIONS, "denominator": OBSERVATIONS}, outputs={"observations": OBSERVATIONS},
            parameters={"metric_id": "ratio", "unit": "ratio", "multiplier": 1, "dataset_id": None}),
        OperationDefinition("view.table", GraphBody((
            Call("prepare", "view.prepare", {"observations": InputRef("observations")},
                {name: ParameterRef(name) for name in ("view_id", "metric_ids", "subject_ids")}),
        ), {"view": OutputRef("prepare")}), inputs={"observations": OBSERVATIONS}, outputs={"view": VIEW},
            parameters={"view_id": None, "metric_ids": (), "subject_ids": ()}),
        OperationDefinition("render.table", GraphBody((
            Call("encode", "representation.encode", {"view": InputRef("view")},
                {"format": ParameterRef("format"), "max_bytes": ParameterRef("max_bytes")}),
        ), {"representation": OutputRef("encode")}), inputs={"view": VIEW}, outputs={"representation": REPRESENTATION},
            parameters={"format": "csv", "max_bytes": 32 * 1024 * 1024}),
        OperationDefinition("save.product", GraphBody((
            Call("commit", "store.commit", {"material": InputRef("material")},
                {name: ParameterRef(name) for name in ("destination", "mode", "expected_revision", "source_revision", "input_basis")}),
        ), {"receipt": OutputRef("commit")}, required_effects=("commit",)),
            inputs={"material": REPRESENTATION}, outputs={"receipt": RECEIPT},
            parameters={"mode": "immutable", "expected_revision": None, "source_revision": None, "input_basis": None},
            required_parameters=("destination",), effects=frozenset({"storage.write"})),
        OperationDefinition("acquire.material", GraphBody((
            Call("receive", "http.acquire", {"url": InputRef("url")},
                {name: ParameterRef(name) for name in ("observation_id", "freshness", "allow_network", "max_bytes", "headers")}),
            Call("attribute", "material.attribute", {"material": OutputRef("receive")}, {"source_id": ParameterRef("source_id")}),
        ), {"material": OutputRef("attribute")}), inputs={"url": URL}, outputs={"material": MATERIAL},
            parameters={"source_id": None, "observation_id": None, "freshness": "observation", "allow_network": True,
                "max_bytes": 16 * 1024 * 1024, "headers": {}},
            effects=frozenset({"network.receive"})),
        OperationDefinition("discover.links", GraphBody((
            Call("links", "index.links", {"material": InputRef("material")}, {"base_url": ParameterRef("base_url")}),
        ), {"links": OutputRef("links")}), inputs={"material": MATERIAL},
            outputs={"links": PortContract(DataContract("index.links", 1), tuple)},
            required_parameters=("base_url",)),
        OperationDefinition("select.link", GraphBody((
            Call("select", "index.select", {"links": InputRef("links")}, {"pattern": ParameterRef("pattern")}),
        ), {"url": OutputRef("select")}),
            inputs={"links": PortContract(DataContract("index.links", 1), tuple)},
            outputs={"url": PortContract(DataContract("index.url", 1), str)},
            required_parameters=("pattern",)),
    )
