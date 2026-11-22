"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from dataclasses import dataclass
from stratbox.core.limits import ExecutionBudget
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import (
    SorsCrosswalkConfig,
    SorsPivotRequest,
    SorsRunConfig,
    SorsSourceBundle,
    SorsSourceFiles,
    SorsSourceInputs,
    SorsWorkbookRequest,
)
from .results import (
    SorsCrosswalkResult,
    SorsPivotResult,
    SorsRestorationResult,
    SorsWorkbookResult,
)

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)


@dataclass(frozen=True, slots=True)
class LoadSorsRequest:
    sources: SorsSourceInputs
    config: SorsRunConfig


@dataclass(frozen=True, slots=True)
class RestoreSorsRequest:
    source: SorsSourceInputs | SorsSourceBundle
    config: SorsRunConfig


@dataclass(frozen=True, slots=True)
class CrosswalkSorsRequest:
    strict: SorsRestorationResult
    config: SorsCrosswalkConfig


@dataclass(frozen=True, slots=True)
class PivotSorsRequest:
    result: SorsRestorationResult | SorsCrosswalkResult
    pivot: SorsPivotRequest


@dataclass(frozen=True, slots=True)
class RenderSorsRequest:
    result: SorsRestorationResult | SorsCrosswalkResult
    workbook: SorsWorkbookRequest = SorsWorkbookRequest()


_TABLES = ExecutionBudget(cells=80_000_000, output_bytes=256 * 1024 * 1024)

READ = OperationDefinition(
    "cbr.sors.read_source_files",
    1,
    "sors-file-read-1",
    SorsSourceFiles,
    SorsSourceInputs,
    frozenset({"filestore"}),
    processing=OperationSemantics(
        stages=(ProcessingStage.PRESERVE,),
        summary="Read a caller-selected bundle of retained source files with bounded byte checks.",
        outputs=(
            OutputPort(
                "sources", DataContract("cbr.sors.source_inputs", 1, DataRole.ORIGINALS)
            ),
        ),
        parameters=(
            "regional_traditional",
            "national_okved2",
            "federal_district_okved2",
            "national_traditional",
            "sme_national_totals",
            "sme_national_okved2",
            "sme_ie_national_okved2",
            "sme_federal_district_okved2",
            "sme_regional_totals",
            "sme_ie_regional_totals",
            "regional_totals_history",
        ),
    ),
)

LOAD = OperationDefinition(
    "cbr.sors.load_sources",
    3,
    "sors-source-bundle-1",
    LoadSorsRequest,
    SorsSourceBundle,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT,),
        summary="Load and align the complete SORS constraint input bundle.",
        inputs=(
            InputPort(
                "sources",
                DataContract("cbr.sors.source_inputs", 1, DataRole.ORIGINALS),
                path="sources",
            ),
        ),
        outputs=(
            OutputPort(
                "bundle", DataContract("cbr.sors.source_bundle", 1, DataRole.EXTRACTS)
            ),
        ),
        parameters=("config",),
    ),
)

RESTORE = OperationDefinition(
    "cbr.sors.restore",
    3,
    "sors-multiscope-rounding-dominance-2026.7",
    RestoreSorsRequest,
    SorsRestorationResult,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.CALCULATE,),
        summary="Run qualified SORS reconstruction with explicit inference and solver evidence.",
        inputs=(
            InputPort(
                "bundle",
                DataContract("cbr.sors.source_bundle", 1, DataRole.EXTRACTS),
                path="source",
                alternatives=(
                    DataContract("cbr.sors.source_inputs", 1, DataRole.ORIGINALS),
                ),
            ),
        ),
        outputs=(
            OutputPort(
                "result", DataContract("cbr.sors.restoration", 1, DataRole.EXTRACTS)
            ),
        ),
        parameters=("config",),
    ),
)

CROSSWALK = OperationDefinition(
    "cbr.sors.crosswalk",
    2,
    "sors-crosswalk-1",
    CrosswalkSorsRequest,
    SorsCrosswalkResult,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.CALCULATE,),
        summary="Calculate an edition-aware crosswalk from supplied SORS results.",
        inputs=(
            InputPort(
                "strict",
                DataContract("cbr.sors.restoration", 1, DataRole.EXTRACTS),
                path="strict",
            ),
        ),
        outputs=(
            OutputPort(
                "result", DataContract("cbr.sors.crosswalk", 1, DataRole.EXTRACTS)
            ),
        ),
        parameters=("config",),
    ),
)

PIVOT = OperationDefinition(
    "cbr.sors.build_pivot",
    2,
    "sors-pivot-1",
    PivotSorsRequest,
    SorsPivotResult,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.VIEW,),
        summary="Construct a selected SORS presentation cut without narrowing its computational scope.",
        inputs=(
            InputPort(
                "result",
                DataContract("cbr.sors.restoration", 1, DataRole.EXTRACTS),
                path="result",
                alternatives=(
                    DataContract("cbr.sors.crosswalk", 1, DataRole.EXTRACTS),
                ),
            ),
        ),
        outputs=(
            OutputPort("pivot", DataContract("cbr.sors.pivot", 1, DataRole.PRODUCTS)),
        ),
        parameters=("pivot",),
    ),
)

RENDER = OperationDefinition(
    "cbr.sors.render_workbook",
    2,
    "sors-xlsx-1",
    RenderSorsRequest,
    SorsWorkbookResult,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.RENDER,),
        summary="Render a supplied SORS result into workbook bytes.",
        inputs=(
            InputPort(
                "result",
                DataContract("cbr.sors.restoration", 1, DataRole.EXTRACTS),
                path="result",
                alternatives=(
                    DataContract("cbr.sors.crosswalk", 1, DataRole.EXTRACTS),
                ),
            ),
        ),
        outputs=(
            OutputPort(
                "workbook",
                DataContract("cbr.sors.workbook", 1, DataRole.PRODUCTS),
                path="representation",
            ),
        ),
        parameters=("workbook",),
    ),
)
