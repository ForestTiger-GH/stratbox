import pytest

from stratbox.macrobanks.cbr_sors_restoration import (
    SorsCertificationConfig,
    SorsCrosswalkConfig,
    SorsPivotRequest,
)


def test_crosswalk_is_disabled_by_default() -> None:
    assert SorsCrosswalkConfig().mode == 'disabled'


def test_certification_mode_is_explicit() -> None:
    assert SorsCertificationConfig().mode == 'closure'
    with pytest.raises(ValueError):
        SorsCertificationConfig(mode='magic')


def test_pivot_requires_exactly_one_axis_selector() -> None:
    with pytest.raises(ValueError):
        SorsPivotRequest()
    with pytest.raises(ValueError):
        SorsPivotRequest(region_code='r1', class_code='01')


def test_nonpositive_solver_time_limits_are_rejected() -> None:
    with pytest.raises(ValueError):
        SorsCertificationConfig(batch_time_limit_seconds=0)
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(batch_time_limit_seconds=0)


def test_expensive_certification_modes_require_unambiguous_scope_or_budget() -> None:
    with pytest.raises(ValueError):
        SorsCertificationConfig(mode='targets')
    with pytest.raises(ValueError):
        SorsCertificationConfig(mode='priority')
    with pytest.raises(ValueError):
        SorsCertificationConfig(mode='all', max_targets=100)


def test_crosswalk_targets_require_explicit_scope() -> None:
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(mode='targets')


def test_crosswalk_all_is_exhaustive_and_scenarios_are_explicit() -> None:
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(mode='all', max_targets=100)
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(scenario_ids=())
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(
            scenario_ids=('core', 'broad'),
            scenario_policy='single',
        )


def test_crosswalk_closure_pass_limit_must_be_positive() -> None:
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(closure_max_passes=0)
