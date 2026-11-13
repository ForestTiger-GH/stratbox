"""Typed operations for selection, acquisition, parsing, calculation and workbook rendering."""

from datetime import date
from importlib.resources import files

from stratbox.base.ioapi.archive_bytes import (
    ArchiveError,
    ArchiveLimits,
    ArchiveReader,
    extract_members,
)
from stratbox.base.net import HttpTransport
from stratbox.base.utils.optional_deps import require_extra
from stratbox.data import (
    AcquiredSource,
    Representation,
    SourcePayload,
    UsedInputReceipt,
    canonical_manifest_bytes,
)
from stratbox.data.representation import CSV, XLSX
from stratbox.execution import (
    ExecutionContext,
    OperationDefinition,
    OperationFailure,
    OperationResult,
    run,
)
from stratbox.execution.source_validation import source_failure, use_payload
from stratbox.macrobanks._cbr import ARCHIVE_TYPES, receive_cbr

from .contracts import (
    BuildFormDataRequest,
    FormData,
    FormKey,
    FormSnapshot,
    FormSource,
    FormViews,
    ParseFormRequest,
    SelectFormSourcesRequest,
)
from .forms.registry import FORM_REGISTRY

_ROOT = "/vfs/credit/forms/"
_LIMITS = ArchiveLimits(200, 256 * 1024 * 1024, 128 * 1024 * 1024, 64 * 1024 * 1024)
_DBF = "application/x-dbf"
SELECT = OperationDefinition(
    "cbr.forms.select_sources",
    1,
    "cbr-forms-source-selection-1",
    SelectFormSourcesRequest,
    tuple,
)
ACQUIRE = OperationDefinition(
    "cbr.forms.acquire",
    1,
    "cbr-forms-source-1",
    FormKey,
    AcquiredSource,
    frozenset({"http"}),
)
PARSE = OperationDefinition(
    "cbr.forms.parse", 1, "cbr-forms-physical-layout-1", ParseFormRequest, FormSnapshot,
    optional_capabilities=frozenset({"archive_decoder"}),
)
BUILD = OperationDefinition(
    "cbr.forms.build_data",
    1,
    "cbr-forms-model-evaluation-1",
    BuildFormDataRequest,
    FormData,
)
VIEWS = OperationDefinition(
    "cbr.forms.build_views", 1, "cbr-forms-views-1", FormData, FormViews
)
RENDER = OperationDefinition(
    "cbr.forms.render_workbook", 1, "cbr-forms-xlsx-1", FormViews, Representation
)


def _source(key: FormKey) -> FormSource:
    if (
        not isinstance(key, FormKey)
        or key.code not in FORM_REGISTRY
        or type(key.as_of) is not date
    ):
        raise OperationFailure("request.form_key_invalid")
    return FormSource(
        key, f"https://www.cbr.ru{_ROOT}{key.code}-{key.as_of:%Y%m%d}.rar"
    )


def select_sources(
    request: SelectFormSourcesRequest, *, context: ExecutionContext | None = None
) -> OperationResult[tuple[FormSource, ...]]:
    def work(req, invocation):
        invocation.stage("select_sources")
        if not req.keys or len(set(req.keys)) != len(req.keys):
            raise OperationFailure("request.form_selection_invalid")
        return tuple(_source(key) for key in req.keys)

    return run(SELECT, request, work, context=context)


def acquire(
    request: FormKey,
    *,
    transport: HttpTransport | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[AcquiredSource]:
    def work(req, invocation):
        invocation.stage("acquire")
        selected = _source(req)
        source = receive_cbr(
            selected.url,
            roots=(_ROOT,),
            media_types=ARCHIVE_TYPES,
            limit=_LIMITS.packed_bytes,
            source_id=f"cbr.form.{req.code}.{req.as_of.isoformat()}",
            transport=transport,
            invocation=invocation,
        )
        if not source.payload.data.startswith((b"Rar!", b"PK\x03\x04")):
            raise OperationFailure("source.archive_signature_invalid")
        return source

    return run(ACQUIRE, request, work, providers={"http": transport}, context=context)


def parse_form(
    request: ParseFormRequest,
    *,
    rar_reader: ArchiveReader | None = None,
    context: ExecutionContext | None = None,
) -> OperationResult[FormSnapshot]:
    def work(req, invocation):
        invocation.stage("select_dbf")
        _source(req.key)
        require_extra("pandas", "dataframe")
        require_extra("dbfread", "dbf")
        from .common.dbf_picker import decode_dbf, pick_dbf_fields
        from .common.direct_form import DirectDatasetSpec, normalize_direct_snapshot

        spec = FORM_REGISTRY[req.key.code].spec
        use_payload(
            req.payload, invocation, role="source_form", limit=_LIMITS.packed_bytes
        )
        direct = isinstance(spec, DirectDatasetSpec)
        if direct:
            required = {
                "REGN": spec.bank_fields,
                "CODE": spec.code_fields,
                **spec.measure_fields,
            }
            optional = spec.optional_measure_fields
            preferred = spec.prefer_stem_contains
        else:
            required = spec.fields
            optional = {"SIDE": spec.side_fields} if spec.side_fields else {}
            preferred = spec.preferred_stem
        if req.payload.data.startswith(b"Rar!") and invocation.context.profile == "managed":
            invocation.require_provider("archive_decoder", rar_reader)
        archived = req.payload.data.startswith((b"Rar!", b"PK"))
        try:
            members = (
                extract_members(
                    req.payload.data,
                    select=lambda names: tuple(
                        name for name in names if name.lower().endswith(".dbf")
                    ),
                    limits=_LIMITS,
                    rar_reader=rar_reader, budget=invocation.budget,
                    checkpoint=invocation.check_cancelled,
                )
                if archived
                else {"source.dbf": req.payload.data}
            )
            name, fields = pick_dbf_fields(
                members,
                field_candidates=required,
                optional_field_candidates=optional,
                prefer_stem_contains=preferred, budget=invocation.budget,
            )
            if archived:
                member = SourcePayload(members[name], _DBF, req.payload.source_id)
                invocation.use(
                    UsedInputReceipt.for_payload(
                        member,
                        "dbf_member",
                        container=req.payload.identity,
                        member=name,
                    )
                )
            invocation.stage("decode_dbf")
            frame = decode_dbf(
                members[name],
                fields,
                tuple(required) + tuple(optional),
                checkpoint=invocation.check_cancelled, budget=invocation.budget,
            )
        except (ArchiveError, OSError, ValueError) as error:
            raise source_failure(error) from None
        if frame.empty:
            raise OperationFailure("source.dbf_empty")
        if direct:
            frame = normalize_direct_snapshot(frame, spec)
        if frame.empty:
            raise OperationFailure("source.dbf_no_observations")
        return FormSnapshot(req.key, fields, frame, tuple(invocation.used_inputs))

    return run(PARSE, request, work, context=context)


def build_form_data(
    request: BuildFormDataRequest, *, context: ExecutionContext | None = None
) -> OperationResult[FormData]:
    def work(req, invocation):
        invocation.stage("validate_selection")
        pd = require_extra("pandas", "dataframe")
        from .common.direct_form import DirectDatasetSpec, build_direct_long
        from .common.formula import build_formula_long
        from .common.models import parse_form_model

        if not req.snapshots:
            raise OperationFailure("request.snapshots_empty")
        code = req.snapshots[0].key.code
        if code not in FORM_REGISTRY or any(
            snapshot.key.code != code for snapshot in req.snapshots
        ):
            raise OperationFailure("request.mixed_forms")
        if len({snapshot.key.as_of for snapshot in req.snapshots}) != len(
            req.snapshots
        ):
            raise OperationFailure("request.duplicate_release")
        for snapshot in req.snapshots:
            for receipt in snapshot.lineage:
                invocation.use(receipt)
        if req.banks is None:
            require_extra("openpyxl", "excel")
            from .common.banks import load_legacy_banks

            bank_inputs = []
            banks = load_legacy_banks(inputs=bank_inputs)
            for receipt in bank_inputs:
                invocation.use(receipt)
        else:
            selected = req.banks
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
        spec = FORM_REGISTRY[code].spec
        model = req.model
        if model is None:
            name = f"form{code}.csv"
            data = (
                files("stratbox.macrobanks.cbr_forms.models")
                .joinpath(name)
                .read_bytes()
            )
            model = SourcePayload(data, CSV, name)
        use_payload(model, invocation, role="form_semantic_model", limit=1_000_000)
        invocation.stage("calculate")
        snapshots = [
            (snapshot.key.as_of.strftime("%d.%m.%Y"), snapshot.rows)
            for snapshot in sorted(req.snapshots, key=lambda item: item.key.as_of)
        ]
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
        return FormData(
            code, long, banks, model_df, order, tuple(invocation.used_inputs)
        )

    return run(BUILD, request, work, context=context)


def build_form_views(
    request: FormData, *, context: ExecutionContext | None = None
) -> OperationResult[FormViews]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        from .common.output import build_form_sheets

        invocation.stage("build_views")
        if req.form not in FORM_REGISTRY:
            raise OperationFailure("request.form_key_invalid")
        for receipt in req.lineage:
            invocation.use(receipt)
        profile = FORM_REGISTRY[req.form].excel_profile
        sheets = build_form_sheets(
            profile=profile,
            df_long=req.long,
            df_banks=req.banks,
            model_df=req.model,
            indicator_order=req.indicator_order,
        )
        return FormViews(req.form, profile, sheets, tuple(invocation.used_inputs))

    return run(VIEWS, request, work, context=context)


def render_workbook(
    request: FormViews, *, context: ExecutionContext | None = None
) -> OperationResult[Representation]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from .common.output import render_form_workbook

        invocation.stage("render")
        for receipt in req.lineage:
            invocation.use(receipt)
        if not req.sheets:
            raise OperationFailure("request.empty_views")
        return Representation(
            f"cbr.forms.{req.profile}-xlsx",
            1,
            XLSX,
            render_form_workbook(req.sheets, profile=req.profile),
        )

    return run(RENDER, request, work, context=context)
