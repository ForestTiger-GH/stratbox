from __future__ import annotations

from stratbox.macrobanks.cbr_sors_restoration.result_grid import _lp_proof_flags


def test_deterministic_bucket_is_not_mislabeled_as_lp_certified() -> None:
    assert _lp_proof_flags('PUBLISHED_BUCKET_IDENTIFIED', ()) == (False, False, False)


def test_two_sided_solver_minmax_marks_bound_certification() -> None:
    assert _lp_proof_flags(
        'PUBLISHED_BUCKET_IDENTIFIED', ('solve:min', 'solve:max')
    ) == (True, True, True)
    assert _lp_proof_flags(
        'ROUNDING_OPTIMUM_IDENTIFIED', ('solve:min', 'solve:max')
    ) == (True, True, True)


def test_joint_selection_records_solver_proof_without_claiming_minmax_bounds() -> None:
    assert _lp_proof_flags('ROUNDING_SELECTED', ('selection:batch:000001',)) == (
        True, False, False
    )
