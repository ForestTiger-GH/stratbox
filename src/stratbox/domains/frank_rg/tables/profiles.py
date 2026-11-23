"""Truthful availability for all registered workbook sources.

No reviewed business-layout profile is claimed without retained publisher
workbook fixtures. Every source accepts a typed caller-supplied byte-bound
profile; the source filename alone never establishes units or reporting grain.
"""
from dataclasses import dataclass
from ..publications.catalog import all_sources, source


@dataclass(frozen=True, slots=True)
class ProfileAvailability:
    source_id: str
    technical_profile: str = "frg.workbook.cells.v1"
    semantic_state: str = "supplied_profile_required"
    required_evidence: tuple[str, ...] = (
        "original_identity", "cell_coordinates", "subject", "metric_definition_version",
        "unit", "measurement_scale", "quantity_kind", "economic_period", "perimeter",
    )
    reviewed_profile_ids: tuple[str, ...] = ()


def profile_availability(source_id: str) -> ProfileAvailability:
    source(source_id)
    return ProfileAvailability(source_id)


def all_profile_availability() -> tuple[ProfileAvailability, ...]:
    return tuple(profile_availability(x) for x in all_sources())
