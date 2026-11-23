"""Explicit source-to-observation alignment requests."""
from dataclasses import dataclass
from datetime import date
from stratbox.domains.cbr.tables.reporting_forms.contracts import FormSnapshot
from stratbox.shared.data.observations import PeriodRef, SubjectRef

@dataclass(frozen=True, slots=True)
class FormSubjectMapping:
    source_namespace: str
    source_id: str
    target: SubjectRef
    edition: str

@dataclass(frozen=True, slots=True)
class AlignFormRequest:
    snapshots: tuple[FormSnapshot, ...]
    dataset_id: str
    version_id: str
    periods: tuple[tuple[date, PeriodRef], ...] = ()
    subjects: tuple[FormSubjectMapping, ...] = ()
