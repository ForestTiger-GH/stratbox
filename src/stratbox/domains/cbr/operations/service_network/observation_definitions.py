"""Portable aligned observation metadata."""

from stratbox.core.registry.operations import definition as _registry_definition

from dataclasses import dataclass
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.snapshots import DatasetSnapshot

@dataclass(frozen=True, slots=True)
class SnapshotOfficeObservationsRequest:
    batch: ObservationBatch
    dataset_id: str
    version_id: str

SNAPSHOT = _registry_definition('cbr.service_network.observations_snapshot', 1)
RESTORE = _registry_definition('cbr.service_network.restore_observations', 1)
