"""Pure fiscal capability metadata; executable work is resolved on invocation."""
from __future__ import annotations

from stratbox.capabilities.catalog import CatalogContribution, MethodDefinition, ProcessingGroup, ProfileDefinition, RecipeDefinition
from stratbox.capabilities.model import CommandDefinition, OperationDefinition, ScenarioDefinition, GraphBody, Call, InputRef, OutputRef, ParameterRef, ReuseContract
from stratbox.capabilities.model import PortContract
from stratbox.capabilities.commands import CALCULATED_OBSERVATIONS
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.views import ObservationView
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import DatasetSnapshot
from .tables.contracts import TableExtract, FlakeTable
from .documents.contracts import PublisherDocument, DocumentValidation
from .documents.conversion import ConvertedDocument
from .analytics.contracts import HeadlineSummary
from .publications.contracts import PublicationIndex, AcquiredAsset


def _port(name, role=DataRole.EXTRACTS):
    types = {"material.bytes": SourcePayload, "minfin.source_cells": TableExtract, "minfin.flake": FlakeTable,
        "observations.batch": ObservationBatch, "minfin.publisher_document": PublisherDocument,
        "minfin.headlines": HeadlineSummary, "observations.view": ObservationView,
        "product.representation": Representation, "dataset.snapshot": DatasetSnapshot,
        "minfin.publication_index": PublicationIndex, "minfin.acquired_asset": AcquiredAsset,
        "minfin.converted_document": ConvertedDocument}
    types["minfin.document.validation"] = DocumentValidation
    return PortContract(DataContract(name, 2 if name in {"minfin.source_cells","minfin.flake"} else 1, role), types.get(name, object))


PAYLOAD = _port("material.bytes", DataRole.ORIGINALS)
EXTRACT = _port("minfin.source_cells")
FLAKE = _port("minfin.flake")
BATCH = _port("observations.batch")
DOCUMENT = _port("minfin.publisher_document")
SUMMARY = _port("minfin.headlines")
VIEW = _port("observations.view", DataRole.PRODUCTS)
REPRESENTATION = _port("product.representation", DataRole.PRODUCTS)
SNAPSHOT = PortContract(DataContract("dataset.snapshot",1),DatasetSnapshot)
INDEX = _port("minfin.publication_index")
ASSET = _port("minfin.acquired_asset", DataRole.ORIGINALS)
ANY = PortContract()

# Every row is a functional boundary. Technical leaves address pure builders,
# codecs or explicit provider actions, never an operation runner.
_STAGES = (
    ("discover", "discover", {"index": PAYLOAD}, INDEX, {"max_links": 2000, "page_url": None}, ("family_id",)),
    ("inspect", "inspect", {"before": INDEX, "after": INDEX}, ANY, {}, ()),
    ("acquire", "acquire", {"asset": ANY}, ASSET, {"max_bytes": 64*1024*1024, "deadline_seconds": 60}, ()),
    ("extract", "extract", {"payload": PAYLOAD}, EXTRACT, {"member": None, "selected_sheets": (), "max_cells": 150000, "csv_encoding": "utf-8-sig", "publication": None}, ("family_id", "format")),
    ("validate", "validate", {"extract": EXTRACT}, ANY, {}, ()),
    ("compare", "compare", {"before": EXTRACT, "after": EXTRACT}, ANY, {"max_changes": 100000}, ()),
    ("map_observations", "map_observations", {"extract": EXTRACT}, ANY, {}, ("bindings",)),
    ("render_csv", "render_csv", {"extract": EXTRACT}, REPRESENTATION, {}, ()),
    ("serialize", "serialize", {"extract": EXTRACT}, REPRESENTATION, {}, ()),
    ("read_representation", "read_representation", {"representation": REPRESENTATION}, EXTRACT, {}, ()),
    ("plan_updates", "plan_updates", {"index": INDEX}, ANY, {"checkpoints": (), "selected_sources": (), "retained_sources": frozenset(), "target": "probe", "force_reprocess": False, "force_refresh": False}, ()),
    ("build_flake", "build_flake", {"extract": EXTRACT}, FLAKE, {"selected_sheet": None, "profile": None}, ("source_id",)),
    ("render_flake", "render_flake", {"flake": FLAKE}, REPRESENTATION, {}, ()),
    ("serialize_flake", "serialize_flake", {"flake": FLAKE}, REPRESENTATION, {}, ()),
    ("read_flake", "read_flake", {"representation": REPRESENTATION}, FLAKE, {}, ()),
    ("flake_snapshot", "flake_snapshot", {"flake": FLAKE}, SNAPSHOT, {}, ("dataset_id", "version_id")),
    ("read_flake_snapshot", "read_flake_snapshot", {"snapshot": SNAPSHOT}, FLAKE, {}, ()),
    ("summarize", "summarize", {"flake": FLAKE}, SUMMARY, {"period_id": None}, ()),
    ("prepare_notice", "prepare_notice", {"summary": SUMMARY, "asset": ANY, "decision": ANY}, ANY, {"include_initial": False, "baseline_original_identity": None}, ()),
    ("integrate", "integrate", {"flake": FLAKE}, BATCH, {"bindings": ()}, ("dataset_id", "release_id")),
    ("observation_snapshot", "observation_snapshot", {"batch": BATCH}, SNAPSHOT, {"dataset_id": None, "version_id": None}, ()),
    ("read_observations", "read_observations", {"snapshot": SNAPSHOT}, BATCH, {}, ()),
    ("summary_snapshot", "summary_snapshot", {"summary": SUMMARY}, SNAPSHOT, {}, ("dataset_id", "version_id")),
    ("read_summary", "read_summary", {"snapshot": SNAPSHOT}, SUMMARY, {}, ()),
    ("prepare_view", "prepare_view", {"summary": SUMMARY}, VIEW, {"metric_ids": ()}, ("view_id",)),
    ("view_snapshot", "view_snapshot", {"view": VIEW}, SNAPSHOT, {"dataset_id": None, "version_id": None}, ()),
    ("read_view", "read_view", {"snapshot": SNAPSHOT}, VIEW, {}, ()),
    ("render_view", "render_view", {"view": VIEW}, REPRESENTATION, {"format": "csv"}, ()),
    ("extract_document", "extract_document", {"payload": PAYLOAD}, DOCUMENT, {"max_pages": 1000}, ("family_id", "publication")),
    ("document_snapshot", "document_snapshot", {"document": DOCUMENT}, SNAPSHOT, {"dataset_id": None, "version_id": None}, ()),
    ("read_document", "read_document", {"snapshot": SNAPSHOT}, DOCUMENT, {}, ()),
    ("render_document", "render_document", {"document": DOCUMENT}, REPRESENTATION, {}, ()),
    ("validate_document", "validate_document", {"document": DOCUMENT}, _port("minfin.document.validation"), {}, ()),
    ("convert_document", "convert_document", {"payload": PAYLOAD}, _port("minfin.converted_document"), {"max_bytes": 64*1024*1024}, ()),
    ("decode_converted_document", "decode_converted_document", {"converted": _port("minfin.converted_document")}, DOCUMENT, {"max_pages": 1000}, ("family_id", "publication")),
    ("document_observations", "document_observations", {"document": DOCUMENT}, BATCH, {}, ("profile", "dataset_id", "release_id")),
)


def contribution():
    """Return all exact stages, source groups and reusable source recipes."""
    definitions, methods = [], []
    for name, handler, inputs, output, parameters, required in _STAGES:
        command = "minfin.stage." + name
        effects = frozenset({"network.receive"}) if name == "acquire" else frozenset()
        providers = frozenset({"http"}) if name == "acquire" else frozenset({"document_converter"}) if name == "convert_document" else frozenset()
        body = GraphBody((Call("build", command,
            {key: InputRef(key) for key in inputs}, {key: ParameterRef(key) for key in (*parameters, *required)}),),
            {"value": OutputRef("build")})
        definitions.extend((
            CommandDefinition(command, "stratbox.domains.minfin.capability_commands:" + handler,
                inputs=inputs, outputs={"value": output}, parameters=parameters, required_parameters=required,
                required_capabilities=providers, effects=effects,
                resource_parameters={"staging_bytes": "max_bytes"} if name in {"acquire","convert_document"} else {},
                reuse=ReuseContract(shareable=not providers, deterministic=not providers, effects=effects)),
            OperationDefinition("minfin." + name, None if name == "build_flake" else body,
                method_slot="fiscal_layout" if name == "build_flake" else None, inputs=inputs, outputs={"value": output},
                parameters=parameters, required_parameters=required, effects=effects),
        ))
        if name == "build_flake":
            methods.append(MethodDefinition("minfin.method.build_flake", "minfin.build_flake", body))
    definitions.extend((
        CommandDefinition("minfin.stage.asset_payload", "stratbox.domains.minfin.capability_commands:asset_payload",
            inputs={"acquired": ASSET}, outputs={"value": PAYLOAD}),
        OperationDefinition("minfin.asset_payload", GraphBody((Call("payload", "minfin.stage.asset_payload", {"acquired": InputRef("acquired")}),),
            {"value": OutputRef("payload")}), inputs={"acquired": ASSET}, outputs={"value": PAYLOAD}),
        CommandDefinition("minfin.stage.asset_context", "stratbox.domains.minfin.capability_commands:asset_context",
            inputs={"acquired": ASSET}, outputs={"publication": ANY, "family_id": ANY, "format": ANY}),
        OperationDefinition("minfin.asset_context", GraphBody((Call("context", "minfin.stage.asset_context", {"acquired": InputRef("acquired")}),),
            {key: OutputRef("context",key) for key in ("publication","family_id","format")}),
            inputs={"acquired": ASSET}, outputs={"publication": ANY, "family_id": ANY, "format": ANY}),
        ScenarioDefinition("minfin.readable", GraphBody((
            Call("extract", "minfin.extract_document", {"payload": InputRef("payload")},
                {"family_id": ParameterRef("family_id"), "publication": ParameterRef("publication"), "max_pages": ParameterRef("max_pages")}),
            Call("render", "minfin.render_document", {"document": OutputRef("extract")}),
        ), {"value": OutputRef("render")}), inputs={"payload": PAYLOAD}, outputs={"value": REPRESENTATION},
            parameters={"max_pages": 1000}, required_parameters=("family_id", "publication"), purpose="Decode ordered document evidence and render the admitted physical scope."),
        ScenarioDefinition("minfin.capture", GraphBody((
            Call("acquire", "minfin.acquire", {"asset": InputRef("asset")}, {"max_bytes": ParameterRef("max_bytes")}),
            Call("payload", "minfin.asset_payload", {"acquired": OutputRef("acquire")}),
            Call("context", "minfin.asset_context", {"acquired": OutputRef("acquire")}),
            Call("extract", "minfin.extract", {"payload": OutputRef("payload")},
                {"family_id": OutputRef("context","family_id"), "format": OutputRef("context","format"), "publication": OutputRef("context","publication")}),
        ), {"original": OutputRef("payload"), "value": OutputRef("extract")}), inputs={"asset": ANY},
            outputs={"original": PAYLOAD, "value": EXTRACT}, parameters={"max_bytes": 64*1024*1024}, effects=frozenset({"network.receive"}),
            purpose="Acquire a qualified publisher asset and expose independently retained source cells."),
        ScenarioDefinition("minfin.legacy_document", GraphBody((
            Call("convert", "minfin.convert_document", {"payload": InputRef("payload")}),
            Call("decode", "minfin.decode_converted_document", {"converted": OutputRef("convert")},
                {"family_id": ParameterRef("family_id"), "publication": ParameterRef("publication")}),
        ), {"value": OutputRef("decode"), "conversion": OutputRef("convert")}), inputs={"payload": PAYLOAD},
            outputs={"value": DOCUMENT, "conversion": _port("minfin.converted_document")},
            required_parameters=("family_id", "publication"), purpose="Convert legacy DOC through an explicit provider and retain both byte identities."),
        ScenarioDefinition("minfin.table_product", GraphBody((
            Call("interpret", "minfin.build_flake", {"extract": InputRef("extract")}, {"source_id": ParameterRef("source_id")}),
            Call("align", "minfin.integrate", {"flake": OutputRef("interpret")},
                {"dataset_id": ParameterRef("dataset_id"), "release_id": ParameterRef("release_id"), "bindings": ParameterRef("bindings")}),
            Call("calculate", "minfin.summarize", {"flake": OutputRef("interpret")}),
            Call("view", "minfin.prepare_view", {"summary": OutputRef("calculate")}, {"view_id": ParameterRef("view_id")}),
            Call("render", "minfin.render_view", {"view": OutputRef("view")}),
        ), {"observations": OutputRef("align"), "summary": OutputRef("calculate"), "view": OutputRef("view"), "value": OutputRef("render")}),
            inputs={"extract": EXTRACT}, outputs={"observations": BATCH, "summary": SUMMARY, "view": VIEW, "value": REPRESENTATION},
            parameters={"bindings": ()},
            required_parameters=("source_id", "dataset_id", "release_id", "view_id"),
            purpose="Interpret and align fiscal rows, calculate admitted headlines and prepare a retained product."),
        ScenarioDefinition("minfin.document_product", GraphBody((
            Call("interpret", "minfin.document_observations", {"document": InputRef("document")},
                {name: ParameterRef(name) for name in ("profile","dataset_id","release_id")}),
            Call("view", "view.table", {"observations": OutputRef("interpret")}, {"view_id": ParameterRef("view_id")}),
            Call("render", "render.table", {"view": OutputRef("view","view")}),
        ), {"observations": OutputRef("interpret"), "view": OutputRef("view","view"), "value": OutputRef("render","representation")}),
            inputs={"document": DOCUMENT}, outputs={"observations": BATCH, "view": VIEW, "value": REPRESENTATION},
            parameters={"view_id": None}, required_parameters=("profile","dataset_id","release_id"),
            purpose="Interpret a reviewed document field projection and render independently retained observations."),
        ScenarioDefinition("minfin.document_ratio", GraphBody((
            Call("numerator", "minfin.document_observations", {"document": InputRef("numerator")},
                {"profile": ParameterRef("numerator_profile"), "dataset_id": ParameterRef("numerator_dataset_id"), "release_id": ParameterRef("release_id")}),
            Call("denominator", "minfin.document_observations", {"document": InputRef("denominator")},
                {"profile": ParameterRef("denominator_profile"), "dataset_id": ParameterRef("denominator_dataset_id"), "release_id": ParameterRef("release_id")}),
            Call("calculate", "calculate.ratio", {"numerator": OutputRef("numerator"), "denominator": OutputRef("denominator")},
                {"pair": ParameterRef("pair"), "dataset_id": ParameterRef("dataset_id")}),
        ), {"observations": OutputRef("calculate","observations")}),
            inputs={"numerator": DOCUMENT,"denominator": DOCUMENT},
            outputs={"observations": CALCULATED_OBSERVATIONS},
            parameters={"dataset_id": None}, required_parameters=("numerator_profile","denominator_profile","numerator_dataset_id","denominator_dataset_id","release_id","pair"),
            purpose="Calculate an explicitly justified ratio from separately reviewed document fields with pinned units, periods and origins."),
    ))
    from stratbox.capabilities.commands.stages import DATASET_REFERENCE
    for identifier, input_name, input_port, snapshot_operation in (
        ("minfin.ingest_observations","batch",BATCH,"minfin.observation_snapshot"),
        ("minfin.ingest_document","document",DOCUMENT,"minfin.document_snapshot"),
    ):
        definitions.append(ScenarioDefinition(identifier, GraphBody((
            Call("snapshot",snapshot_operation,{input_name:InputRef(input_name)},
                {"dataset_id":ParameterRef("dataset_id"),"version_id":ParameterRef("version_id")}),
            Call("ingest","ingest.observations",{"value":OutputRef("snapshot")}),
        ), {"value":OutputRef("ingest"),"snapshot":OutputRef("snapshot")},required_effects=("ingest",)),
            inputs={input_name:input_port}, outputs={"value":DATASET_REFERENCE,"snapshot":SNAPSHOT},
            parameters={"dataset_id":None,"version_id":None},effects=frozenset({"dataset.write"}),
            purpose="Create a semantic snapshot and persist its immutable version through the admitted dataset provider."))
    from .publications.catalog import families
    from stratbox.core.resources import iter_resources, read_document
    groups, recipes = [], []
    profiles = [ProfileDefinition(document["profile_id"], document["declaration"])
        for resource in iter_resources("minfin", "profiles") for document in (read_document(resource),)]
    for family in families():
        for series in family.series:
            group_id = series.source_id + ".processing"
            profiles.append(ProfileDefinition(series.source_id + ".semantics", {
                "source_id": series.source_id, "family_id": family.family_id, "frequency": series.periodicity,
                "value_basis": series.basis, "kind": series.kind,
                "table_profile": family.profiles.table if series.kind == "table" else None,
                "metrics_profile": family.profiles.metrics if series.kind == "table" else None,
                "economic_scope": "reviewed_rows" if series.kind == "table" else "ordered_blocks_with_explicit_reviewed_field_mapping",
            }, group_id=group_id, method_id="minfin.method.build_flake" if series.kind == "table" else None))
            groups.append(ProcessingGroup(group_id, source_ids=(series.source_id,),
                defaults={"source_id": series.source_id} if series.kind == "table" else {},
                methods={"minfin.build_flake": "minfin.method.build_flake"} if series.kind == "table" else {},
                profiles={"minfin.build_flake": series.source_id+".semantics"} if series.kind == "table" else {}))
            recipes.append(RecipeDefinition(series.source_id + ".extract", "source.extract",
                "minfin.legacy_document" if series.slot == "veb_deposits" else "minfin.extract_document" if series.kind == "document" else "minfin.extract",
                selection={"source_id": series.source_id}, defaults={"family_id": family.family_id}, priority=10))
            if series.kind == "table":
                recipes.append(RecipeDefinition(series.source_id + ".product", "source.product", "minfin.table_product",
                    selection={"source_id": series.source_id}, defaults={"source_id": series.source_id}, priority=10))
            else:
                recipes.append(RecipeDefinition(series.source_id + ".product", "source.product", "minfin.document_product",
                    selection={"source_id": series.source_id}, priority=10))
    return CatalogContribution(definitions=tuple(definitions), methods=tuple(methods), groups=tuple(groups), profiles=tuple(profiles), recipes=tuple(recipes))


def dispositions():
    """Every callable declaration has one canonical definition and kind."""
    result = {"minfin."+name: {"capability_id": "minfin."+name, "kind": "operation", "status": "migrated"}
              for name, *_ in _STAGES}
    result.update({name: {"capability_id": name, "kind": "scenario", "status": "migrated"}
                   for name in ("minfin.capture", "minfin.readable")})
    return result


def stage_matrix():
    """Concrete routes separate physical extraction from reviewed economic scope."""
    from .publications.catalog import families
    result = []
    for family in families():
        for series in family.series:
            document = series.kind == "document"
            stages = {"discover": "minfin.discover", "acquire": "minfin.acquire", "preserve": "preserve.material",
                "inspect": "minfin.validate_document" if document else "minfin.validate",
                "validate": "minfin.validate_document" if document else "minfin.validate",
                "read_extract": "minfin.read_document" if document else "minfin.read_representation",
                "ingest": "minfin.ingest_document" if document else "minfin.ingest_observations",
                "calculate": "minfin.document_ratio" if document else "minfin.summarize",
                "read": "minfin.read_document" if document else "minfin.read_representation",
                "extract": "minfin.legacy_document" if series.slot == "veb_deposits" else "minfin.extract_document" if document else "minfin.extract",
                "readable": "minfin.render_document" if document else "minfin.render_csv",
                "snapshot": "minfin.document_snapshot" if document else "minfin.flake_snapshot",
                "compare": "observations.compare" if document else "minfin.compare",
                "integrate": "minfin.document_observations" if document else "minfin.integrate",
                "view": "view.table" if document else "minfin.prepare_view",
                "render": "render.table" if document else "minfin.render_view",
                "save": "save.product", "publish": "publish.release"}
            result.append({"source_id": series.source_id, "group_id": series.source_id+".processing", "stages": stages,
                "semantic_scope": "reviewed_field_profile_required" if document else "reviewed_budget_or_nwf_rows",
                "verification": "deterministic_layout_and_provider_contracts"})
    return tuple(result)
