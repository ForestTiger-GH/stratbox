"""Bounded HTTPS adapter. Consumers may supply a different HttpTransport."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from math import isfinite
import re
from time import monotonic, sleep
from typing import Callable
from urllib.parse import urljoin
import zlib

from stratbox import __version__
from stratbox.base.limits import BudgetMeter

from .contracts import (
    HttpFailure,
    HttpRequest,
    HttpResponse,
    HttpTransport,
    public_https_parts,
)

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_REDIRECT_STATUS = frozenset({301, 302, 303, 307, 308})
_CHUNK = 64 * 1024


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    attempts: int = 3
    initial_delay_seconds: float = 0.5
    max_delay_seconds: float = 5

    def __post_init__(self) -> None:
        if (
            not 1 <= self.attempts <= 10
            or not isfinite(self.initial_delay_seconds)
            or not isfinite(self.max_delay_seconds)
            or not 0 <= self.initial_delay_seconds <= self.max_delay_seconds <= 60
        ):
            raise ValueError("Invalid HTTP retry policy")


def _retry_after(value: str | None, now: datetime) -> float:
    if not value:
        return 0
    if re.fullmatch(r"[0-9]+", value):
        return float(value) if len(value) < 16 else float("inf")
    try:
        parsed = parsedate_to_datetime(value)
        return max(0.0, (parsed - now).total_seconds())
    except (ValueError, TypeError, OverflowError):
        return 0


def exchange(
    request: HttpRequest,
    *,
    transport: HttpTransport | None,
    retry: RetryPolicy | None = None,
    cancelled: Callable[[], bool] | None = None,
    budget: BudgetMeter | None = None,
) -> HttpResponse | HttpFailure:
    """Check admission, perform a bounded exchange, and optionally retry a read."""
    if not request.permits(request.url):
        return HttpFailure("destination_forbidden", "admission")
    if transport is None:
        return HttpFailure("capability_missing", "admission")
    if budget is None:
        budget = request.budget
    metered = getattr(transport, "accounts_http_budget", False)
    if budget is not None and (
        budget.limits.wire_bytes is not None or budget.limits.requests is not None
    ) and not metered:
        return HttpFailure("capability_missing", "admission")
    deadline = monotonic() + request.deadline_seconds
    attempts = (
        retry.attempts
        if retry and (request.method == "GET" or request.read_only_post)
        else 1
    )
    for attempt in range(attempts):
        if cancelled is not None and cancelled():
            return HttpFailure("cancelled", "admission")
        remaining = deadline - monotonic()
        if remaining <= 0:
            return HttpFailure("timeout", "admission")
        observed_decoded = 0
        if budget is not None:
            budget.checkpoint()
            if not metered:
                budget.charge("requests", 1)
            remaining = min(remaining, budget.seconds_left())
            observed_decoded = budget.used("decoded_bytes")
        result = transport.exchange(
            replace(request, deadline_seconds=remaining, budget=budget), cancelled=cancelled
        )
        if budget is not None:
            budget.checkpoint()
        if monotonic() >= deadline:
            return HttpFailure("timeout", "body")
        if isinstance(result, HttpResponse):
            if budget is not None:
                reported = budget.used("decoded_bytes") - observed_decoded
                if reported < len(result.body):
                    budget.charge("decoded_bytes", len(result.body) - reported)
            effective = public_https_parts(result.effective_locator_safe).hostname
            if not any(endpoint.host == effective for endpoint in request.endpoints):
                return HttpFailure("destination_forbidden", "headers")
            if len(result.body) > request.max_response_bytes:
                return HttpFailure("response_too_large", "body")
            if result.status_code not in _RETRY_STATUS:
                return result
            wait = _retry_after(
                result.headers.get("retry-after"), result.observed_at_utc
            )
        elif isinstance(result, HttpFailure):
            if result.reason not in {"connection_error", "timeout", "truncated"}:
                return result
            wait = 0.0
        else:
            return HttpFailure("invalid_http", "headers")
        if attempt + 1 == attempts or retry is None:
            return result
        delay = max(
            wait, min(retry.max_delay_seconds, retry.initial_delay_seconds * 2**attempt)
        )
        if delay > retry.max_delay_seconds or monotonic() + delay >= deadline:
            return result
        until = monotonic() + delay
        while monotonic() < until:
            if budget is not None:
                budget.checkpoint()
            if cancelled is not None and cancelled():
                return HttpFailure("cancelled", "admission")
            sleep(max(0, min(0.05, until - monotonic())))
    raise AssertionError("HTTP exchange exhausted without a result")


class _ReadFailure(Exception):
    def __init__(self, reason):
        self.reason = reason


def _remaining(request: HttpRequest, deadline: float) -> float:
    remaining = deadline - monotonic()
    if request.budget is not None:
        remaining = min(remaining, request.budget.seconds_left())
    return remaining


def _read_body(read, headers, request, deadline, cancelled) -> bytes:
    max_bytes = request.max_response_bytes
    budget = request.budget
    wire_limit = max_bytes
    decoded_limit = max_bytes
    if budget is not None:
        wire = budget.remaining("wire_bytes")
        decoded = budget.remaining("decoded_bytes")
        wire_limit = min(wire_limit, wire) if wire is not None else wire_limit
        decoded_limit = min(decoded_limit, decoded) if decoded is not None else decoded_limit
    length = headers.get("content-length")
    if length is not None:
        if not re.fullmatch(r"[0-9]{1,16}", length) or headers.get("transfer-encoding"):
            raise _ReadFailure("invalid_http")
        length = int(length)
        if budget is not None:
            budget.check("wire_bytes", length)
        if length > wire_limit:
            raise _ReadFailure("response_too_large")
    encoding = headers.get("content-encoding", "identity").lower().strip()
    if encoding not in {"", "identity", "gzip", "deflate"}:
        raise _ReadFailure("invalid_http")
    decoder = None
    if encoding in {"gzip", "deflate"}:
        decoder = zlib.decompressobj(31 if encoding == "gzip" else zlib.MAX_WBITS)
    body = bytearray()
    wire_size = 0
    while True:
        if cancelled is not None and cancelled():
            raise _ReadFailure("cancelled")
        if _remaining(request, deadline) <= 0:
            raise _ReadFailure("timeout")
        chunk = read(min(_CHUNK, wire_limit - wire_size + 1))
        if not chunk:
            break
        if budget is not None:
            budget.charge("wire_bytes", len(chunk))
        wire_size += len(chunk)
        if wire_size > wire_limit:
            raise _ReadFailure("response_too_large")
        if decoder is not None:
            chunk = decoder.decompress(chunk, decoded_limit - len(body) + 1)
            if decoder.unused_data:
                raise _ReadFailure("invalid_http")
        if budget is not None:
            budget.charge("decoded_bytes", len(chunk))
        if len(body) + len(chunk) > decoded_limit or (decoder and decoder.unconsumed_tail):
            raise _ReadFailure("response_too_large")
        body.extend(chunk)
    if _remaining(request, deadline) <= 0:
        raise _ReadFailure("timeout")
    if (length is not None and wire_size != length) or (decoder and not decoder.eof):
        raise _ReadFailure("truncated")
    return bytes(body)


def _follow(request, open_response, cancelled, assurance):
    url = request.url
    deadline = monotonic() + request.deadline_seconds
    headers = {
        "accept-encoding": "identity",
        "user-agent": f"Stratbox/{__version__}",
        **request.headers,
    }
    for hop in range(request.max_redirects + 1):
        if cancelled is not None and cancelled():
            return HttpFailure("cancelled", "admission")
        remaining = _remaining(request, deadline)
        if remaining <= 0:
            return HttpFailure("timeout", "connection")
        if request.budget is not None:
            request.budget.charge("requests", 1)
        with open_response(url, headers, remaining) as (status, response_headers, read):
            incoming = {key.lower(): value for key, value in response_headers.items()}
            if status in _REDIRECT_STATUS:
                location = incoming.get("location")
                target = urljoin(url, location) if location else ""
                if hop == request.max_redirects or not request.permits(target):
                    return HttpFailure("redirect_forbidden", "headers")
                changed_host = public_https_parts(target).hostname != public_https_parts(url).hostname
                if request.method == "POST" and (
                    changed_host or status not in {307, 308}
                    or request.post_redirect != "same_origin_307_308"
                ):
                    return HttpFailure("redirect_forbidden", "headers")
                if changed_host:
                    headers = {
                        key: value for key, value in headers.items()
                        if key in {"accept", "accept-encoding", "user-agent"}
                    }
                elif target != url:
                    headers.pop("if-none-match", None)
                    headers.pop("if-modified-since", None)
                url = target
                continue
            try:
                body = b"" if status in {204, 304} else _read_body(
                    read, incoming, request, deadline, cancelled
                )
            except _ReadFailure as error:
                return HttpFailure(error.reason, "body")
            return HttpResponse(
                status, body, incoming, datetime.now(timezone.utc),
                f"https://{public_https_parts(url).hostname}", assurance,
                sha256(url.encode("utf-8")).hexdigest(),
            )
    raise AssertionError("Redirect limit exhausted")


class RequestsTransport:
    """Standard local HTTPS with bounded bodies and validated redirects."""

    accounts_http_budget = True

    def exchange(
        self, request: HttpRequest, *, cancelled: Callable[[], bool] | None = None
    ) -> HttpResponse | HttpFailure:
        if not request.permits(request.url):
            return HttpFailure("destination_forbidden", "admission")
        try:
            import requests
            from urllib3 import Timeout, exceptions as urllib_errors
        except ImportError:
            return HttpFailure("capability_missing", "admission")

        try:
            with requests.Session() as session:
                session.trust_env = False

                @contextmanager
                def open_response(url, headers, remaining):
                    prepared = requests.Request(
                        request.method, url, headers=headers,
                        data=dict(request.form_fields) if request.form_fields is not None else request.body,
                    ).prepare()
                    if not request.permits(prepared.url):
                        raise _ReadFailure("destination_forbidden")
                    # Session.send may consume a redirect body even when redirects are disabled.
                    with session.get_adapter(prepared.url).send(
                        prepared, timeout=Timeout(total=remaining), stream=True,
                    ) as response:
                        yield (
                            response.status_code, response.headers,
                            lambda size: response.raw.read1(size, decode_content=False),
                        )

                return _follow(request, open_response, cancelled, "tls_host")
        except _ReadFailure as error:
            return HttpFailure(error.reason, "admission")
        except (requests.Timeout, urllib_errors.TimeoutError):
            return HttpFailure("timeout", "connection")
        except urllib_errors.ProtocolError:
            return HttpFailure("truncated", "body")
        except (requests.ConnectionError, OSError):
            return HttpFailure("connection_error", "connection")
        except (requests.RequestException, ValueError, zlib.error):
            return HttpFailure("invalid_http", "headers")
