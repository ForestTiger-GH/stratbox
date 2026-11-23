"""Integrate complete source releases without selecting product layout."""
from .contracts import EscrowDataset, EscrowRelease
from . import snapshots
from stratbox.domains.cbr.tables.project_finance.snapshots import flake_tables

def integrate_values(flakes, coverage, *, selection_complete=True):
    import pandas as pd
    if not flakes:
        raise ValueError("escrow.source_selection_empty")
    ordered = sorted(flakes, key=lambda flake: flake.file_date)
    periods = tuple(flake.file_date for flake in ordered)
    if len(periods) != len(set(periods)):
        raise ValueError("escrow.duplicate_release")
    specs, observations, dimensions, releases = {}, [], [], []
    for flake in ordered:
        flake_tables(flake)
        for column in flake.resolved_columns:
            previous = specs.get(column.spec.code)
            if previous is not None and previous != column.spec:
                raise ValueError("escrow.indicator_edition_conflict")
            specs[column.spec.code] = column.spec
        releases.append(EscrowRelease(flake.file_date, flake.source_name, flake.source_id, flake.original_identity,
                                      flake.sheet_name, flake.method_version, flake.unmapped_headers))
        for row in flake.df_rows.itertuples(index=False, name=None):
            dimensions.append((flake.file_date, *row))
        for source_row, source_column, header, code, token, kind, status, value, row_kind, region, display in flake.df_cells.itertuples(index=False, name=None):
            if code is not None:
                observations.append((flake.file_date, region, row_kind, code, value, token, status,
                                     flake.source_name, flake.sheet_name, source_row, source_column))
    result = EscrowDataset(
        pd.DataFrame(observations, columns=[c.name for c in snapshots.OBSERVATIONS.columns], dtype=object),
        pd.DataFrame(dimensions, columns=[c.name for c in snapshots.ROWS.columns], dtype=object),
        tuple(releases), tuple(sorted(specs.values(), key=lambda spec: spec.code)), coverage, selection_complete,
    )
    snapshots.dataset_tables(result)
    return result
