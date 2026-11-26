"""Small final-protocol test helpers; every scientific stage remains visible."""
from dataclasses import replace
from pathlib import Path
from struct import pack
from types import SimpleNamespace

from stratbox.core.commands import decoding as technical_decoding
from stratbox.core.commands import serialization as technical_serialization
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.shared.data.values import Material

DAY = "2026-04-01"


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)


def series(code):
    return DOMAIN.series["cbr.reporting_forms.f" + str(code)]


def invoke(record, command, inputs, **parameters):
    spec = record.commands[command]
    return spec.method.resolve()(inputs, spec.settings, context(**parameters))


def command(code, name, inputs, **parameters):
    return invoke(series(code), "command." + name, inputs, **parameters)


def dbf(fields, records, *, version=3):
    """Synthetic byte geometry, including exact numeric lexemes and deletion flags."""
    width = 1 + sum(field[2] for field in fields)
    header = pack("<BBBBIHH20x", version, 126, 4, 1, len(records), 33 + 32 * len(fields), width)
    columns = b"".join(pack("<11sc4xBB14x", name.encode("ascii"), kind.encode("ascii"), size, decimals)
        for name, kind, size, decimals in fields)
    rows = b"".join(flag + b"".join(value.ljust(field[2]) for field, value in zip(fields, values))
        for flag, values in records)
    return header + columns + b"\r" + rows + b"\x1a"


def character_dbf(fields, rows):
    return dbf(tuple((name, "C", 20, 0) for name in fields), tuple((b" ",
        tuple(str(value).encode("cp866") for value in row)) for row in rows))


def physical(code, data, **metadata):
    material = Material(data, source_id=series(code).id, metadata=metadata)
    evidence = technical_decoding.dbf_decode({"material": material}, None, context())["physical"]
    # Binding material to this use is distinct from source-neutral physical decoding.
    return replace(evidence, material=material)


def tables(code, data, *, issue_id=DAY):
    return command(code, "table.extract", {"physical": physical(code, data)}, issue_id=issue_id)["tables"]


def dataset(code, fields, rows, *, issue_id=DAY, **parameters):
    extracted = tables(code, character_dbf(fields, rows), issue_id=issue_id)
    return command(code, "table.interpret", {"tables": extracted}, issue_id=issue_id, **parameters)["dataset"]


def calculate(code, source, **parameters):
    target = DOMAIN.calculations["cbr.forms.f" + str(code) + ".model"]
    assert len(target.commands) == 1
    name = next(iter(target.commands))
    return invoke(target, name, {"dataset": source}, **parameters)["dataset"]


def view(source, **parameters):
    return invoke(DOMAIN.products["cbr.forms.workbook"], "command.view.prepare", {"dataset": source}, **parameters)["view"]


def render(prepared, **parameters):
    return invoke(DOMAIN.products["cbr.forms.workbook"], "command.product.render", {"view": prepared}, **parameters)["product"]


def reopen(tmp_path, value):
    """Restore using only final shared encoding and newly opened bytes."""
    encoded = technical_serialization.value_encode({"value": value}, None, context())["representation"]
    path = Path(tmp_path) / encoded.identity.sha256
    path.write_bytes(encoded.data)
    return technical_serialization.value_decode({"representation": path.read_bytes()}, None, context())["value"]


def change_row(source, **changes):
    return replace(source, rows=({**source.rows[0], **changes}, *source.rows[1:]))
