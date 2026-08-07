from __future__ import annotations

import os
from pathlib import Path

import pytest

from stratbox.macrobanks.cbr_sors_restoration import SorsSourceFiles
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    RoundingPolicy,
    SorsPublicationLedger,
    build_publication_graph,
    run_publication_fixed_point,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.loader import load_sors_sources
from stratbox.macrobanks.cbr_sors_restoration.strict.interval_closure import (
    SorsIntervalClosureState,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import build_quantity_graph


def _real_dir() -> Path | None:
    value = os.environ.get('STRATBOX_SORS_REAL_20260701_DIR')
    return Path(value) if value else None


@pytest.mark.skipif(_real_dir() is None, reason='real 01.07.2026 fixture directory is opt-in')
def test_real_20260701_sme_constraints_restore_corporate_udmurtia_47_overdue_fx() -> None:
    root = _real_dir()
    assert root is not None
    files = SorsSourceFiles(
        regional_traditional=root / '01_05_A_Debt_corp_20260701.xlsx',
        national_okved2=root / '01_02_C_Debt_corp_by_activity.xlsx',
        federal_district_okved2=root / '01_03_C_Loans_corp_by_fd_activity_20260701.xlsx',
        national_traditional=root / '01_02_A_Debt_corp_by_activity.xlsx',
        sme_national_totals=root / '01_11_Debt_sme.xlsx',
        sme_national_okved2=root / '01_11_F_Debt_sme_by_activity.xlsx',
        sme_ie_national_okved2=root / '01_11_I_Debt_ie_by_activity.xlsx',
        sme_federal_district_okved2=root / '01_12_A_Loans_sme_by_fd_activity_20260701.xlsx',
        sme_regional_totals=root / '01_13_F_Debt_sme_subj.xlsx',
        sme_ie_regional_totals=root / '01_13_I_Debt_sme_subj.xlsx',
    )
    bundle = load_sors_sources(files, '2026-07-01')
    assert len(bundle.source_grid) == 18266
    assert set(bundle.source_grid['portfolio_scope']) == {
        'CORPORATE_TOTAL', 'SME', 'SME_IE'
    }
    assert set(bundle.validation_grid['status']) == {'PASS'}

    graph = build_quantity_graph(bundle)
    assert int(graph.quantities_grid['quantity_kind'].eq('ATOMIC_COMPONENT').sum()) == 89760
    publication_graph = build_publication_graph(graph)
    state = SorsIntervalClosureState(graph, tolerance=1e-7, max_passes=100)
    ledger = SorsPublicationLedger()
    execution = run_publication_fixed_point(
        state,
        publication_graph,
        ledger,
        policy=RoundingPolicy(step=1.0),
        point_tolerance=1e-6,
        max_passes=100,
    )
    udmurtia = bundle.atomic_regions_grid[
        bundle.atomic_regions_grid['region_name'].str.contains('Удмурт', case=False)
    ].iloc[0]
    region_code = str(udmurtia.region_code)

    sme = ledger.current_record(f'metric:SME:{region_code}:47:overdue_fx')
    ie = ledger.current_record(f'metric:SME_IE:{region_code}:47:overdue_fx')
    corporate = ledger.current_record(
        f'metric:CORPORATE_TOTAL:{region_code}:47:overdue_fx'
    )
    assert sme is not None and sme['published_value'] == 6.0
    assert sme['evidence_method'] == 'PUBLISHED_VALUE_INHERITED'
    assert ie is not None and ie['published_value'] == 6.0
    assert ie['evidence_method'] == 'PUBLISHED_VALUE_INHERITED'
    assert corporate is not None and corporate['published_value'] == 6.0
    assert corporate['evidence_method'] == 'PUBLICATION_CLOSURE_IDENTIFIED'

    row = execution.quantities_grid[
        execution.quantities_grid['quantity_id'].eq(
            f'metric:CORPORATE_TOTAL:{region_code}:47:overdue_fx'
        )
    ].iloc[0]
    assert float(row.lower_bound) == 5.5
    assert float(row.upper_bound) == 6.5
