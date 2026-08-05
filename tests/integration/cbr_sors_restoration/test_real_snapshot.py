from __future__ import annotations

import os
from pathlib import Path

import pytest

from stratbox.macrobanks.cbr_sors_restoration import SorsSourceFiles, load_sors_sources
from stratbox.macrobanks.cbr_sors_restoration.strict.closure import run_deterministic_closure
from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import compile_strict_problem
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import build_quantity_graph


@pytest.mark.skipif(not os.environ.get('STRATBOX_SORS_REAL_DATA_DIR'), reason='real SORS files are not configured')
def test_real_2026_06_snapshot() -> None:
    root = Path(os.environ['STRATBOX_SORS_REAL_DATA_DIR'])
    files = SorsSourceFiles(
        regional_traditional=root / '01_05_A_Debt_corp_20260601.xlsx',
        national_okved2=root / '01_02_C_Debt_corp_by_activity.xlsx',
        federal_district_okved2=root / '01_03_C_Loans_corp_by_fd_activity_20260601.xlsx',
        national_traditional=root / '01_02_A_Debt_corp_by_activity.xlsx',
        regional_totals_history=(root / '01_05_D_Debt_subj.xlsx'),
    )
    bundle = load_sors_sources(files, '2026-06-01')
    graph = build_quantity_graph(bundle)
    closure = run_deterministic_closure(graph)
    compilation = compile_strict_problem(bundle, graph, closure.quantities_grid, point_tolerance=1e-6)
    assert len(bundle.source_grid) == 16_450
    assert len(bundle.atomic_regions_grid) == 85
    assert len(bundle.okved2_classes_grid) == 88
    assert graph.quantities_grid['quantity_kind'].eq('ATOMIC_COMPONENT').sum() == 29_920
    assert graph.quantities_grid['quantity_kind'].eq('REGIONAL_CLASS_METRIC').sum() == 44_880
    assert len(graph.observation_bindings_grid) == 1_324
    assert len(compilation.problem.constraints_grid) == 1_318
    metrics = closure.quantities_grid[closure.quantities_grid['quantity_kind'].eq('REGIONAL_CLASS_METRIC')]
    zero = metrics[(metrics['lower_bound'] == 0.0) & (metrics['upper_bound'] == 0.5) & ~metrics['upper_attained']]
    counts = zero['metric'].value_counts().to_dict()
    assert counts['debt_fx'] == 4_070
    assert counts['overdue_fx'] == 7_204
