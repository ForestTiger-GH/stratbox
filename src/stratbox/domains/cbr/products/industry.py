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


def prepare(rows, parameters=None):
    parameters = parameters or {}
    policy = parameters.get("geography_policy", "strict")
    if policy not in {"strict", "latest", "as_of"}:
        raise ValueError("cbr.product_geography_policy_invalid")
    edition = parameters.get("geography_date")
    if policy == "as_of":
        from datetime import date
        edition = date.fromisoformat(str(edition)).isoformat()
    include_metadata = parameters.get("include_metadata", False)
    if type(include_metadata) is not bool:
        raise ValueError("cbr.product_include_metadata_boolean_required")
    geography = {}
    for row in rows:
        key = row["subject"], row["reporting_date"]
        descriptor = (row["subject_label"], row["subject_kind"], row["subject_parent"], row["subject_order"])
        if key in geography and geography[key] != descriptor:
            raise ValueError("cbr.product_industry_geography_conflict")
        geography[key] = descriptor
    display = {}
    by_subject = defaultdict(list)
    for (subject, day), descriptor in geography.items():
        by_subject[subject].append((day, descriptor))
    for subject, descriptors in by_subject.items():
        observed = sorted(descriptors)
        if policy == "strict" and len({descriptor for _, descriptor in observed}) != 1:
            raise ValueError("cbr.product_industry_geography_conflict")
        eligible = [(day, descriptor) for day, descriptor in observed if policy != "as_of" or day <= edition]
        if not eligible:
            raise ValueError("cbr.product_geography_edition_unavailable")
        display[subject] = eligible[-1][1]
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
            subjects[subject] = display[subject]
            key = subject, row["reporting_date"]
            if key in values:
                raise ValueError("cbr.product_industry_duplicate")
            values[key] = row.get("value")
        ordered = sorted(subjects, key=lambda subject: (subjects[subject][3], subject))
        matrix = tuple((subject, *subjects[subject][:3], *(values.get((subject, day)) for day in dates)) for subject in ordered)
        sheets.append((sheet_name, measure, currency, matrix))
    return {"kind": "prepared_industry", "metric": metric, "name": name, "dates": dates,
        "flow": flow, "sheets": tuple(sheets), "periods": tuple(sorted({row["reference_period"] for row in rows})),
        "geography_policy": policy, "geography_date": edition,
        "geography_history": tuple((subject, day, *descriptor) for (subject, day), descriptor in sorted(geography.items())),
        "include_metadata": include_metadata}


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
        if value.get("include_metadata"):
            metadata = book.create_sheet("Metadata")
            metadata.append(("geography_policy", value["geography_policy"]))
            metadata.append(("geography_date", value.get("geography_date")))
            metadata.append(("subject", "reporting_date", "label", "kind", "parent", "order"))
            for row in value["geography_history"]:
                checkpoint()
                metadata.append(row)
            metadata.freeze_panes = "C4"
        return openpyxl_bytes(book, literal_text=True)
    finally:
        book.close()
