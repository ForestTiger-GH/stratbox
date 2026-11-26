"""Prepare complete product content before formatting or storage effects."""
from collections import defaultdict
from collections.abc import Mapping
from io import BytesIO, StringIO
import csv
import json
from decimal import Decimal

from stratbox.shared.data.values import EncodedProduct, SourceDataset, View


def _form_presentation(rows):
    import pandas as pd
    from importlib.resources import files
    from stratbox.domains.cbr.calculations.reporting_forms.model import parse_form_model
    from stratbox.domains.cbr.products.reporting_forms.output import build_form_sheets
    from stratbox.domains.cbr.products.reporting_forms.settings import FORM_VIEW_SETTINGS
    codes = {str(row.get("form", "")) for row in rows}
    if len(codes) != 1 or next(iter(codes)) not in FORM_VIEW_SETTINGS:
        raise ValueError("cbr.product_form_model_required")
    form = next(iter(codes))
    required = {"reporting_date", "source_code", "name", "measure", "section", "model_unit", "subject_label"}
    if any(not required <= row.keys() or row.get("value_status") not in {"derived", "missing"} for row in rows):
        raise ValueError("cbr.product_form_model_required")
    long = pd.DataFrame([{"Дата": str(row["reporting_date"])[8:10] + "." + str(row["reporting_date"])[5:7] + "." + str(row["reporting_date"])[:4],
        "Банк": row["subject_label"], "REGN": row.get("source_subject", row["subject"]), "Форма": row["form"],
        "IndicatorId": row["metric"], "Код": row["source_code"], "Показатель": row["name"],
        "Значение": row["value"], "Measure": row["measure"], "Раздел": row["section"],
        "Единица": row["model_unit"]} for row in rows], dtype=object)
    banks = long[["Банк", "REGN"]].drop_duplicates().rename(columns={"Банк": "bank", "REGN": "regn"})
    banks["sort"] = range(1, len(banks) + 1)
    model = parse_form_model(files("stratbox.domains.cbr.calculations.reporting_forms.models").joinpath("form" + form + ".csv").read_bytes(), form)
    order = {row["metric"]: row["order"] for row in rows if row.get("order") is not None}
    layout = FORM_VIEW_SETTINGS[form]
    sheets = build_form_sheets(profile=layout, df_long=long, df_banks=banks, model_df=model, indicator_order=order)
    return {"kind": "prepared_form", "form": form, "layout": layout,
        "sheets": tuple((name, tuple(frame.columns), tuple(frame.itertuples(index=False, name=None)))
            for name, frame in sheets.items())}


def prepare(inputs, settings, context):
    dataset = inputs["dataset"]
    if not isinstance(dataset, SourceDataset):
        raise ValueError("cbr.product_dataset_required")
    subjects = frozenset(str(x) for x in context.parameters.get("subjects", ()))
    metrics = frozenset(str(x) for x in context.parameters.get("metrics", ()))
    rows = tuple(dict(row) for row in dataset.rows if (not subjects or str(row.get("subject")) in subjects)
        and (not metrics or str(row.get("metric")) in metrics))
    if not rows:
        raise ValueError("cbr.product_selection_empty")
    if settings.kind == "forms":
        return {"view": View(_form_presentation(rows), {"kind": "forms"}, (*dataset.lineage, dataset.identity), source_uses=dataset.source_uses)}
    if settings.kind == "escrow":
        if "selection_incomplete" in dataset.assessment.qualifications and context.parameters.get("require_complete_history", True):
            raise ValueError("cbr.product_history_incomplete")
        latest = max(str(row["period"]) for row in rows)
        regions = tuple(dict.fromkeys(row["subject"] for row in rows if str(row["period"]) == latest))
        selected = tuple(context.parameters.get("regions", regions))
        if not selected or len(set(selected)) != len(selected) or not set(selected) <= {row["subject"] for row in rows}:
            raise ValueError("cbr.product_region_selection_invalid")
        rows = tuple(row for row in rows if row["subject"] in selected)
    # Source and calculation content is sealed independently of product styling.
    return {"view": View(rows, {"kind": settings.kind, "sheets": tuple(
        {"metric": sheet.metric, "title": sheet.title, "name": sheet.name, "number_format": sheet.number_format}
        for sheet in settings.sheets), "region_order": selected if settings.kind == "escrow" else (),
        "missing_display": context.parameters.get("missing_display", "source_token")}, (*dataset.lineage, dataset.identity), source_uses=dataset.source_uses)}


def _csv(rows):
    stream = StringIO(newline="")
    columns = tuple(dict.fromkeys(key for row in rows for key in row))
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _pivot(rows, *, region_order=(), missing_display="source_token"):
    periods = sorted({str(row["period"]) for row in rows})
    subjects = tuple(region_order) or sorted({str(row["subject"]) for row in rows})
    cells = {}
    for row in rows:
        key = str(row["subject"]), str(row["period"])
        if key in cells:
            raise ValueError("cbr.product_pivot_duplicate")
        cells[key] = row.get("value") if row.get("value") is not None else row.get("raw_token") if missing_display == "source_token" and row.get("value_status") != "blank" else None
    return (tuple(["Subject", *periods]), *(
        tuple([subject, *(cells.get((subject, period)) for period in periods)]) for subject in subjects))


def render(inputs, settings, context):
    view = inputs["view"]
    if not isinstance(view, View):
        raise ValueError("cbr.prepared_view_required")
    fmt = context.parameters.get("format", "xlsx")
    if isinstance(view.value, Mapping) and view.value.get("kind") == "prepared_form":
        if fmt != "xlsx":
            raise ValueError("cbr.product_form_format_unsupported")
        from stratbox.domains.cbr.products.reporting_forms.output import render_form_workbook
        import pandas as pd
        sheets = {name: pd.DataFrame(rows, columns=columns, dtype=object)
            for name, columns, rows in view.value["sheets"]}
        data = render_form_workbook(sheets, profile=view.value["layout"])
        return {"product": EncodedProduct(data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", view.lineage, source_uses=view.source_uses)}
    rows = tuple(dict(row) for row in view.value)
    if fmt == "csv":
        return {"product": EncodedProduct(_csv(rows), "text/csv", view.lineage, source_uses=view.source_uses)}
    if fmt in {"json", "jsonl"}:
        data = ("\n".join(json.dumps(row, ensure_ascii=False, default=str) for row in rows) if fmt == "jsonl"
            else json.dumps(rows, ensure_ascii=False, default=str)).encode()
        return {"product": EncodedProduct(data, "application/x-ndjson" if fmt == "jsonl" else "application/json", view.lineage, source_uses=view.source_uses)}
    if fmt != "xlsx":
        raise ValueError("cbr.product_format_unsupported")
    if view.settings.get("kind") == "escrow":
        import pandas as pd
        from stratbox.domains.cbr.products.project_finance.workbook import build_escrow_workbook
        from stratbox.domains.cbr.products.specifications import Sheet
        from stratbox.core.formats.spreadsheets.workbook_bytes import openpyxl_bytes
        sheets = tuple(Sheet(**dict(item)) for item in view.settings["sheets"])
        pivots = {}
        for spec in sheets:
            selected = tuple(row for row in rows if row["metric"] == spec.metric)
            if not selected:
                continue
            content = _pivot(selected, region_order=view.settings.get("region_order", ()),
                missing_display=view.settings.get("missing_display", "source_token"))
            frame = pd.DataFrame(content[1:], columns=content[0], dtype=object).set_index("Subject")
            frame.index.name = "Регион"
            pivots[spec.metric] = frame
        sheets = tuple(spec for spec in sheets if spec.metric in pivots)
        metadata = tuple(dict.fromkeys((row["subject"], dict(row.get("dimensions", ())).get("row_kind", ""),
            dict(row.get("dimensions", ())).get("federal_district")) for row in rows))
        workbook = build_escrow_workbook(pivots, sheets, checkpoint=context.checkpoint, row_metadata=metadata)
        try:
            data = openpyxl_bytes(workbook, literal_text=True)
        finally:
            workbook.close()
        return {"product": EncodedProduct(data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", view.lineage, source_uses=view.source_uses)}
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    workbook = Workbook()
    workbook.remove(workbook.active)
    sheets = tuple(view.settings.get("sheets", ()))
    groups = defaultdict(list)
    if sheets:
        for sheet in sheets:
            selected = tuple(row for row in rows if row["metric"] == sheet["metric"])
            if selected:
                groups[(sheet["name"], sheet["title"], sheet["number_format"])].extend(selected)
    elif view.settings.get("kind") == "industries":
        order = (("debt", "rubles", "Рубли"), ("overdue_debt", "rubles", "Рубли просроч."),
            ("debt", "foreign_currency_and_precious_metals", "Валюта"),
            ("overdue_debt", "foreign_currency_and_precious_metals", "Валюта просроч."),
            ("debt", "total", "Итого"), ("overdue_debt", "total", "Итого просроч."))
        for measure, currency, name in order:
            selected = [row for row in rows if dict(row.get("dimensions", ())).get("measure") == measure
                and dict(row.get("dimensions", ())).get("currency_scope") == currency]
            if selected:
                groups[(name, name, "#,##0.##########")].extend(selected)
    else:
        for row in rows:
            name = "Office counts" if view.settings.get("kind") == "offices" else str(row.get("form") or "Statistics")
            groups[(name, name, "#,##0.##########")].append(row)
    used = set()
    for (name, title, number_format), selected in groups.items():
        context.checkpoint()
        name = "".join(c for c in name if c not in "[]:*?/\\")[:31] or "Table"
        if name.casefold() in used:
            raise ValueError("cbr.product_sheet_duplicate")
        used.add(name.casefold())
        sheet = workbook.create_sheet(name)
        sheet.cell(2, 1, title)
        content = _pivot(selected, region_order=view.settings.get("region_order", ()),
            missing_display=view.settings.get("missing_display", "source_token")) if sheets else (tuple(selected[0]), *(
            tuple(row.get(column) for column in selected[0]) for row in selected))
        for ordinal, values in enumerate(content, 4):
            for column, value in enumerate(values, 1):
                if isinstance(value, (tuple, list, dict)):
                    value = json.dumps(value, ensure_ascii=False, default=str)
                if view.settings.get("kind") in {"statistics", "offices"} and isinstance(value, Decimal):
                    value = str(value)
                cell = sheet.cell(ordinal, column, value)
                if ordinal == 4:
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill("solid", fgColor="BDD7EE")
                elif column > 1:
                    cell.number_format = number_format
        sheet.freeze_panes = "B5"
        sheet.sheet_view.showGridLines = False
    if not workbook.worksheets:
        raise ValueError("cbr.product_no_sheets")
    from stratbox.core.formats.spreadsheets.workbook_bytes import openpyxl_bytes
    try:
        data = openpyxl_bytes(workbook, literal_text=True)
    finally:
        workbook.close()
    return {"product": EncodedProduct(data,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", view.lineage, source_uses=view.source_uses)}
