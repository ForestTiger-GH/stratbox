"""Source identity mapping, reference editions and explicit alignment scope."""
from dataclasses import dataclass
from stratbox.shared.data.releases import ParsedRelease
from stratbox.shared.data.observations import SubjectRef, MetricRef

@dataclass(frozen=True, slots=True)
class OfficeSubjectMapping:
    source: SubjectRef
    target: SubjectRef
    edition: str

@dataclass(frozen=True, slots=True)
class OfficeRegionMapping:
    source_label: str
    region_id: str
    edition: str

@dataclass(frozen=True, slots=True)
class OfficeMetricMapping:
    source_id: str
    target: MetricRef
    edition: str

@dataclass(frozen=True, slots=True)
class AlignOfficesRequest:
    release: ParsedRelease
    dataset_id: str
    version_id: str
    subjects: tuple[OfficeSubjectMapping, ...] = ()
    regions: tuple[OfficeRegionMapping, ...] = ()
    metrics: tuple[OfficeMetricMapping, ...] = ()
    require_geography: bool = False
