"""Admit reviewed semantic observations as explicit financial-model variables.

The adapter validates the complete observation meaning before materializing the
model's tabular variables. It never treats arbitrary observations as DBF rows.
The immutable original batch remains the retained source of truth.
"""
from datetime import date
from decimal import Decimal
import re

from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.data.observations import MetricRef, PeriodRef, SubjectRef
from stratbox.domains.cbr.tables.reporting_forms.layouts.registry import LAYOUT_REGISTRY
from stratbox.domains.cbr.tables.reporting_forms.layouts.schema import DirectDatasetSpec
from .contracts import FormModelInputs
from .registry import MODEL_REGISTRY


def _variables(batch):
    # Exact scalar, immutable record and lineage admission is shared with storage.
    observation_snapshot(batch)
    if not batch.observations:
        raise ValueError("request.form_model_observations_empty")
    forms = {dict(item.dimensions).get("form") for item in batch.observations}
    if len(forms) != 1 or next(iter(forms)) not in MODEL_REGISTRY:
        raise ValueError("request.form_model_scope_unsupported")
    form = next(iter(forms))
    layout = LAYOUT_REGISTRY[form]
    spec = layout.spec
    direct = isinstance(spec, DirectDatasetSpec)
    channels = tuple({**spec.measure_fields, **spec.optional_measure_fields}) if direct else ("VALUE",)
    unit, scale, quantity = ("percent", Decimal(1), "ratio") if form in {"135", "805"} else (
        "RUB", Decimal(1000), "flow" if form == "102" else "stock")
    bank_fields = spec.bank_fields if direct else spec.fields["REGN"]
    namespaces = {"cbr.banking_group.registration" if field == "REGN_GKO" else "cbr.bank.registration"
                  for field in bank_fields}
    base_dimensions = {"form", "reporting_date", "source_dataset", "source_code", "measure",
                       "source_subject_namespace", "source_subject_id"}
    allowed_dimensions = base_dimensions | {"subject_mapping_edition"}
    if not direct:
        if "PLAN" in spec.fields:
            allowed_dimensions.add("plan")
        if spec.side_fields:
            allowed_dimensions.add("side")
    rows, subjects, targets, periods = {}, {}, {}, {}
    for item in batch.observations:
        dimensions = dict(item.dimensions)
        if (not base_dimensions <= dimensions.keys() or dimensions.keys() - allowed_dimensions
                or dimensions["source_dataset"] != spec.dataset):
            raise ValueError("source.form_model_axes_invalid")
        try:
            reporting_date = date.fromisoformat(dimensions["reporting_date"])
        except (TypeError, ValueError):
            raise ValueError("source.form_model_reporting_date_invalid") from None
        if reporting_date.isoformat() != dimensions["reporting_date"]:
            raise ValueError("source.form_model_reporting_date_invalid")
        if form == "102":
            if item.period.kind != "interval" or item.period.end > reporting_date:
                raise ValueError("source.form_model_flow_period_invalid")
        elif item.period != PeriodRef("as_of", reporting_date):
            raise ValueError("source.form_model_stock_period_invalid")
        if reporting_date in periods and periods[reporting_date] != item.period:
            raise ValueError("source.form_model_period_conflict")
        periods[reporting_date] = item.period
        namespace, registration = dimensions["source_subject_namespace"], dimensions["source_subject_id"]
        if namespace not in namespaces or not re.fullmatch(r"[0-9]+", registration):
            raise ValueError("source.form_model_subject_invalid")
        source = SubjectRef(namespace, registration)
        if item.subject != source and not dimensions.get("subject_mapping_edition"):
            raise ValueError("source.form_model_subject_mapping_missing")
        if registration in subjects and subjects[registration] != (source, item.subject):
            raise ValueError("source.form_model_subject_conflict")
        if item.subject in targets and targets[item.subject] != source:
            raise ValueError("source.form_model_aggregation_unreviewed")
        subjects[registration] = source, item.subject
        targets[item.subject] = source
        perimeter = "consolidated_group" if namespace == "cbr.banking_group.registration" else "credit_institution"
        if item.perimeter != perimeter:
            raise ValueError("source.form_model_perimeter_invalid")
        code, channel = dimensions["source_code"], dimensions["measure"]
        if not code.strip() or channel not in channels:
            raise ValueError("source.form_model_measure_unreviewed")
        expected = MetricRef(f"cbr.forms.{form}.{spec.dataset}.{code}.{channel}", unit, quantity, layout.edition, scale)
        if item.metric != expected:
            raise ValueError("source.form_model_metric_unreviewed")
        if (item.value_status not in {"reported", "blank", "dash", "missing"}
                or item.value is not None and type(item.value) not in {Decimal, int}):
            raise ValueError("source.form_model_value_unqualified")
        if not item.evidence_ref.startswith(f"form:{form}/{reporting_date.isoformat()}/"):
            raise ValueError("source.form_model_evidence_missing")
        plan, side = dimensions.get("plan"), dimensions.get("side")
        if not direct and "PLAN" in spec.fields and (plan is None or not plan.strip()):
            raise ValueError("source.form_model_account_plan_missing")
        key = reporting_date, registration, code, plan, side
        row = rows.setdefault(key, {})
        if channel in row:
            raise ValueError("source.form_model_variable_duplicate")
        row[channel] = item.value
    if any(set(values) != set(channels) for values in rows.values()):
        raise ValueError("source.form_model_channels_incomplete")
    return form, layout.edition, spec, channels, rows, subjects, periods


def prepare_model_inputs(batch):
    """Admit a complete set of source-variable channels for one reviewed form."""
    form, edition, *_ = _variables(batch)
    return FormModelInputs(form, edition, batch)


def model_input_frames(inputs):
    """Materialize calculation variables after revalidating their semantic contract."""
    if not isinstance(inputs, FormModelInputs) or inputs.preparation_version != "cbr.forms.model_inputs.v1":
        raise ValueError("request.form_model_inputs_invalid")
    form, edition, spec, channels, rows, subjects, periods = _variables(inputs.batch)
    if form != inputs.form or edition != inputs.layout_edition:
        raise ValueError("source.form_model_input_edition_mismatch")
    from stratbox.core.runtime.dependencies import require_extra
    pd = require_extra("pandas", "dataframe")
    columns = ["REGN", "CODE", *channels]
    if not isinstance(spec, DirectDatasetSpec):
        if "PLAN" in spec.fields:
            columns.append("PLAN")
        if spec.side_fields:
            columns.append("SIDE")
    frames = []
    for reporting_date in sorted(periods):
        records = []
        for (day, registration, code, plan, side), values in rows.items():
            if day == reporting_date:
                records.append({"REGN": registration, "CODE": code, **values, "PLAN": plan, "SIDE": side})
        frames.append((reporting_date.strftime("%d.%m.%Y"), pd.DataFrame(records, columns=columns, dtype="object")))
    return frames, subjects, periods


__all__ = ("prepare_model_inputs", "model_input_frames")
