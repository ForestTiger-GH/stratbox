from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pandas as pd

CertifyMode = Literal['none', 'candidates', 'targets', 'all']


@dataclass(frozen=True, slots=True)
class SorsRestorationFiles:
    regional_traditional: str | Path
    national_okved2: str | Path
    fd_okved2: str | Path
    national_traditional: str | Path | None = None


@dataclass(frozen=True, slots=True)
class SorsRestorationConfig:
    as_of_date: str
    publication_step: float = 1.0
    feasibility_tolerance: float = 1e-7
    point_tolerance: float = 1e-6
    max_closure_passes: int = 100
    certify_mode: CertifyMode = 'candidates'
    max_lp_targets: int = 50
    target_region_names: tuple[str, ...] = ()
    target_class_codes: tuple[str, ...] = ()
    include_benchmark: bool = False


@dataclass(frozen=True)
class SorsSourceBundle:
    regional_grid: pd.DataFrame
    national_okved2_grid: pd.DataFrame
    fd_okved2_grid: pd.DataFrame
    national_traditional_grid: pd.DataFrame | None
    atomic_regions: pd.DataFrame
    okved2_classes: pd.DataFrame


@dataclass(frozen=True)
class SorsRestorationResult:
    facts_grid: pd.DataFrame
    bounds_grid: pd.DataFrame
    audit: dict[str, object]
    mapping_diagnostics: pd.DataFrame = field(default_factory=pd.DataFrame)
    estimate_grid: pd.DataFrame = field(default_factory=pd.DataFrame)
