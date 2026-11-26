"""Lossless CSV records used by source-local office geometry."""
import csv
from io import StringIO

def csv_rows(data: bytes):
    return tuple(tuple(row) for row in csv.reader(StringIO(data.decode("utf-8-sig"))))
