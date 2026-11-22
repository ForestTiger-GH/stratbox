"""Read-only resolution of logical sources and registered domain profiles.

One source registry describes semantics; profiles implement publisher-specific
rules; the independent OperationCatalog keeps all executable operation IDs.
Resolution creates no network, storage or notification side effects.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache

from ..publications.catalog import family, families
from ..publications.contracts import SourceFamily, SourceSeries
from ..publications.profiles import (
    AcquisitionProfile, acquisition_profile,
    PublicationProfile, IdentificationProfile, publication_profile, identification_profile,
)
from ..tables.profiles import TableProfile, table_profile
from ..analytics.profiles import HeadlineProfile, headline_profile


@dataclass(frozen=True, slots=True)
class BoundFamily:
    source: SourceFamily
    acquisition: AcquisitionProfile
    publication: PublicationProfile
    identification: IdentificationProfile


@dataclass(frozen=True, slots=True)
class BoundSeries:
    parent: BoundFamily
    series: SourceSeries
    table: TableProfile | None
    metrics: HeadlineProfile | None

    @property
    def method_version(self) -> str | None:
        return self.table.method_version if self.table else None


@lru_cache(maxsize=128)
def bind_family(family_id: str) -> BoundFamily:
    source = family(family_id)
    acquisition = acquisition_profile(source.profiles.acquisition)
    publication = publication_profile(source.profiles.discovery)
    identification = identification_profile(source.profiles.identification)
    actual = {item.slot for item in source.series}
    supported = {item.slot for item in identification.rules}
    if actual != supported:
        raise ValueError("minfin.profile.series_slots_incomplete")
    return BoundFamily(source, acquisition, publication, identification)


@lru_cache(maxsize=512)
def bind_series(family_id: str, source_id: str) -> BoundSeries:
    root = bind_family(family_id)
    series = root.source.source(source_id)
    rules = root.identification.rule(series.slot)
    if series.kind == "document":
        if rules.format not in {"pdf", "doc", "docx"}:
            raise ValueError("minfin.profile.document_format_invalid")
        return BoundSeries(root, series, None, None)
    table = table_profile(root.source.profiles.table)
    metrics = headline_profile(root.source.profiles.metrics)
    if rules.format not in table.admitted_formats:
        raise ValueError("minfin.profile.table_format_mismatch")
    if series.basis not in metrics.accepted_basis or series.periodicity not in metrics.periods:
        raise ValueError("minfin.profile.economic_basis_mismatch")
    if series.periodicity == "annual" and series.basis != "annual":
        raise ValueError("minfin.profile.annual_basis_mismatch")
    return BoundSeries(root, series, table, metrics)


def validate_all_profiles() -> tuple[BoundSeries, ...]:
    """Validate all references/slots without importing handlers or executing tasks."""
    return tuple(bind_series(item.family_id, series.source_id)
                 for item in families() for series in item.series)


__all__ = ("BoundFamily", "BoundSeries", "bind_family", "bind_series", "validate_all_profiles")