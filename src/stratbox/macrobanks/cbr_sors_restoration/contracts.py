from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.schema import COMPONENTS, TARGET_METRICS

_CELL_RESOLUTION_MODES = {'closure', 'targets', 'priority', 'all'}
_CROSSWALK_MODES = {'disabled', 'feasibility', 'targets', 'all'}
_CROSSWALK_SCENARIO_POLICIES = {'single', 'feasible_envelope'}
_HIGHS_SOLVERS = {'choose', 'simplex', 'ipm'}
_HIGHS_CROSSOVER_MODES = {'off', 'choose', 'on'}
_DEFAULT_CELL_HORIZONS = (
    'CELL',
    'REGION_COMPONENT',
    'REGION_CROSS_METRIC',
    'REGION_PARENT',
    'FD_SECTION',
    'FEDERAL_DISTRICT_TOTAL',
    'NATIONAL_CLASS',
    'GLOBAL_CONNECTED',
)
_KNOWN_CELL_HORIZONS = set(_DEFAULT_CELL_HORIZONS) | {'NATIONAL_TOTAL'}


@dataclass(frozen=True, slots=True)
class SorsSourceFiles:
    regional_traditional: str | Path
    national_okved2: str | Path
    federal_district_okved2: str | Path
    national_traditional: str | Path
    regional_totals_history: str | Path | None = None


@dataclass(frozen=True, slots=True)
class SorsTargetScope:
    """Scope for six published metrics and the separate crosswalk API."""

    region_codes: tuple[str, ...] = ()
    region_names: tuple[str, ...] = ()
    class_codes: tuple[str, ...] = ()
    metrics: tuple[str, ...] = TARGET_METRICS

    def __post_init__(self) -> None:
        unknown = sorted(set(self.metrics) - set(TARGET_METRICS))
        if unknown:
            raise ValueError(f'Unknown SORS target metrics: {unknown}')


@dataclass(frozen=True, slots=True)
class SorsCellScope:
    """Scope of base RKVS cells: region × OKVED2 class × money component."""

    region_codes: tuple[str, ...] = ()
    region_names: tuple[str, ...] = ()
    class_codes: tuple[str, ...] = ()
    components: tuple[str, ...] = COMPONENTS

    def __post_init__(self) -> None:
        unknown = sorted(set(self.components) - set(COMPONENTS))
        if unknown:
            raise ValueError(f'Unknown SORS RKVS components: {unknown}')


@dataclass(frozen=True, slots=True)
class SorsCellResolutionConfig:
    """Target-centred fixed-point proof engine for individual RKVS cells."""

    mode: str = 'closure'
    scope: SorsCellScope = field(default_factory=SorsCellScope)
    max_target_attempts: int | None = None
    max_attempts_per_target: int = 3
    max_fixed_point_passes: int = 20
    horizon_order: tuple[str, ...] = _DEFAULT_CELL_HORIZONS
    accept_published_bucket: bool = True
    per_solve_time_limit_seconds: float | None = 30.0
    run_time_limit_seconds: float | None = None
    retry_failed_solve: bool = True
    local_solver: str = 'simplex'
    global_solver: str = 'ipm'
    retry_solver: str = 'choose'
    run_crossover: str = 'choose'
    reuse_global_session: bool = True
    threads: int = 1

    def __post_init__(self) -> None:
        if self.mode not in _CELL_RESOLUTION_MODES:
            raise ValueError(
                f'Unsupported SORS cell-resolution mode {self.mode!r}; '
                f'expected one of {sorted(_CELL_RESOLUTION_MODES)}'
            )
        if not self.horizon_order:
            raise ValueError('At least one RKVS expansion horizon is required')
        unknown_horizons = sorted(set(self.horizon_order) - _KNOWN_CELL_HORIZONS)
        if unknown_horizons:
            raise ValueError(f'Unknown RKVS expansion horizons: {unknown_horizons}')
        if len(set(self.horizon_order)) != len(self.horizon_order):
            raise ValueError('RKVS expansion horizons must be unique')
        for name, value in (
            ('max_attempts_per_target', self.max_attempts_per_target),
            ('max_fixed_point_passes', self.max_fixed_point_passes),
            ('threads', self.threads),
        ):
            if value <= 0:
                raise ValueError(f'{name} must be positive')
        if self.max_target_attempts is not None and self.max_target_attempts < 0:
            raise ValueError('max_target_attempts cannot be negative')
        for name, value in (
            ('local_solver', self.local_solver),
            ('global_solver', self.global_solver),
            ('retry_solver', self.retry_solver),
        ):
            if value not in _HIGHS_SOLVERS:
                raise ValueError(
                    f'Unsupported {name} {value!r}; expected one of '
                    f'{sorted(_HIGHS_SOLVERS)}'
                )
        if self.run_crossover not in _HIGHS_CROSSOVER_MODES:
            raise ValueError(
                f'Unsupported run_crossover {self.run_crossover!r}; expected one of '
                f'{sorted(_HIGHS_CROSSOVER_MODES)}'
            )
        if self.mode == 'targets' and not (
            self.scope.region_codes
            or self.scope.region_names
            or self.scope.class_codes
        ):
            raise ValueError(
                'targets cell resolution requires an explicit region or class scope'
            )
        if self.mode == 'priority' and self.max_target_attempts is None:
            raise ValueError('priority cell resolution requires max_target_attempts')
        if self.mode == 'all' and self.max_target_attempts is not None:
            raise ValueError(
                'all cell resolution is exhaustive; max_target_attempts must be None'
            )
        for name, value in (
            ('per_solve_time_limit_seconds', self.per_solve_time_limit_seconds),
            ('run_time_limit_seconds', self.run_time_limit_seconds),
        ):
            if value is not None and value <= 0:
                raise ValueError(f'{name} must be positive when set')


@dataclass(frozen=True, slots=True)
class SorsCrosswalkConfig:
    mode: str = 'disabled'
    mapping_version: str = 'cbr-legacy-okved2-crosswalk-2026.3'
    scenario_ids: tuple[str, ...] = ('core',)
    scenario_policy: str = 'feasible_envelope'
    scope: SorsTargetScope = field(default_factory=SorsTargetScope)
    max_targets: int | None = 250
    point_tolerance: float = 1e-6
    closure_max_passes: int = 50
    per_solve_time_limit_seconds: float | None = 300.0
    batch_time_limit_seconds: float | None = None
    model_reset_interval: int = 25
    retry_failed_solve: bool = True
    threads: int = 1

    def __post_init__(self) -> None:
        if self.mode not in _CROSSWALK_MODES:
            raise ValueError(
                f'Unsupported SORS crosswalk mode {self.mode!r}; '
                f'expected one of {sorted(_CROSSWALK_MODES)}'
            )
        if not self.scenario_ids:
            raise ValueError('At least one crosswalk scenario is required')
        if len(set(self.scenario_ids)) != len(self.scenario_ids):
            raise ValueError('Crosswalk scenario_ids must be unique')
        if self.scenario_policy not in _CROSSWALK_SCENARIO_POLICIES:
            raise ValueError(
                f'Unsupported crosswalk scenario policy {self.scenario_policy!r}; '
                f'expected one of {sorted(_CROSSWALK_SCENARIO_POLICIES)}'
            )
        if self.scenario_policy == 'single' and len(self.scenario_ids) != 1:
            raise ValueError('single scenario policy requires exactly one scenario_id')
        if self.point_tolerance <= 0 or self.closure_max_passes <= 0:
            raise ValueError('Crosswalk tolerances and pass limits must be positive')
        if self.max_targets is not None and self.max_targets < 0:
            raise ValueError('Crosswalk max_targets cannot be negative')
        if self.mode == 'targets' and not (
            self.scope.region_codes
            or self.scope.region_names
            or self.scope.class_codes
        ):
            raise ValueError(
                'crosswalk targets mode requires an explicit region or class scope'
            )
        if self.mode == 'all' and self.max_targets is not None:
            raise ValueError('crosswalk all mode is exhaustive; max_targets must be None')
        if self.model_reset_interval <= 0 or self.threads <= 0:
            raise ValueError(
                'Crosswalk model_reset_interval and threads must be positive'
            )
        for name, value in (
            ('per_solve_time_limit_seconds', self.per_solve_time_limit_seconds),
            ('batch_time_limit_seconds', self.batch_time_limit_seconds),
        ):
            if value is not None and value <= 0:
                raise ValueError(f'Crosswalk {name} must be positive when set')


@dataclass(frozen=True, slots=True)
class SorsRunConfig:
    as_of_date: str
    publication_step: float = 1.0
    point_tolerance: float = 1e-6
    rules_version: str = 'sors-rkvs-2026.5'
    cell_resolution: SorsCellResolutionConfig = field(
        default_factory=SorsCellResolutionConfig
    )

    def __post_init__(self) -> None:
        if self.publication_step <= 0:
            raise ValueError('publication_step must be positive')
        if self.point_tolerance <= 0:
            raise ValueError('point_tolerance must be positive')


@dataclass(frozen=True)
class SorsSourceBundle:
    source_grid: pd.DataFrame
    regional_traditional_grid: pd.DataFrame
    national_traditional_grid: pd.DataFrame
    national_okved2_grid: pd.DataFrame
    federal_district_okved2_grid: pd.DataFrame
    regional_totals_history_grid: pd.DataFrame
    geography_nodes_grid: pd.DataFrame
    atomic_regions_grid: pd.DataFrame
    okved2_classes_grid: pd.DataFrame
    publication_categories_grid: pd.DataFrame
    observation_bindings_grid: pd.DataFrame
    source_manifest_grid: pd.DataFrame
    validation_grid: pd.DataFrame


@dataclass(frozen=True, slots=True)
class SorsPivotRequest:
    region_code: str | None = None
    region_name: str | None = None
    class_code: str | None = None
    evidence_layer: str = 'PRIMARY'
    metrics: tuple[str, ...] = TARGET_METRICS
    include_unidentified: bool = True
    include_bounds: bool = False
    include_status: bool = True

    def __post_init__(self) -> None:
        region_selected = bool(self.region_code or self.region_name)
        class_selected = bool(self.class_code)
        if region_selected == class_selected:
            raise ValueError(
                'Exactly one pivot selector is required: region_code/region_name '
                'or class_code'
            )
        unknown = sorted(set(self.metrics) - set(TARGET_METRICS))
        if unknown:
            raise ValueError(f'Unknown SORS pivot metrics: {unknown}')


@dataclass(frozen=True, slots=True)
class SorsWorkbookRequest:
    output_path: str | Path
    overwrite: bool = False
    include_source_grid: bool = False
    include_primary_grid: bool = True
    include_strict_facts: bool = True
    include_crosswalk_facts: bool = True
    include_crosswalk_bounds: bool = False
    include_crosswalk_mapping: bool = False
    include_components: bool = False
    include_fact_ledger: bool = True
    include_cell_attempts: bool = False
    include_cell_subsystems: bool = False
    include_promotion_events: bool = False
    include_fixed_point_passes: bool = False
    include_derivations: bool = False
    include_constraints: bool = False
    include_validation: bool = True
    include_conflicts: bool = True
    include_solver_runs: bool = False
    include_metadata_sheet: bool = True
    include_dimensions: bool = True
    primary_grid_rows_per_sheet: int | None = None
    pivots: tuple[SorsPivotRequest, ...] = ()

    def __post_init__(self) -> None:
        if (
            self.primary_grid_rows_per_sheet is not None
            and self.primary_grid_rows_per_sheet <= 0
        ):
            raise ValueError('primary_grid_rows_per_sheet must be positive')
