"""Storage-independent acquisition inventories, source flakes and replay."""

from datetime import date
import re

from stratbox.core.execution import Completion, OperationFailure, run
from stratbox.core.formats.archives.members import ArchiveError
from stratbox.core.formats.dbf_lossless import DBFDecodeError
from stratbox.core.operations.source.validation import decode_html, source_failure, use_payload
from stratbox.domains.cbr._source import HTML_TYPES, receive_cbr
from stratbox.shared.evidence import UsedInputReceipt

from .contracts import FormData, FormInventory, FormKey, FormSnapshot, FormSource, FormViews
from .flakes import (extract_value, flakes_from_snapshot, flakes_snapshot, normalize_value)
from .snapshots import history_from_snapshot, integrate_snapshots, result_from_snapshot, result_snapshot
from .source_definitions import (DISCOVER, EXTRACT, FLAKE_SNAPSHOT, INTEGRATE, NORMALIZE,
    RESTORE_DATA, RESTORE_FLAKES, RESTORE_HISTORY, RESTORE_NORMALIZED, RESTORE_VIEWS, RESULT_SNAPSHOT)

INDEX_URL = "https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/"


def _failure(error):
    code = str(error)
    if re.fullmatch(r"(?:dbf|cbr\.forms|request|input)\.[a-z_]+", code):
        return OperationFailure(code)
    return source_failure(error)


def _snapshot_input(req, invocation):
    invocation.use(UsedInputReceipt("dataset_snapshot", req.identity,
        "application/vnd.stratbox.dataset+json", "inline", req.manifest.dataset_id))
    for receipt in req.manifest.inputs:
        invocation.use(receipt)


def discover_sources(request, *, transport=None, context=None):
    def work(req, invocation):
        if ((req.date_from is not None and type(req.date_from) is not date)
                or (req.date_to is not None and type(req.date_to) is not date)
                or req.date_from is not None and req.date_to is not None and req.date_from > req.date_to
                or req.form_codes is not None and (not req.form_codes or len(set(req.form_codes)) != len(req.form_codes)
                    or any(type(code) is not str or re.fullmatch(r"[0-9]{3}", code) is None for code in req.form_codes))):
            raise OperationFailure("request.form_selection_invalid")
        invocation.stage("discover")
        payload = req.payload
        if payload is None:
            payload = receive_cbr(INDEX_URL, roots=("/banking_sector/otchetnost-kreditnykh-organizaciy/",),
                media_types=HTML_TYPES, limit=8 * 1024 * 1024, source_id="cbr.forms.index",
                transport=transport, invocation=invocation).payload
        use_payload(payload, invocation, role="form_index", limit=8 * 1024 * 1024)
        discovered = {}
        for code, token in re.findall(r"/vfs/credit/forms/([0-9]{3})-([0-9]{8})\.rar", decode_html(payload), re.I):
            try:
                period = date(int(token[:4]), int(token[4:6]), int(token[6:]))
            except ValueError:
                raise OperationFailure("source.form_index_date_invalid") from None
            if (req.date_from and period < req.date_from or req.date_to and period > req.date_to
                    or req.form_codes is not None and code not in req.form_codes):
                continue
            key = FormKey(code, period)
            discovered[(period, code)] = FormSource(key, f"https://www.cbr.ru/vfs/credit/forms/{code}-{token}.rar")
        return FormInventory(tuple(discovered[key] for key in sorted(discovered)), payload.identity,
            tuple(invocation.used_inputs), (req.date_from.isoformat() if req.date_from else None,
                req.date_to.isoformat() if req.date_to else None, req.form_codes))
    return run(DISCOVER, request, work, providers={"http": transport}, context=context)


def extract_forms(request, *, rar_reader=None, context=None):
    def work(req, invocation):
        try:
            value = extract_value(req, invocation, rar_reader=rar_reader)
        except (DBFDecodeError, ArchiveError, ValueError) as error:
            raise _failure(error) from None
        if not value.complete:
            return Completion(value, "partial", "source.form_members_incomplete")
        return value
    return run(EXTRACT, request, work, context=context)


def normalize_form(request, *, context=None):
    def work(req, invocation):
        try:
            return normalize_value(req, invocation)
        except ValueError as error:
            raise _failure(error) from None
    return run(NORMALIZE, request, work, context=context)


def flake_snapshot(request, *, context=None):
    def work(req, invocation):
        invocation.stage("encode")
        try:
            result = flakes_snapshot(req.flakes, dataset_id=req.dataset_id, version_id=req.version_id)
        except ValueError as error:
            raise _failure(error) from None
        for item in req.flakes.lineage:
            invocation.use(item)
        invocation.record(result.identity)
        return result
    return run(FLAKE_SNAPSHOT, request, work, context=context)


def restore_flakes(request, *, context=None):
    def work(req, invocation):
        invocation.stage("decode")
        _snapshot_input(req, invocation)
        try:
            result = flakes_from_snapshot(req)
        except ValueError as error:
            raise _failure(error) from None
        return result if result.complete else Completion(result, "partial", "source.form_members_incomplete")
    return run(RESTORE_FLAKES, request, work, context=context)


def snapshot_result(request, *, context=None):
    def work(req, invocation):
        invocation.stage("encode")
        try:
            result = result_snapshot(req.value, dataset_id=req.dataset_id, version_id=req.version_id)
        except (ValueError, TypeError) as error:
            raise _failure(error) from None
        for item in req.value.lineage:
            invocation.use(item)
        invocation.record(result.identity)
        return result
    return run(RESULT_SNAPSHOT, request, work, context=context)


def _restore(request, definition, expected, context):
    def work(req, invocation):
        invocation.stage("decode")
        _snapshot_input(req, invocation)
        try:
            value = result_from_snapshot(req)
        except (ValueError, TypeError, KeyError) as error:
            raise _failure(error) from None
        if not isinstance(value, expected):
            raise OperationFailure("cbr.forms.result_type_mismatch")
        return value
    return run(definition, request, work, context=context)


def restore_normalized(request, *, context=None):
    return _restore(request, RESTORE_NORMALIZED, FormSnapshot, context)


def restore_data(request, *, context=None):
    return _restore(request, RESTORE_DATA, FormData, context)


def restore_views(request, *, context=None):
    return _restore(request, RESTORE_VIEWS, FormViews, context)


def integrate_forms(request, *, context=None):
    def work(req, invocation):
        invocation.stage("integrate")
        try:
            result = integrate_snapshots(req.snapshots, dataset_id=req.dataset_id, version_id=req.version_id)
        except (ValueError, TypeError) as error:
            raise _failure(error) from None
        for item in result.manifest.inputs:
            invocation.use(item)
        invocation.record(result.identity)
        return result
    return run(INTEGRATE, request, work, context=context)


def restore_history(request, *, context=None):
    def work(req, invocation):
        invocation.stage("decode")
        _snapshot_input(req, invocation)
        try:
            return history_from_snapshot(req)
        except (ValueError, TypeError, KeyError) as error:
            raise _failure(error) from None
    return run(RESTORE_HISTORY, request, work, context=context)
