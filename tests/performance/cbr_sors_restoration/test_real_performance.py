from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from time import perf_counter

import pytest

from stratbox.macrobanks.cbr_sors_restoration import (
    SorsCrosswalkConfig,
    SorsCellResolutionConfig,
    SorsRunConfig,
    SorsSourceFiles,
    SorsWorkbookRequest,
    export_sors_workbook,
    run_sors_crosswalk,
    run_sors_restoration,
)

_REAL_ROOT = os.environ.get('STRATBOX_SORS_REAL_DATA_DIR')
_RUN_PERFORMANCE = os.environ.get('STRATBOX_SORS_RUN_PERFORMANCE') == '1'
_HAS_HIGHSPY = importlib.util.find_spec('highspy') is not None

pytestmark = pytest.mark.skipif(
    not (_REAL_ROOT and _RUN_PERFORMANCE),
    reason=(
        'set STRATBOX_SORS_REAL_DATA_DIR and '
        'STRATBOX_SORS_RUN_PERFORMANCE=1 to run real performance gates'
    ),
)


def _files() -> SorsSourceFiles:
    root = Path(str(_REAL_ROOT))
    return SorsSourceFiles(
        regional_traditional=root / '01_05_A_Debt_corp_20260601.xlsx',
        national_okved2=root / '01_02_C_Debt_corp_by_activity.xlsx',
        federal_district_okved2=(
            root / '01_03_C_Loans_corp_by_fd_activity_20260601.xlsx'
        ),
        national_traditional=root / '01_02_A_Debt_corp_by_activity.xlsx',
        regional_totals_history=root / '01_05_D_Debt_subj.xlsx',
    )


def test_full_structural_pass_and_workbook(tmp_path: Path) -> None:
    started = perf_counter()
    result = run_sors_restoration(
        _files(),
        SorsRunConfig(as_of_date='2026-06-01'),
    )
    structural_seconds = perf_counter() - started
    assert structural_seconds < 120
    assert len(result.regional_okved2_grid) == 44_880
    assert result.summary.closure_identified_facts == 11_274

    started = perf_counter()
    workbook = export_sors_workbook(
        result,
        SorsWorkbookRequest(
            output_path=tmp_path / 'sors.xlsx',
            overwrite=True,
        ),
    )
    assert perf_counter() - started < 60
    assert workbook.file_size > 0


@pytest.mark.skipif(not _HAS_HIGHSPY, reason='official highspy is unavailable')
@pytest.mark.parametrize(
    ('target_budget', 'maximum_seconds'),
    ((100, 1_800), (1_000, 10_800)),
)
def test_strict_target_budget(target_budget: int, maximum_seconds: int) -> None:
    started = perf_counter()
    result = run_sors_restoration(
        _files(),
        SorsRunConfig(
            as_of_date='2026-06-01',
            cell_resolution=SorsCellResolutionConfig(
                mode='priority',
                max_target_attempts=target_budget,
                per_solve_time_limit_seconds=30,
                run_time_limit_seconds=1_800,
            ),
        ),
    )
    assert perf_counter() - started < maximum_seconds
    assert result.summary.strict_status == 'OPTIMAL'
    assert result.summary.cell_targets_attempted <= target_budget


@pytest.mark.skipif(not _HAS_HIGHSPY, reason='official highspy is unavailable')
def test_crosswalk_feasibility_gate() -> None:
    strict = run_sors_restoration(
        _files(),
        SorsRunConfig(as_of_date='2026-06-01'),
    )
    started = perf_counter()
    crosswalk = run_sors_crosswalk(
        strict,
        SorsCrosswalkConfig(
            mode='feasibility',
            per_solve_time_limit_seconds=1_800,
        ),
    )
    assert perf_counter() - started < 3_600
    assert crosswalk.status in {'OPTIMAL', 'PARTIAL'}
