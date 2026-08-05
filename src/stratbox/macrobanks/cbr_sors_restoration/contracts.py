from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.schema import TARGET_METRICS

_CERTIFICATION_MODES = {'closure', 'targets', 'priority', 'all'}
_BRIDGE_MODES = {'disabled', 'optimum_only', 'targets'}


@dataclass(frozen=True, slots=True)
class SorsSourceFiles:
    regional_traditional: str | Path
    national_okved2: str | Path
    federal_district_okved2: str | Path
    national_traditional: str | Path
    regional_totals_history: str | Path | None = None


@dataclass(frozen=True, slots=True)
class SorsTargetScope:
    region_codes: tuple[str, ...] = ()
    region_names: tuple[str, ...] = ()
    class_codes: tuple[str, ...] = ()
    metrics: tuple[str, ...] = TARGET_METRICS

    def __post_init__(self) -> None:
        unknown = sorted(set(self.metrics) - set(TARGET_METRICS))
        if unknown:
            raise ValueError(f'Unknown SORS target metrics: {unknown}')


@dataclass(frozen=True, slots=True)
class SorsCertificationConfig:
    mode: str = 'closure'
    scope: SorsTargetScope = field(default_factory=SorsTargetScope)
    max_targets: int | None = None
    batch_size: int = 50
    per_solve_time_limit_seconds: float | None = 30.0
    batch_time_limit_seconds: float | None = None
    model_reset_interval: int = 25
    retry_failed_solve: bool = True
    threads: int = 1

    def __post_init__(self) -> None:
        if self.mode not in _CERTIFICATION_MODES:
            raise ValueError(
                f'Unsupported SORS certification mode {self.mode!r}; '
                f'expected one of {sorted(_CERTIFICATION_MODES)}'
            )
        for name, value in (
            ('batch_size', self.batch_size),
            ('model_reset_interval', self.model_reset_interval),
            ('threads', self.threads),
        ):
            if value <= 0:
                raise ValueError(f'{name} must be positive')
        if self.max_targets is not None and self.max_targets < 0:
            raise ValueError('max_targets cannot be negative')
        if self.mode == 'targets' and not (
            self.scope.region_codes
            or self.scope.region_names
            or self.scope.class_codes
        ):
            raise ValueError(
                'targets certification requires an explicit region or class scope'
            )
        if self.mode == 'priority' and self.max_targets is None:
            raise ValueError('priority certification requires max_targets')
        if self.mode == 'all' and self.max_targets is not None:
            raise ValueError('all certification is exhaustive; max_targets must be None')
        for name, value in (
            ('per_solve_time_limit_seconds', self.per_solve_time_limit_seconds),
            ('batch_time_limit_seconds', self.batch_time_limit_seconds),
        ):
            if value is not None and value <= 0:
                raise ValueError(f'{name} must be positive when set')


@dataclass(frozen=True, slots=True)
class SorsBridgeConfig:
    mode: str = 'disabled'
    mapping_version: str = 'cbr-legacy-okved2-bridge-2026.2'
    objective_tolerance: float = 1e-5
    scope: SorsTargetScope = field(default_factory=SorsTargetScope)
    max_targets: int | None = 250
    per_solve_time_limit_seconds: float | None = 300.0
    batch_time_limit_seconds: float | None = None
    model_reset_interval: int = 25
    retry_failed_solve: bool = True
    threads: int = 1

    def __post_init__(self) -> None:
        if self.mode not in _BRIDGE_MODES:
            raise ValueError(
                f'Unsupported SORS bridge mode {self.mode!r}; '
                f'expected one of {sorted(_BRIDGE_MODES)}'
            )
        if self.objective_tolerance < 0:
            raise ValueError('objective_tolerance cannot be negative')
        if self.max_targets is not None and self.max_targets < 0:
            raise ValueError('max_targets cannot be negative')
        if self.mode == 'targets' and not (
            self.scope.region_codes
            or self.scope.region_names
            or self.scope.class_codes
        ):
            raise ValueError(
                'bridge targets mode requires an explicit region or class scope'
            )
        if self.model_reset_interval <= 0 or self.threads <= 0:
            raise ValueError('Bridge model_reset_interval and threads must be positive')
        for name, value in (
            ('per_solve_time_limit_seconds', self.per_solve_time_limit_seconds),
            ('batch_time_limit_seconds', self.batch_time_limit_seconds),
        ):
            if value is not None and value <= 0:
                raise ValueError(f'Bridge {name} must be positive when set')


@dataclass(frozen=True, slots=True)
class SorsRunConfig:
    as_of_date: str
    publication_step: float = 1.0
    point_tolerance: float = 1e-6
    rules_version: str = 'sors-strict-2026.3'
    strict_certification: SorsCertificationConfig = field(
        default_factory=SorsCertificationConfig
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
    evidence_layer: str = 'STRICT'
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
    include_components: bool = False
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
