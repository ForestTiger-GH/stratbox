"""Publisher dates and source identities, independent of observation semantics."""
from dataclasses import dataclass
from datetime import date, datetime
from stratbox.shared.source_publications import SourceAssetIdentity


@dataclass(frozen=True, slots=True)
class ReleaseContext:
    series_id: str
    issue_id: str
    observation_date: date
    asset_id: str = "main"
    published_on: date | None = None
    captured_at: datetime | None = None

    def __post_init__(self):
        SourceAssetIdentity(self.series_id, self.issue_id, self.asset_id)
        if self.series_id not in {"fns.sme", "fns.1yur"}:
            raise ValueError("fns.series_unknown")
        if (not self.issue_id or not self.asset_id or type(self.observation_date) is not date
                or self.published_on is not None and type(self.published_on) is not date):
            raise ValueError("fns.release_context_invalid")
        if self.captured_at is not None and (
                type(self.captured_at) is not datetime or self.captured_at.utcoffset() is None):
            raise ValueError("fns.capture_timezone_required")


@dataclass(frozen=True, slots=True)
class SourceSeries:
    family_id: str
    series_id: str
    title: str
    periodicity: str
    formats: tuple[str, ...]
    acquisition_profile: str
    extract_profile: str
    integration_profile: str
    observation_basis: str
