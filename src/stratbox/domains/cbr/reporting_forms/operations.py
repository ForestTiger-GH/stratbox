"""Typed operations for selection, acquisition, parsing, calculation and workbook rendering."""

from datetime import date
from importlib.resources import files
from types import MappingProxyType

from stratbox.core.formats.archives.members import (
    ArchiveError,
    ArchiveLimits,
    ArchiveReader,
    extract_members,
)
from stratbox.core.network import HttpTransport
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.evidence import AcquiredSource, SourcePayload, UsedInputReceipt
from stratbox.shared.data.representation import Representation
from stratbox.shared.identity import canonical_manifest_bytes
from stratbox.shared.data.representation import CSV, XLSX
from stratbox.core.execution import (
    ExecutionContext, OperationFailure, OperationResult, run,
)
from stratbox.core.operations.source.validation import source_failure, use_payload
from stratbox.core.operations.tables import record_tables, use_tables
from stratbox.domains.cbr._source import ARCHIVE_TYPES, receive_cbr

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

from .definitions import (
    ACQUIRE, BUILD, PARSE, RENDER, SELECT, VIEWS, _TABLES,
)

_ROOT = "/vfs/credit/forms/"
_LIMITS = ArchiveLimits(200, 256 * 1024 * 1024, 128 * 1024 * 1024, 64 * 1024 * 1024)
_DBF = "application/x-dbf"


def _snapshot_metadata(key, physical_fields):
    return {"form": key.code, "as_of": key.as_of, "fields": dict(physical_fields)}


def _data_metadata(form, indicator_order):
    return {"form": form, "indicator_order": dict(indicator_order)}

def _source(key: FormKey) -> FormSource:
    if (
        not isinstance(key, FormKey)
        or type(key.code) is not str or len(key.code) != 3 or not key.code.isascii() or not key.code.isdigit()
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
    """Compose all-member extraction and explicit form normalization."""
    from .contracts import ExtractFormRequest, NormalizeFormRequest
    from .flakes import extract_value, normalize_value
    from .source_operations import _failure

    def work(req, invocation):
        try:
            flakes = extract_value(ExtractFormRequest(req.key, req.payload), invocation,
                                   rar_reader=rar_reader)
            return normalize_value(NormalizeFormRequest(flakes), invocation)
        except (ArchiveError, ValueError) as error:
            raise _failure(error) from None

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
        snapshots = []
        for snapshot in sorted(req.snapshots, key=lambda item: item.key.as_of):
            frame, = use_tables(
                invocation, (("dbf_rows", snapshot.rows),), receipt=snapshot.evidence,
                role="form_snapshot", metadata=_snapshot_metadata(snapshot.key, snapshot.physical_fields),
            )
            if snapshot.evidence is not None:
                for receipt in snapshot.evidence.inputs:
                    invocation.use(receipt)
            snapshots.append((snapshot.key.as_of.strftime("%d.%m.%Y"), frame))
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
                files("stratbox.domains.cbr.reporting_forms.models")
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
        evidence = record_tables(
            invocation, (("long", long), ("banks", banks), ("model", model_df)),
            metadata=_data_metadata(code, order), parameters={"form": code, "dates": tuple(x[0] for x in snapshots)},
        )
        return FormData(code, long, banks, model_df, MappingProxyType(dict(order)),
                        tuple(invocation.used_inputs), evidence)

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
        order = dict(req.indicator_order)
        long, banks, model = use_tables(
            invocation, (("long", req.long), ("banks", req.banks), ("model", req.model)),
            receipt=req.evidence, role="form_data", metadata=_data_metadata(req.form, order),
        )
        if req.evidence is not None:
            for receipt in req.evidence.inputs:
                invocation.use(receipt)
        profile = FORM_REGISTRY[req.form].excel_profile
        if not long.empty:
            date_col = next((name for name in ("date", "Дата") if name in long), None)
            dates = long[date_col].nunique() if date_col is not None else 1
            invocation.budget.check("cells", len(order) * len(banks) * max(1, dates))
        sheets = build_form_sheets(
            profile=profile,
            df_long=long,
            df_banks=banks,
            model_df=model,
            indicator_order=order,
        )
        evidence = record_tables(invocation, tuple(sheets.items()), metadata={"form": req.form, "profile": profile})
        return FormViews(req.form, profile, MappingProxyType(dict(sheets)), tuple(invocation.used_inputs), evidence)

    return run(VIEWS, request, work, context=context)


def render_workbook(
    request: FormViews, *, style_registry=None, context: ExecutionContext | None = None
) -> OperationResult[Representation]:
    def work(req, invocation):
        require_extra("pandas", "dataframe")
        require_extra("openpyxl", "excel")
        from dataclasses import asdict
        from stratbox.core.rendering.excel.api import active_styles
        from stratbox.core.rendering.excel.registry import BUILTIN_STYLES
        from .common.output import render_form_workbook

        invocation.stage("render")
        if not req.sheets:
            raise OperationFailure("request.empty_views")
        tables = tuple(req.sheets.items())
        frames = use_tables(invocation, tables, receipt=req.evidence, role="form_views",
                            metadata={"form": req.form, "profile": req.profile})
        if req.evidence is not None:
            for receipt in req.evidence.inputs:
                invocation.use(receipt)
        sheets = dict(zip((name for name, _ in tables), frames, strict=True))
        selected = BUILTIN_STYLES if invocation.context.profile == "managed" and style_registry is None else style_registry
        registry = active_styles(selected)
        result = Representation(
            f"cbr.forms.{req.profile}-xlsx",
            1,
            XLSX,
            render_form_workbook(sheets, profile=req.profile, budget=invocation.budget, style_registry=registry),
        )
        invocation.record(result.identity, parameters={
            "profile": req.profile,
            "style": registry.default_preset_name,
            "style_spec": asdict(registry.presets[registry.default_preset_name]),
        })
        return result

    return run(RENDER, request, work, context=context)
