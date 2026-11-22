"""Typed, lightweight Minfin publication/flake/notification operation contracts."""
from __future__ import annotations

from stratbox.core.execution import OperationDefinition, OperationSemantics, ProcessingStage, InputPort, OutputPort
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from .pipeline_models import (
    UpdateRequest, UpdatePlan, BuildFlakeRequest, FlakeTable,
    RenderFlakeRequest, SummaryRequest, HeadlineSummary,
    NoticeRequest, NoticePreparation,
)

_INDEX = DataContract("minfin.publication_index", 1, None)
_CELLS = DataContract("minfin.source_cells", 1, DataRole.EXTRACTS)
_FLAKE = DataContract("minfin.flake", 1, DataRole.EXTRACTS)
_SUMMARY = DataContract("minfin.headlines", 1, DataRole.PRODUCTS)
_NOTICE = DataContract("minfin.notice_preparation", 1, None)

PLAN_UPDATES = OperationDefinition(
    "minfin.plan_updates", 1, "minfin.publisher-marker-check-1", UpdateRequest, UpdatePlan,
    processing=OperationSemantics((ProcessingStage.INSPECT,),
        inputs=(InputPort("index", _INDEX, "index"),),
        outputs=(OutputPort("plan", DataContract("minfin.update_plan", 1, None)),),
        parameters=("target", "selected_sources", "method_version"),
        summary="Compare publisher document modification markers to caller-owned confirmed checkpoints without downloading XLSX."),
)
BUILD_FLAKE = OperationDefinition(
    "minfin.build_flake", 1, "minfin.flake.v1", BuildFlakeRequest, FlakeTable,
    limits=ExecutionBudget(cells=500_000, output_bytes=64 * 1024 * 1024),
    processing=OperationSemantics((ProcessingStage.EXTRACT,),
        inputs=(InputPort("source", _CELLS, "extract"),),
        outputs=(OutputPort("flake", _FLAKE),),
        parameters=("source_id", "selected_sheet"),
        summary="Clean the source-local workbook to one wide flake; strip document decoration and normalize economic period headers."),
)
RENDER_FLAKE = OperationDefinition(
    "minfin.render_flake", 1, "minfin.flake-csv.v1", RenderFlakeRequest, Representation,
    limits=ExecutionBudget(output_bytes=64 * 1024 * 1024),
    processing=OperationSemantics((ProcessingStage.RENDER,),
        inputs=(InputPort("flake", _FLAKE, "flake"),),
        outputs=(OutputPort("csv", DataContract("minfin.flake.csv", 1, DataRole.EXTRACTS)),),
        summary="Render a clean deterministic UTF-8 CSV for optional consumer-owned flake storage."),
)
SUMMARIZE = OperationDefinition(
    "minfin.summarize", 1, "minfin.headlines.v1", SummaryRequest, HeadlineSummary,
    processing=OperationSemantics((ProcessingStage.CALCULATE,),
        inputs=(InputPort("flake", _FLAKE, "flake"),),
        outputs=(OutputPort("summary", _SUMMARY),),
        parameters=("period_id",),
        summary="Calculate three budget headlines or NWF total/liquid stocks and same-period prior-year percentages."),
)
PREPARE_NOTICE = OperationDefinition(
    "minfin.prepare_notice", 1, "minfin.notice-facts.v1", NoticeRequest, NoticePreparation,
    processing=OperationSemantics((ProcessingStage.VIEW,),
        inputs=(InputPort("summary", _SUMMARY, "summary"),
                InputPort("asset", DataContract("minfin.asset", 1, None), "asset"),
                InputPort("decision", DataContract("minfin.update_decision", 1, None), "decision")),
        outputs=(OutputPort("preparation", _NOTICE),),
        parameters=("include_initial",),
        summary="Prepare a source-qualified, channel-neutral notification candidate; initial loads are quiet by default."),
)