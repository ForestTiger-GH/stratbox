"""Select and decode the DBF that implements the form's declared physical layout."""

from pathlib import PurePosixPath
from struct import error as StructError

import pandas as pd

from stratbox.base.ioapi.dbf_bytes import open_dbf_bytes
from stratbox.base.utils.optional_deps import MissingExtra

from .dbf import CBRFieldParser


def pick_dbf_fields(members, *, field_candidates, optional_field_candidates, prefer_stem_contains):
    if set(field_candidates) & set(optional_field_candidates):
        raise ValueError("Required and optional DBF fields overlap")
    candidates = []
    for name, data in members.items():
        try:
            with open_dbf_bytes(data, parserclass=CBRFieldParser) as table:
                fields = {field.upper(): field for field in table.field_names}
        except MissingExtra:
            raise
        except (ValueError, OSError, UnicodeError, StructError):
            continue
        resolved = {}
        score = 20 if prefer_stem_contains and prefer_stem_contains.casefold() in PurePosixPath(name).stem.casefold() else 0
        for field, names in {**field_candidates, **optional_field_candidates}.items():
            physical = next((fields[alias] for alias in names if alias in fields), None)
            if physical is not None:
                resolved[field] = physical
                score += physical.upper() == names[0]
        if field_candidates.keys() <= resolved.keys():
            candidates.append((score, name, resolved))
    if not candidates:
        raise ValueError("DBF_LAYOUT_UNRECOGNIZED")
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        raise ValueError("DBF_LAYOUT_AMBIGUOUS")
    _, name, field_map = candidates[0]
    return name, field_map


def decode_dbf(data: bytes, fields: dict[str, str], columns: tuple[str, ...], *, checkpoint):
    values = {name: [] for name in columns}
    with open_dbf_bytes(data, parserclass=CBRFieldParser) as table:
        for index, record in enumerate(table):
            if index % 8192 == 0:
                checkpoint()
            for column in columns:
                values[column].append(record.get(fields[column]) if column in fields else None)
    return pd.DataFrame({column: pd.Series(value, dtype="object") for column, value in values.items()})
