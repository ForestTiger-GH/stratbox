from dataclasses import dataclass
from datetime import date, tzinfo

from stratbox.data import AcquiredSource, SourcePayload


@dataclass(frozen=True, slots=True)
class AcquireOfficesRequest:
    capture_zone: tzinfo
    baseline: AcquiredSource | None = None


@dataclass(frozen=True, slots=True)
class AcquiredOffices:
    source: AcquiredSource
    capture_date: date

    @property
    def payload(self) -> SourcePayload:
        return self.source.payload


@dataclass(frozen=True, slots=True)
class ParseOfficesRequest:
    payload: SourcePayload
    captured_on: date
    official_as_of: date | None = None
