from stratbox.macrobanks.cbr_sors_restoration.publication import (
    PublicationInterval,
    RoundingPolicy,
    solver_lower_bound,
    solver_upper_bound,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.certification import certify_interval


def test_half_open_zero_is_one_publication_bucket() -> None:
    policy = RoundingPolicy()
    assert policy.single_bucket_interval(PublicationInterval(0.0, 0.5, True, False)) == 0.0
    assert policy.single_bucket_interval(PublicationInterval(0.0, 0.5, True, True)) is None


def test_half_open_nonzero_bucket() -> None:
    policy = RoundingPolicy()
    assert policy.single_bucket_interval(PublicationInterval(10.5, 11.5, True, False)) == 11.0


def test_publication_zero_is_not_exact_zero() -> None:
    result = certify_interval(
        PublicationInterval(0.0, 0.5, True, False),
        policy=RoundingPolicy(),
        point_tolerance=1e-6,
    )
    assert result.identification_status == 'PUBLISHED_BUCKET_IDENTIFIED'
    assert result.is_zero_at_published_precision
    assert not result.is_exact_zero


def test_open_endpoints_use_adjacent_floating_point_solver_bounds() -> None:
    assert solver_lower_bound(0.0, True) == 0.0
    assert solver_lower_bound(0.0, False) > 0.0
    assert solver_upper_bound(0.5, True) == 0.5
    assert solver_upper_bound(0.5, False) < 0.5


def test_unbounded_interval_has_no_publication_bucket() -> None:
    from math import inf

    from stratbox.macrobanks.cbr_sors_restoration.publication import (
        PublicationInterval,
        RoundingPolicy,
    )

    assert RoundingPolicy().single_bucket_interval(
        PublicationInterval(0.0, inf, True, False)
    ) is None
