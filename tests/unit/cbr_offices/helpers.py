"""Explicit source evidence for the office regression tests."""
from datetime import date
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from openpyxl import Workbook

from stratbox.core.commands.calculations import observations_compare
from stratbox.core.commands.serialization import value_decode, value_encode
from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.shared.data.values import Material, WorkbookEvidence


BANK = "cbr.service_network.bank_offices"
TERRITORY = "cbr.service_network.territorial_offices"
HTML = Path(__file__).resolve().parents[2] / "fixtures/universal_core/offices-basic.html"
CAPTURED = date(2026, 11, 22)
OFFICIAL = date(2026, 11, 1)
GRAIN = ("subject_namespace", "subject", "metric", "period", "unit", "scale", "perimeter", "dimensions")


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)


def call(series_id, command_id, inputs, *, settings=None, **parameters):
    command = DOMAIN.series[series_id].commands[command_id]
    return command.method.resolve()(inputs, command.settings if settings is None else settings, context(**parameters))


def bank_evidence(captured=CAPTURED, official=OFFICIAL, data=None):
    material = Material(HTML.read_bytes() if data is None else data, "text/html", BANK)
    physical = call(BANK, "command.document.decode", {"material": material})["physical"]
    tables = call(BANK, "command.table.extract", {"physical": physical})["tables"]
    dataset = call(BANK, "command.table.interpret", {"tables": tables},
        captured_on=captured, official_as_of=official)["dataset"]
    return material, tables, dataset


def compare(before, after):
    return observations_compare({"before": before, "after": after}, {"grain": GRAIN}, context())


def roundtrip(path, value):
    encoded = value_encode({"value": value}, None, context())["representation"]
    path.write_bytes(encoded.data)
    return value_decode({"representation": path.read_bytes()}, None, context())["value"]


def workbook(*, extra=True, formula=True, copies=1):
    book = Workbook()
    sheet = book.active
    sheet.title = "Published observations"
    sheet.append(["Данные по состоянию на 01.11.2026"])
    labels = ["Территория", "Кредитные организации", "Филиалы", "Мобильные офисы", "Всего"]
    sheet.append(labels + (["Дополнительная отметка"] if extra else []))
    names = ["Российская Федерация"] + [f"Новая территория {index:03d}" for index in range(35)]
    for index, name in enumerate(names):
        values = [name, 2, 3, "=2+3" if formula and index == 0 else 5, 10]
        sheet.append(values + (["новая категория"] if extra else []))
    for index in range(1, copies):
        book.copy_worksheet(sheet).title = f"Competing block {index:02d}"
    stream = BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()


def territorial_tables(*, data=None, **parameters):
    material = Material(workbook() if data is None else data,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", TERRITORY)
    physical = WorkbookEvidence(material, read_workbook_cells(material.data))
    parameters.setdefault("as_of", OFFICIAL)
    return call(TERRITORY, "command.table.extract", {"physical": physical}, **parameters)["tables"]
