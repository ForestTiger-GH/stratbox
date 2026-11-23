"""Select reviewed form archive routes and acquire exact publisher bytes."""
from stratbox.core.network import HttpTransport
from stratbox.core.execution import ExecutionContext, OperationFailure, OperationResult, run
from stratbox.shared.evidence import AcquiredSource
from stratbox.domains.cbr.publications.access import ARCHIVE_TYPES, receive_cbr
from stratbox.domains.cbr.publications.profiles import archive_url
from stratbox.domains.cbr.tables.reporting_forms.contracts import FormKey, FormSource, SelectFormSourcesRequest
from stratbox.domains.cbr.tables.reporting_forms.flakes import LIMITS, validate_key
from .definitions import ACQUIRE, SELECT


def _source(key: FormKey) -> FormSource:
    try:
        validate_key(key)
    except ValueError as error:
        raise OperationFailure(str(error)) from None
    return FormSource(
        key, archive_url(key.code, key.as_of)
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
            roots=("/vfs/credit/forms/",),
            media_types=ARCHIVE_TYPES,
            limit=LIMITS.packed_bytes,
            source_id=f"cbr.form.{req.code}.{req.as_of.isoformat()}",
            transport=transport,
            invocation=invocation,
        )
        if not source.payload.data.startswith((b"Rar!", b"PK\x03\x04")):
            raise OperationFailure("source.archive_signature_invalid")
        return source

    return run(ACQUIRE, request, work, providers={"http": transport}, context=context)
