"""Rosstat source contributions to the canonical callable hierarchy.

Physical capture, reviewed interpretation, integration and presentation retain
separate contracts. Scope describes admitted layouts rather than source cards.
"""
from __future__ import annotations

from dataclasses import replace

from stratbox.capabilities.catalog import (
    CatalogContribution, MethodDefinition, ProcessingGroup, ProfileDefinition, RecipeDefinition,
)
from stratbox.capabilities.model import (
    AcceptanceContract, Call, CollectCall, CommandDefinition, GraphBody, InputRef,
    OperationDefinition, OutputRef, ParameterRef, PortContract, ReuseContract, ScenarioDefinition,
)
from stratbox.shared.data.processing import DataContract, DataRole
from ._capability_specs import STAGES

_DEFAULTS = {
    "select": {"issue_ids": (), "asset_roles": ("primary",), "policy": "explicit", "max_assets": 20},
    "extract_workbook": {"container_identity": None, "member": None},
    "extract_document": {"container_identity": None, "member": None},
    "extract_kep2": {"duplicate_year_policy": "last_source_row", "required_indicators": (), "title_aliases": (), "unit_overrides": ()},
    "prepare_view": {"view_id": "rosstat.observations", "metric_ids": ()},
    "render_view": {"format": "csv"},
}
_SOURCES = (
    ("rosstat.socioeconomic_russia", "pdf", "rosstat.russia", "rosstat.scenario.document_product"),
    ("rosstat.socioeconomic_regions", "zip", "rosstat.regions", "rosstat.scenario.regional_workbook_product"),
    ("rosstat.short_term_indicators", "xlsx", "rosstat.short_term", "rosstat.scenario.kep2_product"),
    ("rosstat.population_municipalities", "xlsx", "rosstat.population", "rosstat.scenario.population_product"),
)


def _value_types():
    from stratbox.core.network import HttpRequest
    from stratbox.shared.evidence import SourcePayload, AcquiredSource
    from stratbox.shared.identity import ByteIdentity
    from stratbox.shared.data.workbooks import WorkbookExtract, WorkbookComparison
    from stratbox.shared.data.documents import DocumentExtract
    from stratbox.shared.data.snapshots import DatasetSnapshot
    from stratbox.shared.data.observations import ObservationBatch
    from stratbox.shared.data.views import ObservationView
    from stratbox.shared.data.representation import Representation
    from .tables.contracts import RosstatSourceFlake
    from .tables.comparison import FlakeComparison, FlakeValidation
    from .analytics.indicators import DatasetComparison
    from .integration.datasets import RosstatDataset
    from .publications.contracts import RosstatPublicationIndex, DiscoveredAsset, PublicationIndexDelta, AcquiredRosstatAsset, StoredRosstatAsset
    from .publications.archives import RegionalArchiveInventory
    return {"source.payload": SourcePayload, "rosstat.publications.index_material": SourcePayload,
        "rosstat.publications.index": RosstatPublicationIndex, "rosstat.publications.asset": DiscoveredAsset,
        "rosstat.publications.delta": PublicationIndexDelta, "rosstat.regional_archive.inventory": RegionalArchiveInventory,
        "workbook.cells.extract": WorkbookExtract, "workbook.changes": WorkbookComparison,
        "document.blocks.extract": DocumentExtract, "rosstat.source_flake": RosstatSourceFlake,
        "rosstat.integrated_dataset": RosstatDataset, "rosstat.flake.validation": FlakeValidation,
        "rosstat.flake.comparison": FlakeComparison, "rosstat.dataset.comparison": DatasetComparison,
        "observations.batch": ObservationBatch, "observations.prepared_view": ObservationView, "representation": Representation,
        "workbook.cells.snapshot": DatasetSnapshot, "document.blocks.snapshot": DatasetSnapshot,
        "rosstat.source_flake.snapshot": DatasetSnapshot, "rosstat.integrated_dataset.snapshot": DatasetSnapshot,
        "observations.prepared_view.snapshot": DatasetSnapshot, "dataset.snapshot": DatasetSnapshot,
        "rosstat.transfer.request": HttpRequest, "rosstat.acquired_source": AcquiredSource,
        "rosstat.publications.acquired": AcquiredRosstatAsset, "rosstat.publications.stored": StoredRosstatAsset,
        "material.identity": ByteIdentity, "archive.member_name": str}


def _port(schema, role=None, collection=False, required=True, outcomes=("succeeded",)):
    return PortContract(DataContract(schema, 1, DataRole(role) if role else None),
        value_type=tuple if collection else _value_types().get(schema, object),
        collection=collection, required=required, outcomes=frozenset(outcomes))


def _body(command, inputs, parameters, outputs):
    return GraphBody((Call("perform", command, {name: InputRef(name) for name in inputs},
        {name: ParameterRef(name) for name in parameters}),),
        {name: OutputRef("perform", name) for name in outputs})


def _stage_definitions():
    from stratbox.core.formats.archives.members import ArchiveLimits
    defaults = {**_DEFAULTS,
        "inspect_archive": {"limits": ArchiveLimits(packed_bytes=256*1024**2, unpacked_bytes=512*1024**2, member_bytes=128*1024**2)},
        "extract_members": {"limits": ArchiveLimits(packed_bytes=256*1024**2, unpacked_bytes=512*1024**2, member_bytes=128*1024**2)},
    }
    for capability_id, function, declared_inputs, declared_outputs, parameters, required, partial, summary in STAGES:
        inputs = {name: _port(schema, role, collection, is_required, outcomes)
            for name, schema, role, collection, is_required, outcomes in declared_inputs}
        for name, port in tuple(inputs.items()):
            if port.schema is not None and port.schema.schema_id.endswith(".snapshot"):
                inputs[name] = replace(port, alternatives=(DataContract("dataset.snapshot", 1),))
        # An exact supplied-index operation never has an implicit network fallback.
        if function == "discover":
            inputs["index"] = _port("rosstat.publications.index_material", "originals")
            function = "qualify_index"
        if function == "map_reviewed_cells":
            inputs["physical"] = PortContract(DataContract("workbook.cells.extract", 1, DataRole.EXTRACTS),
                outcomes=frozenset({"succeeded", "partial"}), alternatives=(DataContract("document.blocks.extract", 1, DataRole.EXTRACTS),))
        outputs = {name: _port(schema, role, collection, outcomes=outcomes) for name, schema, role, collection, outcomes in declared_outputs}
        command_id = "rosstat.command." + capability_id.removeprefix("rosstat.")
        command_defaults = defaults.get(function, {})
        command = CommandDefinition(command_id, "stratbox.domains.rosstat.commands:" + function,
            inputs=inputs, outputs=outputs, parameters=command_defaults,
            required_parameters=required, summary=summary,
            reuse=ReuseContract(shareable=False), acceptance=AcceptanceContract(partial_allowed=partial))
        operation = OperationDefinition(capability_id,
            None if function in {"extract_kep2", "map_reviewed_cells"} else _body(command_id, inputs, parameters, outputs),
            method_slot="interpretation" if function in {"extract_kep2", "map_reviewed_cells"} else None, inputs=inputs, outputs=outputs,
            parameters=command_defaults, required_parameters=required, summary=summary,
            acceptance=AcceptanceContract(partial_allowed=partial))
        yield command
        yield operation


def _reviewed_mapping_definitions():
    for kind in ("workbook", "document"):
        physical = _port("workbook.cells.extract" if kind == "workbook" else "document.blocks.extract", "extracts",
            outcomes=("succeeded", "partial"))
        flake = _port("rosstat.source_flake", "extracts", outcomes=("succeeded", "partial"))
        command_id = "rosstat.command.tables.map_" + kind + "_cells"
        operation_id = "rosstat.tables.map_" + kind + "_cells"
        yield CommandDefinition(command_id, "stratbox.domains.rosstat.commands:map_reviewed_cells",
            inputs={"physical": physical}, outputs={"flake": flake}, required_parameters=("profile",),
            acceptance=AcceptanceContract(partial_allowed=True), reuse=ReuseContract(shareable=False))
        yield OperationDefinition(operation_id, _body(command_id, {"physical": physical}, ("profile",), {"flake": flake}),
            inputs={"physical": physical}, outputs={"flake": flake}, required_parameters=("profile",),
            acceptance=AcceptanceContract(partial_allowed=True))


def _edition_definitions():
    for name, defaults in (("extract_population", {"selected_rows": ()}),
            ("extract_regional_industrial_indices", {"selected_rows": (), "selected_years": ()})):
        command_id = "rosstat.command.tables." + name
        inputs = {"workbook": _port("workbook.cells.extract", "extracts", outcomes=("succeeded", "partial"))}
        outputs = {"flake": _port("rosstat.source_flake", "extracts", outcomes=("succeeded", "partial"))}
        yield CommandDefinition(command_id, "stratbox.domains.rosstat.commands:" + name,
            inputs=inputs, outputs=outputs, parameters=defaults, reuse=ReuseContract(shareable=False),
            acceptance=AcceptanceContract(partial_allowed=True))
        yield OperationDefinition("rosstat.tables." + name, method_slot="interpretation", inputs=inputs, outputs=outputs,
            parameters=defaults, acceptance=AcceptanceContract(partial_allowed=True))


def _ingestion_definitions():
    from stratbox.capabilities.commands.stages import DATASET_REFERENCE
    command = CommandDefinition("rosstat.command.integration.ingest", "stratbox.core.capabilities.stages:dataset_ingest",
        inputs={"value": _port("rosstat.integrated_dataset.snapshot", "integrated")}, outputs={"reference": DATASET_REFERENCE},
        required_capabilities=frozenset({"dataset_writer"}), effects=frozenset({"dataset.write"}),
        reuse=ReuseContract(shareable=False, completed=False, effects=frozenset({"dataset.write"})))
    yield command
    yield OperationDefinition("rosstat.integration.ingest_dataset", GraphBody((
        Call("snapshot", "rosstat.command.integration.dataset_snapshot", {"dataset": InputRef("dataset")}),
        Call("ingest", command.id, {"value": OutputRef("snapshot", "snapshot")}),
    ), {"reference": OutputRef("ingest", "reference")}, required_effects=("ingest",)),
        inputs={"dataset": _port("rosstat.integrated_dataset", "integrated")}, outputs={"reference": DATASET_REFERENCE},
        effects=frozenset({"dataset.write"}))


def _acquisition_definitions():
    asset = _port("rosstat.publications.asset")
    request = _port("rosstat.transfer.request")
    original = _port("rosstat.acquired_source", "originals")
    payload = _port("source.payload", "originals")
    acquired = _port("rosstat.publications.acquired", "originals")
    stored = _port("rosstat.publications.stored", "originals")
    from stratbox.core.network import RetryPolicy
    parameters = {"max_bytes": 100 * 1024**2, "deadline_seconds": 120, "retry": RetryPolicy()}
    admit = CommandDefinition("rosstat.command.asset.admit", "stratbox.domains.rosstat.commands:admit_asset",
        inputs={"asset": asset}, outputs={"request": request}, parameters={key: parameters[key] for key in ("max_bytes", "deadline_seconds")})
    receive = CommandDefinition("rosstat.command.asset.receive", "stratbox.domains.rosstat.commands:receive_asset",
        inputs={"request": request, "asset": asset}, outputs={"original": original}, parameters={"retry": RetryPolicy()},
        effects=frozenset({"network.receive"}), required_capabilities=frozenset({"http"}),
        reuse=ReuseContract(shareable=False, deterministic=False, observation_scoped=True, effects=frozenset({"network.receive"})))
    verify = CommandDefinition("rosstat.command.asset.verify", "stratbox.domains.rosstat.commands:verify_envelope",
        inputs={"original": original, "asset": asset}, outputs={"payload": payload, "acquired": acquired})
    acquire = OperationDefinition("rosstat.publications.acquire", GraphBody((
        Call("admit", admit.id, {"asset": InputRef("asset")}, {name: ParameterRef(name) for name in ("max_bytes", "deadline_seconds")}),
        Call("receive", receive.id, {"request": OutputRef("admit", "request"), "asset": InputRef("asset")}, {"retry": ParameterRef("retry")}),
        Call("verify", verify.id, {"original": OutputRef("receive", "original"), "asset": InputRef("asset")}),
    ), {"payload": OutputRef("verify", "payload"), "acquired": OutputRef("verify", "acquired")}, required_checks=("verify",)),
        inputs={"asset": asset}, outputs={"payload": payload, "acquired": acquired}, parameters=parameters, effects=frozenset({"network.receive"}))
    transfer = CommandDefinition("rosstat.command.asset.transfer", "stratbox.domains.rosstat.commands:receive_to_store",
        inputs={"request": request, "asset": asset}, outputs={"stored": stored},
        parameters={"retry": RetryPolicy(), "baseline": None}, required_parameters=("destination",),
        effects=frozenset({"network.receive", "storage.write"}), required_capabilities=frozenset({"http", "output_filestore"}),
        reuse=ReuseContract(shareable=False, completed=False, effects=frozenset({"network.receive", "storage.write"})))
    preserve = OperationDefinition("rosstat.publications.preserve_original", GraphBody((
        Call("admit", admit.id, {"asset": InputRef("asset")}, {name: ParameterRef(name) for name in ("max_bytes", "deadline_seconds")}),
        Call("transfer", transfer.id, {"request": OutputRef("admit", "request"), "asset": InputRef("asset")},
            {name: ParameterRef(name) for name in ("retry", "baseline", "destination")}),
    ), {"stored": OutputRef("transfer", "stored")}, required_effects=("transfer",)),
        inputs={"asset": asset}, outputs={"stored": stored}, parameters={**parameters, "baseline": None}, required_parameters=("destination",),
        effects=frozenset({"network.receive", "storage.write"}))
    capture = ScenarioDefinition("rosstat.publications.acquire_to_store", GraphBody((
        Call("preserve", preserve.id, {"asset": InputRef("asset")},
            {name: ParameterRef(name) for name in (*parameters, "baseline", "destination")}),
    ), {"stored": OutputRef("preserve", "stored")}, required_effects=("preserve",)),
        inputs={"asset": asset}, outputs={"stored": stored}, parameters={**parameters, "baseline": None}, required_parameters=("destination",),
        effects=frozenset({"network.receive", "storage.write"}), purpose="Capture and verify one publisher original under an explicit storage obligation.")
    receive_index = CommandDefinition("rosstat.command.index.receive", "stratbox.domains.rosstat.commands:receive_index",
        outputs={"index": _port("rosstat.publications.index_material", "originals")}, required_parameters=("series_id",),
        effects=frozenset({"network.receive"}), required_capabilities=frozenset({"http"}),
        reuse=ReuseContract(shareable=False, deterministic=False, effects=frozenset({"network.receive"})))
    index_acquire = OperationDefinition("rosstat.publications.acquire_index", _body(receive_index.id, {}, ("series_id",), receive_index.outputs),
        outputs=receive_index.outputs, required_parameters=("series_id",), effects=frozenset({"network.receive"}))
    discover = ScenarioDefinition("rosstat.scenario.discover", GraphBody((
        Call("receive", index_acquire.id, parameters={"series_id": ParameterRef("series_id")}),
        Call("qualify", "rosstat.publications.discover", {"index": OutputRef("receive", "index")}, {"series_id": ParameterRef("series_id")}),
    ), {"index": OutputRef("qualify", "index")}), outputs={"index": _port("rosstat.publications.index")},
        required_parameters=("series_id",), effects=frozenset({"network.receive"}), purpose="Acquire one publisher page and independently qualify its issue/asset inventory.")
    return admit, receive, verify, acquire, transfer, preserve, capture, receive_index, index_acquire, discover


def _product_scenarios():
    payload = _port("source.payload", "originals")
    workbook = _port("workbook.cells.extract", "extracts")
    document = _port("document.blocks.extract", "extracts", outcomes=("succeeded", "partial"))
    flake = _port("rosstat.source_flake", "extracts", outcomes=("succeeded", "partial"))
    dataset = _port("rosstat.integrated_dataset", "integrated")
    view = _port("observations.prepared_view", "products")
    representation = _port("representation")
    for suffix, physical_id, physical_port, extract_id, defaults, required in (
        ("kep2", "rosstat.tables.extract_workbook", "workbook", "rosstat.tables.extract_kep2", {}, ()),
        ("population", "rosstat.tables.extract_workbook", "workbook", "rosstat.tables.extract_population", {"selected_rows": ()}, ()),
        ("workbook", "rosstat.tables.extract_workbook", "workbook", "rosstat.tables.map_workbook_cells", {"container_identity": None, "member": None}, ("profile",)),
        ("document", "rosstat.tables.extract_document", "document", "rosstat.tables.map_document_cells", {}, ("profile", "layout")),
    ):
        steps = [Call("physical", physical_id, {"payload": InputRef("payload")},
            {name: ParameterRef(name) for name in ("series_id", "issue_id", "asset_id", "container_identity", "member")})]
        source = OutputRef("physical", physical_port)
        if suffix == "document":
            steps.append(Call("structure", "rosstat.tables.structure_document", {"document": source}, {"layout": ParameterRef("layout")}))
            source = OutputRef("structure", "document")
        extract_inputs = {"workbook" if suffix in {"kep2", "population"} else "physical": source}
        extract_parameters = ({"selected_rows": ParameterRef("selected_rows")} if suffix == "population" else {} if suffix == "kep2" else {"profile": ParameterRef("profile")})
        steps.append(Call("extract", extract_id, extract_inputs, extract_parameters))
        extract_outputs = {physical_port: source, "flake": OutputRef("extract", "flake")}
        yield ScenarioDefinition("rosstat.scenario." + suffix + "_extract", GraphBody(tuple(steps), extract_outputs),
            inputs={"payload": payload}, outputs={physical_port: workbook if physical_port == "workbook" else document, "flake": flake},
            parameters={"container_identity": None, "member": None, **defaults},
            required_parameters=("series_id", "issue_id", "asset_id", *required),
            acceptance=AcceptanceContract(partial_allowed=True), purpose="Capture physical evidence and interpret exactly the reviewed source scope.")
        steps.extend((
            CollectCall("flakes", (OutputRef("extract", "flake"),),
                _port("rosstat.source_flake", "extracts", collection=True), flake),
            Call("integrate", "rosstat.integration.integrate", {"flakes": OutputRef("flakes")},
                {"dataset_id": ParameterRef("dataset_id"), "release_id": ParameterRef("release_id")}),
            Call("view", "rosstat.products.prepare_view", {"dataset": OutputRef("integrate", "dataset")}),
            Call("render", "rosstat.products.render_view", {"view": OutputRef("view", "view")}, {"format": ParameterRef("format")}),
        ))
        outputs = {physical_port: source, "flake": OutputRef("extract", "flake"), "dataset": OutputRef("integrate", "dataset"),
            "view": OutputRef("view", "view"), "representation": OutputRef("render", "representation")}
        yield ScenarioDefinition("rosstat.scenario." + suffix + "_product", GraphBody(tuple(steps), outputs), inputs={"payload": payload},
            outputs={physical_port: workbook if physical_port == "workbook" else document, "flake": flake, "dataset": dataset, "view": view, "representation": representation},
            parameters={"container_identity": None, "member": None, "format": "csv", **defaults},
            required_parameters=("series_id", "issue_id", "asset_id", "dataset_id", "release_id", *required),
            purpose="Prepare independently retained physical, source, integrated and product values for the exact admitted source scope.",
            acceptance=AcceptanceContract(partial_allowed=True))
    yield ScenarioDefinition("rosstat.scenario.kep2_monthly", GraphBody((
        Call("view", "rosstat.products.prepare_kep2_monthly", {"dataset": InputRef("dataset")}),
        Call("render", "rosstat.products.render_kep2_xlsx", {"view": OutputRef("view", "view")}),
    ), {"view": OutputRef("view", "view"), "representation": OutputRef("render", "representation")}),
        inputs={"dataset": dataset}, outputs={"view": view, "representation": representation},
        purpose="Render the KEP2 monthly workbook from a retained integrated dataset without reacquiring a source.")


def _regional_scenarios():
    """Container, member and physical interpretations remain independent steps."""
    from stratbox.core.formats.archives.members import ArchiveLimits
    members = _port("rosstat.regional_archive.members", "originals", collection=True)
    payload = _port("source.payload", "originals")
    selected = {"payload": payload, "container_identity": _port("material.identity"), "member": _port("archive.member_name")}
    choose = CommandDefinition("rosstat.command.member.select", "stratbox.domains.rosstat.commands:select_member",
        inputs={"members": members}, outputs=selected, required_parameters=("name",))
    project = OperationDefinition("rosstat.publications.select_member", _body(choose.id, choose.inputs, ("name",), selected),
        inputs=choose.inputs, outputs=selected, required_parameters=("name",))
    yield choose
    yield project
    defaults = {"limits": ArchiveLimits(packed_bytes=256*1024**2, unpacked_bytes=512*1024**2, member_bytes=128*1024**2)}
    for kind in ("workbook", "document"):
        port = _port("workbook.cells.extract" if kind == "workbook" else "document.blocks.extract", "extracts",
            outcomes=("succeeded", "partial") if kind == "document" else ("succeeded",))
        flake = _port("rosstat.source_flake", "extracts", outcomes=("succeeded", "partial"))
        steps = [
            Call("inventory", "rosstat.publications.inspect_archive", {"payload": InputRef("payload")}, {"limits": ParameterRef("limits")}),
            Call("members", "rosstat.publications.extract_members", {"payload": InputRef("payload"), "inventory": OutputRef("inventory", "inventory")},
                {"names": (ParameterRef("member"),), "limits": ParameterRef("limits")}),
            Call("member", project.id, {"members": OutputRef("members", "members")}, {"name": ParameterRef("member")}),
            Call("physical", "rosstat.tables.extract_" + kind, {"payload": OutputRef("member", "payload")},
                {"series_id": ParameterRef("series_id"), "issue_id": ParameterRef("issue_id"), "asset_id": ParameterRef("asset_id"),
                 "container_identity": OutputRef("member", "container_identity"), "member": OutputRef("member", "member")}),
        ]
        physical = OutputRef("physical", kind)
        if kind == "document":
            steps.append(Call("structure", "rosstat.tables.structure_document", {"document": physical}, {"layout": ParameterRef("layout")}))
            physical = OutputRef("structure", "document")
        steps.append(Call("extract", "rosstat.tables.map_" + kind + "_cells", {"physical": physical}, {"profile": ParameterRef("profile")}))
        outputs = {kind: physical, "flake": OutputRef("extract", "flake")}
        ports = {kind: port, "flake": flake}
        required = ("series_id", "issue_id", "asset_id", "member", "profile", *(("layout",) if kind == "document" else ()))
        yield ScenarioDefinition("rosstat.scenario.regional_" + kind + "_extract", GraphBody(tuple(steps), outputs),
            inputs={"payload": payload}, outputs=ports, parameters=defaults, required_parameters=required,
            acceptance=AcceptanceContract(partial_allowed=True), purpose="Interpret an explicitly selected regional archive member with container evidence.")
        steps.extend((
            CollectCall("flakes", (OutputRef("extract", "flake"),), _port("rosstat.source_flake", "extracts", collection=True), flake),
            Call("integrate", "rosstat.integration.integrate", {"flakes": OutputRef("flakes")},
                {"dataset_id": ParameterRef("dataset_id"), "release_id": ParameterRef("release_id")}),
            Call("view", "rosstat.products.prepare_view", {"dataset": OutputRef("integrate", "dataset")}),
            Call("render", "rosstat.products.render_view", {"view": OutputRef("view", "view")}, {"format": ParameterRef("format")}),
        ))
        yield ScenarioDefinition("rosstat.scenario.regional_" + kind + "_product", GraphBody(tuple(steps),
            {**outputs, "dataset": OutputRef("integrate", "dataset"), "view": OutputRef("view", "view"), "representation": OutputRef("render", "representation")}),
            inputs={"payload": payload}, outputs={**ports, "dataset": _port("rosstat.integrated_dataset", "integrated"),
                "view": _port("observations.prepared_view", "products"), "representation": _port("representation")},
            parameters={**defaults, "format": "csv"}, required_parameters=(*required, "dataset_id", "release_id"),
            acceptance=AcceptanceContract(partial_allowed=True), purpose="Prepare a product from one explicitly reviewed regional archive member.")


def _industrial_scenarios():
    for definition in _regional_scenarios():
        if not definition.id.startswith("rosstat.scenario.regional_workbook_"):
            continue
        steps = tuple(replace(step, capability_id="rosstat.tables.extract_regional_industrial_indices",
            inputs={"workbook": OutputRef("physical", "workbook")},
            parameters={"selected_rows": ParameterRef("selected_rows"), "selected_years": ParameterRef("selected_years")})
            if isinstance(step, Call) and step.step_id == "extract" else step for step in definition.body.steps)
        yield replace(definition, capability_id=definition.id.replace("regional_workbook", "regional_industrial"),
            body=replace(definition.body, steps=steps),
            parameters={**definition.parameters, "selected_rows": (), "selected_years": ()},
            required_parameters=tuple(name for name in definition.required_parameters if name != "profile"),
            purpose="Interpret the reviewed industrial index archive member with separate monthly and cumulative comparison bases.")


def contribution():
    """Load metadata only; publisher backends activate on command invocation."""
    from stratbox.core.resources import iter_resources, read_document
    profiles = []
    for resource in iter_resources("rosstat", "profiles"):
        profile = read_document(resource)
        declaration = profile["declaration"]
        profiles.append(ProfileDefinition(profile["profile_id"], declaration,
            revision=str(declaration.get("version", 1))))
    groups, methods, recipes = [], [], []
    operations = (*_stage_definitions(), *_edition_definitions())
    for operation_id, method_id in (("rosstat.tables.extract_kep2", "rosstat.kep2.interpret"), ("rosstat.tables.map_reviewed_cells", "rosstat.reviewed_cells.interpret"),
            ("rosstat.tables.extract_population", "rosstat.population.bulletin.interpret"), ("rosstat.tables.extract_regional_industrial_indices", "rosstat.regional.industrial.interpret")):
        operation = next(item for item in operations if item.id == operation_id)
        command_id = "rosstat.command." + operation_id.removeprefix("rosstat.")
        command = next(item for item in operations if item.id == command_id)
        methods.append(MethodDefinition(method_id, operation_id, _body(command_id, operation.inputs, (*command.parameters, *command.required_parameters), operation.outputs)))
    for source_id, representation, group_id, scenario in _SOURCES:
        operation_id = ("rosstat.tables.extract_kep2" if source_id == "rosstat.short_term_indicators" else
            "rosstat.tables.extract_population" if source_id == "rosstat.population_municipalities" else "rosstat.tables.map_reviewed_cells")
        operation = next(item for item in operations if item.id == operation_id)
        method_id = group_id + ".interpret"
        command_id = "rosstat.command." + operation_id.removeprefix("rosstat.")
        command = next(item for item in operations if item.id == command_id)
        body = _body(command_id, operation.inputs, (*command.parameters, *command.required_parameters), operation.outputs)
        methods.append(MethodDefinition(method_id, operation_id, body, group_ids=(group_id,), priority=1))
        formats = ("zip", "rar") if source_id == "rosstat.socioeconomic_regions" else (representation,)
        group_methods = {operation_id: method_id}
        group_profiles = {}
        if source_id == "rosstat.population_municipalities":
            group_profiles[operation_id] = "rosstat.population.bulletin"
        if source_id == "rosstat.socioeconomic_regions":
            group_methods["rosstat.tables.extract_regional_industrial_indices"] = "rosstat.regional.industrial.interpret"
            group_profiles["rosstat.tables.extract_regional_industrial_indices"] = "rosstat.regional.industrial_indices"
        groups.append(ProcessingGroup(group_id, source_ids=(source_id,), representations=formats,
            methods=group_methods, profiles=group_profiles))
        for format_name in formats:
            for goal, target in (("source.extract", scenario.removesuffix("_product") + "_extract"), ("source.product", scenario),
                    ("source.original", "rosstat.publications.acquire"), ("source.capture", "rosstat.publications.acquire_to_store")):
                recipes.append(RecipeDefinition(group_id + "." + format_name + "." + goal,
                    goal, target, selection={"source_id": source_id, "representation": format_name},
                    defaults={"series_id": source_id} if goal in {"source.extract", "source.product"} else {}))
    profiles.extend((
        ProfileDefinition("rosstat.population.bulletin", {"layout_editions": ("2022", "2023", "2024"),
            "native_geography": "Names-only source rows in2022/2023; TERSON-MO source codes in2024; canonical municipal crosswalk is explicit."},
            method_id="rosstat.population.interpret", group_id="rosstat.population"),
        ProfileDefinition("rosstat.regional.industrial_indices", {"layout_editions": ("2026-06", "2026-08"),
            "comparison_bases": ("monthly_yoy", "ytd_yoy", "previous_month")},
            method_id="rosstat.regional.industrial.interpret", group_id="rosstat.regions"),
    ))
    for representation in ("zip", "rar"):
        for goal, suffix in (("source.extract", "extract"), ("source.product", "product")):
            recipes.append(RecipeDefinition("rosstat.regions.industrial." + representation + "." + suffix, goal,
                "rosstat.scenario.regional_industrial_" + suffix, priority=10,
                selection={"source_id": "rosstat.socioeconomic_regions", "representation": representation, "table_id": "industrial_production"},
                defaults={"series_id": "rosstat.socioeconomic_regions"}))
    return CatalogContribution(definitions=(*operations, *_reviewed_mapping_definitions(), *_ingestion_definitions(), *_acquisition_definitions(), *_product_scenarios(), *_regional_scenarios(), *_industrial_scenarios()),
        methods=tuple(methods), groups=tuple(groups), profiles=tuple(profiles), recipes=tuple(recipes))


def dispositions():
    """Every domain callable has one canonical functional destination."""
    return tuple({"operation_id": identifier, "capability_id": identifier, "kind": "operation", "status": "implemented"}
        for identifier, *_ in STAGES) + (
        {"operation_id": "rosstat.publications.acquire", "capability_id": "rosstat.publications.acquire", "kind": "operation", "status": "implemented"},
        {"operation_id": "rosstat.publications.acquire_to_store", "capability_id": "rosstat.publications.acquire_to_store", "kind": "scenario", "status": "implemented"},
    )


def stage_matrix():
    """Concrete routes distinguish implemented mechanisms from reviewed editions."""
    result = []
    for source_id, representation, group_id, scenario in _SOURCES:
        kep2 = source_id == "rosstat.short_term_indicators"
        document = source_id == "rosstat.socioeconomic_russia"
        bindings = {
            "discover": "rosstat.scenario.discover", "acquire": "rosstat.publications.acquire",
            "preserve": "rosstat.publications.acquire_to_store", "readable": "rosstat.tables.readable_document" if document else "rosstat.tables.readable_workbook",
            "extract": "rosstat.tables.extract_kep2" if kep2 else "rosstat.tables.extract_population" if source_id == "rosstat.population_municipalities" else "rosstat.tables.map_reviewed_cells",
            "validate": "rosstat.tables.validate_flake", "compare": "rosstat.analytics.compare_datasets",
            "integrate": "rosstat.integration.integrate", "calculate": "rosstat.analytics.derive_index_growth",
            "view": "rosstat.products.prepare_view", "render": "rosstat.products.render_view",
            "read_extract": "rosstat.tables.read_flake", "inspect": "rosstat.tables.extract_document" if document else "rosstat.tables.extract_workbook",
            "ingest": "rosstat.integration.ingest_dataset",
            "snapshot": "rosstat.integration.dataset_snapshot", "restore": "rosstat.integration.read_dataset",
            "save": "save.product", "publish": "publish.release",
        }
        for stage, capability_id in bindings.items():
            result.append({"source_id": source_id, "group_id": group_id, "stage": stage,
                "capability_id": capability_id, "implementation": "direct" if stage == "extract" else "shared",
                "scope": ("reviewed eleven-indicator KEP2 layout v1" if kep2 else "reviewed2022/2023/2024population bulletin layouts" if source_id == "rosstat.population_municipalities" else "reviewed2026-06/08 industrial-index member or exact-original reviewed mapping" if source_id == "rosstat.socioeconomic_regions" else "exact-original reviewed document profile"),
                "edition_verification": ("deterministic layout fixtures" if kep2 else "checksummed publisher-original physical excerpts" if source_id in {"rosstat.population_municipalities", "rosstat.socioeconomic_regions"} else "explicit caller review required; original publisher PDF unavailable during verification"),
                "applicability": "indices only" if stage == "calculate" else "declared source scope"})
    return tuple(result)
