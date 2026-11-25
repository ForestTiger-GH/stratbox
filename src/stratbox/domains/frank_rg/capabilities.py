"""Typed report capabilities with visible physical and semantic boundaries.

Metadata imports do not load spreadsheet backends. Publisher delivery profiles
remain declarative resources; only technical work functions execute commands.
"""
from __future__ import annotations

from functools import lru_cache

from stratbox.capabilities.catalog import CatalogContribution, MethodDefinition, ProcessingGroup, ProfileDefinition, RecipeDefinition
from stratbox.capabilities.model import (AcceptanceContract, CommandDefinition, OperationDefinition,
    ScenarioDefinition, GraphBody, Call, InputRef, OutputRef, ParameterRef, PortContract, ReuseContract)
from stratbox.shared.data.processing import DataContract, DataRole

_REQUESTS = {'frg.acquire': 'stratbox.domains.frank_rg.publications.contracts:AcquireRequest',
 'frg.align': 'stratbox.domains.frank_rg.integration.contracts:AlignRequest',
 'frg.apply_cleanup': 'stratbox.domains.frank_rg.publications.cleanup:ApplyCleanupRequest',
 'frg.assess_material': 'stratbox.domains.frank_rg.publications.contracts:AssessMaterialRequest',
 'frg.build_flake': 'stratbox.domains.frank_rg.tables.contracts:BuildFlakeRequest',
 'frg.build_history': 'stratbox.domains.frank_rg.integration.contracts:HistoryRequest',
 'frg.calculate': 'stratbox.domains.frank_rg.analytics.contracts:CalculateRequest',
 'frg.capture': 'stratbox.domains.frank_rg.publications.contracts:CaptureRequest',
 'frg.compare': 'stratbox.domains.frank_rg.tables.contracts:CompareExtractRequest',
 'frg.discover': 'stratbox.domains.frank_rg.publications.contracts:DiscoveryRequest',
 'frg.extract': 'stratbox.domains.frank_rg.tables.contracts:ExtractRequest',
 'frg.extract_snapshot': 'stratbox.domains.frank_rg.tables.contracts:ExtractSnapshotRequest',
 'frg.flake_snapshot': 'stratbox.domains.frank_rg.tables.contracts:FlakeSnapshotRequest',
 'frg.inspect': 'stratbox.domains.frank_rg.publications.contracts:InspectionRequest',
 'frg.integrate': 'stratbox.domains.frank_rg.integration.contracts:IntegrateRequest',
 'frg.observation_snapshot': 'stratbox.domains.frank_rg.integration.contracts:ObservationSnapshotRequest',
 'frg.plan_cleanup': 'stratbox.domains.frank_rg.publications.cleanup:PlanCleanupRequest',
 'frg.plan_updates': 'stratbox.domains.frank_rg.publications.contracts:UpdateRequest',
 'frg.prepare_archive': 'stratbox.domains.frank_rg.publications.cleanup:CleanupPlan',
 'frg.prepare_archive_to_store': 'stratbox.domains.frank_rg.operations.housekeeping_definitions:StreamArchiveRequest',
 'frg.prepare_file': 'stratbox.domains.frank_rg.publications.contracts:PrepareFileRequest',
 'frg.prepare_view': 'stratbox.domains.frank_rg.products.contracts:PrepareViewRequest',
 'frg.read_extract': 'stratbox.domains.frank_rg.tables.contracts:ReadExtractRequest',
 'frg.read_flake': 'stratbox.domains.frank_rg.tables.contracts:ReadFlakeRequest',
 'frg.read_observations': 'stratbox.domains.frank_rg.integration.contracts:ReadObservationsRequest',
 'frg.read_view': 'stratbox.domains.frank_rg.products.contracts:ReadViewRequest',
 'frg.readable': 'stratbox.domains.frank_rg.tables.contracts:ReadableRequest',
 'frg.render_view': 'stratbox.domains.frank_rg.products.contracts:RenderViewRequest',
 'frg.scan': 'stratbox.domains.frank_rg.publications.contracts:DiscoveryRequest',
 'frg.select': 'stratbox.domains.frank_rg.publications.contracts:SelectionRequest',
 'frg.validate': 'stratbox.domains.frank_rg.tables.contracts:ValidateExtractRequest',
 'frg.view_snapshot': 'stratbox.domains.frank_rg.products.contracts:ViewSnapshotRequest'}
_DEFAULTS = {'frg.acquire': {'expected_identity': None, 'max_bytes': 67108864},
 'frg.align': {},
 'frg.apply_cleanup': {},
 'frg.assess_material': {'checkpoint': None},
 'frg.build_flake': {},
 'frg.build_history': {},
 'frg.calculate': {},
 'frg.capture': {},
 'frg.compare': {},
 'frg.discover': {'family_ids': (), 'recursive': False},
 'frg.extract': {},
 'frg.extract_snapshot': {'dataset_id': None, 'version_id': None},
 'frg.flake_snapshot': {'dataset_id': None, 'version_id': None},
 'frg.inspect': {},
 'frg.integrate': {},
 'frg.observation_snapshot': {'dataset_id': None, 'version_id': None},
 'frg.plan_cleanup': {'delete_others': False},
 'frg.plan_updates': {'checkpoints': (), 'force_refresh': False},
 'frg.prepare_archive': {},
 'frg.prepare_archive_to_store': {'compression': 'stored',
                                  'expected_revision': None,
                                  'mode': 'immutable',
                                  'report_json': None},
 'frg.prepare_file': {},
 'frg.prepare_view': {'metric_ids': (), 'period_kinds': (), 'subject_ids': ()},
 'frg.read_extract': {},
 'frg.read_flake': {},
 'frg.read_observations': {},
 'frg.read_view': {},
 'frg.readable': {},
 'frg.render_view': {'format': 'csv'},
 'frg.scan': {'family_ids': (), 'recursive': False},
 'frg.select': {'selected_sources': ()},
 'frg.validate': {},
 'frg.view_snapshot': {'dataset_id': None, 'version_id': None}}
_REQUIRED = {'frg.acquire': ['asset'],
 'frg.align': ['batches', 'dataset_id', 'release_id'],
 'frg.apply_cleanup': ['plan', 'authorized_directory', 'expected_sha256'],
 'frg.assess_material': ['report'],
 'frg.build_flake': ['extract', 'profile'],
 'frg.build_history': ['batches', 'dataset_id', 'release_id'],
 'frg.calculate': ['before', 'after', 'dataset_id', 'release_id'],
 'frg.capture': ['source_id', 'period', 'payload', 'format'],
 'frg.compare': ['before', 'after'],
 'frg.discover': ['directory'],
 'frg.extract': ['report'],
 'frg.extract_snapshot': ['extract'],
 'frg.flake_snapshot': ['flake'],
 'frg.inspect': ['index'],
 'frg.integrate': ['flake', 'dataset_id', 'release_id'],
 'frg.observation_snapshot': ['batch'],
 'frg.plan_cleanup': ['directory'],
 'frg.plan_updates': ['catalog'],
 'frg.prepare_archive': ['request',
                         'actions',
                         'directory_identity',
                         'identity'],
 'frg.prepare_archive_to_store': ['plan', 'destination'],
 'frg.prepare_file': ['report'],
 'frg.prepare_view': ['batch', 'view_id'],
 'frg.read_extract': ['snapshot'],
 'frg.read_flake': ['snapshot'],
 'frg.read_observations': ['snapshot'],
 'frg.read_view': ['snapshot'],
 'frg.readable': ['extract'],
 'frg.render_view': ['view'],
 'frg.scan': ['directory'],
 'frg.select': ['inventory'],
 'frg.validate': ['extract'],
 'frg.view_snapshot': ['view']}

@lru_cache(maxsize=1)
def _documents():
    from stratbox.operations.declarations import operation_documents
    from stratbox.capabilities.model.graph import frozen_mapping
    return tuple(frozen_mapping(item) for item in operation_documents("frank_rg"))


def metadata(operation_id):
    """Return inert technical request and projection coordinates."""
    for document in _documents():
        definition = document["definition"]
        if definition["operation_id"] == operation_id:
            return definition
    raise ValueError("frg.capability.unavailable")


def _port(value, *, input=False):
    schema = value["contract"]
    snapshot_input = input and schema["schema_id"] in {
        "workbook.cells.snapshot", "frg.flake.snapshot", "observations.batch.snapshot",
        "observations.prepared_view.snapshot"}
    return PortContract(DataContract(schema["schema_id"], schema.get("version", 1),
        DataRole(schema["role"]) if schema.get("role") else None),
        qualifications=frozenset(value.get("qualifications", ())),
        expected_coverage=frozenset(value.get("coverage", ())),
        collection=value.get("collection", False), required=value.get("required", True),
        alternatives=(DataContract("dataset.snapshot"),) if snapshot_input else ())


def _contracts(definition):
    processing = definition.get("processing", {})
    inputs = {item["name"]: _port(item, input=True) for item in processing.get("inputs", ())}
    outputs = {item["name"]: _port(item) for item in processing.get("outputs", ())}
    fields = {item.get("path", item["name"]).split(".", 1)[0] for item in processing.get("inputs", ())}
    if "" in fields:
        fields = set(_REQUIRED[definition["operation_id"]]) | set(_DEFAULTS[definition["operation_id"]])
    defaults = {key: value for key, value in _DEFAULTS[definition["operation_id"]].items() if key not in fields}
    required = tuple(key for key in _REQUIRED[definition["operation_id"]] if key not in fields)
    return inputs, outputs, defaults, required


def contribution():
    """Contribute all report stages and all fourteen logical source bindings."""
    from stratbox.domains.registry.declarations import source_documents, profile_document
    definitions, methods, profiles, groups, recipes = [], [], [], [], []
    descriptors = {}
    for document in _documents():
        d = document["definition"]
        identifier = d["operation_id"]
        inputs, outputs, defaults, required = _contracts(d)
        descriptors[identifier] = (inputs, outputs, defaults, required)
        if identifier == "frg.scan":
            continue
        effects = frozenset(d.get("possible_effects", ()))
        command_id = identifier + ".command"
        acceptance = AcceptanceContract(coherent_outputs=tuple(outputs), partial_allowed=d.get("partial_allowed", False))
        definitions.append(CommandDefinition(command_id,
            "stratbox.domains.frank_rg.commands:" + identifier.split(".", 1)[1],
            inputs=inputs, outputs=outputs, parameters=defaults, required_parameters=required,
            required_capabilities=frozenset(d.get("required_capabilities", ())), effects=effects,
            acceptance=acceptance, reuse=(ReuseContract(shareable=False)
                if effects or identifier in {"frg.discover", "frg.acquire", "frg.plan_cleanup", "frg.prepare_archive"}
                else ReuseContract(mutation="immutable"))))
        body = GraphBody((Call("work", command_id,
            {name: InputRef(name) for name in inputs},
            {name: ParameterRef(name) for name in (*defaults, *required)}),),
            {name: OutputRef("work", name) for name in outputs},
            required_effects=("work",) if effects else ())
        definitions.append(OperationDefinition(identifier, method_slot="technical",
            inputs=inputs, outputs=outputs, parameters=defaults, required_parameters=required,
            effects=effects, acceptance=acceptance, summary=d.get("processing", {}).get("summary", identifier)))
        methods.append(MethodDefinition(identifier + ".method", identifier, body))
    # A catalog is genuinely a composition: the three independently callable
    # stages retain their own outputs and acceptance boundaries.
    scan_inputs, scan_outputs, scan_defaults, scan_required = descriptors["frg.scan"]
    catalog_port = scan_outputs["catalog"]
    definitions.append(CommandDefinition("frg.catalog.compose.command", "stratbox.domains.frank_rg.commands:compose_catalog",
        inputs={"inventory": scan_outputs["inventory"], "selections": scan_outputs["selections"]},
        outputs={"catalog": catalog_port}, reuse=ReuseContract(shareable=False)))
    definitions.append(OperationDefinition("frg.catalog.compose", GraphBody((
        Call("compose", "frg.catalog.compose.command", {"inventory": InputRef("inventory"), "selections": InputRef("selections")}),
    ), {"catalog": OutputRef("compose", "catalog")}),
        inputs={"inventory": scan_outputs["inventory"], "selections": scan_outputs["selections"]},
        outputs={"catalog": catalog_port}))
    definitions.append(ScenarioDefinition("frg.scan", GraphBody((
        Call("discover", "frg.discover", parameters={name: ParameterRef(name) for name in (*scan_defaults, *scan_required)}),
        Call("inspect", "frg.inspect", {"index": OutputRef("discover", "index")}),
        Call("select", "frg.select", {"inventory": OutputRef("inspect", "inventory")}),
        Call("catalog", "frg.catalog.compose", {"inventory": OutputRef("inspect", "inventory"),
            "selections": OutputRef("select", "selections")}),
    ), {"catalog": OutputRef("catalog", "catalog"), "index": OutputRef("discover", "index"),
        "inventory": OutputRef("inspect", "inventory"), "selections": OutputRef("select", "selections")}),
        inputs=scan_inputs, outputs=scan_outputs, parameters=scan_defaults, required_parameters=scan_required,
        purpose="Discover delivery files, identify logical reports and select periods without changing storage."))
    report_input = descriptors["frg.extract"][0]["report"]
    profile_input = descriptors["frg.build_flake"][0]["profile"]
    product_output = descriptors["frg.render_view"][1]["value"]
    layout_input = PortContract(DataContract("frg.layout_profile", 1))
    definitions.append(CommandDefinition("frg.bind_layout.command", "stratbox.domains.frank_rg.commands:bind_reviewed_layout",
        inputs={"extract": descriptors["frg.build_flake"][0]["extract"], "layout": layout_input},
        outputs={"profile": profile_input}, required_parameters=("periods",), reuse=ReuseContract(shareable=False)))
    definitions.append(OperationDefinition("frg.bind_layout", GraphBody((
        Call("bind", "frg.bind_layout.command", {"extract": InputRef("extract"), "layout": InputRef("layout")},
            {"periods": ParameterRef("periods")}),
    ), {"profile": OutputRef("bind", "profile")}),
        inputs={"extract": descriptors["frg.build_flake"][0]["extract"], "layout": layout_input},
        outputs={"profile": profile_input}, required_parameters=("periods",)))
    definitions.append(ScenarioDefinition("frg.report.product", GraphBody((
        Call("extract", "frg.extract", {"report": InputRef("report")}),
        Call("interpret", "frg.build_flake", {"extract": OutputRef("extract"), "profile": InputRef("profile")}),
        Call("integrate", "frg.integrate", {"flake": OutputRef("interpret")},
            {"dataset_id": ParameterRef("dataset_id"), "release_id": ParameterRef("release_id")}),
        Call("view", "frg.prepare_view", {"batch": OutputRef("integrate")}, {"view_id": ParameterRef("view_id")}),
        Call("render", "frg.render_view", {"view": OutputRef("view")}, {"format": ParameterRef("format")}),
    ), {"extract": OutputRef("extract"), "flake": OutputRef("interpret"), "observations": OutputRef("integrate"),
        "view": OutputRef("view"), "representation": OutputRef("render")}),
        inputs={"report": report_input, "profile": profile_input},
        outputs={"extract": descriptors["frg.extract"][1]["value"], "flake": descriptors["frg.build_flake"][1]["value"],
            "observations": descriptors["frg.integrate"][1]["value"], "view": descriptors["frg.prepare_view"][1]["value"],
            "representation": product_output}, parameters={"format": "csv"},
        required_parameters=("dataset_id", "release_id", "view_id"),
        purpose="Build a product from an explicitly qualified semantic profile, retaining independent physical evidence."))
    sources = source_documents("frank_rg")
    profile_ids = sorted({key for item in sources for key in item["processing"]["profiles"]})
    for profile_id in profile_ids:
        profile = profile_document("frank_rg", profile_id)
        profiles.append(ProfileDefinition(profile_id, profile["declaration"]))
    bindings = {identifier: identifier + ".method" for identifier in descriptors if identifier != "frg.scan"}
    for source in sources:
        source_id = source["series_id"]
        groups.append(ProcessingGroup(source_id + ".reported_metrics", source_ids=(source_id,),
            representations=tuple(source["formats"]), methods=bindings))
        recipes.extend((RecipeDefinition(source_id + ".extract.recipe", "source.extract", "frg.extract",
            selection={"source_id": source_id}), RecipeDefinition(source_id + ".product.recipe", "source.product", "frg.report.product",
            selection={"source_id": source_id})))
    return CatalogContribution(tuple(definitions), tuple(methods), tuple(profiles), tuple(groups), tuple(recipes))


def dispositions():
    """Exact callable dispositions; technical streaming commit is an operation."""
    return tuple({"operation_id": item["definition"]["operation_id"],
        "capability_id": item["definition"]["operation_id"],
        "kind": "scenario" if item["definition"]["operation_id"] == "frg.scan" else "operation",
        "status": "canonical", "implementation": "technical_work_without_nested_runner"} for item in _documents())


def stage_matrix():
    from .publications.catalog import all_sources
    stages = {"discover": "frg.discover", "inspect": "frg.inspect", "acquire": "frg.acquire", "capture": "frg.capture",
        "readable": "frg.readable", "extract": "frg.extract", "interpret": "frg.build_flake", "validate": "frg.validate",
        "compare": "frg.compare", "plan": "frg.plan_updates", "integrate": "frg.integrate", "align": "frg.align",
        "history": "frg.build_history", "calculate": "frg.calculate", "view": "frg.prepare_view", "render": "frg.render_view",
        "snapshot": "frg.flake_snapshot", "restore": "frg.read_flake"}
    stages.update({
        "preserve": {"kind": "shared", "capability_id": "preserve.material",
            "input": "frg.acquire.payload or frg.capture.payload",
            "scope": "unchanged_original_bytes_with_explicit_destination_and_confirmed_receipt"},
        "read_extract": {"kind": "direct", "capability_id": "frg.read_extract",
            "input": "frg.extract_snapshot.snapshot",
            "scope": "complete_source_qualified_physical_workbook_evidence"},
        "ingest": {"kind": "shared", "capability_id": "ingest.observations",
            "input": "frg.integrate.value or frg.align.value or frg.build_history.value or frg.calculate.value",
            "prerequisites": ("frg.build_flake", "frg.integrate"),
            "scope": "ObservationBatch encoded_by_common_semantic_snapshot_then_immutable_dataset_provider_write"},
        "publish": {"kind": "shared", "capability_id": "publish.release",
            "input": "tuple_of_confirmed_preserve.material_receipts",
            "prerequisites": ("frg.report.product", "preserve.material"),
            "scope": "rendered_product_bytes_are_preserved_before_a_coherent_release_manifest_is_conditionally_committed"},
    })
    return tuple({"source_id": source_id, "group_id": source_id + ".reported_metrics",
        "stages": stages.copy(), "semantic_scope": "explicit_byte_bound_profile",
        "publisher_layout_evidence": "required", "publisher_layouts_verified": False} for source_id in all_sources())
