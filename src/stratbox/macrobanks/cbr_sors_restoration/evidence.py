from __future__ import annotations

# Assumption tiers propagate with latent interval bounds.  Higher numbers mean
# that a bound depends on a weaker publication-level premise.  The tier is not
# a numerical tolerance and never changes the official rounding interval.
STRICT_OFFICIAL_TIER = 0
SOURCE_PRESERVING_TIER = 1
ROUNDING_OPTIMAL_TIER = 2
ROUNDING_PREFERRED_TIER = 3
ROUNDING_SELECTED_TIER = 4

EVIDENCE_TIER = {
    'SOURCE_PUBLISHED': STRICT_OFFICIAL_TIER,
    'LATENT_POINT_IDENTIFIED': STRICT_OFFICIAL_TIER,
    'PUBLISHED_BUCKET_IDENTIFIED': STRICT_OFFICIAL_TIER,
    'PUBLISHED_VALUE_INHERITED': SOURCE_PRESERVING_TIER,
    'PUBLICATION_CLOSURE_IDENTIFIED': SOURCE_PRESERVING_TIER,
    'ROUNDING_OPTIMUM_IDENTIFIED': ROUNDING_OPTIMAL_TIER,
    'ROUNDING_OPTIMUM_CLOSURE': ROUNDING_OPTIMAL_TIER,
    'ROUNDING_PREFERRED': ROUNDING_PREFERRED_TIER,
    'ROUNDING_PREFERRED_CLOSURE': ROUNDING_PREFERRED_TIER,
    'ROUNDING_SELECTED': ROUNDING_SELECTED_TIER,
    'ROUNDING_SELECTED_CLOSURE': ROUNDING_SELECTED_TIER,
}

# Strength is used only to choose the current representative when two facts
# have the same published value.  It must never be confused with assumption
# tier: a larger strength is better, whereas a larger tier is weaker.
EVIDENCE_STRENGTH = {
    'SOURCE_PUBLISHED': 100,
    'LATENT_POINT_IDENTIFIED': 100,
    'PUBLISHED_BUCKET_IDENTIFIED': 90,
    'PUBLISHED_VALUE_INHERITED': 70,
    'PUBLICATION_CLOSURE_IDENTIFIED': 65,
    'ROUNDING_OPTIMUM_IDENTIFIED': 50,
    'ROUNDING_OPTIMUM_CLOSURE': 45,
    'ROUNDING_PREFERRED': 40,
    'ROUNDING_PREFERRED_CLOSURE': 35,
    'ROUNDING_SELECTED': 30,
    'ROUNDING_SELECTED_CLOSURE': 25,
}


def evidence_tier(method: str) -> int:
    try:
        return int(EVIDENCE_TIER[str(method)])
    except KeyError as exc:  # pragma: no cover - defensive contract guard
        raise ValueError(f'Unknown SORS evidence method {method!r}') from exc


def evidence_strength(method: str) -> int:
    try:
        return int(EVIDENCE_STRENGTH[str(method)])
    except KeyError as exc:  # pragma: no cover - defensive contract guard
        raise ValueError(f'Unknown SORS evidence method {method!r}') from exc


def closure_evidence_method(*, assumption_tier: int, point_identified: bool) -> str:
    tier = int(assumption_tier)
    if tier <= STRICT_OFFICIAL_TIER:
        return 'LATENT_POINT_IDENTIFIED' if point_identified else 'PUBLISHED_BUCKET_IDENTIFIED'
    if tier == SOURCE_PRESERVING_TIER:
        return 'PUBLICATION_CLOSURE_IDENTIFIED'
    if tier == ROUNDING_OPTIMAL_TIER:
        return 'ROUNDING_OPTIMUM_CLOSURE'
    if tier == ROUNDING_PREFERRED_TIER:
        return 'ROUNDING_PREFERRED_CLOSURE'
    return 'ROUNDING_SELECTED_CLOSURE'


def inheritance_evidence_method(assumption_tier: int) -> str:
    tier = max(SOURCE_PRESERVING_TIER, int(assumption_tier))
    if tier == SOURCE_PRESERVING_TIER:
        return 'PUBLISHED_VALUE_INHERITED'
    if tier == ROUNDING_OPTIMAL_TIER:
        return 'ROUNDING_OPTIMUM_CLOSURE'
    if tier == ROUNDING_PREFERRED_TIER:
        return 'ROUNDING_PREFERRED_CLOSURE'
    return 'ROUNDING_SELECTED_CLOSURE'
