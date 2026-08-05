import sys

import pytest

from stratbox.macrobanks.cbr_sors_restoration.linear.highs import (
    SorsSolverDependencyError,
    _load_highs,
)


def test_solver_has_no_scipy_internal_fallback(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, 'highspy', None)
    with pytest.raises(SorsSolverDependencyError, match='official HiGHS'):
        _load_highs()


def test_bridge_solver_unavailable_returns_partial_result(monkeypatch, small_result) -> None:
    from dataclasses import replace
    from types import SimpleNamespace

    import numpy as np
    import pandas as pd

    from stratbox.macrobanks.cbr_sors_restoration.bridge import operations
    from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsBridgeConfig

    problem = SimpleNamespace(
        num_variables=0,
        num_constraints=0,
        matrix=SimpleNamespace(nnz=0),
        objective=np.asarray([], dtype=float),
    )
    compilation = SimpleNamespace(
        problem=problem,
        target_catalog_grid=pd.DataFrame(
            columns=(
                'target_id', 'region_code', 'region_name', 'class_code',
                'metric', 'indices', 'coefficients', 'constant',
            )
        ),
        mapping_edges_grid=pd.DataFrame(),
    )

    class UnavailableSession:
        def __init__(self, *args, **kwargs):
            raise SorsSolverDependencyError('official HiGHS unavailable')

    monkeypatch.setattr(operations, 'compile_bridge_problem', lambda *args: compilation)
    monkeypatch.setattr(operations, 'HighsSession', UnavailableSession)
    result = operations.run_sors_bridge(
        replace(small_result, _source_bundle=object()),
        SorsBridgeConfig(mode='optimum_only'),
    )
    assert result.status == 'SOLVER_UNAVAILABLE'
    assert len(result.regional_okved2_grid) == len(
        small_result.regional_okved2_grid
    )
    assert result.diagnostics_grid.set_index('key').loc[
        'targets_attempted', 'value'
    ] == 0
