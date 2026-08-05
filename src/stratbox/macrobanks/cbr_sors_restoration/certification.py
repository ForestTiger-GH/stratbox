from __future__ import annotations

from dataclasses import dataclass

from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy


@dataclass(frozen=True, slots=True)
class CertifiedInterval:
    lower: float
    upper: float
    published_value: float | None
    status: str


def certify_interval(lower: float, upper: float, *, policy: RoundingPolicy, point_tolerance: float, evidence_layer: str) -> CertifiedInterval:
    if upper < lower - point_tolerance:
        raise ValueError(f'Invalid certified interval: [{lower}, {upper}]')
    if upper - lower <= point_tolerance:
        value = (lower + upper) / 2.0
        return CertifiedInterval(lower, upper, policy.bucket(value), f'{evidence_layer}_EXACT')
    bucket = policy.single_bucket(lower, upper)
    if bucket is not None:
        return CertifiedInterval(lower, upper, bucket, f'{evidence_layer}_AT_PUBLISHED_PRECISION')
    return CertifiedInterval(lower, upper, None, f'{evidence_layer}_BOUNDED')
