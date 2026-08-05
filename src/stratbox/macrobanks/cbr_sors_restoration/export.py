from __future__ import annotations

from pathlib import Path

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsRestorationResult


def export_sors_restoration_xlsx(result: SorsRestorationResult, path: str | Path) -> Path:
    """Optional analyst workbook; strict facts and uncertain bounds stay separated."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out, engine='openpyxl') as writer:
        result.facts_grid.to_excel(writer, sheet_name='StrictFacts', index=False)
        result.bounds_grid.to_excel(writer, sheet_name='Bounds', index=False)
        result.mapping_diagnostics.to_excel(writer, sheet_name='MappingDiagnostics', index=False)
        pd.DataFrame([result.audit]).to_excel(writer, sheet_name='Audit', index=False)
    return out
