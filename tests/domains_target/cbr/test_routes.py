"""Source semantics survive the direct standard-command boundary."""
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from stratbox.domains.cbr.domain import DOMAIN
from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
from stratbox.shared.data.values import DbfEvidence, Material, SourceDataset, WorkbookEvidence


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)


def call(series_id, command_id, inputs, **parameters):
    command = DOMAIN.series[series_id].commands[command_id]
    return command.method.resolve()(inputs, command.settings, context(**parameters))


def workbook(series, sheets, configure=None):
    book = Workbook()
    book.remove(book.active)
    for name, rows in sheets:
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    if configure:
        configure(book)
    output = BytesIO()
    book.save(output)
    material = Material(output.getvalue(), source_id=series)
    return WorkbookEvidence(material, read_workbook_cells(material.data))


def interpreted(series, sheets, configure=None, **parameters):
    physical = workbook(series, sheets, configure)
    tables = call(series, "command.table.extract", {"physical": physical}, **parameters)["tables"]
    return call(series, "command.table.interpret", {"tables": tables}, **parameters)["dataset"]


def test_static_catalog_covers_every_source_and_resolves_narrow_actions():
    assert len(DOMAIN.series) == 57
    assert {record.publication.family_id for record in DOMAIN.series.values()} == {
        "cbr.banking_sector_structure", "cbr.corporate_lending", "cbr.exchange_rates", "cbr.external_debt",
        "cbr.funding", "cbr.household_finance", "cbr.household_lending", "cbr.monetary_statistics",
        "cbr.project_finance", "cbr.reporting_forms", "cbr.securities", "cbr.service_network"}
    for identifier, record in DOMAIN.series.items():
        assert identifier == record.id
        assert record.publication.series_id == identifier
        assert callable(record.commands["command.table.interpret"].method.resolve())
    with pytest.raises(TypeError):
        DOMAIN.series["invented"] = None


def test_merged_month_headers_retain_unresolved_period_and_exact_units():
    series = "cbr.exchange_rates.exchange_rate"
    dataset = interpreted(series, [("Ежемесячные", [
        ["Source, млн руб."], [None, 2024, None, None, None],
        [None, "Янв", "Фев", "Мар", "Апр"], ["Measure", 10, 20, 30, 40],
    ])], lambda book: book.active.merge_cells("B2:D2"))
    assert [row["value"] for row in dataset.rows] == [10, 20, 30]
    assert dataset.rows[1]["period"] == ("2024-02-01", "2024-02-29")
    assert dataset.rows[0]["scale"] == Decimal(1000000)
    assert "cbr.statistics.period_column_unresolved" in dataset.assessment.findings


def test_source_flow_is_not_inferred_by_renaming_point_dates():
    series = "cbr.corporate_lending.corp_new_loans_a"
    dataset = interpreted(series, [("итого", [
        ["Объем предоставленных кредитов, млн руб.", date(2026, 1, 1)], ["Activity", "12345678901234567890,123450"],
    ])])
    row = dataset.rows[0]
    assert row["value"] == Decimal("12345678901234567890.123450")
    assert row["raw_token"] == "12345678901234567890,123450"
    assert row["measure_kind"] == "flow"
    assert row["period_kind"] == "as_of"
    assert dict(row["dimensions"])["period_qualification"] == "reported_date_interval_unresolved"


def test_statistical_interpretation_reuses_physical_decode_and_checks_source():
    series = "cbr.monetary_statistics.monetary_agg"
    physical = workbook(series, [("Денежные агрегаты", [["Amount, млн руб.", date(2026, 1, 1)], ["Total", 10]])])
    tables = call(series, "command.table.extract", {"physical": physical})["tables"]
    assert tables.tables[0] is physical.workbook.sheets[0]
    with pytest.raises(ValueError, match="source_mismatch"):
        call("cbr.funding.budget_all", "command.table.extract", {"physical": physical})
    result = call(series, "command.table.interpret", {"tables": tables})["dataset"]
    assert result.rows[0]["value"] == 10
    assert result.identity


def test_published_134_fields_require_explicit_measurement_and_preserve_row_code():
    from stratbox.core.formats.dbf_lossless import DBFField, DBFRecord
    series = "cbr.reporting_forms.f134"
    fields = (DBFField("REGN", "N", 4, 0, 1), DBFField("C1", "C", 15, 0, 5), DBFField("C3", "N", 16, 0, 20))
    physical = DbfEvidence(Material(b"retained exact DBF evidence", source_id=series), fields,
        (DBFRecord(1, False, ("0012", "U104.2.2.1", "123")),))
    tables = call(series, "command.table.extract", {"physical": physical}, issue_id="2014-04-01")["tables"]
    with pytest.raises(ValueError, match="measurement_required"):
        call(series, "command.table.interpret", {"tables": tables}, issue_id="2014-04-01")
    dataset = call(series, "command.table.interpret", {"tables": tables}, issue_id="2014-04-01",
        period="2014-04-01", unit="RUB", scale=Decimal(1000))["dataset"]
    assert dataset.rows[0]["source_code"] == "U104.2.2.1"
    assert dataset.rows[0]["value"] == Decimal(123)
    assert "published_fields_only" in dataset.assessment.qualifications
    calculation = DOMAIN.calculations["cbr.forms.f134.model"].commands["command.calculate.formula"]
    with pytest.raises(ValueError, match="requires_publisher_evidence"):
        calculation.method.resolve()({"dataset": dataset}, calculation.settings, context())


def test_office_html_is_decoded_once_then_interpreted_without_network():
    series = "cbr.service_network.bank_offices"
    fixture = Path(__file__).resolve().parents[2] / "fixtures/universal_core/offices-basic.html"
    material = Material(fixture.read_bytes(), "text/html", series)
    physical = call(series, "command.document.decode", {"material": material})["physical"]
    tables = call(series, "command.table.extract", {"physical": physical})["tables"]
    dataset = call(series, "command.table.interpret", {"tables": tables},
        captured_on="2026-11-26", official_as_of="2026-11-01")["dataset"]
    assert dataset.rows
    assert {row["period"] for row in dataset.rows} == {"2026-11-01"}
    assert all(row["measure_kind"] == "count" for row in dataset.rows)


def test_apk_uses_complete_same_period_components_and_never_changes_source():
    from stratbox.domains.cbr.calculations.industry.actions import REQUIRED
    rows = tuple({"metric": metric, "subject": "udmurtia", "period": "2026-07-01", "period_kind": "as_of",
        "unit": "RUB", "scale": Decimal(1000000), "measure_kind": "stock", "perimeter": "CORPORATE_TOTAL",
        "value": Decimal(10), "value_status": "reported", "evidence_ref": metric,
        "dimensions": (("currency_scope", "total"),)} for metric in sorted(REQUIRED))
    source = SourceDataset("cbr.corporate_lending.debt_0105a", rows)
    action = DOMAIN.calculations["cbr.corporate_lending.debt_apk"].commands["command.calculate.formula"]
    result = action.method.resolve()({"dataset": source}, action.settings, context())["dataset"]
    assert {row["metric"]: row["value"] for row in result.rows} == {"lpk": Decimal(10), "apk": Decimal(40)}
    assert len(source.rows) == 5
    with pytest.raises(ValueError, match="required_industries_missing"):
        action.method.resolve()({"dataset": SourceDataset(source.source_id, rows[:-1])}, action.settings, context())


def test_apk_keeps_namespace_and_period_meaning_in_its_operand_grain():
    from stratbox.domains.cbr.calculations.industry.actions import REQUIRED
    action=DOMAIN.calculations["cbr.corporate_lending.debt_apk"].commands["command.calculate.formula"]
    rows=tuple({"metric":metric,"subject":"same-code","subject_namespace":"namespace-a" if i<3 else "namespace-b",
        "period":"2026-07-01","period_kind":"as_of","measure_kind":"stock","unit":"RUB","scale":Decimal(1000000),
        "perimeter":"CORPORATE_TOTAL","value":Decimal(10),"value_status":"reported","evidence_ref":metric,"dimensions":()}
        for i,metric in enumerate(sorted(REQUIRED)))
    with pytest.raises(ValueError,match="required_industries_missing"):
        action.method.resolve()({"dataset":SourceDataset(action.settings.series_id,rows)},action.settings,context())


def test_apk_exact_arithmetic_ignores_the_callers_decimal_precision():
    from decimal import localcontext
    from stratbox.domains.cbr.calculations.industry.actions import REQUIRED
    action=DOMAIN.calculations["cbr.corporate_lending.debt_apk"].commands["command.calculate.formula"]
    value=Decimal("1234567890123456789012345678901234567890.0001")
    rows=tuple({"metric":metric,"subject":"r","subject_namespace":"cbr.published_region","period":"2026-07-01",
        "period_kind":"as_of","measure_kind":"stock","unit":"RUB","scale":Decimal(1000000),"perimeter":"CORPORATE_TOTAL",
        "value":value,"value_status":"reported","evidence_ref":metric,"dimensions":()} for metric in sorted(REQUIRED))
    with localcontext() as low:
        low.prec=3
        output=action.method.resolve()({"dataset":SourceDataset(action.settings.series_id,rows)},action.settings,context())["dataset"]
    assert next(row["value"] for row in output.rows if row["metric"]=="apk")==Decimal("4938271560493827156049382715604938271560.0004")
