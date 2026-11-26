"""Prepare complete region-by-date sheets before publication-style formatting."""
from collections import defaultdict
from types import SimpleNamespace

from stratbox.core.formats.spreadsheets.workbook_bytes import openpyxl_bytes

_ORDER = (("debt", "rubles", "в рублях"), ("overdue_debt", "rubles", "в т.ч. просроч. в рублях"),
    ("debt", "foreign_currency_and_precious_metals", "в инвалюте"),
    ("overdue_debt", "foreign_currency_and_precious_metals", "в т.ч. просроч. в инвалюте"),
    ("debt", "total", "итого"), ("overdue_debt", "total", "в т.ч. просроч. итого"),
    ("new_loans", "rubles", "в рублях"), ("new_loans", "foreign_currency_and_precious_metals", "в инвалюте"),
    ("new_loans", "total", "итого"))


def prepare(rows):
    metrics = {row["metric"] for row in rows}
    if len(metrics) != 1:
        raise ValueError("cbr.product_single_industry_required")
    metric = next(iter(metrics))
    dates = tuple(sorted({row["reporting_date"] for row in rows}))
    labels = {row["metric_label"] for row in rows}
    if len(labels) != 1:
        raise ValueError("cbr.product_industry_label_conflict")
    name = next(iter(labels))
    groups = defaultdict(list)
    for row in rows:
        dimensions = dict(row["dimensions"])
        groups[(dimensions["measure"], dimensions["currency_scope"])].append(row)
    measures = {key[0] for key in groups}
    flow = measures == {"new_loans"}
    expected = {(measure, currency) for measure, currency, _ in _ORDER
        if (measure == "new_loans") == flow}
    if set(groups) != expected:
        raise ValueError("cbr.product_industry_sheet_set_incomplete")
    sheets = []
    for measure, currency, sheet_name in _ORDER:
        if (measure, currency) not in groups:
            continue
        selected = groups[(measure, currency)]
        subjects = {}
        values = {}
        for row in selected:
            subject = row["subject"]
            descriptor = (row["subject_label"], row["subject_kind"], row["subject_parent"], row["subject_order"])
            if subject in subjects and subjects[subject] != descriptor:
                raise ValueError("cbr.product_industry_geography_conflict")
            subjects[subject] = descriptor
            key = subject, row["reporting_date"]
            if key in values:
                raise ValueError("cbr.product_industry_duplicate")
            values[key] = row.get("value")
        ordered = sorted(subjects, key=lambda subject: (subjects[subject][3], subject))
        matrix = tuple((subject, *subjects[subject][:3], *(values.get((subject, day)) for day in dates)) for subject in ordered)
        sheets.append((sheet_name, measure, currency, matrix))
    return {"kind": "prepared_industry", "metric": metric, "name": name, "dates": dates,
        "flow": flow, "sheets": tuple(sheets), "periods": tuple(sorted({row["reference_period"] for row in rows}))}


def render(value, checkpoint):
    import pandas as pd
    from openpyxl import Workbook
    from stratbox.domains.cbr.products.corporate_lending.industry.rendering import _write_cbr_industry_sheet
    book = Workbook()
    book.remove(book.active)
    dates = value["dates"]
    try:
        for sheet, measure, currency, rows in value["sheets"]:
            checkpoint()
            frame = pd.DataFrame(rows, columns=("region_code", "region_name", "region_kind", "federal_district_name", *dates), dtype=object)
            label = "Объем кредитов" if value["flow"] else "Просроченная задолженность" if measure == "overdue_debt" else "Задолженность"
            denomination = {"rubles": "в рублях", "foreign_currency_and_precious_metals": "в иностранной валюте и драгоценных металлах", "total": "всего"}[currency]
            subtitle = ("Выдачи за отчетные месяцы " + value["periods"][0] + " — " + value["periods"][-1]
                if value["flow"] else "Динамика по состоянию на отчетные даты с " + dates[0][8:] + "." + dates[0][5:7] + "." + dates[0][:4] + " по " + dates[-1][8:] + "." + dates[-1][5:7] + "." + dates[-1][:4])
            _write_cbr_industry_sheet(book, table=SimpleNamespace(df_table=frame, data_columns=len(dates)), sheet_name=sheet,
                title=f"{label}, {value['name']}, {denomination}, в региональном разрезе, млн руб.", subtitle=subtitle, dates=dates)
            if value["flow"]:
                for ordinal, period in enumerate(value["periods"], 2):
                    book[sheet].cell(3, ordinal, period[5:7] + "." + period[:4])
        return openpyxl_bytes(book, literal_text=True)
    finally:
        book.close()
