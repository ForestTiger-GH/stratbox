"""Monthly projection preserves qualified subset coverage and caller layout."""
from datetime import date
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from stratbox.domains.rosstat.methods import products
from stratbox.shared.data.selection import ObservationQuery
from stratbox.shared.data.values import Assessment, SourceDataset


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)


def dataset(assessment=Assessment()):
    base = {"subject_namespace": "iso3166-1", "subject": "RU", "unit": "RUB", "scale": Decimal(1),
        "measure_kind": "flow", "perimeter": "national", "period_kind": "interval", "measure": "absolute",
        "indicator_id": "investment", "metric": "investment.absolute", "raw_token": None,
        "unit_literal": "RUB", "footnotes": (), "number_format": "0.0", "evidence_ref": "fixture!C2"}
    rows = ({**base, "frequency": "monthly", "period": ("2024-01-01", "2024-01-31"),
        "period_start": date(2024, 1, 1), "period_end": date(2024, 1, 31), "display_date": date(2024, 2, 1),
        "value": Decimal(0), "value_status": "reported"},
        {**base, "frequency": "monthly", "period": ("2024-02-01", "2024-02-29"),
        "period_start": date(2024, 2, 1), "period_end": date(2024, 2, 29), "display_date": date(2024, 3, 1),
        "value": None, "value_status": "blank"},
        {**base, "frequency": "annual", "period": ("2024-01-01", "2024-12-31"),
        "period_start": date(2024, 1, 1), "period_end": date(2024, 12, 31), "display_date": date(2025, 1, 1),
        "value": Decimal(12), "value_status": "reported"})
    return SourceDataset("rosstat.short_term_indicators", rows, assessment=assessment)


def test_monthly_projection_records_parent_scope_and_qualifies_selected_members():
    original = dataset()
    view = products.monthly({"dataset": original}, None, context())["view"]
    assert len(view.value.rows) == 2 and view.value.assessment.complete
    assert view.value.assessment.coverage.parent_identity == original.identity
    assert "selected_scope" in view.value.assessment.qualifications
    partial = products.monthly({"dataset": dataset(Assessment("partial", ("publisher field unresolved",)))}, None, context())["view"]
    assert not partial.value.assessment.complete
    with pytest.raises(ValueError, match="monthly_query_required"):
        products.monthly({"dataset": original}, None,
            context(observation_query=ObservationQuery(filters={"frequency": ("annual",)})))


def test_layout_and_empty_period_policy_do_not_change_underlying_scientific_values():
    original = dataset()
    ctx = context(workbook_settings={"sheet_name": "Selected data", "headers": ("Item", "Unit"),
        "header_row": 3, "freeze_panes": "C4", "number_format": "0.000", "date_cells": "date",
        "include_evidence": False, "include_metadata": False, "include_empty_periods": True})
    view = products.monthly({"dataset": original}, None, ctx)["view"]
    encoded = products.render_monthly_workbook({"view": view}, None, context())["product"]
    book = load_workbook(BytesIO(encoded.data), data_only=True)
    try:
        assert book.sheetnames == ["Selected data"]
        sheet = book.active
        assert sheet["A3"].value == "Item" and sheet.freeze_panes == "C4"
        assert sheet["C3"].value.date() == date(2024, 2, 1) and sheet["D3"].value.date() == date(2024, 3, 1)
        assert sheet["C4"].value == 0 and sheet["D4"].value is None
        assert sheet["C4"].number_format == "0.000"
    finally:
        book.close()
    assert original.rows[0]["value"] == Decimal(0) and original.rows[1]["value"] is None
    with pytest.raises(ValueError, match="boolean_setting_required"):
        products.monthly({"dataset": original}, None, context(include_metadata="false"))
