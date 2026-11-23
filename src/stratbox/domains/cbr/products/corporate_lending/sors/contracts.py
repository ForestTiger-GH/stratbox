"""Typed corporate lending contracts owned by this processing boundary."""
from __future__ import annotations

from dataclasses import dataclass

from stratbox.domains.cbr.analytics.corporate_lending.sors.schema import TARGET_METRICS


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
                'Exactly one pivot selector is required: region_code/region_name or class_code'
            )
        unknown = sorted(set(self.metrics) - set(TARGET_METRICS))
        if unknown:
            raise ValueError(f'Unknown SORS pivot metrics: {unknown}')


@dataclass(frozen=True, slots=True)
class SorsWorkbookRequest:
    include_source_grid: bool = False
    include_primary_grid: bool = True
    include_restored_facts: bool = True
    include_crosswalk_facts: bool = True
    include_crosswalk_bounds: bool = False
    include_crosswalk_mapping: bool = False
    include_components: bool = False
    include_fact_ledger: bool = True
    include_publication_partitions: bool = False
    include_publication_tokens: bool = False
    include_inheritance_events: bool = False
    include_promotion_events: bool = False
    include_fixed_point_passes: bool = False
    include_optimization_rounds: bool = False
    include_target_bounds: bool = False
    include_rounding_profiles: bool = False
    include_selection_attempts: bool = False
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
        if self.primary_grid_rows_per_sheet is not None and self.primary_grid_rows_per_sheet <= 0:
            raise ValueError('primary_grid_rows_per_sheet must be positive')
