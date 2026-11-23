"""Evidence admission for immutable logical escrow values."""
from dataclasses import asdict, replace
from stratbox.core.operations.tables import record_tables, use_tables
from . import snapshots

def flake_evidence(value):
    tables = (("rows", value.df_rows), ("observations", value.df_long), ("cells", value.df_cells))
    metadata = {"source_name": value.source_name, "period": value.file_date, "sheet": value.sheet_name,
                "header_row": value.header_row_index, "source_id": value.source_id,
                "original": asdict(value.original_identity) if value.original_identity else None,
                "method": value.method_version, "unmapped_headers": value.unmapped_headers,
                "columns": [asdict(column) for column in value.resolved_columns], "rows": [asdict(row) for row in value.rows]}
    return tables, metadata


def seal_flake(value, invocation):
    snapshots.flake_tables(value)
    tables, metadata = flake_evidence(value)
    return replace(value, evidence=record_tables(invocation, tables, metadata=metadata))


def use_flake(value, invocation):
    tables, metadata = flake_evidence(value)
    frames = use_tables(invocation, tables, receipt=value.evidence, metadata=metadata, role="escrow_flake")
    copied = replace(value, df_rows=frames[0], df_long=frames[1], df_cells=frames[2])
    snapshots.flake_tables(copied)
    return copied
