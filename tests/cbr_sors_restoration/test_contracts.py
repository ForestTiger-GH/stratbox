import pytest

from stratbox.macrobanks.cbr_sors_restoration import (
    SorsCellResolutionConfig,
    SorsCellScope,
    SorsCrosswalkConfig,
    SorsPivotRequest,
)


def test_crosswalk_is_disabled_by_default() -> None:
    assert SorsCrosswalkConfig().mode == 'disabled'


def test_cell_resolution_mode_is_explicit() -> None:
    config = SorsCellResolutionConfig()
    assert config.mode == 'closure'
    assert config.horizon_order[0] == 'CELL'
    assert config.horizon_order[-1] == 'GLOBAL_CONNECTED'
    with pytest.raises(ValueError):
        SorsCellResolutionConfig(mode='magic')


def test_cell_scope_accepts_only_base_components() -> None:
    assert SorsCellScope(components=('overdue_rub',)).components == ('overdue_rub',)
    with pytest.raises(ValueError):
        SorsCellScope(components=('debt_total',))


def test_pivot_requires_exactly_one_axis_selector() -> None:
    with pytest.raises(ValueError):
        SorsPivotRequest()
    with pytest.raises(ValueError):
        SorsPivotRequest(region_code='r1', class_code='01')


def test_nonpositive_solver_time_limits_are_rejected() -> None:
    with pytest.raises(ValueError):
        SorsCellResolutionConfig(run_time_limit_seconds=0)
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(batch_time_limit_seconds=0)


def test_target_cell_modes_require_unambiguous_scope_or_budget() -> None:
    with pytest.raises(ValueError):
        SorsCellResolutionConfig(mode='targets')
    with pytest.raises(ValueError):
        SorsCellResolutionConfig(mode='priority')
    with pytest.raises(ValueError):
        SorsCellResolutionConfig(mode='all', max_target_attempts=100)


def test_target_cell_mode_accepts_explicit_rkvs_scope() -> None:
    config = SorsCellResolutionConfig(
        mode='targets',
        scope=SorsCellScope(
            region_names=('Белгородская область',),
            class_codes=('01',),
            components=('overdue_rub',),
        ),
    )
    assert config.scope.components == ('overdue_rub',)


def test_cell_horizons_are_known_and_unique() -> None:
    with pytest.raises(ValueError):
        SorsCellResolutionConfig(horizon_order=('CELL', 'CELL'))
    with pytest.raises(ValueError):
        SorsCellResolutionConfig(horizon_order=('CELL', 'UNKNOWN'))


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
            scenario_ids=('core', 'broad'), scenario_policy='single'
        )


def test_crosswalk_closure_pass_limit_must_be_positive() -> None:
    with pytest.raises(ValueError):
        SorsCrosswalkConfig(closure_max_passes=0)


def test_national_total_is_supported_as_optional_horizon() -> None:
    config = SorsCellResolutionConfig(
        horizon_order=('CELL', 'NATIONAL_TOTAL', 'GLOBAL_CONNECTED')
    )
    assert config.horizon_order[1] == 'NATIONAL_TOTAL'
