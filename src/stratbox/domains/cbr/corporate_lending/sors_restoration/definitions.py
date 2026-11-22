"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from dataclasses import dataclass
from stratbox.core.limits import ExecutionBudget
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import SorsCrosswalkConfig, SorsPivotRequest, SorsRunConfig, SorsSourceBundle, SorsSourceFiles, SorsSourceInputs, SorsWorkbookRequest
from .results import SorsCrosswalkResult, SorsPivotResult, SorsRestorationResult, SorsWorkbookResult

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
)

LOAD = OperationDefinition(
    "cbr.sors.load_sources",
    3,
    "sors-source-bundle-1",
    LoadSorsRequest,
    SorsSourceBundle, limits=_TABLES,
)

RESTORE = OperationDefinition(
    "cbr.sors.restore",
    3,
    "sors-multiscope-rounding-dominance-2026.7",
    RestoreSorsRequest,
    SorsRestorationResult, limits=_TABLES,
)

CROSSWALK = OperationDefinition(
    "cbr.sors.crosswalk",
    2,
    "sors-crosswalk-1",
    CrosswalkSorsRequest,
    SorsCrosswalkResult, limits=_TABLES,
)

PIVOT = OperationDefinition(
    "cbr.sors.build_pivot", 2, "sors-pivot-1", PivotSorsRequest, SorsPivotResult, limits=_TABLES,
)

RENDER = OperationDefinition(
    "cbr.sors.render_workbook", 2, "sors-xlsx-1", RenderSorsRequest, SorsWorkbookResult, limits=_TABLES,
)

