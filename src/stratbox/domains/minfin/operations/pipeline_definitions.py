"""Independent integration, durable calculation and product boundaries."""
from stratbox.core.execution import InputPort, OperationDefinition, OperationSemantics, OutputPort, ProcessingStage as S
from stratbox.core.execution.semantics import ProcessingFunction
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.views import ObservationView, OBSERVATION_VIEW, OBSERVATION_VIEW_SNAPSHOT
from ..integration.contracts import IntegrateRequest, ObservationSnapshotRequest, ReadObservationsRequest
from ..analytics.contracts import HeadlineSummary, SummarySnapshotRequest, ReadSummaryRequest
from ..products.contracts import PrepareHeadlineViewRequest, ViewSnapshotRequest, ReadViewRequest, RenderViewRequest

_FLAKE = DataContract("minfin.flake", 2, DataRole.EXTRACTS)
_BATCH = DataContract("observations.batch", 1, DataRole.INTEGRATED)
_SNAPSHOT = DataContract("observations.batch.snapshot", 1)
_HEADLINES = DataContract("minfin.headlines", 1, DataRole.PRODUCTS)
_CALC = DataContract("minfin.headlines.snapshot", 1, DataRole.PRODUCTS)
_VIEW = OBSERVATION_VIEW
_VIEW_SNAPSHOT = OBSERVATION_VIEW_SNAPSHOT
_GENERIC = DataContract("dataset.snapshot", 1)


def _op(name, request, response, stage, source, path, target, *, parameters=(), snapshot=False):
    outputs = (OutputPort("value", target),)
    if snapshot:
        outputs += (OutputPort("snapshot", _GENERIC),)
    return OperationDefinition("minfin." + name, 1, "minfin." + name + ".v1", request, response,
        processing=OperationSemantics(() if snapshot or name.startswith("read_") else (stage,),
            function=ProcessingFunction.ENCODE if snapshot else ProcessingFunction.REPLAY if name.startswith("read_") else ProcessingFunction.PROCESS, inputs=(InputPort("input", source, path),),
            outputs=outputs, parameters=parameters, summary={
                "integrate": "Map reviewed or explicitly bound source rows to qualified observations with exact periods, units and lineage.",
                "observation_snapshot": "Encode integrated observations for caller-selected logical storage.",
                "read_observations": "Restore every qualified observation from a pinned complete dataset.",
                "summary_snapshot": "Retain the calculation result, method version and exact source-flake identity.",
                "read_summary": "Replay retained headlines independently of current source data or calculator implementation.",
                "prepare_view": "Prepare admitted headline metrics and qualified comparisons for display.",
                "view_snapshot": "Encode the prepared view for independent storage and replay.",
                "read_view": "Restore a prepared view without rebuilding its analytics.",
                "render_view": "Render a prepared view using an explicitly selected portable format.",
            }[name]))

INTEGRATE = _op("integrate", IntegrateRequest, ObservationBatch, S.INTEGRATE, _FLAKE, "flake", _BATCH,
                parameters=("dataset_id", "release_id", "bindings"))
OBSERVATION_SNAPSHOT = _op("observation_snapshot", ObservationSnapshotRequest, DatasetSnapshot, S.INGEST,
                         _BATCH, "batch", _SNAPSHOT, parameters=("dataset_id", "version_id"), snapshot=True)
READ_OBSERVATIONS = _op("read_observations", ReadObservationsRequest, ObservationBatch, S.READ_EXTRACT,
                       _SNAPSHOT, "snapshot", _BATCH)
SUMMARY_SNAPSHOT = _op("summary_snapshot", SummarySnapshotRequest, DatasetSnapshot, S.PRESERVE,
                      _HEADLINES, "summary", _CALC, parameters=("dataset_id", "version_id"), snapshot=True)
READ_SUMMARY = _op("read_summary", ReadSummaryRequest, HeadlineSummary, S.READ_EXTRACT, _CALC, "snapshot", _HEADLINES)
PREPARE_VIEW = _op("prepare_view", PrepareHeadlineViewRequest, ObservationView, S.VIEW,
                  _HEADLINES, "summary", _VIEW, parameters=("view_id", "metric_ids"))
VIEW_SNAPSHOT = _op("view_snapshot", ViewSnapshotRequest, DatasetSnapshot, S.PRESERVE,
                   _VIEW, "view", _VIEW_SNAPSHOT, parameters=("dataset_id", "version_id"), snapshot=True)
READ_VIEW = _op("read_view", ReadViewRequest, ObservationView, S.READ_EXTRACT, _VIEW_SNAPSHOT, "snapshot", _VIEW)
RENDER_VIEW = _op("render_view", RenderViewRequest, Representation, S.RENDER, _VIEW, "view",
                 DataContract("observations.view.representation", 1, DataRole.PRODUCTS), parameters=("format",))
