"""FNS capability metadata and explicit scientific method bindings.

Physical evidence, reviewed observations, alignment and products have separate
contracts. Loading this contribution does not import a decoder or a transport.
"""
from __future__ import annotations

from stratbox.capabilities.catalog import (
    CatalogContribution, MethodDefinition, ProcessingGroup, ProfileDefinition,
    RecipeDefinition, ReferenceDefinition,
)
from stratbox.capabilities.model import (
    AcceptanceContract, CommandDefinition, OperationDefinition, ScenarioDefinition,
    GraphBody, Call, InputRef, OutputRef, ParameterRef, PortContract, ReuseContract, SemanticPredicate,
)
from stratbox.capabilities.commands import MATERIAL, MATERIAL_INPUT, REPRESENTATION
from stratbox.shared.data.processing import DataContract, DataRole


FAMILIES = (
    ("fns.sme", "population_records", "full-json", "published-counts-alignment", "statistics-post", ("json",)),
    ("fns.1yur", "registration_statistics", "all-workbook-cells", "identity-field-alignment", "dated-links", ("xls", "xlsx", "zip", "rar")),
)
_PURE = ReuseContract(mutation="immutable")
_RUNTIME = "stratbox.domains.fns.capability_commands:"
_LAYERS = ("flake", "projection", "dataset", "calculation", "view")


def _port(series, name, role=None):
    return PortContract(DataContract(series + "." + name, 1, role))


def _ports(series):
    from .publications.contracts import ReleaseContext
    from .tables.contracts import JsonFlake, SourceProjection, ValidationReport, FlakeComparison
    from .tables.legal_entities.contracts import WorkbookBundle
    from .integration.contracts import FnsDataset
    from .analytics.calculations import Calculation
    from .products.views import PreparedView
    from stratbox.shared.data.representation import Representation
    from stratbox.shared.evidence import AcquisitionReceipt
    from stratbox.shared.materials import MaterialArtifact
    ports = {
        "release": _port(series, "release_context"),
        "flake": _port(series, "physical_evidence", DataRole.EXTRACTS),
        "projection": _port(series, "reported_projection", DataRole.EXTRACTS),
        "dataset": _port(series, "integrated_dataset", DataRole.INTEGRATED),
        "calculation": _port(series, "calculation", DataRole.PRODUCTS),
        "view": _port(series, "prepared_view", DataRole.PRODUCTS),
        "readable": _port(series, "readable", DataRole.READABLE),
        "report": _port(series, "validation"),
        "comparison": _port(series, "comparison"),
        "acquisition": _port(series, "acquisition_receipt"),
        "index": _port(series, "publication_index"),
        "artifact": _port(series, "material_artifact", DataRole.PRODUCTS),
        "readable_artifact": _port(series, "readable_artifact", DataRole.READABLE),
    }
    types = {"release": ReleaseContext, "flake": JsonFlake if series == "fns.sme" else WorkbookBundle,
        "projection": SourceProjection, "dataset": FnsDataset, "calculation": Calculation,
        "view": PreparedView, "readable": Representation, "report": ValidationReport,
        "acquisition": AcquisitionReceipt, "artifact": MaterialArtifact, "readable_artifact": MaterialArtifact,
        "index": tuple if series == "fns.sme" else dict}
    for name, value_type in types.items():
        predicates = (SemanticPredicate("series_id" if name == "release" else "context.series_id", "equals", series,
            "fns.source_family_mismatch"),) if name in {"release", "flake", "projection", "dataset", "calculation", "view"} else ()
        ports[name] = PortContract(ports[name].schema, value_type, predicates=predicates)
    from stratbox.shared.data.calculations import ObservationComparison
    ports["comparison"] = PortContract(DataContract(series + ".observation_comparison", 1), ObservationComparison)
    ports["source_comparison"] = PortContract(DataContract(series + ".source_revision_comparison", 1), FlakeComparison)
    return ports


def _command(identifier, function, *, series, inputs, outputs, parameters=None,
             required_parameters=(), effects=frozenset(), providers=frozenset(),
             optional_providers=frozenset(), fixed=None, resources=None):
    return CommandDefinition(identifier, _RUNTIME + function, inputs=inputs, outputs=outputs,
        parameters=parameters or {}, required_parameters=required_parameters,
        fixed={"series_id": series, **(fixed or {})}, effects=effects,
        required_capabilities=providers, optional_capabilities=optional_providers, resources=resources or {},
        reuse=(_PURE if not effects else
            ReuseContract(deterministic=False, observation_scoped=True, effects=effects)
            if effects <= {"network.receive"} else ReuseContract(shareable=False, effects=effects)))


def _single(identifier, command, *, inputs, outputs, parameters=None,
            required_parameters=(), method_slot=False, effects=frozenset(),
            output_ports=None):
    names = output_ports or {name: name for name in outputs}
    body = GraphBody((Call("apply", command,
        {name: InputRef(name) for name in inputs},
        {name: ParameterRef(name) for name in (*tuple(parameters or {}), *required_parameters)}),),
        {name: OutputRef("apply", port) for name, port in names.items()})
    definition = OperationDefinition(identifier, body=None if method_slot else body,
        method_slot="scientific_method" if method_slot else None,
        inputs=inputs, outputs=outputs, parameters=parameters or {},
        required_parameters=required_parameters, effects=effects)
    return definition, body


def contribution():
    """Return both complete FNS routes using independent command leaves."""
    definitions, methods, profiles, groups, recipes, references = [], [], [], [], [], []
    for series, group_name, physical_profile, alignment_profile, acquisition_profile, formats in FAMILIES:
        ports = _ports(series)
        group_id = series + "." + group_name
        op = lambda name: series + "." + name
        cmd = lambda name: series + ".command." + name
        limit = 4_000_000 if series == "fns.sme" else 30_000_000
        physical_id, alignment_id, acquisition_id = (series + "." + name for name in
            (physical_profile, alignment_profile, acquisition_profile))
        projection_id = series + ".reviewed-projection"
        from importlib import import_module
        mapping = import_module("stratbox.domains.fns.integration." +
            ("sme" if series == "fns.sme" else "legal_entities") + ".alignment")
        reference_id = series + ".field-mapping"
        references.append(ReferenceDefinition(reference_id, mapping.PROFILE, mapping.MAP_IDENTITY.sha256))
        defaults = {"profile": {}}
        entries = (
            ("readable", "readable", {"flake": ports["flake"]}, {"readable": ports["readable"]}, {}),
            ("validate", "validate", {"flake": ports["flake"]}, {"report": ports["report"]}, {}),
            ("project", "project", {"flake": ports["flake"]}, {"projection": ports["projection"]}, defaults),
            ("align", "align", {"projection": ports["projection"]}, {"dataset": ports["dataset"]}, defaults),
            ("compare_flakes", "compare_flakes", {"before": ports["flake"], "after": ports["flake"]}, {"comparison": ports["source_comparison"]}, {}),
            ("compare_datasets", "compare_datasets", {"before": ports["dataset"], "after": ports["dataset"]}, {"comparison": ports["comparison"]}, {}),
            ("calculate_changes", "calculate_changes", {"before": ports["dataset"], "after": ports["dataset"]}, {"calculation": ports["calculation"]}, {"metric_ids": ()}),
            ("calculate_shares", "calculate_shares", {"dataset": ports["dataset"]}, {"calculation": ports["calculation"]},
                {"numerator_metric": None, "denominator_metric": None, "numerator_dimensions": (), "denominator_dimensions": ()}),
            ("view", "view", {"dataset": ports["dataset"]}, {"view": ports["view"]},
                {"metric_ids": (), "subject_ids": (), "period_kinds": (), "dimensions": ()}),
            ("view_calculation", "view", {"dataset": ports["calculation"]}, {"view": ports["view"]},
                {"metric_ids": (), "subject_ids": (), "period_kinds": (), "dimensions": ()}),
            ("render", "render", {"view": ports["view"]}, {"representation": REPRESENTATION}, {"format": "csv"}),
            ("render_artifact", "render_artifact", {"view": ports["view"]}, {"artifact": ports["artifact"]}, {"format": "csv"}),
            ("readable_artifact", "readable_artifact", {"flake": ports["flake"]}, {"artifact": ports["readable_artifact"]}, {}),
            ("regional_product", "regional_product", {"flake": ports["flake"]}, {"representation": REPRESENTATION}, {}),
            ("read_representation", "read_regional", {"payload": MATERIAL, "release": ports["release"]}, {"dataset": ports["dataset"]}, {}),
            ("discover", "discover", {"index": MATERIAL}, {"index": ports["index"]}, {"year": None, "base_url": None}),
        )
        for name, function, inputs, outputs, parameters in entries:
            definitions.append(_command(cmd(name), function, series=series, inputs=inputs, outputs=outputs, parameters=parameters))
            specialized = name in {"project", "align"}
            definition, body = _single(op(name), cmd(name), inputs=inputs, outputs=outputs,
                parameters=parameters, method_slot=specialized)
            definitions.append(definition)
            if specialized:
                profile_id = projection_id if name == "project" else alignment_id
                method_id = op("method." + name)
                methods.append(MethodDefinition(method_id, op(name), body,
                    reference_ids=(reference_id,) if name == "align" else ()))
                profiles.append(ProfileDefinition(profile_id,
                    {"edition": "1", "series_id": series, "stage": name,
                     "scope": "reviewed_part_i_historical_epochs" if series == "fns.1yur" else "all_present_reviewed_counters"},
                    method_id=method_id, group_id=group_id))
        # A bounded read is visible independently from physical decoding.
        definitions.append(_command(cmd("extract"), "extract", series=series,
            inputs={"payload": MATERIAL, "release": ports["release"]}, outputs={"flake": ports["flake"]},
            parameters=defaults, resources={"parse": 1},
            optional_providers=frozenset({"archive_decoder"}) if series == "fns.1yur" else frozenset()))
        extract_body = GraphBody((
            Call("read", "material.read", {"material": InputRef("payload")}, {"max_bytes": limit}),
            Call("decode", cmd("extract"), {"payload": OutputRef("read"), "release": InputRef("release")},
                 {"profile": ParameterRef("profile")}),
        ), {"flake": OutputRef("decode", "flake")})
        definitions.append(OperationDefinition(op("extract"), method_slot="physical_decode",
            inputs={"payload": MATERIAL_INPUT, "release": ports["release"]}, outputs={"flake": ports["flake"]}, parameters=defaults))
        methods.append(MethodDefinition(op("method.extract"), op("extract"), extract_body))
        profiles.append(ProfileDefinition(physical_id, {"series_id": series, "formats": formats,
            "edition": "1", "scope": "all_supplied_records_fields_and_tokens" if series == "fns.sme" else "all_admitted_members_cells_formula_context"},
            method_id=op("method.extract"), group_id=group_id))
        definitions.append(_command(cmd("acquire"), "acquire", series=series,
            inputs={"release": ports["release"]},
            outputs={"payload": MATERIAL, "release": ports["release"], "acquisition": ports["acquisition"]},
            parameters={"url": None, "profile": {}}, effects=frozenset({"network.receive"}), providers=frozenset({"http"})))
        acquired, acquired_body = _single(op("acquire"), cmd("acquire"),
            inputs={"release": ports["release"]},
            outputs={"payload": MATERIAL, "release": ports["release"], "acquisition": ports["acquisition"]},
            parameters={"url": None, "profile": {}}, method_slot=True, effects=frozenset({"network.receive"}))
        definitions.append(acquired)
        methods.append(MethodDefinition(op("method.acquire"), op("acquire"), acquired_body))
        profiles.append(ProfileDefinition(acquisition_id, {"series_id": series,
            "edition": "1", "request": "official_read_only_post" if series == "fns.sme" else "dated_official_link"},
            method_id=op("method.acquire"), group_id=group_id))
        # Every retained scientific layer has a family- and layer-specific codec.
        for layer in _LAYERS:
            from stratbox.shared.data.snapshots import DatasetSnapshot
            from .tables.snapshots import snapshot_contract
            snapshot = PortContract(snapshot_contract(series, layer), DatasetSnapshot)
            stored_snapshot = PortContract(snapshot.schema, DatasetSnapshot,
                alternatives=(DataContract("dataset.snapshot", 1),))
            for restore in (False, True):
                name = ("read_" if restore else "") + layer + "_snapshot"
                inputs = {"snapshot": stored_snapshot} if restore else {layer: ports[layer]}
                outputs = {layer: ports[layer]} if restore else {"snapshot": snapshot}
                definitions.append(_command(cmd(name), "replay" if restore else "snapshot", series=series,
                    inputs=inputs, outputs=outputs, fixed={"layer": layer}))
                definitions.append(_single(op(name), cmd(name), inputs=inputs, outputs=outputs)[0])
        process_calls = (
            Call("extract", op("extract"), {"payload": InputRef("payload"), "release": InputRef("release")}, profile_id=physical_id),
            Call("project", op("project"), {"flake": OutputRef("extract", "flake")}, profile_id=projection_id),
            Call("align", op("align"), {"projection": OutputRef("project", "projection")}, profile_id=alignment_id),
            Call("view", op("view"), {"dataset": OutputRef("align", "dataset")}),
            Call("render", op("render"), {"view": OutputRef("view", "view")}, {"format": ParameterRef("format")}),
        )
        process_outputs = {"flake": OutputRef("extract", "flake"), "projection": OutputRef("project", "projection"),
            "dataset": OutputRef("align", "dataset"), "view": OutputRef("view", "view"),
            "representation": OutputRef("render", "representation")}
        process_ports = {name: ports[name] if name in ports else REPRESENTATION for name in process_outputs}
        definitions.append(ScenarioDefinition(op("process"), GraphBody(process_calls, process_outputs),
            inputs={"payload": MATERIAL_INPUT, "release": ports["release"]}, outputs=process_ports,
            parameters={"format": "csv"}, purpose="Retain physical evidence and derive independently accepted source, integrated and product values."))
        definitions.append(ScenarioDefinition(op("parse"), GraphBody((process_calls[0],
            Call("regional", op("regional_product"), {"flake": OutputRef("extract", "flake")})),
            {"flake": OutputRef("extract", "flake"), "representation": OutputRef("regional", "representation")}),
            inputs={"payload": MATERIAL_INPUT, "release": ports["release"]},
            outputs={"flake": ports["flake"], "representation": REPRESENTATION},
            purpose="Prepare the explicit regional CSV projection while retaining full supplied physical evidence."))
        for name, downstream, outputs in (("capture_full", "process", process_ports),
                                         ("capture", "parse", {"flake": ports["flake"], "representation": REPRESENTATION})):
            outputs = {**outputs, "original": MATERIAL, "acquisition": ports["acquisition"]}
            definitions.append(ScenarioDefinition(op(name), GraphBody((
                Call("acquire", op("acquire"), {"release": InputRef("release")}, {"url": ParameterRef("url")}, profile_id=acquisition_id),
                Call("process", op(downstream), {"payload": OutputRef("acquire", "payload"),
                    "release": OutputRef("acquire", "release")}, {"format": ParameterRef("format")} if downstream == "process" else {}),
            ), {**{key: OutputRef("process", key) for key in outputs if key not in {"original", "acquisition"}},
                "original": OutputRef("acquire", "payload"), "acquisition": OutputRef("acquire", "acquisition")}),
                inputs={"release": ports["release"]}, outputs=outputs, parameters={"url": None, "format": "csv"},
                effects=frozenset({"network.receive"}), purpose="Acquire one observed edition and expose independently useful retained stages."))
        # Revision comparison has the same physical meaning as compare_flakes.
        definitions.append(_single(op("compare"), cmd("compare_flakes"),
            inputs={"before": ports["flake"], "after": ports["flake"]}, outputs={"comparison": ports["source_comparison"]})[0])
        groups.append(ProcessingGroup(group_id, source_ids=(series,), representations=formats,
            methods={op(name): op("method." + name) for name in ("acquire", "extract", "project", "align")},
            profiles={op("acquire"): acquisition_id, op("extract"): physical_id,
                      op("project"): projection_id, op("align"): alignment_id}))
        recipes.extend(RecipeDefinition(op("recipe." + name), goal, op(name), selection={"source_id": series})
            for name, goal in (("extract", "source.extract"), ("process", "source.product"),
                               ("capture_full", "source.capture"), ("parse", "source.regional_csv")))
        definitions.append(ScenarioDefinition(op("discover_online"), GraphBody((
            Call("acquire", "acquire.material", {"url": ParameterRef("index_url")}),
            Call("discover", op("discover"), {"index": OutputRef("acquire", "material")},
                {"year": ParameterRef("year"), "base_url": ParameterRef("index_url")}),
        ), {"index": OutputRef("discover", "index")}), outputs={"index": ports["index"]},
            parameters={"year": None}, required_parameters=("index_url",), effects=frozenset({"network.receive"}),
            purpose="Acquire one explicitly selected publisher index and enumerate its observed issue membership."))
    return CatalogContribution(definitions=tuple(definitions), methods=tuple(methods), profiles=tuple(profiles),
        groups=tuple(groups), recipes=tuple(recipes), references=tuple(references))


def dispositions():
    """Final callable dispositions; convenience routes become scenarios."""
    stages = ("acquire", "align", "calculate_changes", "calculate_shares", "calculation_snapshot", "capture",
        "capture_full", "compare", "compare_datasets", "compare_flakes", "dataset_snapshot", "discover", "extract",
        "flake_snapshot", "parse", "process", "project", "projection_snapshot", "read_calculation_snapshot",
        "read_dataset_snapshot", "read_flake_snapshot", "read_projection_snapshot", "read_representation",
        "read_view_snapshot", "readable", "readable_artifact", "render", "render_artifact", "validate", "view", "view_snapshot")
    return tuple({"original_id": series + "." + name, "capability_id": series + "." + name,
        "kind": "scenario" if name in {"capture", "capture_full", "parse", "process"} else "operation",
        "status": "canonical", "semantics": "literal_source_revision" if name == "compare" else "explicit_stage"}
        for series, *_ in FAMILIES for name in stages)


def stage_matrix():
    """Concrete stage routes retain exact evidence and projection scope limits."""
    routes = {"discover": "discover", "acquire": "acquire", "inspect": "validate", "extract": "extract",
        "readable": "readable", "read_extract": "read_flake_snapshot", "validate": "validate", "compare": "compare_flakes", "integrate": "align",
        "calculate": "calculate_changes", "view": "view", "render": "render"}
    return tuple({"source_id": series, "group_id": series + "." + group,
        "stages": {**{stage: {"kind": "direct", "capability_id": series + "." + route} for stage, route in routes.items()},
            "preserve": {"kind": "shared", "capability_id": "preserve.material"},
            "ingest": {"kind": "shared", "capability_id": "ingest.observations", "input": "dataset_snapshot.snapshot"},
            "publish": {"kind": "shared", "capability_id": "publish.release"}},
        "scope": "all_supplied_json_fields_then_reviewed_present_counters" if series == "fns.sme" else
                 "all_admitted_workbook_cells_then_reviewed_historical_part_i_projection",
        "coverage": "physical_completeness_and_analytical_scope_are_independent"}
        for series, group, *_ in FAMILIES)
