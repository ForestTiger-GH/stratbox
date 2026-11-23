"""The same explicit boundaries are registered separately for each FNS family."""
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.core.execution.semantics import InputPort, OperationSemantics, OutputPort, ProcessingFunction, ProcessingStage
from stratbox.shared.data.calculations import ObservationComparison
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.materials import MaterialArtifact

from ..analytics.calculations import Calculation
from ..integration.contracts import FnsDataset
from ..products.views import PreparedView
from ..tables.comparison import FlakeComparison
from ..tables.contracts import SourceProjection, ValidationReport
from ..tables.snapshots import snapshot_contract
from .contracts import (
    CalculationRequest, CaptureFullRequest, ChangesRequest, CompareDatasetsRequest,
    CompareFlakesRequest, DatasetRequest, ExtractRequest, FlakeRequest, ProcessedRelease,
    ProcessRequest, ProjectionRequest, RenderRequest, SharesRequest, SnapshotRequest,
    ViewRequest, ViewValueRequest,
)

_S = ProcessingStage
_F = ProcessingFunction


def definitions(series_id, flake_type):
    flake = DataContract(series_id + ".flake", 1, DataRole.EXTRACTS)
    projection = DataContract(series_id + ".reported_projection", 1, DataRole.EXTRACTS)
    dataset = DataContract(series_id + ".integrated_dataset", 1, DataRole.INTEGRATED)
    calculation = DataContract(series_id + ".calculation", 1, DataRole.PRODUCTS)
    view = DataContract(series_id + ".prepared_view", 1, DataRole.PRODUCTS)
    representation = DataContract("representation.bytes", 1, DataRole.PRODUCTS)
    snapshot = DataContract("dataset.snapshot", 1)
    original = DataContract(series_id + ".original", 1, DataRole.ORIGINALS)
    result = {}

    def add(name, request_type, value_type, stages, inputs, outputs, parameters=(), summary="", *,
            function=_F.PROCESS, composition=False, network=False):
        result[name.upper()] = OperationDefinition(series_id + "." + name, 1,
            series_id.replace(".", "-") + "-" + name.replace("_", "-") + "-1", request_type, value_type,
            required_capabilities=frozenset({"http"}) if network else frozenset(),
            optional_capabilities=frozenset({"archive_decoder"}) if series_id == "fns.1yur" and name in {"extract", "process", "capture_full"} else frozenset(),
            processing=OperationSemantics(stages=stages, inputs=inputs, outputs=outputs, parameters=parameters,
                summary=summary, composition=composition, function=function))

    add("extract", ExtractRequest, flake_type, (_S.EXTRACT,),
        (InputPort("source", original, "payload"),), (OutputPort("flake", flake),), ("release",),
        "Extract all supplied source records or admitted workbook cells before selecting economic fields.")
    add("readable", FlakeRequest, Representation, (_S.READABLE,), (InputPort("flake", flake, "flake"),),
        (OutputPort("readable", DataContract(series_id + ".readable", 1, DataRole.READABLE)),
         OutputPort("representation", representation)),
        summary="Render source-readable evidence directly from the full retained flake.")
    add("validate", FlakeRequest, ValidationReport, (_S.VALIDATE,), (InputPort("flake", flake, "flake"),),
        (OutputPort("report", DataContract(series_id + ".validation", 1)),),
        summary="Assess the reviewed source profile and expose errors, omissions and disagreements.")
    add("compare_flakes", CompareFlakesRequest, FlakeComparison, (_S.COMPARE,),
        (InputPort("before", flake, "before"), InputPort("after", flake, "after")),
        (OutputPort("comparison", DataContract(series_id + ".flake_comparison", 1)),),
        summary="Compare physical source evidence for the same publication issue, independent of economic interpretation.")
    add("project", FlakeRequest, SourceProjection, (_S.EXTRACT,), (InputPort("flake", flake, "flake"),),
        (OutputPort("projection", projection),),
        summary="Select reviewed reported fields from retained source evidence and record every projection qualification.")
    add("align", ProjectionRequest, FnsDataset, (_S.INTEGRATE,), (InputPort("projection", projection, "projection"),),
        (OutputPort("dataset", dataset),),
        summary="Apply the explicit dated identity map while retaining source geography, omitted fields and map identity.")
    add("compare_datasets", CompareDatasetsRequest, ObservationComparison, (_S.COMPARE,),
        (InputPort("before", dataset, "before"), InputPort("after", dataset, "after")),
        (OutputPort("comparison", DataContract("observations.comparison", 1)),),
        summary="Assess revisions only across matching metrics, editions, periods, perimeters and dimensions.")
    add("calculate_changes", ChangesRequest, Calculation, (_S.CALCULATE,),
        (InputPort("before", dataset, "before"), InputPort("after", dataset, "after")),
        (OutputPort("calculation", calculation),), ("metric_ids",),
        "Calculate matched net stock changes with both source vintages; these are not births, entries or exits.")
    add("calculate_shares", SharesRequest, Calculation, (_S.CALCULATE,), (InputPort("dataset", dataset, "dataset"),),
        (OutputPort("calculation", calculation),),
        ("numerator_metric", "denominator_metric", "numerator_dimensions", "denominator_dimensions"),
        "Calculate explicitly selected same-period stock shares, retaining zero-denominator diagnostics.")
    add("view", ViewRequest, PreparedView, (_S.VIEW,),
        (InputPort("dataset", dataset, "dataset", alternatives=(calculation,)),), (OutputPort("view", view),),
        ("metric_ids", "subject_ids", "period_kinds", "dimensions"),
        "Prepare an exact selection from retained observations without automatic aggregation.")
    add("render", RenderRequest, Representation, (_S.RENDER,), (InputPort("view", view, "view"),),
        (OutputPort("representation", representation),), ("format",),
        "Render a prepared view as CSV, JSON, JSONL or XLSX independently of source parsing.")
    add("render_artifact", RenderRequest, MaterialArtifact, (_S.RENDER,), (InputPort("view", view, "view"),),
        (OutputPort("artifact", DataContract("material.artifact", 1)),), ("format",),
        "Render and package an explicit source-associated artifact for independent material storage.")
    add("readable_artifact", FlakeRequest, MaterialArtifact, (_S.READABLE,), (InputPort("flake", flake, "flake"),),
        (OutputPort("artifact", DataContract("material.artifact", 1)),),
        summary="Package source-readable evidence and lineage for the selected material store.")
    for name, value_type, request_type, contract, path in (
        ("flake", flake_type, FlakeRequest, flake, "flake"),
        ("projection", SourceProjection, ProjectionRequest, projection, "projection"),
        ("dataset", FnsDataset, DatasetRequest, dataset, "dataset"),
        ("calculation", Calculation, CalculationRequest, calculation, "calculation"),
        ("view", PreparedView, ViewValueRequest, view, "view"),
    ):
        encoded_contract = snapshot_contract(series_id, name)
        add(name + "_snapshot", request_type, DatasetSnapshot, (),
            (InputPort(name, contract, path),),
            (OutputPort("snapshot", encoded_contract), OutputPort("dataset_snapshot", snapshot)),
            summary="Encode the complete " + name + " envelope for neutral immutable dataset storage.", function=_F.ENCODE)
        add("read_" + name + "_snapshot", SnapshotRequest, value_type, (),
            (InputPort("snapshot", encoded_contract, "snapshot"),), (OutputPort(name, contract),),
            summary="Validate and replay a retained " + name + " without the original file or a spreadsheet engine.", function=_F.REPLAY)
    outputs = (OutputPort("original", original, "original"),
        OutputPort("payload", DataContract("source.payload", 1, DataRole.ORIGINALS), "original"),
        OutputPort("flake", flake, "flake"), OutputPort("projection", projection, "projection"),
        OutputPort("dataset", dataset, "dataset"), OutputPort("view", view, "view"),
        OutputPort("representation", representation, "representation"))
    add("process", ProcessRequest, ProcessedRelease, (_S.EXTRACT, _S.INTEGRATE, _S.VIEW, _S.RENDER),
        (InputPort("source", original, "payload"),), outputs, ("release", "format"),
        "Compose extraction, projection, identity alignment and rendering while returning every retained boundary.", composition=True)
    add("capture_full", CaptureFullRequest, ProcessedRelease,
        (_S.ACQUIRE, _S.EXTRACT, _S.INTEGRATE, _S.VIEW, _S.RENDER), (), outputs, ("release", "url", "format"),
        "Acquire the selected publication and return full flakes, projections, datasets, prepared views and rendered bytes.",
        composition=True, network=True)
    return result
