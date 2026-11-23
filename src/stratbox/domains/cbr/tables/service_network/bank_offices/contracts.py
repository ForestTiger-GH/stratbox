from dataclasses import dataclass
from datetime import date, tzinfo

from stratbox.shared.evidence import AcquiredSource, SourcePayload
from stratbox.shared.data.releases import ParsedRelease


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


@dataclass(frozen=True, slots=True)
class ReadOfficesRequest:
    payload: SourcePayload
    captured_on: date
    official_as_of: date | None = None
    period_basis: str | None = None


@dataclass(frozen=True, slots=True)
class SnapshotOfficesRequest:
    release: ParsedRelease
    dataset_id: str
    version_id: str
