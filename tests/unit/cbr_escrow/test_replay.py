"""Cold-process continuation through source geometry, observations and prepared views."""
from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import os
import subprocess
import sys

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
from stratbox.core.commands.observations import observations_merge
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.domains.cbr.common.escrow import required_indicators
from stratbox.domains.cbr.methods.actions import escrow, observations, serialization
from stratbox.domains.cbr.products import actions
from stratbox.domains.cbr.products.specifications import ESCROW_CONTENT
from stratbox.domains.cbr.methods.tables.project_finance.columns import resolve_indicator_spec_by_header
from stratbox.domains.cbr.products.project_finance.pivots import build_escrow_pivot
from stratbox.shared.data.values import Assessment, Material, SourceDataset, WorkbookEvidence, fingerprint
from stratbox.shared.evidence import SourcePayload

SERIES = "cbr.project_finance.escrow"

def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)

def source(request):
    period = request.source_name.rsplit("_", 1)[1].split(".")[0]
    issue = f"{period[4:]}-{period[2:4]}-{period[:2]}"
    ctx = context(issue_id=issue)
    material = Material(request.payload.data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", SERIES)
    physical = WorkbookEvidence(material, read_workbook_cells(material.data))
    commands = DOMAIN.series[SERIES].commands
    tables = escrow.extract({"physical": physical}, commands["command.table.extract"].settings, ctx)["tables"]
    dataset = escrow.interpret({"tables": tables}, commands["command.table.interpret"].settings, ctx)["dataset"]
    return physical, tables, dataset

def history(*requests):
    return observations_merge({"datasets": tuple(source(request)[2] for request in requests)}, {}, context())["dataset"]

def prepared(dataset, settings=ESCROW_CONTENT, **parameters):
    return actions.prepare({"dataset": dataset}, settings, context(**parameters))["view"]

def rendered(view):
    return actions.render({"view": view}, ESCROW_CONTENT, context())["product"]

def encoded(value):
    return serialization.encode({"value": value}, None, context())["representation"]

def decoded(value):
    return serialization.decode({"representation": value}, None, context())["value"]

def publication(*, period="01062026", region="Example region", amount="0012.2500", extra=True):
    book = Workbook()
    sheet = book.active
    sheet.title = "Regions"
    specs = list(required_indicators())
    headers = [spec.canonical_name for spec in specs]
    values = [7.25 if spec.value_kind == "percent" else amount for spec in specs]
    if extra:
        headers.append("Unmapped source measure")
    sheet.append(["No.", "Субъект Российской Федерации (федеральный округ)", *headers])
    sheet.append(["Центральный ФО", None, *values, *(["not understood"] if extra else [])])
    region_values = list(values)
    region_values[0], region_values[1], region_values[2] = 0, None, "—"
    sheet.append([1, region, *region_values, *(["NA"] if extra else [])])
    sheet.append(["Итого", None, *values, *(["=1+1"] if extra else [])])
    buffer = BytesIO()
    book.save(buffer)
    book.close()
    return SimpleNamespace(payload=SourcePayload(buffer.getvalue(), source_id=SERIES), source_name=f"escrow_{period}.xlsx")


def test_source_table_and_observations_replay_preserve_precision_and_unknown_cells(tmp_path):
    physical, table, dataset = source(publication())
    restored = decoded(encoded(table))
    assert restored == table
    cells = [escrow.decode_cell(item) for row in table.tables[0].rows for item in row] if hasattr(escrow, "decode_cell") else None
    from stratbox.domains.cbr.methods.tables.project_finance.parser import decode_cell
    states = {decode_cell(item)[2] for row in table.tables[0].rows for item in row}
    assert {"blank", "marker", "unparsed", "formula_unresolved", "numeric"} <= states
    assert "Unmapped source measure" in table.tables[0].headers
    exact = next(row for row in dataset.rows if row["raw_token"] == "0012.2500")
    assert exact["value"] == Decimal("12.2500")
    assert dataset.semantics["unmapped_headers"] == ("Unmapped source measure",)
    assert decoded(encoded(dataset)) == dataset
    assert encoded(decoded(encoded(dataset))).identity == encoded(dataset).identity
    assert physical.material.identity in dataset.lineage


def test_prepared_product_renders_in_fresh_process_without_source_parser(tmp_path):
    dataset = history(publication(), publication(period="01072026", region="New region"))
    assert "Example region" in {row["subject"] for row in dataset.rows}
    view = prepared(dataset)
    assert "Example region" not in view.settings["region_order"]
    retained = tmp_path / "prepared.json"
    retained.write_bytes(encoded(view).data)
    target = tmp_path / "product.xlsx"
    script = r'''
import sys
from pathlib import Path
from types import SimpleNamespace
from stratbox.domains.cbr.methods.actions.serialization import decode
from stratbox.domains.cbr.products.actions import render
from stratbox.domains.cbr.products.specifications import ESCROW_CONTENT
ctx=SimpleNamespace(parameters={},checkpoint=lambda:None)
view=decode({"representation":Path(sys.argv[1]).read_bytes()},None,ctx)["value"]
product=render({"view":view},ESCROW_CONTENT,ctx)["product"]
Path(sys.argv[2]).write_bytes(product.data)
'''
    result = subprocess.run([sys.executable, "-c", script, str(retained), str(target)], env=os.environ.copy(), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    book = load_workbook(target, data_only=True)
    assert book["ССПКДПФО"]["B5"].value == 7.25
    assert book["ССПКДПФО"]["B5"].number_format == "#,##0.00"
    book.close()


def test_prepared_view_replay_keeps_tokens_and_actual_source_coordinates():
    dataset = history(publication(), publication(period="01072026"))
    view = prepared(dataset)
    restored = decoded(encoded(view))
    assert rendered(restored) == rendered(view)
    assert any(row["raw_token"] == "—" for row in restored.value)
    assert {use.coordinate.issue_id for use in dataset.source_uses} == {"2026-06-01", "2026-07-01"}
    assert all(use.coordinate.material_identity is not None for use in dataset.source_uses)


def test_duplicate_observations_are_never_averaged():
    frame = pd.DataFrame({"indicator_code": ["x", "x"], "Регион": ["r", "r"], "Дата": ["2026-01-01"] * 2, "Значение": [2, 10]})
    with pytest.raises(ValueError, match="duplicate_observation"):
        build_escrow_pivot(frame, "x", region_order=["r"], date_order=["2026-01-01"])
    with pytest.raises(Exception, match="duplicate"):
        history(publication(), publication())


def test_changed_material_identity_cannot_be_admitted_as_original_physical_evidence():
    physical, table, dataset = source(publication())
    changed = replace(physical, material=replace(physical.material, data=b"different original"))
    with pytest.raises(ValueError, match="identity_mismatch"):
        encoded(changed)
    modified = replace(dataset, assessment=Assessment("partial", qualifications=frozenset({"selection_incomplete"})))
    assert modified.identity != dataset.identity
    with pytest.raises(ValueError, match="history_incomplete"):
        prepared(modified)
    assert prepared(modified, require_complete_history=False)


def test_average_and_weighted_rates_have_distinct_semantic_identity():
    weighted = resolve_indicator_spec_by_header("Средневзвешенная ставка по кредитным договорам по федеральному округу, %")
    average = resolve_indicator_spec_by_header("Средняя ставка по кредитным договорам по федеральному округу, %")
    assert average.code != weighted.code
    assert average.unit == weighted.unit == "percent"
