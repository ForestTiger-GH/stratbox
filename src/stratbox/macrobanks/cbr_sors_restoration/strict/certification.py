from __future__ import annotations

from dataclasses import dataclass

from stratbox.macrobanks.cbr_sors_restoration.publication import (
    PublicationInterval,
    RoundingPolicy,
)


@dataclass(frozen=True, slots=True)
class IntervalCertification:
    identification_status: str
    exact_value: float | None
    published_value: float | None
    value: float | None
    value_precision: str
    is_zero_at_published_precision: bool
    is_exact_zero: bool


def certify_interval(
    interval: PublicationInterval,
    *,
    policy: RoundingPolicy,
    point_tolerance: float,
) -> IntervalCertification:
    if interval.upper < interval.lower - point_tolerance:
        raise ValueError(
            f'Invalid certified interval [{interval.lower}, {interval.upper}]'
        )
    point = (
        interval.upper - interval.lower <= point_tolerance
        and interval.lower_attained
        and interval.upper_attained
    )
    if point:
        exact = (interval.lower + interval.upper) / 2.0
        published = policy.bucket(exact)
        return IntervalCertification(
            identification_status='POINT_IDENTIFIED',
            exact_value=exact,
            published_value=published,
            value=exact,
            value_precision='EXACT',
            is_zero_at_published_precision=published == 0.0,
            is_exact_zero=abs(exact) <= point_tolerance,
        )
    published = policy.single_bucket_interval(interval)
    if published is not None:
        return IntervalCertification(
            identification_status='PUBLISHED_BUCKET_IDENTIFIED',
            exact_value=None,
            published_value=published,
            value=published,
            value_precision='PUBLISHED',
            is_zero_at_published_precision=published == 0.0,
            is_exact_zero=False,
        )
    return IntervalCertification(
        identification_status='BOUNDED',
        exact_value=None,
        published_value=None,
        value=None,
        value_precision='NONE',
        is_zero_at_published_precision=False,
        is_exact_zero=False,
    )
