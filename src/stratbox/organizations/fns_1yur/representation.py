from csv import writer
from io import StringIO

from stratbox.data.releases import csv_rows

from .semantics import SchemaError, validate_canonical


def read_canonical(data):
    fields, rows = validate_canonical(data)
    with StringIO(newline="") as stream:
        output = writer(stream, lineterminator="\n")
        output.writerows(csv_rows(data))
        if stream.getvalue().encode("utf-8") != data:
            raise SchemaError("CSV_NON_CANONICAL")
    return fields, rows
