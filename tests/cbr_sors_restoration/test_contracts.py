import pytest

from stratbox.macrobanks.cbr_sors_restoration import (
    SorsBridgeConfig,
    SorsCertificationConfig,
    SorsPivotRequest,
    SorsRunConfig,
)


def test_bridge_is_disabled_by_default() -> None:
    assert SorsBridgeConfig().mode == 'disabled'


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
        SorsBridgeConfig(batch_time_limit_seconds=0)


def test_expensive_certification_modes_require_unambiguous_scope_or_budget() -> None:
    with pytest.raises(ValueError):
        SorsCertificationConfig(mode='targets')
    with pytest.raises(ValueError):
        SorsCertificationConfig(mode='priority')
    with pytest.raises(ValueError):
        SorsCertificationConfig(mode='all', max_targets=100)


def test_bridge_targets_require_explicit_scope() -> None:
    with pytest.raises(ValueError):
        SorsBridgeConfig(mode='targets')
