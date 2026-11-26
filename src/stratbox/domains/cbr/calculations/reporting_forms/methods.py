"""Evaluate reviewed financial models on retained, semantically admitted observations."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from importlib import import_module
from importlib.resources import files

from stratbox.shared.data.values import Assessment, DerivedDataset, SourceDataset
from stratbox.shared.identity import ByteIdentity

SUPPORTED_FORMS = frozenset({"101", "102", "123", "135", "802", "805"})


def _admit(row, settings, spec, channels):
    """Retained values require the same scientific admission as fresh source rows."""
    if row.get("form") != settings.code or row.get("value_status") not in {"reported", "blank", "dash", "missing"}:
        raise ValueError("cbr.form_model_input_unqualified")
    day = row.get("reporting_date")
    try:
        issued = date.fromisoformat(day)
    except (TypeError, ValueError):
        raise ValueError("cbr.form_model_reporting_date_required") from None
    code, measure = str(row.get("source_code", "")), str(row.get("measure", ""))
    if not code or measure not in channels:
        raise ValueError("cbr.form_model_measure_unqualified")
    expected_metric = f"cbr.forms.{settings.code}.{spec.dataset}.{code}.{measure}"
    if row.get("source_dataset") != spec.dataset or row.get("source_metric", row.get("metric")) != expected_metric:
        raise ValueError("cbr.form_model_metric_unreviewed")
    ratio = settings.code in {"135", "805"}
    if row.get("unit") != ("percent" if ratio else settings.unit) or row.get("scale") != (Decimal(1) if ratio else settings.scale):
        raise ValueError("cbr.form_model_metric_unreviewed")
    if row.get("measure_kind") != ("ratio" if ratio else "flow" if settings.code == "102" else "stock"):
        raise ValueError("cbr.form_model_quantity_invalid")
    namespace = row.get("source_subject_namespace", row.get("subject_namespace"))
    permitted = {"cbr.banking_group.registration"} if settings.code == "802" else (
        {"cbr.banking_group.registration", "cbr.bank.registration"} if settings.code == "805" else {"cbr.bank.registration"})
    if namespace not in permitted or row.get("subject_namespace") not in {namespace, "canonical"}:
        raise ValueError("cbr.form_model_subject_namespace_invalid")
    raw_subject = str(row.get("source_subject", row.get("subject", "")))
    if not raw_subject.isdecimal() or not int(raw_subject):
        raise ValueError("cbr.form_model_subject_invalid")
    perimeter = "consolidated_group" if namespace == "cbr.banking_group.registration" else "credit_institution"
    if row.get("perimeter") != perimeter:
        raise ValueError("cbr.form_model_perimeter_invalid")
    period = row.get("period")
    if settings.code == "102":
        if row.get("period_kind") != "interval" or not isinstance(period, tuple) or len(period) != 2:
            raise ValueError("cbr.form_model_flow_period_invalid")
        try:
            start, end = map(date.fromisoformat, period)
        except (TypeError, ValueError):
            raise ValueError("cbr.form_model_flow_period_invalid") from None
        if start > end or end >= issued:
            raise ValueError("cbr.form_model_flow_period_invalid")
    elif row.get("period_kind") != "as_of" or period != day:
        raise ValueError("cbr.form_model_stock_period_invalid")
    extras = dict(row.get("dimensions", ()))
    if settings.code == "101" and (not extras.get("PLAN") or not extras.get("A_P")):
        raise ValueError("cbr.form_model_account_plan_missing")
    if not row.get("evidence_ref"):
        raise ValueError("cbr.form_model_evidence_missing")
    numeric = row.get("value")
    if (row["value_status"] == "reported") != (numeric is not None):
        raise ValueError("cbr.form_model_value_status_invalid")
    if numeric is not None and (not isinstance(numeric, (Decimal, int)) or not Decimal(numeric).is_finite()):
        raise ValueError("cbr.form_model_value_invalid")
    return day, raw_subject, code, measure, extras


def calculate(inputs, settings, context):
    import pandas as pd
    from stratbox.domains.cbr.calculations.reporting_forms.model import parse_form_model
    from stratbox.domains.cbr.calculations.reporting_forms.formula import build_formula_long
    from stratbox.domains.cbr.calculations.reporting_forms.direct_form import build_direct_long
    from stratbox.domains.cbr.methods.tables.reporting_forms.layouts.schema import DirectDatasetSpec

    dataset = inputs["dataset"]
    if not isinstance(dataset, SourceDataset) or dataset.source_id != settings.series_id:
        raise ValueError("cbr.form_model_dataset_mismatch")
    if settings.code not in SUPPORTED_FORMS:
        raise ValueError("cbr.form_financial_model_requires_publisher_evidence")
    spec = import_module("stratbox.domains.cbr.methods.tables.reporting_forms.layouts.form" + settings.code).DEFAULT_SPEC
    channels = {**spec.measure_fields, **spec.optional_measure_fields} if isinstance(spec, DirectDatasetSpec) else {"VALUE": ()}
    accepted, axes = {}, {}
    for row in dataset.rows:
        context.checkpoint()
        day, subject, code, measure, extras = _admit(row, settings, spec, channels)
        key = day, subject, code, extras.get("PLAN"), extras.get("A_P")
        values = accepted.setdefault(key, {})
        if measure in values:
            raise ValueError("cbr.form_model_duplicate_variable")
        values[measure] = row.get("value")
        axis_key = day, subject
        previous = axes.setdefault(axis_key, row)
        axis_fields = ("subject", "subject_namespace", "source_subject", "source_subject_namespace", "period", "period_kind", "perimeter")
        if any(previous.get(name) != row.get(name) for name in axis_fields):
            raise ValueError("cbr.form_model_axes_conflict")
    if not accepted:
        raise ValueError("cbr.form_model_inputs_empty")
    formula_bytes = files("stratbox.domains.cbr.calculations.reporting_forms.models").joinpath("form" + settings.code + ".csv").read_bytes()
    model = parse_form_model(formula_bytes, settings.code)
    output = []
    for day in sorted({key[0] for key in accepted}):
        source = []
        for (observed, subject, code, plan, side), values in accepted.items():
            if observed != day:
                continue
            mandatory = set(spec.measure_fields) if isinstance(spec, DirectDatasetSpec) else {"VALUE"}
            if not mandatory <= values.keys():
                raise ValueError("cbr.form_model_channels_incomplete")
            source.append({"REGN": subject, "CODE": code, **values,
                **({"PLAN": plan} if plan is not None else {}), **({"SIDE": side} if side is not None else {})})
        subjects = sorted(subject for observed, subject in axes if observed == day)
        banks = pd.DataFrame([(str(axes[(day, value)].get("subject_label", value)), value, ordinal)
            for ordinal, value in enumerate(subjects, 1)], columns=["bank", "regn", "sort"])
        snapshots = [(date.fromisoformat(day).strftime("%d.%m.%Y"), pd.DataFrame(source, dtype=object))]
        if isinstance(spec, DirectDatasetSpec):
            long, order = build_direct_long(date_raw_list=snapshots, banks_df=banks, model_df=model, spec=spec)
        else:
            long, order = build_formula_long(snapshots, banks, model, spec)
        for item in long.to_dict("records"):
            original = axes[(day, str(item["REGN"]))]
            value = item["Значение"]
            missing = value is None or value == "" or value != value
            unit = item["Единица"]
            output.append({"metric": str(item["IndicatorId"]), "subject": original["subject"],
                "subject_namespace": original["subject_namespace"], "period": original["period"],
                "period_kind": original["period_kind"], "measure_kind": "ratio" if unit == "percent" else original["measure_kind"],
                "unit": "RUB" if unit == "thousand_rub" else unit,
                "scale": Decimal(1000) if unit == "thousand_rub" else Decimal(1),
                "perimeter": original["perimeter"], "value": None if missing else Decimal(str(value)),
                "value_status": "missing" if missing else "derived", "raw_token": None,
                "evidence_ref": f"cbr.form_model:{settings.code}/{day}/{item['REGN']}/{item['IndicatorId']}",
                "name": str(item["Показатель"]), "form": settings.code, "order": order.get(str(item["IndicatorId"])),
                "reporting_date": day, "source_code": str(item["Код"]), "source_dataset": spec.dataset,
                "measure": str(item["Measure"]), "section": str(item["Раздел"]), "model_unit": unit,
                "subject_label": str(item["Банк"]),
                **{name: original[name] for name in ("source_subject", "source_subject_namespace") if name in original}})
    missing = any(row["value"] is None for row in output)
    assessment = Assessment("partial" if missing else "complete", ("cbr.form_model_missing_operands",) if missing else ())
    result = DerivedDataset(settings.series_id, tuple(output), {"calculation": "financial_formulas", "form": settings.code},
        dataset.issue_id, (*dataset.lineage, dataset.identity, ByteIdentity.of(formula_bytes)), assessment,
        source_uses=dataset.source_uses)
    return {"dataset": result}
