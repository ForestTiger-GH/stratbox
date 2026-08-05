from __future__ import annotations

from pathlib import Path

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsRestorationResult


def _strict_okved2_facts(result: SorsRestorationResult) -> pd.DataFrame:
    facts = result.facts_grid
    return facts[
        facts['classifier_id'].astype(str).eq('okved2')
        & facts['geography_kind'].astype(str).eq('atomic_region')
        & facts['is_reconstructed'].astype(bool)
    ].copy()


def export_sors_restoration_xlsx(result: SorsRestorationResult, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    restored = _strict_okved2_facts(result)
    with pd.ExcelWriter(out, engine='xlsxwriter', engine_kwargs={'options': {'constant_memory': True}}) as writer:
        result.canonical_grid.to_excel(writer, sheet_name='SourceGrid', index=False)
        result.facts_grid.to_excel(writer, sheet_name='FactsGrid', index=False)
        restored.to_excel(writer, sheet_name='RestoredOnly', index=False)
        result.bounds_grid.to_excel(writer, sheet_name='Bounds', index=False)
        result.bridge_diagnostics_grid.to_excel(writer, sheet_name='BridgeDiagnostics', index=False)
        result.mapping_edges_grid.to_excel(writer, sheet_name='Mapping', index=False)
        result.constraints_grid.to_excel(writer, sheet_name='Constraints', index=False)
        result.conflicts_grid.to_excel(writer, sheet_name='Conflicts', index=False)
        pd.DataFrame([result.audit]).to_excel(writer, sheet_name='Audit', index=False)
        if not restored.empty:
            for metric, group in restored.groupby('metric', sort=False):
                pivot = group.pivot_table(index='geography_name', columns='activity_code', values='value', aggfunc='first')
                pivot.to_excel(writer, sheet_name=str(metric)[:31])
            by_region = restored.pivot_table(index=['geography_name', 'activity_code', 'activity_name'], columns='metric', values='value', aggfunc='first').reset_index()
            by_region.to_excel(writer, sheet_name='ByRegionOKVED2', index=False)
            by_okved = restored.pivot_table(index=['activity_code', 'activity_name', 'geography_name'], columns='metric', values='value', aggfunc='first').reset_index()
            by_okved.to_excel(writer, sheet_name='ByOKVED2Region', index=False)
    return out
