from __future__ import annotations

import os
from pathlib import Path

import pytest

from stratbox.macrobanks.cbr_sors_restoration import SorsSourceFiles, load_sors_sources
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    RoundingPolicy,
    SorsPublicationLedger,
    build_publication_graph,
    run_publication_fixed_point,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.interval_closure import SorsIntervalClosureState
from stratbox.macrobanks.cbr_sors_restoration.strict.compiler import compile_strict_problem
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import build_quantity_graph


def _files(root: Path, yyyymmdd: str) -> SorsSourceFiles:
    history = root / '01_05_D_Debt_subj.xlsx'
    return SorsSourceFiles(
        regional_traditional=root / f'01_05_A_Debt_corp_{yyyymmdd}.xlsx',
        national_okved2=root / '01_02_C_Debt_corp_by_activity.xlsx',
        federal_district_okved2=root / f'01_03_C_Loans_corp_by_fd_activity_{yyyymmdd}.xlsx',
        national_traditional=root / '01_02_A_Debt_corp_by_activity.xlsx',
        sme_national_totals=root / '01_11_Debt_sme.xlsx',
        sme_national_okved2=root / '01_11_F_Debt_sme_by_activity.xlsx',
        sme_ie_national_okved2=root / '01_11_I_Debt_ie_by_activity.xlsx',
        sme_federal_district_okved2=root / f'01_12_A_Loans_sme_by_fd_activity_{yyyymmdd}.xlsx',
        sme_regional_totals=root / '01_13_F_Debt_sme_subj.xlsx',
        sme_ie_regional_totals=root / '01_13_I_Debt_sme_subj.xlsx',
        regional_totals_history=(history if history.exists() else None),
    )


def _snapshot(root: Path, as_of_date: str, yyyymmdd: str):
    bundle = load_sors_sources(_files(root, yyyymmdd), as_of_date)
    graph = build_quantity_graph(bundle)
    state = SorsIntervalClosureState(graph, tolerance=1e-7, max_passes=100)
    ledger = SorsPublicationLedger()
    publication = run_publication_fixed_point(
        state,
        build_publication_graph(graph),
        ledger,
        policy=RoundingPolicy(step=1.0),
        point_tolerance=1e-6,
        max_passes=100,
    )
    compilation = compile_strict_problem(
        bundle,
        graph,
        state.quantities_grid,
        point_tolerance=1e-6,
    )
    return bundle, graph, publication, compilation


@pytest.mark.skipif(
    not os.environ.get('STRATBOX_SORS_REAL_DATA_DIR'),
    reason='real SORS files are not configured',
)
def test_real_2026_06_snapshot() -> None:
    root = Path(os.environ['STRATBOX_SORS_REAL_DATA_DIR'])
    bundle, graph, publication, compilation = _snapshot(
        root, '2026-06-01', '20260601'
    )
    assert set(bundle.source_grid['portfolio_scope'].astype(str)) == {
        'CORPORATE_TOTAL', 'SME', 'SME_IE'
    }
    assert len(bundle.atomic_regions_grid) == 85
    assert len(bundle.okved2_classes_grid) == 88
    assert graph.quantities_grid['quantity_kind'].eq('ATOMIC_COMPONENT').sum() == 89_760
    assert graph.quantities_grid['quantity_kind'].eq('REGIONAL_CLASS_METRIC').sum() == 134_640
    constraints = compilation.problem.constraints_grid
    assert int(constraints['model_layer'].astype(str).eq('STRICT').sum()) > 1_318
    assert int(constraints['model_layer'].astype(str).eq('STRICT_DOMINANCE').sum()) == 59_840

    current = publication.current_facts_grid
    metric_zero = current[
        current['quantity_kind'].eq('REGIONAL_CLASS_METRIC')
        & current['published_value'].astype(float).eq(0.0)
    ]
    assert len(metric_zero) > 11_274
    assert publication.status == 'FIXED_POINT'


@pytest.mark.skipif(
    not os.environ.get('STRATBOX_SORS_REAL_DATA_DIR'),
    reason='real SORS files are not configured',
)
def test_real_2026_07_snapshot() -> None:
    root = Path(os.environ['STRATBOX_SORS_REAL_DATA_DIR'])
    july_file = root / '01_05_A_Debt_corp_20260701.xlsx'
    if not july_file.exists():
        pytest.skip('2026-07-01 SORS snapshot is not configured')

    bundle, graph, publication, compilation = _snapshot(
        root, '2026-07-01', '20260701'
    )
    assert len(bundle.atomic_regions_grid) == 85
    assert len(bundle.okved2_classes_grid) == 88
    assert graph.quantities_grid['quantity_kind'].eq('ATOMIC_COMPONENT').sum() == 89_760
    assert graph.quantities_grid['quantity_kind'].eq('REGIONAL_CLASS_METRIC').sum() == 134_640
    constraints = compilation.problem.constraints_grid
    assert int(constraints['model_layer'].astype(str).eq('STRICT').sum()) > 1_318
    assert int(constraints['model_layer'].astype(str).eq('STRICT_DOMINANCE').sum()) == 59_840

    current = publication.current_facts_grid
    metric_zero = current[
        current['quantity_kind'].eq('REGIONAL_CLASS_METRIC')
        & current['portfolio_scope'].astype(str).eq('CORPORATE_TOTAL')
        & current['published_value'].astype(float).eq(0.0)
    ]
    assert len(metric_zero) >= 11_370
    udmurtia_47 = current[
        current['quantity_id'].astype(str).eq(
            'metric:CORPORATE_TOTAL:0105a_region_056:47:overdue_fx'
        )
    ]
    assert len(udmurtia_47) == 1
    assert float(udmurtia_47.iloc[0]['published_value']) == 6.0
    assert publication.status == 'FIXED_POINT'
