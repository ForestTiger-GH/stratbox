"""Alignment admits qualified axes and preserves source measurements."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import Workbook
from openpyxl.styles import Alignment

from stratbox.shared.data.observations import MetricRef, PeriodRef, SubjectRef
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.source_publications import SourceAssetIdentity
from stratbox.domains.cbr.publications.contracts import IdentifiedOriginal
from stratbox.domains.cbr.tables.statistics.extraction import extract_workbook_value
from stratbox.domains.cbr.integration.statistics.alignment import align_statistics, _unit
from stratbox.domains.cbr.integration.statistics.contracts import ColumnPeriodBinding, RowBinding
from stratbox.domains.cbr.integration.statistics.snapshots import dataset_snapshot, dataset_from_snapshot


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MONETARY = "cbr.monetary_statistics.monetary_agg"
EXCHANGE = "cbr.exchange_rates.exchange_rate"
CORPORATE_FLOW = "cbr.corporate_lending.corp_new_loans_a"


def flake(series, sheets, configure=None):
    book = Workbook()
    book.remove(book.active)
    for name, rows in sheets:
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    if configure:
        configure(book)
    buffer = BytesIO()
    book.save(buffer)
    return extract_workbook_value(IdentifiedOriginal(
        SourceAssetIdentity(series, "capture-1", "main"), SourcePayload(buffer.getvalue(), XLSX, series), "xlsx"))


def observations(dataset):
    return tuple(item for batch in dataset.batches for item in batch.observations)


def test_merged_year_covers_every_month_and_missing_year_stays_diagnostic():
    value = flake(EXCHANGE, [("Ежемесячные", [
        ["Monthly source, млн руб."], [None, 2024, None, None, None],
        [None, "Янв", "Фев", "Мар", "Апр"], ["Measure", 10, 20, 30, 40],
    ])], lambda book: book.active.merge_cells("B2:D2"))
    data = align_statistics((value,))
    items = observations(data)
    assert [item.value for item in items] == [10, 20, 30]
    assert [item.period.end for item in items] == [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31)]
    assert {item.code for item in data.diagnostics} == {"cbr.statistics.period_column_unresolved"}
    with pytest.raises(ValueError, match="unresolved_semantics"):
        align_statistics((value,), strict=True)
    repaired = align_statistics((value,), period_bindings=(ColumnPeriodBinding(
        EXCHANGE, "Ежемесячные", 5, PeriodRef("interval", start=date(2024, 4, 1), end=date(2024, 4, 30))),))
    assert [item.value for item in observations(repaired)] == [10, 20, 30, 40]
    assert not repaired.diagnostics


def test_russian_month_year_headers_are_intervals_and_exact_tokens_survive():
    value = flake(CORPORATE_FLOW, [("итого", [
        ["Объем предоставленных кредитов, млн руб."], ["Activity", "Январь2019", "Фев-2019"],
        ["Activity A", "12345678901234567890,123450", "—"],
    ])])
    data = align_statistics((value,), strict=True)
    first, second = observations(data)
    assert first.period == PeriodRef("interval", start=date(2019, 1, 1), end=date(2019, 1, 31))
    assert second.period.end == date(2019, 2, 28)
    assert first.value == Decimal("12345678901234567890.123450")
    assert first.raw_token == "12345678901234567890,123450"
    assert first.metric.unit == "RUB" and first.metric.scale == Decimal(1_000_000)
    assert second.value_status == "dash"
    assert dataset_from_snapshot(dataset_snapshot(data)) == data


def test_ambiguous_header_units_never_select_an_arbitrary_currency_or_ratio():
    value = flake(MONETARY, [("Денежные агрегаты", [
        ["Measures: млн руб.; млрд долларов США; %", date(2026, 1, 1)],
        ["Explicit monetary amount, млн руб.", 20], ["Unspecified measure", 30],
    ])])
    data = align_statistics((value,))
    explicit, unspecified = observations(data)
    assert explicit.metric.unit == "RUB" and explicit.metric.scale == Decimal(1_000_000)
    assert unspecified.metric.unit == "source_unspecified" and unspecified.metric.scale is None
    assert [item.code for item in data.diagnostics] == ["cbr.statistics.unit_ambiguous"]
    assert [item.value for item in observations(data)] == [20, 30]


def test_rate_words_and_denomination_labels_do_not_override_measurement_units():
    value = flake("cbr.corporate_lending.structure_by_benchmark_interest_rate_type", [("Данные", [
        ["Структура задолженности по виду процентной ставки, млн руб.", date(2026, 1, 1)],
        ["Задолженность с плавающей процентной ставкой", 100], ["в рублях", 80],
    ])], lambda book: setattr(book.active["A3"], "alignment", Alignment(indent=1)))
    data = align_statistics((value,), strict=True)
    assert {(item.metric.unit, item.metric.scale, item.metric.quantity_kind) for item in observations(data)} == {
        ("RUB", Decimal(1_000_000), "stock")}
    assert _unit("сред. значение") is None
    assert _unit("начисленные проценты") is None
    assert _unit("в рублях") is None


def test_source_subject_identity_is_scoped_to_series_and_sheet():
    rows = [["Amount, млн руб.", date(2026, 1, 1)], ["Total", 10]]
    first = flake("cbr.funding.funds_all", [("итого", rows), ("в рублях", rows)])
    second = flake("cbr.funding.budget_all", [("итого", rows)])
    data = align_statistics((first, second), strict=True)
    assert len({item.subject for item in observations(data)}) == 3
    assert all(item.subject.namespace == "cbr.source_row" for item in observations(data))


def test_period_qualification_does_not_leak_into_an_explicit_interval():
    value = flake(CORPORATE_FLOW, [("итого", [
        ["Объем предоставленных кредитов, млн руб.", date(2026, 1, 1), date(2026, 2, 1)],
        ["Activity A", 10, 20],
    ])])
    data = align_statistics((value,), period_bindings=(ColumnPeriodBinding(
        CORPORATE_FLOW, "итого", 3, PeriodRef("interval", start=date(2026, 1, 1), end=date(2026, 1, 31))),))
    first, second = observations(data)
    assert dict(first.dimensions)["period_qualification"] == "reported_date_interval_unresolved"
    assert "period_qualification" not in dict(second.dimensions)
    assert second.period.kind == "interval"


def test_semantic_binding_cannot_relabel_millions_as_unscaled_values():
    value = flake(MONETARY, [("Денежные агрегаты", [
        ["Amount, млн руб.", date(2026, 1, 1)], ["Total", "120,00"],
    ])])
    wrong = RowBinding(MONETARY, "Денежные агрегаты", 2,
                       MetricRef("canonical.total", "RUB", "stock", scale=Decimal(1)), SubjectRef("canonical", "total"))
    with pytest.raises(ValueError, match="binding_measurement_mismatch"):
        align_statistics((value,), row_bindings=(wrong,))
    correct = replace(wrong, metric=replace(wrong.metric, scale=Decimal(1_000_000)))
    item = observations(align_statistics((value,), row_bindings=(correct,), strict=True))[0]
    assert item.value == Decimal("120.00") and item.raw_token == "120,00"
    assert item.metric.scale == Decimal(1_000_000)
    assert item.subject == SubjectRef("canonical", "total")


def test_embedded_sections_keep_independent_stock_and_month_axes():
    series = "cbr.corporate_lending.sme_borrowers_info"
    value = flake(series, [("Данные", [
        ["Количество заемщиков с задолженностью, ед."], [], [None, "01.02.2019", "01.03.2019"],
        ["Micro", 10, 11], [], ["Количество заемщиков, получивших кредит за отчетный месяц, ед."],
        [None, "Январь 2019", "Февраль 2019"], ["Micro", 2, 3],
    ])])
    data = align_statistics((value,), strict=True)
    items = observations(data)
    assert len(items) == 4
    assert [item.period.kind for item in items] == ["as_of", "as_of", "interval", "interval"]
    assert items[0].period.as_of == date(2019, 2, 1)
    assert items[2].period.start == date(2019, 1, 1)
    assert items[0].metric.id != items[2].metric.id
    assert all(item.metric.unit == "count" for item in items)
    with pytest.raises(ValueError, match="period_binding_scope_ambiguous"):
        align_statistics((value,), period_bindings=(ColumnPeriodBinding(
            series, "Данные", 2, PeriodRef("as_of", as_of=date(2019, 2, 1))),))


def test_explicit_bindings_resolve_only_the_axes_they_cover():
    value = flake(MONETARY, [("Денежные агрегаты", [
        ["Amount, млн руб."], [None, date(2026, 1, 1), date(2026, 2, 1)],
        [None, date(2025, 12, 31), date(2026, 1, 31)], ["Total", 10, 20],
    ])])
    with pytest.raises(ValueError, match="period_axis_ambiguous"):
        align_statistics((value,))
    bindings = tuple(ColumnPeriodBinding(MONETARY, "Денежные агрегаты", column,
        PeriodRef("as_of", as_of=day)) for column, day in ((2, date(2026, 1, 1)), (3, date(2026, 2, 1))))
    with pytest.raises(ValueError, match="period_axis_ambiguous"):
        align_statistics((value,), period_bindings=bindings[:1])
    assert [item.value for item in observations(align_statistics((value,), period_bindings=bindings, strict=True))] == [10, 20]


def test_qualified_all_blank_metric_rows_remain_distinct_from_footnotes():
    def configure(book):
        for row in (3, 4):
            for column in (2, 3):
                book.active.cell(row, column).number_format = "0.00"
    value = flake(MONETARY, [("Денежные агрегаты", [
        ["Amount, млн руб.", date(2026, 1, 1), date(2026, 2, 1)],
        ["Reported", 10, 20], ["Unavailable measure"], ["1) Source methodology"],
    ])], configure)
    items = observations(align_statistics((value,), strict=True))
    assert len(items) == 4
    assert [item.value_status for item in items] == ["reported", "reported", "blank", "blank"]
    assert all("methodology" not in dict(item.dimensions)["source_hierarchy"] for item in items)


def test_overlapping_external_debt_editions_are_separate_source_measures():
    rows = [["Amount, млн долларов США", date(2021, 1, 1)], ["Всего", 100]]
    value = flake("cbr.external_debt.debt_maturity", [("2014-2022", rows), ("2021-2026", rows)])
    items = observations(align_statistics((value,), strict=True))
    assert len(items) == 2 and items[0].period == items[1].period
    assert items[0].metric.id != items[1].metric.id
    assert items[0].subject != items[1].subject
    assert {dict(item.dimensions)["source_sheet"] for item in items} == {"2014-2022", "2021-2026"}


def test_reported_transactions_and_growth_keep_their_source_measure_basis():
    value = flake("cbr.monetary_statistics.survey_cb", [
        ("Операции", [["Операции, млн руб.", date(2026, 1, 1)], ["Задолженность", 10]]),
        ("ММ_%", [["Темпы прироста, %", date(2026, 1, 1)], ["Задолженность", 2]]),
    ])
    flow, growth = observations(align_statistics((value,), strict=True))
    assert flow.metric.quantity_kind == "flow"
    assert growth.metric.quantity_kind == "ratio"
    assert dict(flow.dimensions)["measure_basis"] == "reported_transactions"
    assert dict(growth.dimensions)["measure_basis"] == "reported_growth_mom"
    assert flow.metric.id != growth.metric.id


def test_exchange_sections_preserve_quote_units_and_cumulative_growth_periods():
    def configure(book):
        for row in (4, 6, 8):
            book.active.merge_cells(start_row=row, start_column=2, end_row=row, end_column=3)
    value = flake(EXCHANGE, [("Ежемесячные", [
        ["Exchange indicators"], [None, 2024, 2024], [None, "Янв", "Фев"],
        [None, "Номинальные курсы (рублей за единицу иностранной валюты)"],
        ["Номинальный курс доллара США на конец периода", "90,00", "91,00"],
        [None, "Индексы (в % прироста к предыдущему периоду)"],
        ["Индекс номинального курса рубля", 1, 2],
        [None, "Индексы (в % прироста к соответствующему периоду предыдущего года)"],
        [None, 2024, 2024], [None, "Янв", "Янв - Фев"],
        ["Индекс номинального курса рубля", 3, 4],
    ])], configure)
    items = observations(align_statistics((value,), strict=True))
    assert len(items) == 6
    assert items[0].metric.unit == "RUB_per_USD" and items[0].period.as_of == date(2024, 1, 31)
    assert items[2].metric.unit == "percent" and items[2].metric.quantity_kind == "index"
    assert dict(items[2].dimensions)["measure_basis"] == "reported_growth_period"
    assert items[-1].period == PeriodRef("interval", start=date(2024, 1, 1), end=date(2024, 2, 29))
    assert dict(items[-1].dimensions)["measure_basis"] == "reported_growth_comparable_year_period"
    assert items[2].metric.id != items[-1].metric.id


def test_annotated_period_and_value_tokens_retain_their_source_qualification():
    def configure(book):
        for column in (2, 4):
            book.active.cell(1, column).number_format = "mmm-yy"
    value = flake("cbr.monetary_statistics.survey_cb", [("Операции", [
        ["Операции, млн руб.", date(2025, 11, 1), "дек.25**", date(2026, 1, 1)],
        ["Total", "27,4", "28,5**", "29,0"],
    ])], configure)
    items = observations(align_statistics((value,), strict=True))
    assert all(item.period.kind == "interval" for item in items)
    assert items[1].period == PeriodRef("interval", start=date(2025, 12, 1), end=date(2025, 12, 31))
    assert items[1].value == Decimal("28.5") and items[1].raw_token == "28,5**"
    assert dict(items[1].dimensions)["source_period_label"] == "дек.25**"
    assert dict(items[1].dimensions)["source_value_qualification"] == "annotated"
    as_of = flake(MONETARY, [("Денежные агрегаты", [
        ["Amount, млрд руб.", "01.04.2026**"], ["Total", 10],
    ])])
    assert observations(align_statistics((as_of,), strict=True))[0].period == PeriodRef("as_of", as_of=date(2026, 4, 1))


def test_declared_table_unit_anchor_applies_without_filling_missing_source_labels():
    value = flake("cbr.monetary_statistics.balance_odc", [("Кредиты", [
        [None, date(2026, 1, 1)], ["Кредиты и займы, млн рублей", 100],
        ["Кредиты нефинансовым организациям", 80],
    ])])
    items = observations(align_statistics((value,), strict=True))
    assert {(item.metric.unit, item.metric.scale) for item in items} == {("RUB", Decimal(1_000_000))}
    missing = flake("cbr.monetary_statistics.balance_odc", [("Кредиты", [
        [None, date(2026, 1, 1)], ["Кредиты и займы", 100],
    ])])
    data = align_statistics((missing,))
    assert observations(data)[0].metric.unit == "source_unspecified"
    assert {item.code for item in data.diagnostics} == {"cbr.statistics.unit_anchor_unresolved", "cbr.statistics.unit_unresolved"}


def test_numeric_cells_next_to_a_source_note_do_not_become_an_economic_measure():
    value = flake("cbr.external_debt.debt_maturity", [("2014-2022", [
        ["Amount, млн долларов США", date(2021, 1, 1)], ["Total", 100],
        ["Дата последнего обновления: 29 марта 2024 года.", 0], ["Other debt", 20],
    ])])
    data = align_statistics((value,))
    assert [item.value for item in observations(data)] == [100, 20]
    assert [item.code for item in data.diagnostics] == ["cbr.statistics.source_note_contains_values"]
    assert value.sheets[0].cell(3, 2).value == 0


def test_conflicting_source_unit_is_retained_without_inventing_a_correction():
    value = flake("cbr.household_lending.mortgage_ihc", [("итого", [
        ["Ипотечные жилищные кредиты", "01.02.2024"],
        ["Объем кредитов на создание объектов ИЖС за месяц, млн руб.", 100],
        ["  на приобретение объектов ИЖС за месяц, единиц", 20],
    ])])
    data = align_statistics((value,))
    item = observations(data)[1]
    assert item.value == 20 and item.metric.unit == "source_conflicting" and item.metric.scale is None
    assert [item.code for item in data.diagnostics] == ["cbr.statistics.source_unit_conflict"]


def test_merged_label_section_with_styled_blanks_does_not_invent_a_metric():
    def configure(book):
        book.active.merge_cells("A2:B2")
        book.active["C2"].number_format = "0.00"
    value = flake("cbr.banking_sector_structure.obs_table_20s", [("Активы - всего", [
        [None, "Amount, млрд руб.", date(2026, 1, 1)],
        ["Assets total"], ["1", "Cash", 100],
    ])], configure)
    items = observations(align_statistics((value,), strict=True))
    assert len(items) == 1 and items[0].value == 100
    assert dict(items[0].dimensions)["source_section"] == "Assets total"
