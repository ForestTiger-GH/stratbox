"""Prepare semantic model inputs and calculate independently of source storage."""
from dataclasses import asdict
from importlib.resources import files
from types import MappingProxyType
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import canonical_manifest_bytes, ByteIdentity
from stratbox.shared.data.representation import CSV
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.data.tables import table_identity
from stratbox.core.execution import ExecutionContext, OperationFailure, OperationResult, run
from stratbox.core.operations.source.validation import use_payload
from stratbox.core.operations.tables import record_tables
from stratbox.domains.cbr.analytics.reporting_forms.contracts import (
    BuildFormDataRequest, FormData, CalculateFormRequest, PrepareFormModelInputsRequest, FormModelInputs,
)
from stratbox.domains.cbr.analytics.reporting_forms.inputs import (
    prepare_model_inputs as admit_inputs, model_input_frames,
)
from stratbox.domains.cbr.tables.reporting_forms.layouts.registry import LAYOUT_REGISTRY
from stratbox.domains.cbr.analytics.reporting_forms.registry import MODEL_REGISTRY
from .definitions import BUILD
from .model_definitions import PREPARE, CALCULATE


def _data_metadata(form, indicator_order):
    return {"form": form, "indicator_order": dict(indicator_order)}


def _prepare(batch, invocation):
    invocation.stage("prepare_model_inputs")
    try:
        result = admit_inputs(batch)
    except (ValueError, TypeError) as error:
        raise OperationFailure(str(error)) from None
    for receipt in batch.lineage:
        invocation.use(receipt)
    invocation.use(UsedInputReceipt("integrated_form_observations", observation_snapshot(batch).identity,
        "application/vnd.stratbox.dataset+json", "inline", batch.dataset_id))
    invocation.record(ByteIdentity.of(canonical_manifest_bytes(asdict(result))))
    return result


def prepare_model_inputs(request: PrepareFormModelInputsRequest, *, context: ExecutionContext | None = None) -> OperationResult[FormModelInputs]:
    return run(PREPARE, request, lambda req, invocation: _prepare(req.batch, invocation), context=context)


def _calculate(req, invocation):
    invocation.stage("validate_selection")
    pd = require_extra("pandas", "dataframe")
    from stratbox.domains.cbr.analytics.reporting_forms.direct_form import build_direct_long
    from stratbox.domains.cbr.tables.reporting_forms.layouts.schema import DirectDatasetSpec
    from stratbox.domains.cbr.analytics.reporting_forms.formula import build_formula_long
    from stratbox.domains.cbr.analytics.reporting_forms.model import parse_form_model

    try:
        snapshots, subjects, periods = model_input_frames(req.inputs)
    except (ValueError, TypeError) as error:
        raise OperationFailure(str(error)) from None
    code = req.inputs.form
    for receipt in req.inputs.batch.lineage:
        invocation.use(receipt)
    invocation.use(UsedInputReceipt("integrated_form_observations", observation_snapshot(req.inputs.batch).identity,
        "application/vnd.stratbox.dataset+json", "inline", req.inputs.batch.dataset_id))
    invocation.use(UsedInputReceipt.for_payload(SourcePayload(canonical_manifest_bytes({
        "form": code, "layout_edition": req.inputs.layout_edition,
        "preparation_version": req.inputs.preparation_version,
    }), "application/json"), "form_model_input_rules"))
    if req.banks is None and req.selection_profile == "all_admitted":
        from stratbox.domains.cbr.tables.reporting_forms.layouts.schema import normalize_regn
        admitted = sorted({normalize_regn(value) for _, frame in snapshots for value in frame["REGN"] if normalize_regn(value)})
        banks = pd.DataFrame([(identifier, identifier, index) for index, identifier in enumerate(admitted, 1)],
                             columns=["bank", "regn", "sort"])
        invocation.use(UsedInputReceipt.for_payload(SourcePayload(canonical_manifest_bytes(
            {"selection_profile": "all_admitted", "subjects": admitted}), "application/json"), "bank_selection"))
    elif req.banks is None and req.selection_profile == "legacy":
        from stratbox.domains.cbr.analytics.reporting_forms.banks import load_legacy_banks
        bank_inputs = []
        banks = load_legacy_banks(inputs=bank_inputs)
        for receipt in bank_inputs:
            invocation.use(receipt)
        banks = banks.loc[banks["regn"].astype(str).isin(subjects)].copy()
    elif req.banks is None:
        raise OperationFailure("request.bank_selection_profile_invalid")
    else:
        selected = req.banks
        if any(item.regn not in subjects for item in selected):
            raise OperationFailure("request.bank_selection_subject_absent")
        if any(
            not item.regn.isascii()
            or not item.regn.isdecimal()
            or not item.label.strip()
            for item in selected
        ):
            raise OperationFailure("request.bank_selection_invalid")
        banks = pd.DataFrame(
            [
                (item.label, item.regn, index)
                for index, item in enumerate(selected, 1)
            ],
            columns=["bank", "regn", "sort"],
        )
        selection = SourcePayload(
            canonical_manifest_bytes(
                {
                    "banks": [(item.regn, item.label) for item in selected],
                }
            ),
            "application/json",
        )
        invocation.use(UsedInputReceipt.for_payload(selection, "bank_selection"))
    if banks.empty or not banks["regn"].is_unique or not banks["bank"].is_unique:
        raise OperationFailure("request.bank_selection_invalid")
    spec = LAYOUT_REGISTRY[code].spec
    model = req.model
    if model is None:
        name = MODEL_REGISTRY[code].resource
        data = (
            files("stratbox.domains.cbr.analytics.reporting_forms.models")
            .joinpath(name)
            .read_bytes()
        )
        model = SourcePayload(data, CSV, name)
    use_payload(model, invocation, role="form_semantic_model", limit=1_000_000)
    invocation.stage("calculate")
    invocation.budget.check("cells", len(banks) * len(snapshots))
    try:
        model_df = parse_form_model(model.data, code)
        if isinstance(spec, DirectDatasetSpec):
            long, order = build_direct_long(
                date_raw_list=snapshots,
                banks_df=banks,
                model_df=model_df,
                spec=spec,
            )
        else:
            long, order = build_formula_long(snapshots, banks, model_df, spec)
    except (ValueError, KeyError, RuntimeError):
        raise OperationFailure("source.form_semantics_invalid") from None
    # Preserve the semantic identifiers and periods beside the familiar model columns.
    date_periods = {day.strftime("%d.%m.%Y"): period for day, period in periods.items()}
    long["SourceSubjectNamespace"] = long["REGN"].map(lambda value: subjects[str(value)][0].namespace)
    long["SubjectNamespace"] = long["REGN"].map(lambda value: subjects[str(value)][1].namespace)
    long["SubjectId"] = long["REGN"].map(lambda value: subjects[str(value)][1].id)
    long["PeriodKind"] = long["Дата"].map(lambda value: date_periods[value].kind)
    long["PeriodAsOf"] = long["Дата"].map(lambda value: date_periods[value].as_of)
    long["PeriodStart"] = long["Дата"].map(lambda value: date_periods[value].start)
    long["PeriodEnd"] = long["Дата"].map(lambda value: date_periods[value].end)
    evidence = record_tables(
        invocation, (("long", long), ("banks", banks), ("model", model_df)),
        metadata=_data_metadata(code, order), parameters={"form": code, "dates": tuple(x[0] for x in snapshots)},
    )
    return FormData(code, long, banks, model_df, MappingProxyType(dict(order)),
                    tuple(invocation.used_inputs), evidence)


def calculate(request: CalculateFormRequest, *, context: ExecutionContext | None = None) -> OperationResult[FormData]:
    """Evaluate only prepared, revalidated semantic inputs."""
    return run(CALCULATE, request, _calculate, context=context)


def build_form_data(request: BuildFormDataRequest, *, context: ExecutionContext | None = None) -> OperationResult[FormData]:
    """Explicitly compose source-projection alignment, admission and calculation."""
    from stratbox.domains.cbr.integration.reporting_forms.alignment import align
    from stratbox.domains.cbr.integration.reporting_forms.contracts import AlignFormRequest
    def work(req, invocation):
        if not req.snapshots:
            raise OperationFailure("request.snapshots_empty")
        source_version = ByteIdentity.of(canonical_manifest_bytes(tuple(
            {"key": asdict(item.key), "fields": dict(item.physical_fields),
             "tables": asdict(table_identity((("dbf_rows", item.rows),)))}
            for item in req.snapshots))).sha256
        batch = align(AlignFormRequest(req.snapshots, "cbr.forms.model-source", source_version, req.periods), invocation)
        prepared = _prepare(batch, invocation)
        return _calculate(CalculateFormRequest(prepared, req.banks, req.model, req.selection_profile), invocation)
    return run(BUILD, request, work, context=context)
