"""Fiscal scientific assertions using static specifications and standard evidence."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from stratbox.core.commands.standard import calculate_formula, document_decode, workbook_decode
from stratbox.domains.minfin.domain import DOMAIN
from stratbox.domains.minfin.common.numbers import numeric_value
from stratbox.domains.minfin.common.periods import normalize_period
from stratbox.domains.minfin.common.semantics import DocumentField, DocumentRules, RowRule
from stratbox.domains.minfin.methods import budget, documents, publications
from stratbox.domains.minfin.calculations.fund import FUND_LIQUID_ASSETS
from stratbox.shared.data.values import Material


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)


def workbook(rows, *, headers=("2025-10", "2026-10"), source="minfin.fedbud.annex3.monthly"):
    value = Workbook()
    sheet = value.active
    sheet.title = "Fiscal source"
    sheet.append(("Code", "Indicator", *headers))
    for row in rows:
        sheet.append(row)
    stream = BytesIO()
    value.save(stream)
    return Material(stream.getvalue(), source_id=source, metadata={"issue_id": "issue-42"})


def budget_dataset(*, values=("110", "135", "-25")):
    material = workbook((("1", "Доходы, всего", "100.0000", values[0]),
        ("2", "Расходы, всего", "120", values[1]),
        ("3", "Дефицит (-)/Профицит (+)", "-20", values[2])))
    settings = DOMAIN.series[material.source_id].commands["command.table.extract"].settings
    physical = workbook_decode({"material": material}, None, context())["physical"]
    physical = replace(physical, material=material)
    tables = budget.extract({"physical": physical}, settings, context())["tables"]
    return budget.interpret({"tables": tables}, settings, context())["dataset"], settings


def test_all_thirteen_records_are_explicit_immutable_and_lazy_methods_resolve():
    assert len(DOMAIN.series) == 13
    assert set(DOMAIN.series) >= {"minfin.nwf.flows", "minfin.nwf.volume", "minfin.nwf.preferred_shares", "minfin.nwf.veb_deposits"}
    for record in DOMAIN.series.values():
        assert all(callable(spec.method.resolve()) for spec in record.commands.values())
    with pytest.raises(TypeError):
        DOMAIN.series["invented"] = None
    assert DOMAIN.series["minfin.nwf.veb_deposits"].publication.formats == {"doc"}


@pytest.mark.parametrize("raw,status,value", [(None, "missing", None), ("", "blank", None),
    ("—", "dash", None), ("0", "reported", Decimal(0)),
    ("1\u00a0234,5000", "reported", Decimal("1234.5000"))])
def test_numeric_status_and_exact_scalars_remain_distinct(raw, status, value):
    assert numeric_value(raw) == (value, status)


@pytest.mark.parametrize("header,frequency,expected", [("2026", "annual", "2026"),
    ("1 кв. 2026", "quarterly", "2026-Q1"), ("окт. 26", "monthly", "2026-10"),
    ("2026-10-01 00:00:00", "monthly", "2026-10"), ("01.10.2026", "monthly", "2026-10")])
def test_period_labels_have_explicit_frequency(header, frequency, expected):
    assert normalize_period(header, frequency) == expected


def test_budget_ytd_intervals_exact_values_and_source_coordinates():
    dataset, settings = budget_dataset()
    assert len(dataset.rows) == 6
    first = dataset.rows[0]
    assert first["period"] == ("2025-01-01", "2025-10-31")
    assert first["measure_kind"] == "flow" and first["value_basis"] == "ytd"
    assert first["scale"] == Decimal("1e9") and first["unit"] == "RUB"
    assert first["value"] == Decimal("100.0000")
    assert "row=2&column=3" in first["evidence_ref"]
    assert budget.validate({"dataset": dataset}, settings, context())["dataset"] is dataset
    aligned = budget.align({"dataset": dataset}, settings, context())["dataset"]
    assert aligned.rows == dataset.rows


def test_inconsistent_budget_balance_and_wrong_units_are_rejected():
    dataset, settings = budget_dataset(values=("110", "135", "999"))
    with pytest.raises(ValueError, match="balance_inconsistent"):
        budget.validate({"dataset": dataset}, settings, context())
    dataset, settings = budget_dataset()
    wrong = replace(dataset, rows=({**dataset.rows[0], "unit": "USD"}, *dataset.rows[1:]))
    with pytest.raises(ValueError, match="unit_mismatch"):
        budget.validate({"dataset": wrong}, settings, context())


def test_nwf_stock_dates_and_same_date_liquid_formula():
    material = workbook((("2", "Объем на конец периода", "100", "120"),
        ("5", "Размещено в иные разрешенные активы на конец периода", "30", "40")),
        headers=("01.10.2025", "01.10.2026"), source="minfin.nwf.flows")
    settings = DOMAIN.series[material.source_id].commands["command.table.extract"].settings
    physical = workbook_decode({"material": material}, None, context())["physical"]
    tables = budget.extract({"physical": physical}, settings, context())["tables"]
    dataset = budget.interpret({"tables": tables}, settings, context())["dataset"]
    assert {row["period"] for row in dataset.rows} == {"2025-10-01", "2026-10-01"}
    assert all(row["measure_kind"] == "stock" for row in dataset.rows)
    result = calculate_formula({"dataset": dataset}, FUND_LIQUID_ASSETS.settings, context())["dataset"]
    assert {row["value"] for row in result.rows} == {Decimal(70), Decimal(80)}
    assert all(row["metric"] == "nwf.liquid" and row["value_status"] == "derived" for row in result.rows)


def test_nwf_mixed_rows_need_explicit_individual_semantics():
    material = workbook((("9", "Caller identified flow", "—", "0"),), source="minfin.nwf.flows")
    settings = DOMAIN.series[material.source_id].commands["command.table.extract"].settings
    ctx = context(row_rules=(RowRule("9", "nwf.explicit_flow", "Caller identified flow", "period_flow", "USD", Decimal(1)),))
    tables = budget.extract({"physical": workbook_decode({"material": material}, None, ctx)["physical"]}, settings, ctx)["tables"]
    dataset = budget.interpret({"tables": tables}, settings, ctx)["dataset"]
    assert dataset.rows[0]["value_status"] == "dash" and dataset.rows[0]["value"] is None
    assert dataset.rows[1]["value"] == 0 and dataset.rows[1]["period"] == ("2026-10-01", "2026-10-31")
    assert dataset.rows[1]["unit"] == "USD" and dataset.rows[1]["measure_kind"] == "flow"
    budget.validate({"dataset": dataset}, settings, ctx)


def test_cards_use_attachment_date_and_stable_document_identity_after_rename():
    html = '''<div class="document_card" data-href="/ru/?id_57=80042"><span class="date">Изменено: 12.11.2026</span><a class="file_item" href="/common/upload/library/renamed.xlsx">New name</a></div><div class="document_card" data-href="/ru/?id_57=80039"><span class="date">Изменено: 01.10.2026</span><a class="file_item" href="/common/upload/library/quarter.xlsx">Other</a></div>'''
    rules = DOMAIN.series["minfin.fedbud.annex3.monthly"].commands["command.publication.scan"].settings
    listing = publications.scan({"index": Material(html.encode(), "text/html")}, rules, context())["listing"]
    entries = {entry.source_id: entry for entry in listing.entries}
    assert entries["minfin.fedbud.annex3.monthly"].issue_id == "2026-11-12"
    assert entries["minfin.fedbud.annex3.quarterly"].issue_id == "2026-10-01"
    selected = publications.select({"listing": listing}, rules, context())["selection"]
    request = publications.prepare_request({"locator": selected.entries[0]}, rules, context())["request"]
    assert request.url.endswith("renamed.xlsx") and request.metadata["document_id"] == "id_57:80042"


def test_conflicting_document_and_filename_evidence_stays_unresolved():
    html = '''<div class="document_card" data-href="/ru/?id_57=80042"><a class="file_item" href="/common/upload/library/Prilozhenie_3_dannye_109-111_demo_kvartal.xlsx">file</a></div>'''
    rules = DOMAIN.series["minfin.fedbud.annex3.monthly"].commands["command.publication.scan"].settings
    listing = publications.scan({"index": Material(html.encode(), "text/html")}, rules, context())["listing"]
    assert not listing.entries and any("conflicting_identity" in value for value in listing.assessment.findings)


def test_document_geometry_fields_and_actual_currency_remain_explicit():
    from docx import Document
    document = Document()
    document.add_paragraph("ФНБ на 01.05.2026")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text, table.cell(0, 1).text = "Показатель", "Значение"
    table.cell(1, 0).text, table.cell(1, 1).text = "Остаток", "10,2500"
    output = BytesIO()
    document.save(output)
    material = Material(output.getvalue(), source_id="minfin.nwf.volume", metadata={"issue_id": "issue-document"})
    physical = document_decode({"material": material}, None, context())["physical"]
    settings = DocumentRules(material.source_id,
        (DocumentField(1, 1, 1, "nwf.volume_usd", "USD", Decimal(1), "2026-05-01", "Остаток"),),
        ("ФНБ на 01.05.2026",))
    tables = documents.extract({"physical": physical}, settings, context())["tables"]
    dataset = documents.interpret({"tables": tables}, settings, context())["dataset"]
    assert dataset.rows[0]["unit"] == "USD" and dataset.rows[0]["value"] == Decimal("10.2500")
    assert dataset.rows[0]["period"] == "2026-05-01"
    with pytest.raises(ValueError, match="reviewed_fields_required"):
        documents.interpret({"tables": tables}, DocumentRules(material.source_id), context())
    with pytest.raises(ValueError, match="layout_unsupported"):
        documents.interpret({"tables": tables}, replace(settings, required_text=("different date",)), context())


@pytest.mark.parametrize("source_id", tuple(source.id for source in DOMAIN.series.values() if source.publication.formats == {"xlsx"}))
def test_every_declared_workbook_series_uses_a_real_type_correct_semantic_route(source_id):
    spec = DOMAIN.series[source_id]
    settings = spec.commands["command.table.extract"].settings
    headers = {"monthly": ("2025-10", "2026-10"), "quarterly": ("2 кв.2025", "2 кв.2026"),
               "annual": ("2025", "2026")}[settings.frequency]
    rows = (("2", "Объем на конец периода", "100", "110"),
            ("5", "Размещено в иные разрешенные активы на конец периода", "30", "40")) if source_id == "minfin.nwf.flows" else (
        ("1", "Доходы, всего", "100", "110"), ("2", "Расходы, всего", "120", "135"),
        ("3", "Дефицит (-)/Профицит (+)", "-20", "-25"))
    physical = workbook_decode({"material": workbook(rows, headers=headers, source=source_id)}, None, context())["physical"]
    tables = spec.commands["command.table.extract"].method.resolve()({"physical": physical}, settings, context())["tables"]
    value = spec.commands["command.table.interpret"].method.resolve()({"tables": tables}, settings, context())["dataset"]
    validated = spec.commands["command.observations.validate"].method.resolve()({"dataset": value}, settings, context())["dataset"]
    assert validated.rows and validated.source_id == source_id
    assert all(row["frequency"] == settings.frequency for row in validated.rows)
    assert all(row["period_kind"] == ("as_of" if source_id == "minfin.nwf.flows" else "interval") for row in validated.rows)


def test_fiscal_dataset_portable_roundtrip_retains_exact_values_periods_and_provenance():
    from stratbox.core.commands.standard import value_decode, value_encode
    value, _ = budget_dataset()
    representation = value_encode({"value": value}, None, context())["representation"]
    replay = value_decode({"representation": representation}, None, context())["value"]
    assert replay == value and replay.identity == value.identity
    assert replay.rows[0]["raw_token"] == "100.0000"
    assert replay.source_uses == value.source_uses and replay.source_uses
    use = replay.source_uses[0]
    assert use.qualification == "domain_validated" and use.coordinate.source_id == value.source_id
    assert use.coordinate.issue_id == "issue-42"
    assert len(use.coordinate.layout_identity) == len(use.coordinate.semantic_identity) == 64
    aligned = budget.align({"dataset": value}, DOMAIN.series[value.source_id].commands["command.observations.align"].settings,
        context())["dataset"]
    assert aligned.source_uses == value.source_uses


def test_formula_without_cache_is_unparsed_and_never_fabricated():
    material = workbook((("1", "Доходы, всего", "100", "=100+10"),
        ("2", "Расходы, всего", "120", "135"),
        ("3", "Дефицит (-)/Профицит (+)", "-20", "-25")))
    settings = DOMAIN.series[material.source_id].commands["command.table.extract"].settings
    physical = workbook_decode({"material": material}, None, context())["physical"]
    tables = budget.extract({"physical": physical}, settings, context())["tables"]
    value = budget.interpret({"tables": tables}, settings, context())["dataset"]
    missing = next(row for row in value.rows if row["metric"] == "budget.revenue" and row["period_end"] == "2026-10-31")
    assert missing["value"] is None and missing["value_status"] == "unparsed"
    assert "minfin.table.formula_without_cache" in value.assessment.findings


def test_budget_change_compares_matching_accumulation_windows_and_rejects_different_months():
    from stratbox.core.commands.standard import calculate_change
    from stratbox.core.execution.service import ExecutionFailure
    from stratbox.domains.minfin.calculations.budget import BUDGET_CHANGES
    value, _ = budget_dataset()
    revenue = replace(value, rows=tuple(row for row in value.rows if row["metric"] == "budget.revenue"))
    difference = calculate_change({"observations": revenue}, BUDGET_CHANGES.settings, context())["dataset"]
    assert difference.rows[0]["value"] == Decimal(10)
    mismatched = replace(revenue, rows=(revenue.rows[0], {**revenue.rows[1],
        "period": ("2026-01-01", "2026-09-30"), "period_end": "2026-09-30"}))
    with pytest.raises(ExecutionFailure, match="accumulation_window|comparison_window"):
        calculate_change({"observations": mismatched}, BUDGET_CHANGES.settings, context())


def test_explicit_issue_context_reaches_source_uses_and_conflicting_context_is_rejected():
    value, settings = budget_dataset()
    material = workbook((("1", "Доходы, всего", "100", "110"),
        ("2", "Расходы, всего", "120", "135"), ("3", "Дефицит (-)/Профицит (+)", "-20", "-25")))
    material = replace(material, metadata={})
    physical = workbook_decode({"material": material}, None, context())["physical"]
    tables = budget.extract({"physical": physical}, settings, context())["tables"]
    interpreted = budget.interpret({"tables": tables, "issue": {"issue_id": "explicit-publication"}},
        settings, context())["dataset"]
    assert interpreted.issue_id == "explicit-publication"
    assert interpreted.source_uses[0].coordinate.issue_id == "explicit-publication"
    with pytest.raises(ValueError, match="issue_context_conflict"):
        budget.interpret({"tables": replace(tables, issue_id="retained-publication"),
            "issue": {"issue_id": "different-publication"}}, settings, context())
