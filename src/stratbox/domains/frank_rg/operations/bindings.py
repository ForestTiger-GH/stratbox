"""Resolve declarative report sources to registered, typed domain methods."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ..publications.catalog import families, family
from ..publications.contracts import SourceFamily, SourceSeries
from ..publications.profiles import (
    DiscoveryProfile, IdentificationProfile, NamingProfile, RecognitionRule, SelectionProfile,
    discovery_profile, identification_profile, naming_profile, selection_profile,
)


@dataclass(frozen=True, slots=True)
class BoundFamily:
    source: SourceFamily
    discovery: DiscoveryProfile
    identification: IdentificationProfile
    selection: SelectionProfile
    naming: NamingProfile


@dataclass(frozen=True, slots=True)
class BoundSource:
    parent: BoundFamily
    series: SourceSeries
    rule: RecognitionRule


@lru_cache(maxsize=128)
def bind_family(family_id: str) -> BoundFamily:
    source = family(family_id)
    refs = source.profiles
    discovery = discovery_profile(refs.discovery)
    identification = identification_profile(refs.identification)
    selection = selection_profile(refs.selection)
    naming = naming_profile(refs.naming)
    if {item.slot for item in source.series} != {item.slot for item in identification.rules}:
        raise ValueError("frg.profile.series_slots_incomplete")
    for item in source.series:
        if item.periodicity != identification.rule(item.slot).periodicity:
            raise ValueError("frg.profile.periodicity_mismatch")
    return BoundFamily(source, discovery, identification, selection, naming)


@lru_cache(maxsize=1024)
def bind_source(source_id: str) -> BoundSource:
    for source in families():
        for item in source.series:
            if item.source_id == source_id:
                bound = bind_family(source.family_id)
                return BoundSource(bound, item, bound.identification.rule(item.slot))
    raise ValueError("frg.registry.unknown_source")


def validate_all_profiles() -> tuple[BoundSource, ...]:
    result = tuple(bind_source(item.source_id) for source in families() for item in source.series)
    from ..publications.naming import normalize_label_text
    labels = [normalize_label_text(item.rule.canonical_label) for item in result]
    if len(labels) != len(set(labels)):
        raise ValueError("frg.profile.ambiguous_canonical_label")
    return result


__all__ = ("BoundFamily", "BoundSource", "bind_family", "bind_source", "validate_all_profiles")
