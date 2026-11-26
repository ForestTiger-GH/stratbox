"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

_OPTIMIZATION_MODES = {"none", "targets", "priority", "all"}
_CROSSWALK_MODES = {"disabled", "feasibility", "targets", "all"}
_CROSSWALK_SCENARIO_POLICIES = {"single", "feasible_envelope"}
_HIGHS_SOLVERS = {"choose", "simplex", "ipm"}
_HIGHS_CROSSOVER_MODES = {"off", "choose", "on"}

from dataclasses import dataclass, field
from math import isfinite
from datetime import date

from stratbox.domains.cbr.calculations.sors.portfolio import PRIMARY_PORTFOLIO_SCOPE

from stratbox.domains.cbr.calculations.sors.schema import TARGET_METRICS


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
class SorsDeterministicConfig:
    """Cheap publication fixed point executed before and after Solver waves."""

    max_fixed_point_passes: int = 100
    interval_closure_max_passes: int = 100
    inheritance_enabled: bool = True

    def __post_init__(self) -> None:
        if self.max_fixed_point_passes <= 0:
            raise ValueError('max_fixed_point_passes must be positive')
        if self.interval_closure_max_passes <= 0:
            raise ValueError('interval_closure_max_passes must be positive')


@dataclass(frozen=True, slots=True)
class SorsSelectionPolicy:
    """Controlled publication-bucket choice after the rounding-optimal face.

    Selection is based on the number of feasible publication buckets and on the
    global rounding cost of each bucket.  Absolute interval width is only an
    optional emergency guard; it is deliberately not the main criterion because
    rounding uncertainty can accumulate through several independent aggregates.
    """

    enabled: bool = True
    bucket_competition_enabled: bool = True
    fallback_benchmark_selection_enabled: bool = True
    max_candidate_buckets: int = 5
    max_relative_interval_width: float | None = 0.25
    max_interval_width_mln: float | None = None
    min_preference_l1_gap_mln: float = 0.01
    allow_zero_selection: bool = False
    max_linf_degradation_mln: float | None = None
    max_l1_degradation_mln: float = 1.0
    max_joint_selection_targets: int = 25

    def __post_init__(self) -> None:
        if self.max_candidate_buckets <= 1:
            raise ValueError('max_candidate_buckets must be greater than one')
        if (
            self.max_relative_interval_width is not None
            and self.max_relative_interval_width <= 0
        ):
            raise ValueError('max_relative_interval_width must be positive when set')
        if self.max_interval_width_mln is not None and self.max_interval_width_mln <= 0:
            raise ValueError('max_interval_width_mln must be positive when set')
        if self.min_preference_l1_gap_mln < 0:
            raise ValueError('min_preference_l1_gap_mln cannot be negative')
        if (
            self.max_linf_degradation_mln is not None
            and self.max_linf_degradation_mln < 0
        ):
            raise ValueError('max_linf_degradation_mln cannot be negative when set')
        if self.max_l1_degradation_mln < 0:
            raise ValueError('max_l1_degradation_mln cannot be negative')
        if self.max_joint_selection_targets <= 0:
            raise ValueError('max_joint_selection_targets must be positive')


@dataclass(frozen=True, slots=True)
class SorsOptimizationConfig:
    """Optimization waves after deterministic publication closure is exhausted."""

    mode: str = 'none'
    scope: SorsTargetScope = field(default_factory=SorsTargetScope)
    max_targets: int | None = 250
    max_fixed_point_rounds: int = 20
    include_internal_components: bool = True
    strict_minmax_enabled: bool = True
    rounding_optimal_enabled: bool = True
    selection: SorsSelectionPolicy = field(default_factory=SorsSelectionPolicy)
    per_solve_time_limit_seconds: float | None = 30.0
    solver: str = 'simplex'
    rounding_solver: str = 'ipm'
    run_crossover: str = 'choose'
    threads: int = 1

    def __post_init__(self) -> None:
        if self.mode not in _OPTIMIZATION_MODES:
            raise ValueError(
                f'Unsupported SORS optimization mode {self.mode!r}; '
                f'expected one of {sorted(_OPTIMIZATION_MODES)}'
            )
        if self.max_fixed_point_rounds <= 0 or self.threads <= 0:
            raise ValueError('Optimization round limit and threads must be positive')
        if self.max_targets is not None and self.max_targets < 0:
            raise ValueError('max_targets cannot be negative')
        if self.mode == 'targets' and not (
            self.scope.region_codes or self.scope.region_names or self.scope.class_codes
        ):
            raise ValueError('targets optimization requires an explicit region or class scope')
        if self.mode == 'priority' and self.max_targets is None:
            raise ValueError('priority optimization requires max_targets')
        if self.mode == 'all' and self.max_targets is not None:
            raise ValueError('all optimization is exhaustive; max_targets must be None')
        for name, value in (
            ('solver', self.solver),
            ('rounding_solver', self.rounding_solver),
        ):
            if value not in _HIGHS_SOLVERS:
                raise ValueError(
                    f'Unsupported {name} {value!r}; expected one of {sorted(_HIGHS_SOLVERS)}'
                )
        if self.run_crossover not in _HIGHS_CROSSOVER_MODES:
            raise ValueError(
                f'Unsupported run_crossover {self.run_crossover!r}; expected one of '
                f'{sorted(_HIGHS_CROSSOVER_MODES)}'
            )
        if (
            self.per_solve_time_limit_seconds is not None
            and self.per_solve_time_limit_seconds <= 0
        ):
            raise ValueError('per_solve_time_limit_seconds must be positive when set')


@dataclass(frozen=True, slots=True)
class SorsCrosswalkConfig:
    mode: str = 'disabled'
    mapping_fingerprint: str | None = None
    scenario_ids: tuple[str, ...] = ('core',)
    scenario_policy: str = 'feasible_envelope'
    scope: SorsTargetScope = field(default_factory=SorsTargetScope)
    max_targets: int | None = 250
    point_tolerance: float = 1e-6
    closure_max_passes: int = 50
    per_solve_time_limit_seconds: float | None = 300.0
    batch_time_limit_seconds: float | None = None
    model_reset_interval: int = 25
    threads: int = 1

    def __post_init__(self) -> None:
        if self.mode not in _CROSSWALK_MODES:
            raise ValueError(
                f'Unsupported SORS crosswalk mode {self.mode!r}; expected one of '
                f'{sorted(_CROSSWALK_MODES)}'
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
        if not isfinite(self.point_tolerance) or self.point_tolerance <= 0 or self.closure_max_passes <= 0:
            raise ValueError('Crosswalk tolerances and pass limits must be positive')
        if self.max_targets is not None and self.max_targets < 0:
            raise ValueError('Crosswalk max_targets cannot be negative')
        if self.mode == 'targets' and not (
            self.scope.region_codes or self.scope.region_names or self.scope.class_codes
        ):
            raise ValueError('crosswalk targets mode requires an explicit region or class scope')
        if self.mode == 'all' and self.max_targets is not None:
            raise ValueError('crosswalk all mode is exhaustive; max_targets must be None')
        if self.model_reset_interval <= 0 or self.threads <= 0:
            raise ValueError('Crosswalk model_reset_interval and threads must be positive')
        for name, value in (
            ('per_solve_time_limit_seconds', self.per_solve_time_limit_seconds),
            ('batch_time_limit_seconds', self.batch_time_limit_seconds),
        ):
            if value is not None and (not isfinite(value) or value <= 0):
                raise ValueError(f'Crosswalk {name} must be positive when set')


@dataclass(frozen=True, slots=True)
class SorsRunConfig:
    as_of_date: str
    publication_step: float = 1.0
    point_tolerance: float = 1e-6
    primary_portfolio_scope: str = 'CORPORATE_TOTAL'
    deterministic: SorsDeterministicConfig = field(default_factory=SorsDeterministicConfig)
    optimization: SorsOptimizationConfig = field(default_factory=SorsOptimizationConfig)

    @property
    def rules_fingerprint(self) -> str:
        from stratbox.domains.cbr.calculations.sors.fingerprints import implementation_fingerprint
        return implementation_fingerprint()

    def __post_init__(self) -> None:
        date.fromisoformat(self.as_of_date)
        if not isfinite(self.publication_step) or self.publication_step <= 0:
            raise ValueError('publication_step must be positive')
        if not isfinite(self.point_tolerance) or self.point_tolerance <= 0:
            raise ValueError('point_tolerance must be positive')
        if self.primary_portfolio_scope != PRIMARY_PORTFOLIO_SCOPE:
            raise ValueError(
                'SORS restoration currently exports only the primary corporate cube; '
                f'primary_portfolio_scope must be {PRIMARY_PORTFOLIO_SCOPE!r}'
            )
