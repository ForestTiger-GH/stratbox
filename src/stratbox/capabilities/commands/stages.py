"""Typed neutral stage commands, free of publisher selection and orchestration."""
from stratbox.capabilities.model import CommandDefinition, PortContract, ReuseContract
from stratbox.capabilities.commands import ANY, MATERIAL, MATERIAL_INPUT, OBSERVATIONS, RECEIPT, REPRESENTATION
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot, SnapshotReference
from stratbox.shared.data.workbooks import WorkbookExtract, WorkbookComparison
from stratbox.shared.data.documents import DocumentExtract
from stratbox.shared.data.views import ObservationView
from stratbox.shared.data.stages import IntegratedBatch, QualifiedMaterial, ObservationComparison
from stratbox.shared.data.updates import UpdatePlan
from stratbox.shared.material_collections import CollectionManifest
from stratbox.shared.materials import MaterialArtifact, ArtifactReference
from stratbox.shared.evidence import MaterialReference
from stratbox.shared.source_versions import OriginalVersion, OriginalVersionComparison
from stratbox.shared.data.query import TablePreview

SNAPSHOT = PortContract(DataContract("dataset.snapshot", 1), DatasetSnapshot)
WORKBOOK_EXTRACT = PortContract(DataContract("workbook.cells.extract", 1, DataRole.EXTRACTS), WorkbookExtract)
DOCUMENT = PortContract(DataContract("document.blocks.extract", 1, DataRole.EXTRACTS), DocumentExtract)
PHYSICAL_READABLE = PortContract(DataContract("physical.readable", 1, DataRole.READABLE))
MEMBERS = PortContract(DataContract("material.members", 1), tuple)
COLLECTION = PortContract(DataContract("material.collection", 1), CollectionManifest)
INTEGRATED = PortContract(DataContract("observations.integrated", 1, DataRole.INTEGRATED), IntegratedBatch)
QUALIFIED = PortContract(DataContract("material.qualified", 1), QualifiedMaterial)
DATASET_REFERENCE = PortContract(DataContract("dataset.reference", 1), SnapshotReference)
VIEW = PortContract(DataContract("observations.view", 1, DataRole.PRODUCTS), ObservationView)
ARTIFACT = PortContract(DataContract("material.artifact", 1), MaterialArtifact)
ARTIFACT_REFERENCE = PortContract(DataContract("material.artifact.reference", 1), ArtifactReference)
MATERIAL_REFERENCE = PortContract(DataContract("material.reference", 1), MaterialReference)
BYTES = 32 * 1024 * 1024
PURE = ReuseContract(mutation="immutable")


def definitions():
    prefix = "stratbox.core.capabilities.stages:"
    def pure(name, handler, inputs, output, parameters=None, required=(), fixed=None, optional=()):
        return CommandDefinition("stage." + name, prefix + handler, inputs=inputs, outputs={"value": output},
            parameters=parameters or {}, required_parameters=required, fixed=fixed or {},
            optional_capabilities=frozenset(optional), reuse=PURE)
    result = [
        CommandDefinition("stage.material.preserve", prefix + "material_preserve", inputs={"material": ANY},
            outputs={"value": RECEIPT}, required_parameters=("destination",),
            parameters={"mode": "immutable", "expected_revision": None, "source_revision": None, "input_basis": None},
            effects=frozenset({"storage.write"}), required_capabilities=frozenset({"output_filestore"}),
            reuse=ReuseContract(shareable=False, completed=False, effects=frozenset({"storage.write"}))),
        pure("archive.members", "archive_members", {"material": MATERIAL}, MEMBERS,
            {"names": (), "max_members": 250, "max_bytes": BYTES, "max_unpacked_bytes": BYTES,
             "max_member_bytes": BYTES, "media_type": "application/octet-stream"}, optional=("archive_reader",)),
        pure("archive.pack", "archive_pack", {"members": MEMBERS}, MATERIAL,
            {"max_members": 250, "max_bytes": BYTES, "max_unpacked_bytes": BYTES, "max_member_bytes": BYTES}),
        pure("collection.encode", "collection_encode", {"collection": COLLECTION}, REPRESENTATION, {"max_bytes": BYTES}),
        pure("collection.decode", "collection_decode", {"material": ANY}, COLLECTION, {"max_bytes": BYTES}),
        pure("workbook.extract", "workbook_extract", {"material": MATERIAL}, WORKBOOK_EXTRACT,
            {"asset_id": "main"}, ("series_id", "issue_id")),
        pure("document.decode", "document_decode", {"material": MATERIAL}, DOCUMENT,
            {"asset_id": "main", "max_pages": 10_000}, ("series_id", "issue_id")),
        pure("document.readable", "readable", {"value": DOCUMENT}, PHYSICAL_READABLE, {"max_bytes": BYTES}),
        pure("workbook.readable", "readable", {"value": WORKBOOK_EXTRACT}, PHYSICAL_READABLE, {"max_bytes": BYTES}),
        pure("snapshot.encode", "snapshot_encode", {"snapshot": SNAPSHOT}, REPRESENTATION, {"max_bytes": BYTES}),
        pure("snapshot.decode", "snapshot_decode", {"material": ANY}, SNAPSHOT, {"max_bytes": BYTES, "max_cells": 5_000_000}),
        pure("workbook.compare", "compare", {"before": WORKBOOK_EXTRACT, "after": WORKBOOK_EXTRACT},
            PortContract(DataContract("workbook.comparison", 1), WorkbookComparison)),
        pure("material.compare", "compare", {"before": ANY, "after": ANY}, ANY),
        pure("observations.compare", "compare", {"before": OBSERVATIONS, "after": OBSERVATIONS},
            PortContract(DataContract("observations.comparison", 1), ObservationComparison), {"kind": "revision"}),
        pure("processing.plan_update", "plan_update", {}, PortContract(DataContract("processing.update_plan", 1), UpdatePlan),
            {"retained": (), "coverage": None}, ("targets",)),
        pure("snapshot.query", "query_snapshot", {"snapshot": SNAPSHOT}, PortContract(value_type=TablePreview),
            {"expected_identity": None}, ("query",)),
        pure("observations.align", "align", {"observations": OBSERVATIONS}, INTEGRATED,
            {"mappings": {}, "references": (), "require_mapped": False}),
        pure("observations.query", "query_observations", {"observations": OBSERVATIONS}, OBSERVATIONS,
            {"metric_ids": (), "subject_ids": (), "period_kinds": ()}),
        pure("integrated.query", "query_observations", {"observations": INTEGRATED}, INTEGRATED,
            {"metric_ids": (), "subject_ids": (), "period_kinds": ()}),
        pure("csv.qualify", "qualify_csv", {"material": MATERIAL}, QUALIFIED,
            {"columns": (), "encoding": "utf-8", "delimiter": ",", "max_bytes": BYTES, "max_rows": 1_000_000}, ("contract",)),
        pure("qualified.snapshot", "qualified_encode", {"value": QUALIFIED}, REPRESENTATION, {"max_bytes": BYTES}),
        pure("qualified.replay", "qualified_decode", {"material": ANY}, QUALIFIED, {"max_bytes": BYTES}),
        CommandDefinition("stage.reference.editions", prefix + "reference_editions", outputs={"value": PortContract(value_type=tuple)},
            parameters={"references": ()}, reference_ids=("reference.geography.names", "reference.banks", "reference.okved2"), reuse=PURE),
        pure("release.manifest", "release_manifest", {"receipts": PortContract(value_type=tuple)}, REPRESENTATION,
            {"members": (), "input_versions": {}, "member_versions": {}, "expected_members": {}, "max_bytes": BYTES}, ("release_id",)),
        pure("release.basis", "release_basis", {"manifest": REPRESENTATION}, PortContract(value_type=str), {"max_bytes": BYTES}),
        CommandDefinition("stage.release.verify", prefix + "release_verify", inputs={"receipts": PortContract(value_type=tuple)},
            outputs={"value": PortContract(value_type=tuple)}, required_capabilities=frozenset({"output_filestore"}),
            reuse=ReuseContract(shareable=False)),
        CommandDefinition("stage.dataset.ingest", prefix + "dataset_ingest", inputs={"value": ANY},
            outputs={"value": DATASET_REFERENCE}, effects=frozenset({"dataset.write"}),
            required_capabilities=frozenset({"dataset_writer"}),
            reuse=ReuseContract(shareable=False, completed=False, effects=frozenset({"dataset.write"}))),
        CommandDefinition("stage.dataset.query", prefix + "dataset_query", inputs={"reference": DATASET_REFERENCE},
            outputs={"value": SNAPSHOT}, parameters={"components": None, "max_cells": 5_000_000},
            required_capabilities=frozenset({"dataset_reader"}), reuse=ReuseContract(shareable=False)),
        CommandDefinition("stage.dataset.versions", prefix + "dataset_versions", required_parameters=("dataset_id",),
            outputs={"value": PortContract(value_type=tuple)}, required_capabilities=frozenset({"dataset_catalog"}),
            reuse=ReuseContract(shareable=False)),
        CommandDefinition("stage.material.resolve", prefix + "material_resolve", inputs={"reference": MATERIAL_REFERENCE},
            outputs={"value": MATERIAL}, parameters={"max_bytes": BYTES}, required_capabilities=frozenset({"filestore"}),
            reuse=ReuseContract(shareable=False)),
        CommandDefinition("stage.material.locate", prefix + "material_locate", outputs={"material": MATERIAL, "reference": MATERIAL_REFERENCE},
            parameters={"max_bytes": BYTES, "media_type": "application/octet-stream", "source_id": None, "charset": None,
                "expected_identity": None, "expected_revision": None}, required_parameters=("path",),
            required_capabilities=frozenset({"filestore"}), reuse=ReuseContract(shareable=False)),
        CommandDefinition("stage.artifact.resolve", prefix + "artifact_resolve", inputs={"reference": ARTIFACT_REFERENCE},
            outputs={"value": ARTIFACT}, parameters={"max_bytes": BYTES}, required_capabilities=frozenset({"filestore"}),
            reuse=ReuseContract(shareable=False)),
        CommandDefinition("stage.artifact.parts", prefix + "artifact_parts", inputs={"artifact": ARTIFACT},
            outputs={"data": REPRESENTATION, "descriptor": REPRESENTATION}, parameters={"max_bytes": BYTES}, reuse=PURE),
        CommandDefinition("stage.artifact.destinations", prefix + "artifact_destinations", outputs={"data": ANY, "descriptor": ANY},
            parameters={"descriptor_destination": None}, required_parameters=("destination",), reuse=PURE),
        pure("artifact.reference", "artifact_reference", {"artifact": ARTIFACT, "data": RECEIPT, "descriptor": RECEIPT}, ARTIFACT_REFERENCE),
        pure("source.compare_versions", "source_compare_versions", {"candidate": PortContract(value_type=OriginalVersion),
                "baseline": PortContract(value_type=object, required=False)}, PortContract(value_type=OriginalVersionComparison),
            {"absence": None, "presence": None}, ("baseline_state",)),
        CommandDefinition("stage.material.reconcile", prefix + "reconcile_material", inputs={"receipt": RECEIPT},
            outputs={"value": RECEIPT}, required_capabilities=frozenset({"filestore"}), reuse=ReuseContract(shareable=False)),
        pure("notification.qualify", "notification_qualify", {"lookup": ANY, "receipt": PortContract(required=False)}, ANY),
    ]
    for name, port in (("observations", OBSERVATIONS), ("view", VIEW), ("workbook", WORKBOOK_EXTRACT),
            ("document", DOCUMENT), ("integrated", INTEGRATED)):
        result.extend((pure(name + ".snapshot", "snapshot", {"value": port}, SNAPSHOT, {"max_bytes": BYTES}),
            pure(name + ".replay", "replay", {"snapshot": SNAPSHOT}, port, fixed={"value_kind": name})))
    return tuple(result)
