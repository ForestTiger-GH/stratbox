"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from dataclasses import dataclass
from stratbox.core.limits import ExecutionBudget
from stratbox.core.execution.contracts import OperationDefinition
from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsCrosswalkConfig
from stratbox.domains.cbr.products.corporate_lending.sors.contracts import SorsPivotRequest
from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsRunConfig
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceBundle
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceFiles
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceInputs
from stratbox.domains.cbr.products.corporate_lending.sors.contracts import SorsWorkbookRequest
from stratbox.domains.cbr.analytics.corporate_lending.sors.results import SorsCrosswalkResult
from stratbox.domains.cbr.products.corporate_lending.sors.results import SorsPivotResult
from stratbox.domains.cbr.analytics.corporate_lending.sors.results import SorsRestorationResult
from stratbox.domains.cbr.products.corporate_lending.sors.results import SorsWorkbookResult, SorsViewPack

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.core.execution.semantics import (
    InputPort,
    OutputPort,
    OperationSemantics,
    ProcessingStage,
)


@dataclass(frozen=True, slots=True)
class PrepareSorsOriginalsRequest:
    sources: SorsSourceInputs
    config: SorsRunConfig


@dataclass(frozen=True, slots=True)
class RestoreSorsRequest:
    source: SorsSourceBundle
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
class PrepareSorsRequest:
    sources: SorsSourceInputs
    config: SorsRunConfig


@dataclass(frozen=True, slots=True)
class PrepareSorsFlakesRequest:
    sources: SorsSourceInputs
    config: SorsRunConfig


@dataclass(frozen=True, slots=True)
class RestoreSorsOriginalsRequest:
    sources: SorsSourceInputs
    config: SorsRunConfig


@dataclass(frozen=True, slots=True)
class BuildSorsViewsRequest:
    result: SorsRestorationResult | SorsCrosswalkResult
    workbook: SorsWorkbookRequest = SorsWorkbookRequest()


@dataclass(frozen=True, slots=True)
class RenderSorsRequest:
    views: SorsViewPack


_TABLES = ExecutionBudget(cells=80_000_000, output_bytes=256 * 1024 * 1024)

READ = OperationDefinition(
    "cbr.sors.read_source_files",
    2,
    "sors-file-read-1",
    SorsSourceFiles,
    SorsSourceInputs,
    frozenset({"filestore"}),
    processing=OperationSemantics(
        stages=(ProcessingStage.ACQUIRE,),
        summary="Read a caller-selected bundle of retained source files with bounded byte checks.",
        outputs=(
            OutputPort(
                "sources", DataContract("cbr.sors.source_inputs", 2)
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
    "cbr.sors.prepare_from_originals",
    1,
    "sors-source-bundle-2",
    PrepareSorsOriginalsRequest,
    SorsSourceBundle,
    limits=_TABLES,
    processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT, ProcessingStage.INTEGRATE),
        composition=True,
        summary="Load and align the complete SORS constraint input bundle.",
        inputs=(
            InputPort(
                "sources",
                DataContract("cbr.sors.source_inputs", 2),
                path="sources",
            ),
        ),
        outputs=(
            OutputPort(
                "bundle", DataContract("cbr.sors.source_bundle", 2, DataRole.INTEGRATED)
            ),
        ),
        parameters=("config",),
    ),
)

RESTORE = OperationDefinition(
    "cbr.sors.restore",
    5,
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
                DataContract("cbr.sors.source_bundle", 2, DataRole.INTEGRATED),
                path="source",
            ),
        ),
        outputs=(
            OutputPort(
                "result", DataContract("cbr.sors.restoration", 2, DataRole.INTEGRATED)
            ),
        ),
        parameters=("config",),
    ),
)

CROSSWALK = OperationDefinition(
    "cbr.sors.crosswalk",
    3,
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
                DataContract("cbr.sors.restoration", 2, DataRole.INTEGRATED),
                path="strict",
            ),
        ),
        outputs=(
            OutputPort(
                "result", DataContract("cbr.sors.crosswalk", 2, DataRole.INTEGRATED)
            ),
        ),
        parameters=("config",),
    ),
)

PIVOT = OperationDefinition(
    "cbr.sors.build_pivot",
    3,
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
                DataContract("cbr.sors.restoration", 2, DataRole.INTEGRATED),
                path="result",
                alternatives=(
                    DataContract("cbr.sors.crosswalk", 2, DataRole.INTEGRATED),
                ),
            ),
        ),
        outputs=(
            OutputPort("pivot", DataContract("cbr.sors.pivot", 1, DataRole.PRODUCTS)),
        ),
        parameters=("pivot",),
    ),
)

PREPARE = OperationDefinition(
    "cbr.sors.prepare_inputs", 1, "sors-source-bundle-2", PrepareSorsRequest, SorsSourceBundle,
    limits=_TABLES, processing=OperationSemantics(
        stages=(ProcessingStage.INTEGRATE,),
        summary="Align retained source observations and the regional industry flake into a qualified SORS input bundle.",
        inputs=(InputPort("sources", DataContract("cbr.sors.source_observations", 1, DataRole.EXTRACTS), path="sources"),),
        outputs=(OutputPort("bundle", DataContract("cbr.sors.source_bundle", 2, DataRole.INTEGRATED)),),
        parameters=("config",)))

PREPARE_FROM_FLAKES = OperationDefinition(
    "cbr.sors.prepare_from_flakes", 1, "sors-source-flakes-composition-1", PrepareSorsFlakesRequest, SorsSourceBundle,
    limits=_TABLES, processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT, ProcessingStage.INTEGRATE), composition=True,
        summary="Interpret retained workbook flakes and align source observations for SORS.",
        inputs=(InputPort("sources", DataContract("cbr.sors.source_flakes", 1, DataRole.EXTRACTS), path="sources"),),
        outputs=(OutputPort("bundle", DataContract("cbr.sors.source_bundle", 2, DataRole.INTEGRATED)),),
        parameters=("config",)))

RESTORE_FROM_ORIGINALS = OperationDefinition(
    "cbr.sors.restore_from_originals", 1, "sors-originals-composition-1", RestoreSorsOriginalsRequest, SorsRestorationResult,
    limits=_TABLES, processing=OperationSemantics(
        stages=(ProcessingStage.EXTRACT, ProcessingStage.INTEGRATE, ProcessingStage.CALCULATE), composition=True,
        summary="Explicitly extract originals, prepare a complete input bundle and restore SORS data.",
        inputs=(InputPort("sources", DataContract("cbr.sors.source_inputs", 2), path="sources"),),
        outputs=(OutputPort("result", DataContract("cbr.sors.restoration", 2, DataRole.INTEGRATED)),),
        parameters=("config",)))

VIEWS = OperationDefinition(
    "cbr.sors.build_views", 1, "sors-prepared-views-1", BuildSorsViewsRequest, SorsViewPack,
    limits=_TABLES, processing=OperationSemantics(
        stages=(ProcessingStage.VIEW,), summary="Prepare every selected SORS sheet, including pivots and audit tables.",
        inputs=(InputPort("result", DataContract("cbr.sors.restoration", 2, DataRole.INTEGRATED), path="result",
            alternatives=(DataContract("cbr.sors.crosswalk", 2, DataRole.INTEGRATED),)),),
        outputs=(OutputPort("views", DataContract("cbr.sors.views", 1, DataRole.PRODUCTS)),),
        parameters=("workbook",)))

RENDER = OperationDefinition(
    "cbr.sors.render_views", 1, "sors-xlsx-2", RenderSorsRequest, SorsWorkbookResult,
    limits=_TABLES, processing=OperationSemantics(
        stages=(ProcessingStage.RENDER,), summary="Render supplied prepared SORS sheets without data selection or calculation.",
        inputs=(InputPort("views", DataContract("cbr.sors.views", 1, DataRole.PRODUCTS), path="views"),),
        outputs=(OutputPort("workbook", DataContract("cbr.sors.workbook", 1, DataRole.PRODUCTS), path="representation"),)))



@dataclass(frozen=True, slots=True)
class SorsBundleSnapshotRequest:
    value: SorsSourceBundle
    dataset_id: str = "cbr.sors.bundle"
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class SorsRestorationSnapshotRequest:
    value: SorsRestorationResult
    dataset_id: str = "cbr.sors.restoration"
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class SorsCrosswalkSnapshotRequest:
    value: SorsCrosswalkResult
    dataset_id: str = "cbr.sors.crosswalk"
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReadSorsSnapshotRequest:
    snapshot: DatasetSnapshot


def _snapshot_definition(name, request_type, contract, snapshot_contract):
    return OperationDefinition(f"cbr.sors.{name}", 1, "sors-replay-context-1", request_type, DatasetSnapshot, limits=_TABLES,
        processing=OperationSemantics(stages=(ProcessingStage.RENDER,),
            inputs=(InputPort("value", contract, path="value"),),
            outputs=(OutputPort("snapshot", snapshot_contract), OutputPort("dataset", DataContract("dataset.snapshot"))),
            parameters=("dataset_id", "version_id"), summary="Encode all SORS data and declared continuation dependencies."))


def _read_snapshot_definition(name, result_type, contract, snapshot_contract):
    return OperationDefinition(f"cbr.sors.{name}", 1, "sors-replay-context-1", ReadSorsSnapshotRequest, result_type, limits=_TABLES,
        processing=OperationSemantics(stages=(ProcessingStage.READ_EXTRACT,),
            inputs=(InputPort("snapshot", snapshot_contract, path="snapshot", alternatives=(DataContract("dataset.snapshot"),)),),
            outputs=(OutputPort("value", contract),), summary="Validate and reconstruct the complete SORS continuation context."))


BUNDLE_SNAPSHOT = _snapshot_definition("bundle_snapshot", SorsBundleSnapshotRequest,
    DataContract("cbr.sors.source_bundle", 2, DataRole.INTEGRATED), DataContract("cbr.sors.bundle.snapshot", 1, DataRole.INTEGRATED))
READ_BUNDLE_SNAPSHOT = _read_snapshot_definition("read_bundle_snapshot", SorsSourceBundle,
    DataContract("cbr.sors.source_bundle", 2, DataRole.INTEGRATED), DataContract("cbr.sors.bundle.snapshot", 1, DataRole.INTEGRATED))
RESTORATION_SNAPSHOT = _snapshot_definition("restoration_snapshot", SorsRestorationSnapshotRequest,
    DataContract("cbr.sors.restoration", 2, DataRole.INTEGRATED), DataContract("cbr.sors.restoration.snapshot", 1, DataRole.INTEGRATED))
READ_RESTORATION_SNAPSHOT = _read_snapshot_definition("read_restoration_snapshot", SorsRestorationResult,
    DataContract("cbr.sors.restoration", 2, DataRole.INTEGRATED), DataContract("cbr.sors.restoration.snapshot", 1, DataRole.INTEGRATED))
CROSSWALK_SNAPSHOT = _snapshot_definition("crosswalk_snapshot", SorsCrosswalkSnapshotRequest,
    DataContract("cbr.sors.crosswalk", 2, DataRole.INTEGRATED), DataContract("cbr.sors.crosswalk.snapshot", 1, DataRole.INTEGRATED))
READ_CROSSWALK_SNAPSHOT = _read_snapshot_definition("read_crosswalk_snapshot", SorsCrosswalkResult,
    DataContract("cbr.sors.crosswalk", 2, DataRole.INTEGRATED), DataContract("cbr.sors.crosswalk.snapshot", 1, DataRole.INTEGRATED))


@dataclass(frozen=True, slots=True)
class SorsViewSnapshotRequest:
    value: SorsViewPack
    dataset_id: str = "cbr.sors.views"
    version_id: str | None = None

VIEW_SNAPSHOT = _snapshot_definition("view_snapshot", SorsViewSnapshotRequest,
    DataContract("cbr.sors.views", 1, DataRole.PRODUCTS), DataContract("cbr.sors.views.snapshot", 1, DataRole.PRODUCTS))
READ_VIEW_SNAPSHOT = _read_snapshot_definition("read_view_snapshot", SorsViewPack,
    DataContract("cbr.sors.views", 1, DataRole.PRODUCTS), DataContract("cbr.sors.views.snapshot", 1, DataRole.PRODUCTS))
