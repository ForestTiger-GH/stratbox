"""Replay preserves financial meaning and provenance across representations."""
from dataclasses import replace
import json

import pytest

from stratbox.core.execution import ExecutionContext
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.representation import Representation
from stratbox.shared.identity import ByteIdentity
from stratbox.domains.minfin import (
    ReadFlakeRequest, RenderFlakeRequest, SerializeFlakeRequest, SummaryRequest,
    calculate_headlines, read_source_flake, render_source_flake, serialize_source_flake,
)
from stratbox.domains.minfin.tables.contracts import FlakeColumn, FlakeRow, FlakeTable


def _budget_flake():
    return FlakeTable(
        "minfin.fedbud", "minfin.fedbud.annex3.monthly", ByteIdentity.of(b"original workbook"),
        "Federal budget", "monthly", "ytd",
        (FlakeColumn(4, "October 2025 **", "2025-10"), FlakeColumn(7, "October 2026 **", "2026-10")),
        (FlakeRow(9, "1", "Доходы, всего", ("100.0000", "110")),
         FlakeRow(12, "2", "Расходы, всего", ("120", "135")),
         FlakeRow(18, "3", "Дефицит (-)/Профицит (+)", ("-20", "-25"))),
        "minfin.flake.budget.v2", "billion_rub",
    )


def _serialize(flake):
    result = serialize_source_flake(SerializeFlakeRequest(flake))
    assert result.outcome == "succeeded", result.diagnostics
    return result


def test_complete_replay_preserves_coordinates_units_exact_scalars_and_headlines():
    original = _budget_flake()
    encoded = _serialize(original)
    decoded = read_source_flake(ReadFlakeRequest(encoded.value))
    assert decoded.outcome == "succeeded", decoded.diagnostics
    assert decoded.value == original
    direct = calculate_headlines(SummaryRequest(original))
    retained = calculate_headlines(SummaryRequest(decoded.value))
    assert direct.outcome == retained.outcome == "succeeded"
    assert direct.value == retained.value
    assert direct.computation.computation_id == retained.computation.computation_id
    assert direct.used_inputs and decoded.used_inputs and encoded.used_inputs
    assert encoded.value.data == _serialize(decoded.value).value.data


def test_nwf_mixed_units_null_and_empty_are_distinct_and_historical_method_survives():
    original = replace(_budget_flake(), family_id="minfin.nwf", source_id="minfin.nwf.flows",
                       value_basis="stock", unit_hint="mixed", method_version="minfin.flake.historic.v1",
                       rows=(FlakeRow(7, "2", "Other source row", (None, "")),
                             FlakeRow(11, "2.1", "Exact zero", ("0", "0.000"))))
    decoded = read_source_flake(ReadFlakeRequest(_serialize(original).value))
    assert decoded.outcome == "succeeded", decoded.diagnostics
    assert decoded.value == original
    assert decoded.value.unit_hint == "mixed"
    # Replay admits retained historical data; calculating with a different
    # currently registered economic method requires explicit reprocessing.
    summary = calculate_headlines(SummaryRequest(decoded.value))
    assert summary.outcome == "failed"
    assert summary.diagnostics[0].code == "minfin.summary.profile_mismatch"


def test_same_csv_bytes_with_different_originals_do_not_share_computation_identity():
    original = _budget_flake()
    another = replace(original, original_identity=ByteIdentity.of(b"revised original"),
                      sheet_name="Revised title",
                      columns=(replace(original.columns[0], original_header="October 2025"), original.columns[1]))
    first = render_source_flake(RenderFlakeRequest(original))
    second = render_source_flake(RenderFlakeRequest(another))
    assert first.outcome == second.outcome == "succeeded"
    assert first.value.identity == second.value.identity
    assert first.computation.computation_id != second.computation.computation_id
    assert _serialize(original).value.identity != _serialize(another).value.identity


def test_changed_values_and_calculation_period_change_computation_identity():
    original = _budget_flake()
    changed = replace(original, rows=(replace(original.rows[0], values=("100", "120")),
                                      original.rows[1], replace(original.rows[2], values=("-20", "-15"))))
    first = calculate_headlines(SummaryRequest(original))
    second = calculate_headlines(SummaryRequest(changed))
    earlier = calculate_headlines(SummaryRequest(original, "2025-10"))
    assert first.outcome == second.outcome == earlier.outcome == "succeeded"
    assert len({r.computation.computation_id for r in (first, second, earlier)}) == 3
    assert first.used_inputs != second.used_inputs
    assert first.value.metrics[0].value == "110"
    assert second.value.metrics[0].value == "120"


@pytest.mark.parametrize("damage", [
    lambda doc: doc.update(schema="minfin.flake.v999"),
    lambda doc: doc.update(unrecognized="invented metadata"),
    lambda doc: doc["original_identity"].update(size=True),
    lambda doc: doc["rows"][0].update(values=[0, "1"]),
    lambda doc: doc["rows"][0].update(values=["1"]),
    lambda doc: doc["columns"][0].update(period_id="2025-13"),
    lambda doc: doc["columns"][1].update(source_column=4),
    lambda doc: doc["rows"][1].update(source_row=9),
])
def test_malformed_retained_values_are_rejected(damage):
    encoded = _serialize(_budget_flake()).value
    document = json.loads(encoded.data)
    damage(document)
    malformed = replace(encoded, data=json.dumps(document).encode())
    result = read_source_flake(ReadFlakeRequest(malformed))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "minfin.flake.representation_invalid"


def test_csv_is_an_export_and_cannot_masquerade_as_lossless_flake():
    exported = render_source_flake(RenderFlakeRequest(_budget_flake()))
    result = read_source_flake(ReadFlakeRequest(exported.value))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "minfin.flake.representation_invalid"


def test_replay_and_render_respect_input_cell_and_output_budgets():
    flake = _budget_flake()
    encoded = _serialize(flake).value
    for budget in (ExecutionBudget(input_bytes=1), ExecutionBudget(cells=1), ExecutionBudget(output_bytes=1)):
        context = ExecutionContext(budget=budget)
        result = read_source_flake(ReadFlakeRequest(encoded), context=context)
        assert result.outcome == "failed"
        assert result.diagnostics[0].code.startswith("budget.")
    tiny = render_source_flake(RenderFlakeRequest(flake), context=ExecutionContext(budget=ExecutionBudget(output_bytes=1)))
    assert tiny.outcome == "failed" and tiny.value is None


def test_duplicate_json_keys_are_rejected():
    encoded = _serialize(_budget_flake()).value
    malformed = replace(encoded, data=b'{"schema":"minfin.flake.v1",' + encoded.data[1:])
    result = read_source_flake(ReadFlakeRequest(malformed))
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "minfin.flake.representation_invalid"


def test_flake_build_records_full_extract_identity_and_selected_options():
    from stratbox.domains.minfin import BuildFlakeRequest, build_source_flake
    from stratbox.domains.minfin.tables.contracts import Cell, Sheet, TableExtract

    sheet = "Source"
    rows = [
        ("Code", "Indicator", "2025-10", "2026-10"),
        ("1", "Доходы, всего", "100", "110"),
        ("2", "Расходы, всего", "120", "135"),
        ("3", "Дефицит (-)/Профицит (+)", "-20", "-25"),
    ]
    cells = tuple(Cell(sheet, row, col, "text", value)
                  for row, values in enumerate(rows, 1) for col, value in enumerate(values, 1))
    source = TableExtract("minfin.fedbud", "minfin.fedbud.annex3.monthly", ByteIdentity.of(b"source"),
                          "xlsx", (Sheet(sheet, 4, 4, cells),))
    changed_cells = tuple(replace(cell, value="111") if (cell.row, cell.column) == (2, 4) else cell
                          for cell in cells)
    changed = replace(source, sheets=(replace(source.sheets[0], cells=changed_cells),))
    first = build_source_flake(BuildFlakeRequest(source, source.source_id))
    second = build_source_flake(BuildFlakeRequest(changed, changed.source_id))
    assert first.outcome == second.outcome == "succeeded"
    assert first.value.original_identity == second.value.original_identity
    assert first.used_inputs != second.used_inputs
    assert first.computation.computation_id != second.computation.computation_id
    assert first.computation.output == _serialize(first.value).value.identity
