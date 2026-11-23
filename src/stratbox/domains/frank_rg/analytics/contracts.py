from dataclasses import dataclass
from stratbox.shared.data.observations import ObservationBatch


@dataclass(frozen=True, slots=True)
class CalculateRequest:
    before: ObservationBatch
    after: ObservationBatch
    dataset_id: str
    release_id: str
