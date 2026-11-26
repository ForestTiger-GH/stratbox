"""Territory-label candidates, explicitly distinct from statistical perimeters."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Literal
from stratbox.shared.data.observations import SubjectRef
from stratbox.shared.identity import ByteIdentity
GEOGRAPHY_KINDS = frozenset({'country', 'federal_district', 'subject', 'statistical_aggregate', 'other', 'municipality', 'municipal_district', 'municipal_okrug', 'urban_okrug', 'urban_settlement', 'rural_settlement', 'intracity_area'})

@dataclass(frozen=True, slots=True)
class RegionNameContext:
    source_family: str | None = None
    as_of: date | None = None
    observed_kind: str | None = None
    source_code: str | None = None
    code_namespace: str | None = None
    perimeter_hint: str | None = None

    def __post_init__(self) -> None:
        if self.as_of is not None and type(self.as_of) is not date:
            raise ValueError('Region matching date must be a date')
        if self.observed_kind is not None and self.observed_kind not in GEOGRAPHY_KINDS:
            raise ValueError('Unknown region context kind')
        for value in (self.source_family, self.source_code, self.code_namespace, self.perimeter_hint):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError('Region context fields must be nonempty strings')
        if bool(self.source_code) != bool(self.code_namespace):
            raise ValueError('Verified region code requires an explicit namespace')

@dataclass(frozen=True, slots=True)
class RegionNameRule:
    rule_id: str
    alias: str
    canonical_name: str
    subject_namespace: str
    subject_id: str
    kind: str
    perimeter_id: str | None = None
    source_family: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    review_basis: str | None = None

@dataclass(frozen=True, slots=True)
class RegionNameMatch:
    raw_name: str
    normalized_name: str
    status: Literal['exact', 'alias', 'unmatched', 'ambiguous', 'out_of_scope']
    subject: SubjectRef | None
    canonical_name: str | None
    perimeter_id: str | None
    reference_content_id: str
    matched_rule_id: str | None = None
    candidates: tuple[str, ...] = ()
    ruleset_identity: ByteIdentity | None = None
    reference_id: str | None = None
    reference_snapshot_identity: ByteIdentity | None = None
    provenance: Literal['packaged', 'supplied'] = 'packaged'
