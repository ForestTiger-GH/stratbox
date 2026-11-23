"""A complete readable cell transcript with source coordinates and statuses."""
import csv
from io import StringIO
from stratbox.shared.data.representation import Representation
from .snapshots import flake_tables


def readable_flake(value):
    flake_tables(value)
    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("source_name", "period", "sheet_name", *value.df_cells.columns))
    for cells in value.df_cells.itertuples(index=False, name=None):
        writer.writerow((value.source_name, value.file_date, value.sheet_name, *cells))
    return Representation("cbr.escrow.readable_cells", 1, "text/csv", stream.getvalue().encode("utf-8"), "utf-8")
