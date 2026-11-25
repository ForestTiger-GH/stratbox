"""Exact stage operations expose reusable commands and independent effects."""
from stratbox.capabilities.catalog import CatalogContribution
from stratbox.capabilities.model import OperationDefinition, GraphBody, Call, InputRef, OutputRef, ParameterRef
from stratbox.capabilities.commands.stages import definitions as commands, ARTIFACT, ARTIFACT_REFERENCE, MATERIAL_REFERENCE
from stratbox.capabilities.commands import RECEIPT, REPRESENTATION


def definitions():
    operations = []
    names = {"stage.material.preserve": "preserve.material", "stage.collection.encode": "material.collection.snapshot",
        "stage.collection.decode": "material.collection.replay", "stage.snapshot.encode": "snapshot.encode",
        "stage.snapshot.decode": "snapshot.decode", "stage.observations.align": "align.observations",
        "stage.observations.query": "query.observations", "stage.integrated.query": "query.integrated",
        "stage.dataset.ingest": "ingest.observations", "stage.dataset.query": "query.dataset",
        "stage.dataset.versions": "list.dataset_versions", "stage.csv.qualify": "qualify.csv",
        "stage.release.manifest": "prepare.release", "stage.workbook.readable": "readable.workbook",
        "stage.reference.editions": "resolve.reference_editions", "stage.source.compare_versions": "compare.source_versions",
        "stage.material.resolve": "read.material_reference", "stage.artifact.resolve": "read.artifact",
        "stage.material.reconcile": "reconcile.material", "stage.notification.qualify": "qualify.notification"}
    names["stage.material.locate"] = "read.material_location"
    for command in commands():
        name = names.get(command.capability_id, command.capability_id.removeprefix("stage."))
        parameters = {key: ParameterRef(key) for key in (*command.parameters, *command.required_parameters)}
        step = Call("stage", command.capability_id, {key: InputRef(key) for key in command.inputs}, parameters)
        outputs = {"receipt": command.outputs["value"]} if name == "preserve.material" else command.outputs
        references = {key: OutputRef("stage", "value" if name == "preserve.material" else key) for key in outputs}
        operations.append(OperationDefinition(name, GraphBody((step,), references,
            required_effects=("stage",) if command.effects else ()), inputs=command.inputs,
            outputs=outputs,
            parameters=command.parameters, required_parameters=command.required_parameters,
            effects=command.effects, reference_ids=command.reference_ids))
    from stratbox.capabilities.commands import MATERIAL
    operations.append(OperationDefinition("read.material_file", GraphBody((
        Call("read", "material.read_file", {}, {key: ParameterRef(key) for key in ("path", "max_bytes", "media_type")}),
    ), {"material": OutputRef("read")}), outputs={"material": MATERIAL},
        parameters={"max_bytes": 16 * 1024 * 1024, "media_type": "application/octet-stream"}, required_parameters=("path",)))
    operations.append(OperationDefinition("transfer.material", GraphBody((
        Call("read", "stage.material.resolve", {"reference": InputRef("reference")}, {"max_bytes": ParameterRef("max_bytes")}),
        Call("save", "stage.material.preserve", {"material": OutputRef("read")},
            {key: ParameterRef(key) for key in ("destination", "mode", "expected_revision", "source_revision", "input_basis")}),
    ), {"receipt": OutputRef("save")}, required_effects=("save",)), inputs={"reference": MATERIAL_REFERENCE},
        outputs={"receipt": RECEIPT}, parameters={"max_bytes": 32 * 1024 * 1024, "mode": "immutable",
            "expected_revision": None, "source_revision": None, "input_basis": None}, required_parameters=("destination",),
        effects=frozenset({"storage.write"})))
    for transfer in (False, True):
        read = (Call("read", "stage.artifact.resolve", {"reference": InputRef("reference")},
            {"max_bytes": ParameterRef("max_bytes")}),) if transfer else ()
        artifact = OutputRef("read") if transfer else InputRef("artifact")
        operations.append(OperationDefinition("transfer.artifact" if transfer else "save.artifact", GraphBody((*read,
            Call("parts", "stage.artifact.parts", {"artifact": artifact}, {"max_bytes": ParameterRef("max_bytes")}),
            Call("destinations", "stage.artifact.destinations", {}, {"destination": ParameterRef("destination"),
                "descriptor_destination": ParameterRef("descriptor_destination")}),
            Call("data", "store.commit", {"material": OutputRef("parts", "data")},
                {"destination": OutputRef("destinations", "data")}),
            Call("metadata", "store.commit", {"material": OutputRef("parts", "descriptor")},
                {"destination": OutputRef("destinations", "descriptor")}, depends_on=("data",)),
            Call("reference", "stage.artifact.reference", {"artifact": artifact,
                "data": OutputRef("data"), "descriptor": OutputRef("metadata")}),
        ), {"artifact": OutputRef("reference"), "data_receipt": OutputRef("data"), "descriptor_receipt": OutputRef("metadata")},
            required_effects=("data", "metadata")),
            inputs={"reference": ARTIFACT_REFERENCE} if transfer else {"artifact": ARTIFACT},
            outputs={"artifact": ARTIFACT_REFERENCE, "data_receipt": RECEIPT, "descriptor_receipt": RECEIPT},
            parameters={"max_bytes": 32 * 1024 * 1024, "descriptor_destination": None}, required_parameters=("destination",),
            effects=frozenset({"storage.write"})))
    # Release publication is gated by all confirmed members before its single
    # conditional pointer write. Retained data members remain independently usable.
    operations.append(OperationDefinition("publish.release", GraphBody((
        Call("verify", "stage.release.verify", {"receipts": InputRef("receipts")}),
        Call("manifest", "stage.release.manifest", {"receipts": OutputRef("verify")},
            {key: ParameterRef(key) for key in ("release_id", "members", "input_versions", "member_versions", "expected_members", "max_bytes")}),
        Call("basis", "stage.release.basis", {"manifest": OutputRef("manifest")}),
        Call("publish", "store.commit", {"material": OutputRef("manifest")},
            {**{key: ParameterRef(key) for key in ("destination", "mode", "expected_revision", "source_revision")},
                "input_basis": OutputRef("basis")}),
    ), {"manifest": OutputRef("manifest"), "receipt": OutputRef("publish")}, required_effects=("publish",)),
        inputs={"receipts": next(item for item in commands() if item.capability_id == "stage.release.manifest").inputs["receipts"]},
        outputs={"manifest": REPRESENTATION, "receipt": RECEIPT}, parameters={"members": (), "input_versions": {},
            "member_versions": {}, "expected_members": {},
            "max_bytes": 32 * 1024 * 1024, "mode": "immutable", "expected_revision": None,
            "source_revision": None}, required_parameters=("release_id", "destination"),
        effects=frozenset({"storage.write"})))
    return tuple(operations)


def contribution():
    from stratbox.capabilities.catalog import ReferenceDefinition
    from stratbox.shared.reference.assets import load_reference
    references = []
    for package in ("geography", "banks", "okved2"):
        value = load_reference("stratbox.shared.reference." + package)
        references.append(ReferenceDefinition(value.edition.reference_id, value.edition.edition_id,
            value.snapshot_identity.sha256))
    return CatalogContribution(definitions=(*commands(), *definitions()), references=tuple(references))


def dispositions():
    """Semantic destinations for each neutral declaration in the admission baseline.

    Multiple targets describe independent reusable stages of one convenience
    route. All targets resolve through the same capability catalog and executor.
    """
    return {
        "dataset.list_versions": ("list.dataset_versions",),
        "dataset.query_snapshot": ("snapshot.query",),
        "dataset.read_snapshot": ("query.dataset",),
        "dataset.write_snapshot": ("ingest.observations",),
        "material.archive": ("archive.pack", "preserve.material"),
        "material.read_artifact": ("read.artifact",),
        "material.read_collection": ("material.collection.replay",),
        "material.read_location": ("read.material_location",),
        "material.save_artifact": ("save.artifact",),
        "material.serialize_collection": ("material.collection.snapshot",),
        "material.transfer": ("transfer.material",),
        "material.transfer_artifact": ("transfer.artifact",),
        "notifications.deliver": ("notify.required",),
        "notifications.prepare": ("notification.prepare_intents",),
        "notifications.qualify": ("qualify.notification",),
        "notifications.reconcile": ("notify.reconcile",),
        "document.extract": ("document.decode",),
        "document.readable": ("document.readable",),
        "document.replay": ("document.replay",),
        "document.snapshot": ("document.snapshot",),
        "observations.prepare_view": ("view.table",),
        "observations.render_view": ("render.table",),
        "observations.replay_view": ("view.replay",),
        "observations.view_snapshot": ("view.snapshot",),
        "processing.plan_update": ("processing.plan_update",),
        "workbook.compare": ("workbook.compare",),
        "workbook.extract": ("workbook.extract",),
        "workbook.readable": ("readable.workbook",),
        "workbook.replay": ("workbook.replay",),
        "workbook.snapshot": ("workbook.snapshot",),
        "source.compare_original_versions": ("compare.source_versions",),
        "source.read_original": ("read.material_reference",),
        "source.receive_original": ("acquire.material",),
        "source.receive_to_store": ("scenario.capture_original",),
        "source.reconcile_original": ("reconcile.material",),
        "source.save_original": ("preserve.material",),
    }
