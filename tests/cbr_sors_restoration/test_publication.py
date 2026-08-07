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


def test_candidate_buckets_cover_accumulated_rounding_interval() -> None:
    policy = RoundingPolicy(step=1.0)
    assert policy.candidate_buckets(10.0, 12.0) == (10.0, 11.0, 12.0)
    assert policy.candidate_buckets(0.0, 1.2) == (0.0, 1.0)
    assert policy.candidate_buckets(5.5, 6.5, upper_attained=False) == (6.0,)


def test_publication_ledger_accepts_rounding_preferred_evidence() -> None:
    from types import SimpleNamespace

    from stratbox.macrobanks.cbr_sors_restoration.publication.ledger import (
        SorsPublicationLedger,
    )

    ledger = SorsPublicationLedger()
    quantity = SimpleNamespace(
        quantity_id='metric:CORPORATE_TOTAL:r1:01:debt_rub',
        quantity_kind='REGIONAL_CLASS_METRIC',
        portfolio_scope='CORPORATE_TOTAL',
        region_code='r1',
        class_code='01',
        component=None,
        metric='debt_rub',
    )
    assert ledger.promote_external_bucket(
        quantity,
        published_value=11.0,
        evidence_method='ROUNDING_PREFERRED',
        restoration_pass=0,
        optimization_round=1,
        proof_ids=('rounding:competition:000001', 'selection:preferred:000001'),
        details='test',
    )
    row = ledger.current_record(quantity.quantity_id)
    assert row is not None
    assert row['evidence_method'] == 'ROUNDING_PREFERRED'
    assert row['latent_constraint_mode'] == 'PUBLICATION_BUCKET'
