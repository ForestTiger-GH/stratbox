"""Bounded HTTPS adapter. Consumers may supply a different HttpTransport."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from math import isfinite
import re
from time import monotonic, sleep
from typing import Callable
from urllib.parse import urljoin
import zlib

from stratbox import __version__

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
    retry_read_only_post: bool = False

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
) -> HttpResponse | HttpFailure:
    """Check admission, perform a bounded exchange, and optionally retry a read."""
    if not request.permits(request.url):
        return HttpFailure("destination_forbidden", "admission")
    if transport is None:
        return HttpFailure("capability_missing", "admission")
    deadline = monotonic() + request.deadline_seconds
    attempts = (
        retry.attempts
        if retry and (request.method == "GET" or retry.retry_read_only_post)
        else 1
    )
    for attempt in range(attempts):
        if cancelled is not None and cancelled():
            return HttpFailure("cancelled", "admission")
        remaining = deadline - monotonic()
        if remaining <= 0:
            return HttpFailure("timeout", "admission")
        result = transport.exchange(
            replace(request, deadline_seconds=remaining), cancelled=cancelled
        )
        if monotonic() >= deadline:
            return HttpFailure("timeout", "body")
        if isinstance(result, HttpResponse):
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
            if cancelled is not None and cancelled():
                return HttpFailure("cancelled", "admission")
            sleep(max(0, min(0.05, until - monotonic())))
    raise AssertionError("HTTP exchange exhausted without a result")


class _ReadFailure(Exception):
    def __init__(self, reason):
        self.reason = reason


def _read_body(response, max_bytes: int, deadline: float, cancelled) -> bytes:
    length = response.headers.get("Content-Length")
    if length is not None:
        if not re.fullmatch(r"[0-9]{1,16}", length) or response.headers.get(
            "Transfer-Encoding"
        ):
            raise _ReadFailure("invalid_http")
        length = int(length)
        if length > max_bytes:
            raise _ReadFailure("response_too_large")
    encoding = response.headers.get("Content-Encoding", "identity").lower().strip()
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
        if monotonic() >= deadline:
            raise _ReadFailure("timeout")
        chunk = response.raw.read1(
            min(_CHUNK, max_bytes - wire_size + 1), decode_content=False
        )
        if not chunk:
            break
        wire_size += len(chunk)
        if wire_size > max_bytes:
            raise _ReadFailure("response_too_large")
        if decoder is not None:
            chunk = decoder.decompress(chunk, max_bytes - len(body) + 1)
            if decoder.unconsumed_tail:
                raise _ReadFailure("response_too_large")
            if decoder.unused_data:
                raise _ReadFailure("invalid_http")
        body.extend(chunk)
        if len(body) > max_bytes:
            raise _ReadFailure("response_too_large")
    if monotonic() >= deadline:
        raise _ReadFailure("timeout")
    if (length is not None and wire_size != length) or (
        decoder is not None and not decoder.eof
    ):
        raise _ReadFailure("truncated")
    return bytes(body)


class RequestsTransport:
    """One logical exchange, with redirects validated before each request."""

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

        url = request.url
        deadline = monotonic() + request.deadline_seconds
        headers = {
            "accept-encoding": "identity",
            "user-agent": f"Stratbox/{__version__}",
            **request.headers,
        }
        stage = "connection"
        try:
            with requests.Session() as session:
                session.trust_env = False
                for hop in range(request.max_redirects + 1):
                    if cancelled is not None and cancelled():
                        return HttpFailure("cancelled", "admission")
                    remaining = deadline - monotonic()
                    if remaining <= 0:
                        return HttpFailure("timeout", "connection")
                    stage = "connection"
                    # Use the adapter directly. Session.send builds a redirect
                    # candidate and can read an unbounded redirect body even
                    # with allow_redirects=False.
                    prepared = requests.Request(
                        request.method,
                        url,
                        headers=headers,
                        data=dict(request.form_fields)
                        if request.form_fields is not None
                        else request.body,
                    ).prepare()
                    if not request.permits(prepared.url):
                        return HttpFailure("destination_forbidden", "admission")
                    adapter = session.get_adapter(prepared.url)
                    with adapter.send(
                        prepared, timeout=Timeout(total=remaining), stream=True
                    ) as response:
                        stage = "headers"
                        status = response.status_code
                        if status in _REDIRECT_STATUS:
                            location = response.headers.get("Location")
                            target = urljoin(url, location) if location else ""
                            if hop == request.max_redirects or not request.permits(
                                target
                            ):
                                return HttpFailure("redirect_forbidden", "headers")
                            changed_host = (
                                public_https_parts(target).hostname
                                != public_https_parts(url).hostname
                            )
                            if request.method == "POST" and (
                                changed_host
                                or status not in {307, 308}
                                or request.post_redirect != "same_origin_307_308"
                            ):
                                return HttpFailure("redirect_forbidden", "headers")
                            if changed_host:
                                headers = {
                                    key: value
                                    for key, value in headers.items()
                                    if key
                                    in {"accept", "accept-encoding", "user-agent"}
                                }
                            url = target
                            continue
                        stage = "body"
                        body = (
                            b""
                            if status in {204, 304}
                            else _read_body(
                                response,
                                request.max_response_bytes,
                                deadline,
                                cancelled,
                            )
                        )
                        return HttpResponse(
                            status,
                            body,
                            response.headers,
                            datetime.now(timezone.utc),
                            f"https://{public_https_parts(url).hostname}",
                        )
        except _ReadFailure as error:
            return HttpFailure(error.reason, stage)
        except (requests.Timeout, urllib_errors.TimeoutError):
            return HttpFailure("timeout", stage)
        except urllib_errors.ProtocolError:
            return HttpFailure("truncated", stage)
        except (requests.ConnectionError, OSError):
            return HttpFailure("connection_error", stage)
        except (requests.RequestException, ValueError, zlib.error):
            return HttpFailure("invalid_http", stage)
        return HttpFailure("redirect_forbidden", "headers")
