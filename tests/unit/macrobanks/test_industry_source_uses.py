"""Industry calculations and prepared products retain actual publication pairs."""
from dataclasses import replace

import pytest

from stratbox.core.execution import prepare_input
from stratbox.core.execution.value_context import value_context
from stratbox.core.registry import operation_catalog
from stratbox.shared.data.processing import DataContract
from stratbox.shared.evidence import SourcePayload
from stratbox.domains.cbr.products.corporate_lending.industry.contracts import IndustryPivotRequest
from stratbox.domains.cbr.tables.corporate_lending.industry.sources import industry_source_uses
import stratbox.domains.cbr.operations.corporate_lending.debt as debt
import stratbox.domains.cbr.operations.corporate_lending.issuance as issuance

from test_cbr_industries_0104a_issuance import _book as issuance_book
from test_cbr_industries_0105a_debt_corp import _workbook_bytes


@pytest.fixture(scope="module", params=["debt", "issuance"])
def publication(request):
    if request.param == "debt":
        domain, family, source = debt, "0105a", "cbr.corporate_lending.debt_0105a"
        original = debt.ParseIndustryRequest(SourcePayload(_workbook_bytes(
            report_date="01.02.2019", kemerovo_name="Кемеровская область")),
            "01_05_A_Debt_corp_20190201.xlsx")
    else:
        domain, family, source = issuance, "0104a", "cbr.corporate_lending.issuance_0104a"
        original = issuance.ParseIssuanceRequest(SourcePayload(issuance_book()),
            "01_04_A_New_loans_corp_20190201.xlsx")
    parsed = domain.parse(original)
    assert parsed.outcome == "succeeded", parsed.diagnostics
    return domain, family, source, original, parsed.value


def test_source_bound_apk_pivots_and_replays_preserve_the_actual_publication(publication):
    domain, family, source_id, original, parsed = publication
    catalog = operation_catalog()
    bound = catalog.bind_source(source_id, format="xlsx")
    prefix = "cbr.industries." + family
    operation = catalog.get(prefix + ".calculate_apk")
    contract = next(contract for contract in operation.processing.inputs[0].alternatives
        if contract.schema_id.endswith(".parsed_file"))
    calculation = bound.bind(prefix + ".calculate_apk",
        inputs={"stream": prepare_input(parsed, contract)}).invoke()
    assert calculation.outcome == "succeeded", calculation.diagnostics
    uses = calculation.value.source_uses
    assert len(uses) == 1
    assert uses[0].coordinate.source_id == source_id
    assert uses[0].coordinate.issue_id == parsed.report_date
    assert uses[0].coordinate.asset_id == parsed.source_id
    assert uses[0].coordinate.material_identity == original.payload.identity
    assert value_context(calculation.value).source_ids == (source_id,)
    snapshot = domain.build_calculation_snapshot(domain.IndustrySnapshotRequest(
        calculation.value, "test.calculation", "capture"))
    assert snapshot.outcome == "succeeded", snapshot.diagnostics
    restored = bound.bind(prefix + ".read_calculation_snapshot", inputs={
        "snapshot": prepare_input(snapshot.value, DataContract("dataset.snapshot"))}).invoke()
    assert restored.outcome == "succeeded", restored.diagnostics
    assert restored.value.source_uses == uses
    pivot_input = catalog.get(prefix + ".build_pivots").processing.inputs[0]
    calculation_contract = next(contract for contract in pivot_input.alternatives
        if contract.schema_id.endswith(".calculation"))
    pivots = bound.bind(prefix + ".build_pivots", inputs={
        "stream": prepare_input(restored.value, calculation_contract)}, parameters={
            "pivot": IndustryPivotRequest("region_code", "report_date", sheet_dimensions=("measure", "currency_scope")),
            "industry_code": "apk"}).invoke()
    assert pivots.outcome == "succeeded", pivots.diagnostics
    assert pivots.value.source_uses == uses
    assert all(table.source_uses == uses for table in pivots.value.tables)
    retained_view = domain.build_view_snapshot(domain.IndustrySnapshotRequest(
        pivots.value, "test.view", "capture"))
    assert retained_view.outcome == "succeeded", retained_view.diagnostics
    replayed = bound.bind(prefix + ".read_view_snapshot", inputs={
        "snapshot": prepare_input(retained_view.value, DataContract("dataset.snapshot"))}).invoke()
    assert replayed.outcome == "succeeded", replayed.diagnostics
    assert replayed.value.source_uses == uses


def test_only_admitted_schema_coordinates_establish_an_industry_source(publication):
    _, _, source_id, _, parsed = publication
    frame = parsed.df_stream.copy()
    frame["source_name"] = "An unrelated filename cannot change the publisher source"
    assert industry_source_uses(frame)[0].coordinate.source_id == source_id
    frame["series_code"] = "unreviewed.schema"
    frame["source_name"] = "01_05_A_Debt_corp_20190201.xlsx"
    assert industry_source_uses(frame) == ()
