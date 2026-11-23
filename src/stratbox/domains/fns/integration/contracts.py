"""Domain-qualified observations retain selected scope and reference editions."""
from dataclasses import dataclass

from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.identity import ByteIdentity

from ..publications.contracts import ReleaseContext
from ..tables.contracts import FieldDisposition


@dataclass(frozen=True, slots=True)
class FnsDataset:
    context: ReleaseContext
    source_identity: ByteIdentity
    batch: ObservationBatch
    profile_id: str
    coverage: SnapshotCoverage
    qualifications: tuple[str, ...]
    dispositions: tuple[FieldDisposition, ...] = ()
    details_json: str = "{}"
    parents: tuple[ByteIdentity, ...] = ()

    def __post_init__(self):
        if (not isinstance(self.context, ReleaseContext) or not isinstance(self.source_identity, ByteIdentity)
                or not isinstance(self.batch, ObservationBatch)
                or not self.batch.dataset_id.startswith(self.context.series_id + ".")
                or not isinstance(self.profile_id, str) or not self.profile_id
                or not isinstance(self.coverage, SnapshotCoverage)
                or not isinstance(self.qualifications, tuple) or any(type(item) is not str for item in self.qualifications)
                or not isinstance(self.dispositions, tuple) or any(not isinstance(item, FieldDisposition) for item in self.dispositions)
                or not isinstance(self.parents, tuple) or len(set(self.parents)) != len(self.parents)
                or any(not isinstance(item, ByteIdentity) for item in self.parents)):
            raise ValueError("fns.dataset_invalid")

    @property
    def identity(self):
        from .snapshots import dataset_snapshot
        return dataset_snapshot(self).identity
