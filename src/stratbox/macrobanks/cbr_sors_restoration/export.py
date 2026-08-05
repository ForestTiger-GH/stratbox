from __future__ import annotations

from pathlib import Path

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsRestorationResult


def _strict_restored(result: SorsRestorationResult) -> pd.DataFrame:
    facts = result.facts_grid
    return facts[
        facts['classifier_id'].astype(str).eq('okved2')
        & facts['geography_kind'].astype(str).eq('atomic_region')
        & facts['is_reconstructed'].astype(bool)
        & ~facts['is_estimate'].astype(bool)
    ].copy()


def _conditional_estimates(result: SorsRestorationResult) -> pd.DataFrame:
    estimates = result.estimates_grid
    if estimates.empty:
        return estimates
    return estimates[
        estimates['classifier_id'].astype(str).eq('okved2')
        & estimates['geography_kind'].astype(str).eq('atomic_region')
        & estimates['is_estimate'].astype(bool)
    ].copy()


def _write_metric_pivots(writer, frame: pd.DataFrame, prefix: str) -> None:
    if frame.empty:
        return
    for metric, group in frame.groupby('metric', sort=False):
        sheet = f'{prefix}_{metric}'[:31]
        pivot = group.pivot_table(
            index='geography_name',
            columns='activity_code',
            values='value',
            aggfunc='first',
        )
        pivot.to_excel(writer, sheet_name=sheet)


def export_sors_restoration_xlsx(
    result: SorsRestorationResult,
    path: str | Path,
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    restored = _strict_restored(result)
    estimates = _conditional_estimates(result)
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        result.canonical_grid.to_excel(writer, sheet_name='SourceGrid', index=False)
        result.facts_grid.to_excel(writer, sheet_name='FactsGrid', index=False)
        restored.to_excel(writer, sheet_name='StrictRestored', index=False)
        result.estimates_grid.to_excel(writer, sheet_name='ConditionalEstimates', index=False)
        result.bounds_grid.to_excel(writer, sheet_name='StrictBounds', index=False)
        result.bridge_bounds_grid.to_excel(writer, sheet_name='BridgeBounds', index=False)
        result.bridge_diagnostics_grid.to_excel(
            writer, sheet_name='BridgeDiagnostics', index=False
        )
        result.mapping_edges_grid.to_excel(writer, sheet_name='Mapping', index=False)
        result.constraints_grid.to_excel(writer, sheet_name='Constraints', index=False)
        result.conflicts_grid.to_excel(writer, sheet_name='Conflicts', index=False)
        pd.DataFrame([result.audit]).to_excel(writer, sheet_name='Audit', index=False)
        _write_metric_pivots(writer, restored, 'STRICT')
        _write_metric_pivots(writer, estimates, 'BRIDGE')
        if not restored.empty:
            by_region = restored.pivot_table(
                index=['geography_name', 'activity_code', 'activity_name'],
                columns='metric',
                values='value',
                aggfunc='first',
            ).reset_index()
            by_region.to_excel(
                writer, sheet_name='Strict_ByRegionOKVED2', index=False
            )
        if not estimates.empty:
            by_region_est = estimates.pivot_table(
                index=['geography_name', 'activity_code', 'activity_name'],
                columns='metric',
                values='value',
                aggfunc='first',
            ).reset_index()
            by_region_est.to_excel(
                writer, sheet_name='Bridge_ByRegionOKVED2', index=False
            )
    return out
