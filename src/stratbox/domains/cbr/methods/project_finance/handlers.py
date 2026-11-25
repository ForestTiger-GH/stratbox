"""Source discovery, history, views and workbook representation for escrow accounts."""
from dataclasses import asdict, replace
from datetime import date
from pathlib import PurePosixPath
from stratbox.core.formats.spreadsheets.workbook_bytes import openpyxl_bytes
from stratbox.core.network import HttpTransport
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.evidence import AcquiredSource
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.representation import XLSX
from stratbox.core.execution import Completion, ExecutionContext, OperationFailure, OperationResult
from stratbox.core.operations.source.validation import use_payload
from stratbox.core.execution.batch import attempt_batch, require_batch_values
from stratbox.core.operations.tables import record_tables, use_tables
from stratbox.domains.cbr.publications.access import HTML_TYPES, WORKBOOK_LIMIT, XLSX_TYPES, official_url, receive_cbr, admit_workbook, validate_workbook
from stratbox.domains.cbr.operations.project_finance.contracts import BuildEscrowViewsRequest, DiscoverEscrowRequest, EscrowHistoryBuildRequest, EscrowDataset, EscrowPivotPack, EscrowSourceLink, ParseEscrowRequest, ParsedEscrowFile
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.domains.cbr.publications.project_finance.sources import ESCROW_SOURCE_ROOTS
from stratbox.domains.cbr.operations.project_finance.definitions import ACQUIRE, DISCOVER, HISTORY, PARSE, RENDER, VIEWS, _TABLES
_ROOTS = ESCROW_SOURCE_ROOTS

def discover(request: DiscoverEscrowRequest, *, transport: HttpTransport | None=None, invocation=None) -> OperationResult[tuple[EscrowSourceLink, ...]]:

    def work(req, invocation):
        from stratbox.domains.cbr.publications.project_finance.sources import CBR_ESCROW_INDEX_URL, discover_escrow_source_links
        invocation.stage('discover')
        index = req.index
        if index is None:
            index = receive_cbr(CBR_ESCROW_INDEX_URL, roots=('/statistics/',), media_types=HTML_TYPES, limit=5000000, source_id='cbr.escrow.index', transport=transport, invocation=invocation).payload
        use_payload(index, invocation, role='source_index', limit=5000000)
        links = discover_escrow_source_links(index.data)
        if not links:
            raise OperationFailure('source.index_empty')
        return links
    return work(request, invocation)

def acquire(request: EscrowSourceLink, *, transport: HttpTransport | None=None, invocation=None) -> OperationResult[AcquiredSource]:

    def work(req, invocation):
        from stratbox.domains.cbr.publications.project_finance.sources import _source_id_from_absolute_url
        invocation.stage('acquire')
        path = official_url(req.url, roots=_ROOTS)
        if req.format not in {'xlsx', 'html'} or (req.format == 'xlsx' and (not path.casefold().endswith('.xlsx'))) or (req.format == 'html' and (not path.casefold().startswith('/analytics/finansirovanie-dolevogo-stroitelstva/'))) or (req.format == 'xlsx' and PurePosixPath(path).name != req.source_name) or (req.source_id != _source_id_from_absolute_url(req.url)):
            raise OperationFailure('request.source_identity_mismatch')
        acquired = receive_cbr(req.url, roots=_ROOTS, media_types=XLSX_TYPES if req.format == 'xlsx' else HTML_TYPES, limit=WORKBOOK_LIMIT, source_id=req.source_id, transport=transport, invocation=invocation)
        if req.format == 'xlsx':
            validate_workbook(acquired.payload.data, budget=invocation.budget)
        return acquired
    return work(request, invocation)

def _parse(req, invocation, *, decoded=None):
    require_extra('pandas', 'dataframe')
    require_extra('openpyxl', 'excel')
    from stratbox.domains.cbr.tables.project_finance.parser import extract_date_from_filename, parse_escrow_excel_bytes
    use_payload(req.payload, invocation, role='source_workbook', limit=WORKBOOK_LIMIT)
    if req.source_name.casefold().endswith(('.html', '.htm')) or req.payload.media_type == 'text/html':
        raise OperationFailure('source.escrow_layout_unsupported')
    admit_workbook(req.payload.data, invocation)
    named_date = extract_date_from_filename(req.source_name)
    try:
        day = date.fromisoformat(named_date) if named_date is not None else req.as_of
    except ValueError:
        raise OperationFailure('source.date_invalid') from None
    if type(day) is not date:
        raise OperationFailure('request.release_date_required')
    if req.as_of is not None and req.as_of != day:
        raise OperationFailure('source.date_mismatch')
    try:
        value = parse_escrow_excel_bytes(req.payload.data, source_name=req.source_name, as_of=day.isoformat(), decoded=decoded)
        from stratbox.domains.cbr.tables.project_finance.snapshots import flake_tables
        flake_tables(value)
    except ValueError:
        raise OperationFailure('source.workbook_layout_unresolved') from None
    except (KeyError, OSError):
        raise OperationFailure('source.workbook_invalid') from None
    if value.df_cells.empty:
        raise OperationFailure('source.observations_empty')
    return replace(value, source_id=req.payload.source_id)

def parse(request: ParseEscrowRequest, *, invocation=None, decoded=None) -> OperationResult[ParsedEscrowFile]:

    def work(req, invocation):
        invocation.stage('parse')
        value = _parse(req, invocation, decoded=decoded)
        from stratbox.domains.cbr.tables.project_finance.evidence import seal_flake
        return seal_flake(value, invocation)
    return work(request, invocation)

def build_history(request: EscrowHistoryBuildRequest, *, invocation=None) -> OperationResult[EscrowDataset]:
    """Explicit original-to-dataset composition using the standalone stage logic."""

    def work(req, invocation):
        require_extra('pandas', 'dataframe')
        from stratbox.domains.cbr.integration.project_finance.assembly import integrate_values
        from stratbox.domains.cbr.integration.project_finance.evidence import seal_dataset
        invocation.stage('extract')
        if not req.sources:
            raise OperationFailure('request.source_selection_empty')
        batch = attempt_batch(req.sources, lambda source: _parse(source, invocation), invocation, continue_on_error=req.continue_on_error)
        require_batch_values(batch, 'source.no_valid_workbooks')
        checkpoint = (lambda: None) if batch.stopped is not None else None
        if checkpoint is None:
            invocation.stage('integrate')
        try:
            result = integrate_values(batch.values, SnapshotCoverage('unknown', 'Selected escrow publications; publisher historical coverage is unspecified.'), selection_complete=not batch.failed and batch.stopped is None)
        except ValueError as error:
            raise OperationFailure(str(error) if str(error).startswith('escrow.') else 'escrow.integration_invalid') from None
        result = replace(result, failures=tuple(((source.payload.source_id or source.source_name, diagnostic.code) for source, diagnostic in batch.failed)), stop_reason=batch.stopped.code if batch.stopped else None)
        result = seal_dataset(result, invocation, checkpoint=checkpoint)
        if not result.selection_complete:
            return Completion(result, 'partial', batch.stopped or 'source.selection_incomplete')
        return result
    return work(request, invocation)

def build_views(request: BuildEscrowViewsRequest, *, invocation=None) -> OperationResult[EscrowPivotPack]:

    def work(req, invocation):
        require_extra('pandas', 'dataframe')
        from stratbox.domains.cbr.products.project_finance.views import prepare_dataset_view
        from stratbox.domains.cbr.products.project_finance.evidence import seal_view
        invocation.stage('build_views')
        if not isinstance(req.dataset, EscrowDataset):
            raise OperationFailure('request.integrated_dataset_required')
        try:
            value = prepare_dataset_view(req.dataset, req.view, invocation)
            return seal_view(value, invocation)
        except (TypeError, ValueError) as error:
            raise OperationFailure(str(error) if str(error).startswith('escrow.') else 'request.escrow_view_invalid') from None
    return work(request, invocation)

def render_workbook(request: EscrowPivotPack, *, invocation=None) -> OperationResult[Representation]:

    def work(req, invocation):
        require_extra('pandas', 'dataframe')
        require_extra('openpyxl', 'excel')
        from stratbox.domains.cbr.products.project_finance.workbook import build_escrow_workbook
        from stratbox.domains.cbr.products.project_finance.evidence import use_view
        invocation.stage('render')
        try:
            value = use_view(req, invocation)
        except (TypeError, ValueError) as error:
            raise OperationFailure(str(error) if str(error).startswith('escrow.') else 'request.escrow_view_invalid') from None
        workbook = build_escrow_workbook(value.pivots, list(value.indicator_specs), checkpoint=invocation.check_cancelled, row_metadata=value.row_metadata)
        try:
            return Representation('cbr.escrow.workbook', 2, XLSX, openpyxl_bytes(workbook, literal_text=True, budget=invocation.budget))
        finally:
            workbook.close()
    return work(request, invocation)


def capability_acquire(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.acquire', acquire)


def capability_build_history(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.build_history', build_history)


def capability_build_views(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.build_views', build_views)


def capability_discover(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.discover', discover)


def capability_parse(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.parse', parse)


def capability_render_workbook(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.escrow.render_workbook', render_workbook)
