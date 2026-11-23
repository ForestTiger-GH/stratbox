from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from time import perf_counter

import pytest

from stratbox.core.storage.filestore import LocalFileStore

from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsCrosswalkConfig
from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsOptimizationConfig
from stratbox.domains.cbr.analytics.corporate_lending.sors.contracts import SorsRunConfig
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceFiles
from stratbox.domains.cbr.products.corporate_lending.sors.contracts import SorsWorkbookRequest
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import CrosswalkSorsRequest
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import RenderSorsRequest
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import RestoreSorsRequest
from stratbox.domains.cbr.operations.corporate_lending.sors.api import run_crosswalk
from stratbox.domains.cbr.operations.corporate_lending.sors.api import read_source_files
from stratbox.domains.cbr.operations.corporate_lending.sors.api import build_views, render_views, prepare_from_originals
from stratbox.domains.cbr.operations.corporate_lending.sors.definitions import BuildSorsViewsRequest, PrepareSorsOriginalsRequest
from stratbox.domains.cbr.operations.corporate_lending.sors.api import restore

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
        sme_national_totals=root / '01_11_Debt_sme.xlsx',
        sme_national_okved2=root / '01_11_F_Debt_sme_by_activity.xlsx',
        sme_ie_national_okved2=root / '01_11_I_Debt_ie_by_activity.xlsx',
        sme_federal_district_okved2=(
            root / '01_12_A_Loans_sme_by_fd_activity_20260601.xlsx'
        ),
        sme_regional_totals=root / '01_13_F_Debt_sme_subj.xlsx',
        sme_ie_regional_totals=root / '01_13_I_Debt_sme_subj.xlsx',
        regional_totals_history=root / '01_05_D_Debt_subj.xlsx',
    )


def test_full_structural_pass_and_workbook(tmp_path: Path) -> None:
    started = perf_counter()
    inputs = read_source_files(_files(), store=LocalFileStore())
    assert inputs.outcome == "succeeded", inputs.diagnostics
    bundle = prepare_from_originals(PrepareSorsOriginalsRequest(inputs.value, SorsRunConfig(as_of_date="2026-06-01")))
    assert bundle.outcome == "succeeded", bundle.diagnostics
    operation = restore(RestoreSorsRequest(
        bundle.value,
        SorsRunConfig(as_of_date='2026-06-01'),
    ))
    assert operation.outcome == "succeeded", operation.diagnostics
    result = operation.value
    structural_seconds = perf_counter() - started
    assert structural_seconds < 120
    assert len(result.regional_okved2_grid) == 44_880
    component_zeros = result.current_component_facts_grid
    assert int(component_zeros['published_value'].astype(float).eq(0.0).sum()) == 11_274

    started = perf_counter()
    views = build_views(BuildSorsViewsRequest(result, SorsWorkbookRequest()))
    assert views.outcome == "succeeded", views.diagnostics
    exported = render_views(RenderSorsRequest(views.value))
    assert exported.outcome == "succeeded", exported.diagnostics
    workbook = exported.value
    assert perf_counter() - started < 60
    assert workbook.representation.identity.size > 0


@pytest.mark.skipif(not _HAS_HIGHSPY, reason='official highspy is unavailable')
@pytest.mark.parametrize(
    ('target_budget', 'maximum_seconds'),
    ((100, 1_800), (1_000, 10_800)),
)
def test_strict_target_budget(target_budget: int, maximum_seconds: int) -> None:
    started = perf_counter()
    inputs = read_source_files(_files(), store=LocalFileStore())
    assert inputs.outcome == "succeeded", inputs.diagnostics
    bundle = prepare_from_originals(PrepareSorsOriginalsRequest(inputs.value, SorsRunConfig(as_of_date="2026-06-01")))
    assert bundle.outcome == "succeeded", bundle.diagnostics
    operation = restore(RestoreSorsRequest(
        bundle.value,
        SorsRunConfig(
            as_of_date='2026-06-01',
            optimization=SorsOptimizationConfig(
                mode='priority',
                max_targets=target_budget,
                per_solve_time_limit_seconds=30,
            ),
        ),
    ))
    assert operation.outcome == "succeeded", operation.diagnostics
    result = operation.value
    assert perf_counter() - started < maximum_seconds
    assert result.summary.strict_status == 'OPTIMAL'
    assert result.summary.optimization_targets_attempted <= target_budget


@pytest.mark.skipif(not _HAS_HIGHSPY, reason='official highspy is unavailable')
def test_crosswalk_feasibility_gate() -> None:
    inputs = read_source_files(_files(), store=LocalFileStore())
    assert inputs.outcome == "succeeded", inputs.diagnostics
    bundle = prepare_from_originals(PrepareSorsOriginalsRequest(inputs.value, SorsRunConfig(as_of_date="2026-06-01")))
    assert bundle.outcome == "succeeded", bundle.diagnostics
    strict = restore(RestoreSorsRequest(bundle.value, SorsRunConfig(as_of_date="2026-06-01")))
    assert strict.outcome == "succeeded", strict.diagnostics
    started = perf_counter()
    operation = run_crosswalk(CrosswalkSorsRequest(
        strict.value,
        SorsCrosswalkConfig(
            mode='feasibility',
            per_solve_time_limit_seconds=1_800,
        ),
    ))
    assert operation.outcome == "succeeded", operation.diagnostics
    assert perf_counter() - started < 3_600
    assert operation.value.status in {'OPTIMAL', 'PARTIAL'}
