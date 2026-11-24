"""Canonical technical contracts; executable functions load only on invocation."""
from stratbox.capabilities.model import CommandDefinition, PortContract, ReuseContract
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.views import ObservationView
from stratbox.shared.data.workbook_cells import WorkbookCells
from stratbox.shared.evidence import SourcePayload, StoredBytesReceipt

MATERIAL = PortContract(DataContract("material.bytes", 1, DataRole.ORIGINALS), SourcePayload)
MATERIAL_INPUT = PortContract(MATERIAL.schema)
URL = PortContract(DataContract("index.url", 1), str)
WORKBOOK = PortContract(DataContract("workbook.cells", 1), WorkbookCells)
SELECTION = PortContract(DataContract("workbook.selection", 1))
OBSERVATIONS = PortContract(DataContract("observations.batch", 1, DataRole.EXTRACTS), ObservationBatch)
VIEW = PortContract(DataContract("observations.view", 1, DataRole.PRODUCTS), ObservationView)
REPRESENTATION = PortContract(DataContract("product.representation", 1, DataRole.PRODUCTS), Representation)
RECEIPT = PortContract(DataContract("storage.receipt", 1), StoredBytesReceipt)
ANY = PortContract()
PURE = ReuseContract(mutation="immutable")


def definitions():
    prefix = "stratbox.core.capabilities."
    return (
        CommandDefinition("material.read", prefix + "materials:material_read", inputs={"material": MATERIAL_INPUT},
            outputs={"value": MATERIAL}, parameters={"max_bytes": 16 * 1024 * 1024,
            "media_type": "application/octet-stream"}, reuse=PURE),
        CommandDefinition("material.read_file", prefix + "materials:material_read", inputs={},
            outputs={"value": MATERIAL}, parameters={"max_bytes": 16 * 1024 * 1024,
            "media_type": "application/octet-stream"}, required_parameters=("path",),
            required_capabilities=frozenset({"filestore"}), resource_parameters={"staging_bytes": "max_bytes"},
            reuse=ReuseContract(shareable=False)),
        CommandDefinition("material.attribute", prefix + "materials:material_attribute", inputs={"material": MATERIAL},
            outputs={"value": MATERIAL}, parameters={"source_id": None}, reuse=PURE),
        CommandDefinition("http.acquire", prefix + "materials:http_acquire", inputs={"url": URL},
            outputs={"value": MATERIAL}, parameters={"max_bytes": 16 * 1024 * 1024,
            "headers": {}, "observation_id": None, "freshness": "observation", "allow_network": True},
            required_capabilities=frozenset({"http"}),
            resource_parameters={"staging_bytes": "max_bytes", "temporary_bytes": "max_bytes"},
            effects=frozenset({"network.receive"}),
            reuse=ReuseContract(deterministic=False, observation_scoped=True, effects=frozenset({"network.receive"}))),
        CommandDefinition("workbook.decode", prefix + "workbooks:workbook_decode", inputs={"material": MATERIAL},
            outputs={"value": WORKBOOK}, resources={"parse": 1}, reuse=PURE),
        CommandDefinition("workbook.readable", prefix + "workbooks:workbook_readable", inputs={"workbook": WORKBOOK},
            outputs={"value": REPRESENTATION}, parameters={"max_bytes": 32 * 1024 * 1024}, reuse=PURE),
        CommandDefinition("table.select", prefix + "tables:table_select", inputs={"workbook": WORKBOOK},
            outputs={"value": SELECTION}, parameters={"profile": {}}, reuse=PURE),
        CommandDefinition("table.reshape", prefix + "tables:table_reshape", inputs={"table": SELECTION},
            outputs={"value": SELECTION}, parameters={"transpose": False}, reuse=PURE),
        CommandDefinition("fields.interpret", prefix + "tables:fields_interpret", inputs={"table": SELECTION},
            outputs={"value": OBSERVATIONS}, parameters={"profile": {}}, reuse=PURE),
        CommandDefinition("minfin.fields.interpret_budget", "stratbox.domains.minfin.tables.capability_method:interpret_budget",
            inputs={"table": SELECTION}, outputs={"value": OBSERVATIONS}, parameters={"profile": {}}, reuse=PURE),
        CommandDefinition("schema.check", prefix + "tables:schema_check", inputs={"value": OBSERVATIONS},
            outputs={"value": OBSERVATIONS}, parameters={"min_rows": 1, "require_reported": False}, reuse=PURE),
        CommandDefinition("numbers.evaluate", prefix + "tables:numbers_evaluate",
            inputs={"numerator": OBSERVATIONS, "denominator": OBSERVATIONS}, outputs={"value": OBSERVATIONS},
            parameters={"metric_id": "ratio", "unit": "ratio", "multiplier": 1, "dataset_id": None}, reuse=PURE),
        CommandDefinition("view.prepare", prefix + "products:view_prepare", inputs={"observations": OBSERVATIONS},
            outputs={"value": VIEW}, parameters={"view_id": None, "metric_ids": (), "subject_ids": ()}, reuse=PURE),
        CommandDefinition("representation.encode", prefix + "products:representation_encode", inputs={"view": VIEW},
            outputs={"value": REPRESENTATION}, parameters={"format": "csv", "max_bytes": 32 * 1024 * 1024}, reuse=PURE),
        CommandDefinition("store.commit", prefix + "materials:store_commit", inputs={"material": REPRESENTATION},
            outputs={"value": RECEIPT}, parameters={"mode": "immutable", "expected_revision": None,
                "source_revision": None, "input_basis": None}, required_parameters=("destination",),
            required_capabilities=frozenset({"output_filestore"}), effects=frozenset({"storage.write"}),
            reuse=ReuseContract(shareable=False, completed=False, effects=frozenset({"storage.write"}))),
        CommandDefinition("index.links", prefix + "indexes:index_links", inputs={"material": MATERIAL},
            outputs={"value": PortContract(DataContract("index.links", 1), tuple)},
            required_parameters=("base_url",), parameters={"encoding": "utf-8", "max_links": 10_000}, reuse=PURE),
        CommandDefinition("index.select", prefix + "indexes:index_select",
            inputs={"links": PortContract(DataContract("index.links", 1), tuple)},
            outputs={"value": PortContract(DataContract("index.url", 1), str)}, required_parameters=("pattern",), reuse=PURE),
    )
