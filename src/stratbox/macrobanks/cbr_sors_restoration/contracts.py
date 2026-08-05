from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


@dataclass(frozen=True, slots=True)
class SorsSourceFiles:
    regional_traditional: str | Path
    national_okved2: str | Path
    fd_okved2: str | Path
    national_traditional: str | Path


@dataclass(frozen=True, slots=True)
class SorsTargetScope:
    region_names: tuple[str, ...] = ()
    class_codes: tuple[str, ...] = ()
    metrics: tuple[str, ...] = (
        'debt_rub', 'debt_fx', 'debt_total',
        'overdue_rub', 'overdue_fx', 'overdue_total',
    )
    certify_all: bool = False
    max_targets: int | None = 250


@dataclass(frozen=True, slots=True)
class SorsRunConfig:
    as_of_date: str
    publication_step: float = 1.0
    mapping_version: str = 'cbr-legacy-okved2-bridge-2026.1'
    bridge_profile_tolerance: float = 1e-6
    point_tolerance: float = 1e-6
    target_scope: SorsTargetScope = field(default_factory=SorsTargetScope)
    solver_time_limit_seconds: float | None = 300.0
    solver_threads: int = 1


@dataclass(frozen=True)
class SorsSourceBundle:
    canonical_grid: pd.DataFrame
    regional_traditional_grid: pd.DataFrame
    national_traditional_grid: pd.DataFrame
    national_okved2_grid: pd.DataFrame
    fd_okved2_grid: pd.DataFrame
    geography_nodes: pd.DataFrame
    atomic_regions: pd.DataFrame
    okved2_classes: pd.DataFrame
    published_other_classes: tuple[str, ...]
    source_manifest: pd.DataFrame


@dataclass(frozen=True)
class SorsRestorationResult:
    canonical_grid: pd.DataFrame
    facts_grid: pd.DataFrame
    bounds_grid: pd.DataFrame
    bridge_diagnostics_grid: pd.DataFrame
    constraints_grid: pd.DataFrame
    mapping_edges_grid: pd.DataFrame
    conflicts_grid: pd.DataFrame
    audit: dict[str, object]

