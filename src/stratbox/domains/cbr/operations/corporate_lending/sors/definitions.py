"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition


from dataclasses import dataclass
from stratbox.core.limits import ExecutionBudget
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

READ = _registry_definition('cbr.sors.read_source_files', 2)

LOAD = _registry_definition('cbr.sors.prepare_from_originals', 1)

RESTORE = _registry_definition('cbr.sors.restore', 5)

CROSSWALK = _registry_definition('cbr.sors.crosswalk', 3)

PIVOT = _registry_definition('cbr.sors.build_pivot', 3)

PREPARE = _registry_definition('cbr.sors.prepare_inputs', 1)

PREPARE_FROM_FLAKES = _registry_definition('cbr.sors.prepare_from_flakes', 1)

RESTORE_FROM_ORIGINALS = _registry_definition('cbr.sors.restore_from_originals', 1)

VIEWS = _registry_definition('cbr.sors.build_views', 1)

RENDER = _registry_definition('cbr.sors.render_views', 1)


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


BUNDLE_SNAPSHOT = _registry_definition('cbr.sors.bundle_snapshot', 1)
READ_BUNDLE_SNAPSHOT = _registry_definition('cbr.sors.read_bundle_snapshot', 1)
RESTORATION_SNAPSHOT = _registry_definition('cbr.sors.restoration_snapshot', 1)
READ_RESTORATION_SNAPSHOT = _registry_definition('cbr.sors.read_restoration_snapshot', 1)
CROSSWALK_SNAPSHOT = _registry_definition('cbr.sors.crosswalk_snapshot', 1)
READ_CROSSWALK_SNAPSHOT = _registry_definition('cbr.sors.read_crosswalk_snapshot', 1)


@dataclass(frozen=True, slots=True)
class SorsViewSnapshotRequest:
    value: SorsViewPack
    dataset_id: str = "cbr.sors.views"
    version_id: str | None = None

VIEW_SNAPSHOT = _registry_definition('cbr.sors.view_snapshot', 1)
READ_VIEW_SNAPSHOT = _registry_definition('cbr.sors.read_view_snapshot', 1)
