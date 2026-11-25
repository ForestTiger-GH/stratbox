"""Storage-independent acquisition inventories, source flakes and replay."""
from datetime import date
import re
from stratbox.core.execution import Completion, OperationFailure
from stratbox.core.formats.archives.members import ArchiveError
from stratbox.core.formats.dbf_lossless import DBFDecodeError
from stratbox.core.operations.source.validation import decode_html, source_failure, use_payload
from stratbox.domains.cbr.publications.access import HTML_TYPES, receive_cbr
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.domains.cbr.analytics.reporting_forms.contracts import FormData
from stratbox.domains.cbr.tables.reporting_forms.contracts import FormInventory, FormKey, FormSnapshot, FormSource
from stratbox.domains.cbr.products.reporting_forms.contracts import FormViews
from stratbox.domains.cbr.tables.reporting_forms.flakes import extract_value, flakes_from_snapshot, flakes_snapshot
from stratbox.domains.cbr.tables.reporting_forms.projection import normalize_value
from stratbox.domains.cbr.operations.reporting_forms.codecs import history_from_snapshot, source_history_snapshot, result_from_snapshot, result_snapshot
from stratbox.domains.cbr.operations.reporting_forms.definitions import PARSE
from stratbox.domains.cbr.tables.reporting_forms.contracts import ParseFormRequest
from stratbox.core.execution import ExecutionContext, OperationResult
from stratbox.core.formats.archives.members import ArchiveReader
from stratbox.domains.cbr.operations.reporting_forms.source_definitions import DISCOVER, EXTRACT, FLAKE_SNAPSHOT, HISTORY, NORMALIZE, RESTORE_DATA, RESTORE_FLAKES, RESTORE_HISTORY, RESTORE_NORMALIZED, RESTORE_VIEWS, RESULT_SNAPSHOT
from stratbox.domains.cbr.publications.profiles import archive_url, reporting_form_index
from stratbox.domains.cbr.publications.catalog import FORM_CODES
from urllib.parse import urljoin
INDEX_URL = reporting_form_index('101')

def _failure(error):
    code = str(error)
    if re.fullmatch('(?:dbf|cbr\\.forms|request|input|source)\\.[a-z_]+', code):
        return OperationFailure(code)
    return source_failure(error)

def _snapshot_input(req, invocation):
    invocation.use(UsedInputReceipt('dataset_snapshot', req.identity, 'application/vnd.stratbox.dataset+json', 'inline', req.manifest.dataset_id))
    for receipt in req.manifest.inputs:
        invocation.use(receipt)

def discover_sources(request, *, transport=None, invocation=None):

    def work(req, invocation):
        if req.date_from is not None and type(req.date_from) is not date or (req.date_to is not None and type(req.date_to) is not date) or (req.date_from is not None and req.date_to is not None and (req.date_from > req.date_to)) or (req.form_codes is not None and (not req.form_codes or len(set(req.form_codes)) != len(req.form_codes) or any((type(code) is not str or re.fullmatch('[0-9]{3}', code) is None for code in req.form_codes)))):
            raise OperationFailure('request.form_selection_invalid')
        invocation.stage('discover')
        payload = req.payload
        if payload is None:
            payload = receive_cbr(INDEX_URL, roots=('/banking_sector/otchetnost-kreditnykh-organizaciy/',), media_types=HTML_TYPES, limit=8 * 1024 * 1024, source_id='cbr.forms.index', transport=transport, invocation=invocation).payload
        use_payload(payload, invocation, role='form_index', limit=8 * 1024 * 1024)
        discovered = {}
        unsupported = {}
        for code, token in re.findall('/vfs/credit/forms/([0-9]{3})-([0-9]{8})\\.rar', decode_html(payload), re.I):
            try:
                period = date(int(token[:4]), int(token[4:6]), int(token[6:]))
            except ValueError:
                raise OperationFailure('source.form_index_date_invalid') from None
            if req.date_from and period < req.date_from or (req.date_to and period > req.date_to) or (req.form_codes is not None and code not in req.form_codes):
                continue
            key = FormKey(code, period)
            if code not in FORM_CODES:
                unsupported[period, code] = (FormSource(key, urljoin(INDEX_URL, f'/vfs/credit/forms/{code}-{token}.rar')), 'source.form_profile_unsupported')
                continue
            discovered[period, code] = FormSource(key, archive_url(code, period))
        return FormInventory(tuple((discovered[key] for key in sorted(discovered))), payload.identity, tuple(invocation.used_inputs), (req.date_from.isoformat() if req.date_from else None, req.date_to.isoformat() if req.date_to else None, req.form_codes), tuple((unsupported[key] for key in sorted(unsupported))))
    return work(request, invocation)

def extract_forms(request, *, rar_reader=None, invocation=None):

    def work(req, invocation):
        try:
            value = extract_value(req, invocation, rar_reader=rar_reader)
        except (DBFDecodeError, ArchiveError, ValueError) as error:
            raise _failure(error) from None
        if not value.complete:
            return Completion(value, 'partial', 'source.form_members_incomplete')
        return value
    return work(request, invocation)

def normalize_form(request, *, invocation=None):

    def work(req, invocation):
        try:
            return normalize_value(req, invocation)
        except ValueError as error:
            raise _failure(error) from None
    return work(request, invocation)

def flake_snapshot(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('encode')
        try:
            result = flakes_snapshot(req.flakes, dataset_id=req.dataset_id, version_id=req.version_id)
        except ValueError as error:
            raise _failure(error) from None
        for item in req.flakes.lineage:
            invocation.use(item)
        invocation.record(result.identity)
        return result
    return work(request, invocation)

def restore_flakes(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('decode')
        _snapshot_input(req, invocation)
        try:
            result = flakes_from_snapshot(req)
        except ValueError as error:
            raise _failure(error) from None
        return result if result.complete else Completion(result, 'partial', 'source.form_members_incomplete')
    return work(request, invocation)

def snapshot_result(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('encode')
        try:
            result = result_snapshot(req.value, dataset_id=req.dataset_id, version_id=req.version_id)
        except (ValueError, TypeError) as error:
            raise _failure(error) from None
        for item in req.value.lineage:
            invocation.use(item)
        invocation.record(result.identity)
        return result
    return work(request, invocation)

def _restore(request, definition, expected, invocation):

    def work(req, invocation):
        invocation.stage('decode')
        _snapshot_input(req, invocation)
        try:
            value = result_from_snapshot(req)
        except (ValueError, TypeError, KeyError) as error:
            raise _failure(error) from None
        if not isinstance(value, expected):
            raise OperationFailure('cbr.forms.result_type_mismatch')
        return value
    return work(request, invocation)

def restore_normalized(request, *, invocation=None):
    return _restore(request, RESTORE_NORMALIZED, FormSnapshot, invocation)

def restore_data(request, *, invocation=None):
    return _restore(request, RESTORE_DATA, FormData, invocation)

def restore_views(request, *, invocation=None):
    return _restore(request, RESTORE_VIEWS, FormViews, invocation)

def build_source_history(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('source_history')
        try:
            result = source_history_snapshot(req.snapshots, dataset_id=req.dataset_id, version_id=req.version_id)
        except (ValueError, TypeError) as error:
            raise _failure(error) from None
        for item in result.manifest.inputs:
            invocation.use(item)
        invocation.record(result.identity)
        return result
    return work(request, invocation)

def restore_history(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('decode')
        _snapshot_input(req, invocation)
        try:
            return history_from_snapshot(req)
        except (ValueError, TypeError, KeyError) as error:
            raise _failure(error) from None
    return work(request, invocation)

def parse_form(request: ParseFormRequest, *, rar_reader: ArchiveReader | None=None, invocation=None) -> OperationResult[FormSnapshot]:
    """Compose all-member extraction and explicit form normalization."""
    from stratbox.domains.cbr.tables.reporting_forms.contracts import ExtractFormRequest, NormalizeFormRequest
    from stratbox.domains.cbr.tables.reporting_forms.flakes import extract_value
    from stratbox.domains.cbr.tables.reporting_forms.projection import normalize_value
    from stratbox.domains.cbr.methods.reporting_forms.extracts import _failure

    def work(req, invocation):
        try:
            flakes = extract_value(ExtractFormRequest(req.key, req.payload), invocation, rar_reader=rar_reader)
            return normalize_value(NormalizeFormRequest(flakes), invocation)
        except (ArchiveError, ValueError) as error:
            raise _failure(error) from None
    return work(request, invocation)


def capability_build_source_history(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.build_history', build_source_history)


def capability_discover_sources(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.discover_sources', discover_sources)


def capability_extract_forms(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.extract', extract_forms)


def capability_flake_snapshot(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.flake_snapshot', flake_snapshot)


def capability_normalize_form(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.normalize', normalize_form)


def capability_parse_form(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.parse', parse_form)


def capability_restore_data(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.restore_data', restore_data)


def capability_restore_flakes(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.restore_flakes', restore_flakes)


def capability_restore_history(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.restore_history', restore_history)


def capability_restore_normalized(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.restore_normalized', restore_normalized)


def capability_restore_views(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.restore_views', restore_views)


def capability_snapshot_result(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.result_snapshot', snapshot_result)
