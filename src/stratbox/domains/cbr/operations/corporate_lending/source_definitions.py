"""Independent source-observation operations for corporate publications."""

from stratbox.core.registry.operations import definition as _registry_definition

from dataclasses import dataclass
from stratbox.core.limits import ExecutionBudget
from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake
from stratbox.domains.cbr.tables.corporate_lending.observations import CorporateSourceDataset
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot

SOURCE = DataContract("cbr.corporate_lending.source_observations", 1, DataRole.EXTRACTS)
SNAPSHOT = DataContract("cbr.corporate_lending.source_observations.snapshot", 1, DataRole.EXTRACTS)


@dataclass(frozen=True, slots=True)
class ExtractCorporateObservationsRequest:
    flake: WorkbookFlake
    periods: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class CorporateObservationSnapshotRequest:
    value: CorporateSourceDataset
    dataset_id: str = "cbr.corporate_lending.source_observations"
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReadCorporateObservationSnapshotRequest:
    snapshot: DatasetSnapshot


EXTRACT = _registry_definition('cbr.corporate_lending.extract_observations')

ENCODE = _registry_definition('cbr.corporate_lending.observation_snapshot')

DECODE = _registry_definition('cbr.corporate_lending.read_observation_snapshot')
