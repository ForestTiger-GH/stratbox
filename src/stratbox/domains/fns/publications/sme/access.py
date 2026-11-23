"""SME official POST acquisition and index discovery; no table projection."""
from datetime import date
from stratbox.core.network import HttpRequest, HttpsEndpoint, RetryPolicy
from stratbox.core.execution import OperationFailure
from stratbox.core.operations.source.acquisition import receive_source
from stratbox.core.operations.source.validation import source_failure, use_payload
from .source import FnsError, LIMIT_HTML, LIMIT_JSON, discover_dates, format_source_date

DATASET = "fns.sme"
_HOST = "rmsp.nalog.ru"
_PAGE = HttpsEndpoint(_HOST, "/statistics.html")
_API = HttpsEndpoint(_HOST, "/statistics-proc.json")


def discover_dates_from_source(index, invocation, transport):
    payload = index
    if payload is None:
        invocation.stage("acquire_index")
        payload = receive_source(
            HttpRequest(
                "GET",
                f"https://{_HOST}{_PAGE.path}",
                (_PAGE,),
                max_response_bytes=LIMIT_HTML,
            ),
            transport=transport,
            invocation=invocation,
            source_id=f"{DATASET}.index",
            media_types=frozenset({"text/html", "application/xhtml+xml"}),
            retry=RetryPolicy(),
        ).payload
    invocation.stage("discover")
    use_payload(payload, invocation, role="source_index", limit=LIMIT_HTML)
    try:
        return tuple(discover_dates(payload.data))
    except (FnsError, ValueError) as error:
        raise source_failure(error) from None

def _check_date(value):
    if type(value) is not date or not date(2016, 8, 1) <= value <= date(2099, 12, 31):
        raise OperationFailure("request.invalid_release_date")


def acquire_source(as_of, invocation, transport):
    invocation.stage("acquire")
    _check_date(as_of)
    source = receive_source(
        HttpRequest(
            "POST",
            f"https://{_HOST}{_API.path}",
            (_API,),
            {"accept": "application/json"},
            form_fields={"statDate": format_source_date(as_of)},
            max_response_bytes=LIMIT_JSON,
            read_only_post=True,
        ),
        transport=transport,
        invocation=invocation,
        source_id=DATASET,
        media_types=frozenset({"application/json", "text/json", "text/plain"}),
        retry=RetryPolicy(),
    )
    if not source.payload.data.lstrip().startswith(b"["):
        raise OperationFailure("source.json_signature_invalid")
    return source
