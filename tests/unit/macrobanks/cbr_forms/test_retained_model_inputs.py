"""Financial-model admission from retained integrated observations."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO

import pandas as pd
import pytest
from openpyxl import load_workbook

from stratbox.core.storage.datasets import operations as datasets
from stratbox.core.storage.datasets.files import FileDatasetStore
from stratbox.core.storage.filestore.local import LocalFileStore
from stratbox.domains.cbr.operations import reporting_forms as forms
from stratbox.shared.data.observations import PeriodRef, SubjectRef
from stratbox.shared.data.observation_snapshots import observation_snapshot

DAY = date(2026, 4, 1)


def accepted(result):
    assert result.outcome == "succeeded", result.diagnostics
    return result.value


def projection(code, columns, rows, fields):
    return forms.FormSnapshot(forms.FormKey(code, DAY), fields, pd.DataFrame(rows, columns=columns, dtype="object"), ())


def aligned_group():
    snapshot = projection("802", ("REGN", "CODE", "total"), (("1000", "14", "1.2300"),),
                          {"REGN": "REGN_GKO", "CODE": "STR", "total": "VSEGO"})
    mapping = forms.FormSubjectMapping("cbr.banking_group.registration", "1000",
                                      SubjectRef("banking_group", "group-a"), "group-map.v1")
    return accepted(forms.align_forms(forms.AlignFormRequest((snapshot,), "forms.integrated", "version-1", subjects=(mapping,))))


def reopen(tmp_path, batch):
    encoded = accepted(forms.snapshot_observations(forms.SnapshotFormObservationsRequest(batch, "retained.forms", "version-1")))
    store = FileDatasetStore(LocalFileStore(str(tmp_path)), "datasets", provider_id="files", scope_id="test")
    written = accepted(datasets.write_snapshot(datasets.WriteSnapshotRequest(encoded), store=store))
    other = FileDatasetStore(LocalFileStore(str(tmp_path)), "datasets", provider_id="files", scope_id="test")
    loaded = accepted(datasets.read_snapshot(datasets.ReadSnapshotRequest(written.reference), store=other))
    return accepted(forms.restore_observations(loaded))


def test_retained_group_observations_prepare_calculate_and_render_without_source_projection(tmp_path):
    original = aligned_group()
    restored = reopen(tmp_path, original)
    prepared = accepted(forms.prepare_model_inputs(forms.PrepareFormModelInputsRequest(restored)))
    calculated = accepted(forms.calculate(forms.CalculateFormRequest(prepared)))
    capital = calculated.long.loc[calculated.long["Код"].eq("14")].iloc[0]
    assert capital["Значение"] == Decimal("1.2300")
    assert capital["REGN"] == "1000"
    assert capital["SourceSubjectNamespace"] == "cbr.banking_group.registration"
    assert capital["SubjectNamespace"] == "banking_group" and capital["SubjectId"] == "group-a"
    assert capital["PeriodKind"] == "as_of" and capital["PeriodAsOf"] == DAY
    assert any(item.role == "integrated_form_observations" and item.identity == observation_snapshot(restored).identity
               for item in calculated.lineage)
    views = accepted(forms.build_form_views(calculated))
    workbook = accepted(forms.render_workbook(views))
    opened = load_workbook(BytesIO(workbook.data), data_only=True)
    assert "Данные" in opened.sheetnames
    opened.close()


def test_retained_income_observations_keep_explicit_interval_through_model_calculation(tmp_path):
    snapshot = projection("102", ("REGN", "CODE", "VALUE"), (("1000", "27000", "123.4500"),),
                          {"REGN": "REGN", "CODE": "CODE", "VALUE": "SIM_ITOGO"})
    period = PeriodRef("interval", start=date(2026, 1, 1), end=date(2026, 3, 31))
    batch = accepted(forms.align_forms(forms.AlignFormRequest((snapshot,), "income.integrated", "version-1", ((DAY, period),))))
    restored = reopen(tmp_path, batch)
    prepared = accepted(forms.prepare_model_inputs(forms.PrepareFormModelInputsRequest(restored)))
    calculated = accepted(forms.calculate(forms.CalculateFormRequest(prepared)))
    row = calculated.long.loc[calculated.long.IndicatorId.eq("net_fee_income")].iloc[0]
    assert row["Значение"] == Decimal("123.4500")
    assert row.PeriodKind == "interval" and row.PeriodStart == period.start and row.PeriodEnd == period.end
    missing = forms.build_form_data(forms.BuildFormDataRequest((snapshot,)))
    assert missing.outcome == "failed" and missing.diagnostics[0].code == "request.form_flow_period_required"
    composed = accepted(forms.build_form_data(forms.BuildFormDataRequest((snapshot,), periods=((DAY, period),))))
    pd.testing.assert_frame_equal(composed.long, calculated.long)


@pytest.mark.parametrize("change,diagnostic", (
    (lambda item: replace(item, metric=replace(item.metric, unit="USD")), "source.form_model_metric_unreviewed"),
    (lambda item: replace(item, metric=replace(item.metric, scale=Decimal(1))), "source.form_model_metric_unreviewed"),
    (lambda item: replace(item, metric=replace(item.metric, definition_version="unreviewed")), "source.form_model_metric_unreviewed"),
    (lambda item: replace(item, period=PeriodRef("capture", DAY)), "source.form_model_stock_period_invalid"),
    (lambda item: replace(item, dimensions=tuple(pair for pair in item.dimensions if pair[0] != "reporting_date")), "source.form_model_axes_invalid"),
    (lambda item: replace(item, perimeter="credit_institution"), "source.form_model_perimeter_invalid"),
))
def test_preparation_rejects_semantically_incompatible_observations(change, diagnostic):
    batch = aligned_group()
    changed = replace(batch, observations=(change(batch.observations[0]), *batch.observations[1:]))
    result = forms.prepare_model_inputs(forms.PrepareFormModelInputsRequest(changed))
    assert result.outcome == "failed" and result.diagnostics[0].code == diagnostic


def test_preparation_rejects_missing_channels_and_calculation_rechecks_admission():
    batch = aligned_group()
    incomplete = replace(batch, observations=batch.observations[:1])
    result = forms.prepare_model_inputs(forms.PrepareFormModelInputsRequest(incomplete))
    assert result.outcome == "failed" and result.diagnostics[0].code == "source.form_model_channels_incomplete"
    valid = accepted(forms.prepare_model_inputs(forms.PrepareFormModelInputsRequest(batch)))
    forged = replace(valid, batch=incomplete)
    result = forms.calculate(forms.CalculateFormRequest(forged))
    assert result.outcome == "failed" and result.diagnostics[0].code == "source.form_model_channels_incomplete"


def test_account_plan_is_required_and_keeps_same_account_in_other_chapters_separate(tmp_path):
    snapshot = projection("101", ("REGN", "CODE", "VALUE", "PLAN", "SIDE"),
                          (("1481", "45.2", "123.4", "A", "1"), ("1481", "45.2", "999.9", "B", "1")),
                          {"REGN": "REGN", "CODE": "NUM_SC", "VALUE": "IITG", "PLAN": "PLAN", "SIDE": "A_P"})
    batch = accepted(forms.align_forms(forms.AlignFormRequest((snapshot,), "balance.integrated", "version-1")))
    retained = reopen(tmp_path, batch)
    prepared = accepted(forms.prepare_model_inputs(forms.PrepareFormModelInputsRequest(retained)))
    calculated = accepted(forms.calculate(forms.CalculateFormRequest(prepared)))
    value = calculated.long.loc[calculated.long.IndicatorId.eq("loans_individuals"), "Значение"].iloc[0]
    assert value == Decimal("123.4")
    missing = replace(batch, observations=tuple(replace(item, dimensions=tuple(pair for pair in item.dimensions if pair[0] != "plan"))
                                                for item in batch.observations))
    refused = forms.prepare_model_inputs(forms.PrepareFormModelInputsRequest(missing))
    assert refused.outcome == "failed" and refused.diagnostics[0].code == "source.form_model_account_plan_missing"
