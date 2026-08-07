import pytest

from stratbox.macrobanks.cbr_sors_restoration import (
    SorsCrosswalkConfig,
    SorsDeterministicConfig,
    SorsOptimizationConfig,
    SorsPivotRequest,
    SorsSelectionPolicy,
    SorsTargetScope,
)


def test_crosswalk_is_disabled_by_default() -> None:
    assert SorsCrosswalkConfig().mode == 'disabled'


def test_deterministic_publication_fixed_point_is_explicit() -> None:
    config = SorsDeterministicConfig()
    assert config.inheritance_enabled
    assert config.max_fixed_point_passes == 100
    with pytest.raises(ValueError):
        SorsDeterministicConfig(max_fixed_point_passes=0)


def test_optimization_is_disabled_by_default_and_modes_are_validated() -> None:
    assert SorsOptimizationConfig().mode == 'none'
    with pytest.raises(ValueError):
        SorsOptimizationConfig(mode='magic')


def test_target_mode_requires_explicit_region_or_class_scope() -> None:
    with pytest.raises(ValueError):
        SorsOptimizationConfig(mode='targets')
    config = SorsOptimizationConfig(
        mode='targets',
        scope=SorsTargetScope(region_names=('Белгородская область',), metrics=('debt_rub',)),
    )
    assert config.scope.metrics == ('debt_rub',)


def test_all_mode_is_exhaustive() -> None:
    with pytest.raises(ValueError):
        SorsOptimizationConfig(mode='all', max_targets=100)
    assert SorsOptimizationConfig(mode='all', max_targets=None).max_targets is None


def test_selection_policy_is_separate_from_numerical_tolerance() -> None:
    policy = SorsSelectionPolicy(max_selection_width_mln=2.5)
    assert policy.max_selection_width_mln == 2.5
    assert policy.max_selection_width_ratio == 0.01
    with pytest.raises(ValueError):
        SorsSelectionPolicy(max_selection_width_mln=0)


def test_target_scope_accepts_only_published_metrics() -> None:
    assert SorsTargetScope(metrics=('overdue_rub',)).metrics == ('overdue_rub',)
    with pytest.raises(ValueError):
        SorsTargetScope(metrics=('performing_rub',))


def test_pivot_requires_exactly_one_axis_selector() -> None:
    with pytest.raises(ValueError):
        SorsPivotRequest()
    with pytest.raises(ValueError):
        SorsPivotRequest(region_code='r1', class_code='01')


def test_nonpositive_solver_time_limits_are_rejected() -> None:
    with pytest.raises(ValueError):
        SorsOptimizationConfig(per_solve_time_limit_seconds=0)
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(batch_time_limit_seconds=0)


def test_solver_strategies_are_explicit_and_validated() -> None:
    config = SorsOptimizationConfig()
    assert config.solver == 'simplex'
    assert config.rounding_solver == 'ipm'
    assert config.run_crossover == 'choose'
    with pytest.raises(ValueError):
        SorsOptimizationConfig(rounding_solver='magic')
    with pytest.raises(ValueError):
        SorsOptimizationConfig(run_crossover='magic')


def test_crosswalk_targets_require_explicit_scope() -> None:
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(mode='targets')


def test_crosswalk_all_is_exhaustive_and_scenarios_are_explicit() -> None:
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(mode='all', max_targets=100)
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(scenario_ids=())
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(scenario_ids=('core', 'broad'), scenario_policy='single')
