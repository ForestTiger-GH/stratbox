from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from stratbox.data import ComputationReceipt, Representation

if TYPE_CHECKING:
    import pandas as pd


def _empty_frame():
    from pandas import DataFrame

    return DataFrame()


@dataclass(frozen=True, slots=True)
class SorsRunSummary:
    dataset_id: str
    strict_model_id: str
    execution_run_id: str
    as_of_date: str
    publication_step: float
    strict_status: str
    solver_backend: str | None
    solver_version: str | None
    source_rows: int
    atomic_regions: int
    okved2_classes: int
    portfolio_scopes: tuple[str, ...]
    primary_component_quantities: int
    auxiliary_component_quantities: int
    latent_component_quantities: int
    regional_metric_rows: int
    raw_publication_observations: int
    unique_publication_constraints: int
    deterministic_status: str
    deterministic_passes: int
    deterministic_bound_updates: int
    publication_facts: int
    publication_zero_facts: int
    inherited_facts: int
    strict_identified_facts: int
    rounding_optimal_facts: int
    rounding_preferred_facts: int
    rounding_selected_facts: int
    auxiliary_publication_facts: int
    optimization_status: str = 'DISABLED'
    optimization_rounds: int = 0
    optimization_targets_attempted: int = 0
    tau_star_mln: float | None = None
    l1_star_mln: float | None = None
    relaxed_l1_star_mln: float | None = None
    relaxed_linf_at_l1_mln: float | None = None


@dataclass(frozen=True)
class SorsRestorationResult:
    source_grid: pd.DataFrame
    source_manifest_grid: pd.DataFrame
    validation_grid: pd.DataFrame
    regional_okved2_grid: pd.DataFrame
    components_grid: pd.DataFrame
    restored_facts_grid: pd.DataFrame
    derivations_grid: pd.DataFrame
    constraints_grid: pd.DataFrame
    variables_grid: pd.DataFrame
    solver_runs_grid: pd.DataFrame
    conflicts_grid: pd.DataFrame
    audit_grid: pd.DataFrame
    summary: SorsRunSummary
    facts_ledger_grid: pd.DataFrame = field(default_factory=_empty_frame)
    current_component_facts_grid: pd.DataFrame = field(default_factory=_empty_frame)
    publication_partitions_grid: pd.DataFrame = field(default_factory=_empty_frame)
    inheritance_events_grid: pd.DataFrame = field(default_factory=_empty_frame)
    publication_tokens_grid: pd.DataFrame = field(default_factory=_empty_frame)
    promotion_events_grid: pd.DataFrame = field(default_factory=_empty_frame)
    fixed_point_passes_grid: pd.DataFrame = field(default_factory=_empty_frame)
    optimization_rounds_grid: pd.DataFrame = field(default_factory=_empty_frame)
    target_bounds_grid: pd.DataFrame = field(default_factory=_empty_frame)
    rounding_profiles_grid: pd.DataFrame = field(default_factory=_empty_frame)
    selection_attempts_grid: pd.DataFrame = field(default_factory=_empty_frame)
    _source_bundle: object | None = None
    _strict_problem: object | None = None
    evidence: ComputationReceipt | None = None


@dataclass(frozen=True)
class SorsCrosswalkResult:
    regional_okved2_grid: pd.DataFrame
    crosswalk_bounds_grid: pd.DataFrame
    crosswalk_facts_grid: pd.DataFrame
    scenario_bounds_grid: pd.DataFrame
    mapping_edges_grid: pd.DataFrame
    relations_grid: pd.DataFrame
    constraints_grid: pd.DataFrame
    variables_grid: pd.DataFrame
    derivations_grid: pd.DataFrame
    diagnostics_grid: pd.DataFrame
    solver_runs_grid: pd.DataFrame
    conflicts_grid: pd.DataFrame
    audit_grid: pd.DataFrame
    crosswalk_run_id: str
    status: str
    _strict_result: object | None = None
    evidence: ComputationReceipt | None = None


@dataclass(frozen=True)
class SorsPivotResult:
    table: pd.DataFrame
    orientation: str
    selected_region_code: str | None
    selected_region_name: str | None
    selected_class_code: str | None
    metrics: tuple[str, ...]
    source_rows: int
    output_rows: int
    identified_cells: int
    unidentified_cells: int
    evidence: ComputationReceipt | None = None


@dataclass(frozen=True, slots=True)
class SorsWorkbookResult:
    representation: Representation
    sheet_names: tuple[str, ...]
    sheet_count: int
