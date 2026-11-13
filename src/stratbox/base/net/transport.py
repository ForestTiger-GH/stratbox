"""Bounded HTTPS adapter. Consumers may supply a different HttpTransport."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from io import BytesIO
from math import isfinite
import re
from time import monotonic, sleep
from typing import BinaryIO, Callable
from urllib.parse import unquote, urljoin, urlunsplit
import zlib

from stratbox import __version__
from stratbox.base.limits import BudgetMeter
from stratbox.data.evidence import ByteIdentity

from .contracts import (
    HttpFailure,
    HttpRequest,
    HttpResponse,
    HttpStreamResponse,
    HttpTransport,
    HttpsEndpoint,
    StreamingHttpTransport,
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
    transport: HttpTransport | None = None,
    retry: RetryPolicy | None = None,
    cancelled: Callable[[], bool] | None = None,
    budget: BudgetMeter | None = None,
) -> HttpResponse | HttpFailure:
    """Check admission, perform a bounded exchange, and optionally retry a read."""
    return _exchange(request, transport, retry, cancelled, budget)


def exchange_into(
    request: HttpRequest, sink: BinaryIO, *,
    transport: StreamingHttpTransport | None = None,
    retry: RetryPolicy | None = None,
    cancelled: Callable[[], bool] | None = None,
    budget: BudgetMeter | None = None,
) -> HttpStreamResponse | HttpFailure:
    """Receive into private seekable staging, resetting it before each attempt."""
    accepted = False
    try:
        result = _exchange(request, transport, retry, cancelled, budget, sink)
        accepted = isinstance(result, HttpStreamResponse)
        return result
    finally:
        if not accepted:
            sink.seek(0)
            sink.truncate(0)


def _exchange(request, transport, retry, cancelled, budget, sink=None):
    if not request.permits(request.url):
        return HttpFailure("destination_forbidden", "admission")
    if transport is None:
        from stratbox.base.runtime import active_providers

        defaults = active_providers()
        if defaults is None:
            return HttpFailure("capability_missing", "admission")
        transport = defaults.http
    if sink is not None and not callable(getattr(transport, "exchange_into", None)):
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
        attempt_request = replace(request, deadline_seconds=remaining, budget=budget)
        if sink is None:
            result = transport.exchange(attempt_request, cancelled=cancelled)
            response = result
            size = len(result.body) if isinstance(result, HttpResponse) else 0
        else:
            sink.seek(0)
            sink.truncate(0)
            result = transport.exchange_into(attempt_request, sink, cancelled=cancelled)
            response = result.response if isinstance(result, HttpStreamResponse) else None
            size = result.identity.size if isinstance(result, HttpStreamResponse) else 0
        if budget is not None:
            budget.checkpoint()
        if monotonic() >= deadline:
            return HttpFailure("timeout", "body")
        if isinstance(response, HttpResponse):
            if budget is not None:
                reported = budget.used("decoded_bytes") - observed_decoded
                if reported < size:
                    budget.charge("decoded_bytes", size - reported)
            if isinstance(transport, RoutedTransport):
                admitted = transport.accepts_response(request, response)
            else:
                effective = public_https_parts(response.effective_locator_safe).hostname
                admitted = response.route_id is None and any(endpoint.host == effective for endpoint in request.endpoints)
            if not admitted:
                return HttpFailure("destination_forbidden", "headers")
            if size > request.max_response_bytes:
                return HttpFailure("response_too_large", "body")
            if response.status_code not in _RETRY_STATUS:
                return result
            wait = _retry_after(
                response.headers.get("retry-after"), response.observed_at_utc
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


def _read_body(read, headers, request, deadline, cancelled, write):
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
    digest = sha256()
    decoded_size = 0
    wire_size = 0

    def checkpoint():
        if cancelled is not None and cancelled():
            raise _ReadFailure("cancelled")
        if _remaining(request, deadline) <= 0:
            raise _ReadFailure("timeout")

    def accept(chunk):
        nonlocal decoded_size
        if budget is not None:
            budget.charge("decoded_bytes", len(chunk))
        decoded_size += len(chunk)
        if decoded_size > decoded_limit:
            raise _ReadFailure("response_too_large")
        digest.update(chunk)
        try:
            if chunk and write(chunk) != len(chunk):
                raise OSError("Short staging write")
        except OSError:
            raise _ReadFailure("staging_failed") from None

    while True:
        checkpoint()
        chunk = read(min(_CHUNK, wire_limit - wire_size + 1))
        if not chunk:
            break
        if budget is not None:
            budget.charge("wire_bytes", len(chunk))
        wire_size += len(chunk)
        if wire_size > wire_limit:
            raise _ReadFailure("response_too_large")
        if decoder is None:
            accept(chunk)
            continue
        while chunk:
            checkpoint()
            decoded = decoder.decompress(chunk, min(_CHUNK, decoded_limit - decoded_size + 1))
            if decoder.unused_data:
                raise _ReadFailure("invalid_http")
            accept(decoded)
            chunk = decoder.unconsumed_tail
    checkpoint()
    if (length is not None and wire_size != length) or (decoder and not decoder.eof):
        raise _ReadFailure("truncated")
    return ByteIdentity(digest.hexdigest(), decoded_size), wire_size


def _follow(request, open_response, cancelled, assurance, sink=None):
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
                buffer = BytesIO() if sink is None else sink
                identity, wire_size = (ByteIdentity.of(b""), 0) if status in {204, 304} else _read_body(
                    read, incoming, request, deadline, cancelled, buffer.write,
                )
            except _ReadFailure as error:
                return HttpFailure(error.reason, "body")
            response = HttpResponse(
                status, buffer.getvalue() if sink is None else b"", incoming, datetime.now(timezone.utc),
                f"https://{public_https_parts(url).hostname}", assurance,
                sha256(url.encode("utf-8")).hexdigest(), wire_size,
            )
            return response if sink is None else HttpStreamResponse(response, identity)
    raise AssertionError("Redirect limit exhausted")


class RequestsTransport:
    """Standard local HTTPS with bounded bodies and validated redirects."""

    accounts_http_budget = True

    def __init__(self, *, ca_bundle: str | None = None):
        if ca_bundle is not None and (not isinstance(ca_bundle, str) or not ca_bundle.strip()):
            raise ValueError("CA bundle must be a nonempty path")
        self._tls_options = {"verify": ca_bundle} if ca_bundle is not None else {}

    def exchange(
        self, request: HttpRequest, *, cancelled: Callable[[], bool] | None = None
    ) -> HttpResponse | HttpFailure:
        return self._exchange(request, cancelled)

    def exchange_into(
        self, request: HttpRequest, sink: BinaryIO, *, cancelled: Callable[[], bool] | None = None,
    ) -> HttpStreamResponse | HttpFailure:
        return self._exchange(request, cancelled, sink)

    def _exchange(self, request, cancelled, sink=None):
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
                        prepared, timeout=Timeout(total=remaining), stream=True, **self._tls_options,
                    ) as response:
                        yield (
                            response.status_code, response.headers,
                            lambda size: response.raw.read1(size, decode_content=False),
                        )

                return _follow(request, open_response, cancelled, "tls_host", sink)
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


_GATEWAY_HEADERS = frozenset({"accept", "accept-encoding", "content-type", "user-agent"})


@dataclass(frozen=True, slots=True)
class HttpsRoute:
    """Map admitted source hosts to a fixed HTTPS gateway and path prefix."""

    route_id: str
    source_hosts: tuple[str, ...]
    gateway_base: str
    methods: frozenset[str] = frozenset({"GET"})

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", self.route_id):
            raise ValueError("Invalid route identifier")
        if isinstance(self.source_hosts, str) or isinstance(self.methods, str):
            raise ValueError("Expected host and method collections")
        hosts = tuple(self.source_hosts)
        if not hosts or len(set(hosts)) != len(hosts):
            raise ValueError("Invalid source hosts")
        for host in hosts:
            HttpsEndpoint(host, "/")
        base = public_https_parts(self.gateway_base)
        methods = frozenset(self.methods)
        if "?" in self.gateway_base or not base.path.endswith("/") or not methods or not methods <= {"GET", "POST"}:
            raise ValueError("Invalid gateway route")
        object.__setattr__(self, "source_hosts", hosts)
        object.__setattr__(self, "methods", methods)

    def wire_request(self, request: HttpRequest) -> HttpRequest:
        source = public_https_parts(request.url)
        if (
            source.hostname not in self.source_hosts or request.method not in self.methods
            or not request.permits(request.url) or not request.headers.keys() <= _GATEWAY_HEADERS
        ):
            raise ValueError("Request is outside the configured route")
        gateway = public_https_parts(self.gateway_base)
        path = gateway.path + source.path.lstrip("/")
        url = urlunsplit((gateway.scheme, gateway.hostname, path, source.query, ""))
        endpoint = HttpsEndpoint(gateway.hostname, unquote(path), allow_query="?" in request.url)
        return replace(request, url=url, endpoints=(endpoint,), max_redirects=0)


class RoutedTransport:
    """Keep the logical policy and the observed gateway identity distinct."""

    def __init__(self, backend: StreamingHttpTransport, routes: tuple[HttpsRoute, ...], *,
                 direct_hosts: frozenset[str] | None = None):
        self._backend = backend
        self._routes = {}
        ids = set()
        for route in routes:
            if route.route_id in ids or any(host in self._routes for host in route.source_hosts):
                raise ValueError("Duplicate HTTP route")
            ids.add(route.route_id)
            self._routes.update((host, route) for host in route.source_hosts)
        if direct_hosts is not None:
            for host in direct_hosts:
                HttpsEndpoint(host, "/")
        self._direct_hosts = None if direct_hosts is None else frozenset(direct_hosts)

    @property
    def accounts_http_budget(self):
        return getattr(self._backend, "accounts_http_budget", False)

    def route_for(self, request: HttpRequest) -> HttpsRoute | None:
        return self._routes.get(public_https_parts(request.url).hostname)

    def exchange(self, request, *, cancelled=None):
        return self._perform(request, cancelled)

    def exchange_into(self, request, sink, *, cancelled=None):
        return self._perform(request, cancelled, sink)

    def _perform(self, request, cancelled, sink=None):
        if not request.permits(request.url):
            return HttpFailure("destination_forbidden", "admission")
        route = self.route_for(request)
        if route is None:
            hosts = self._direct_hosts
            if hosts is not None:
                request = replace(request, endpoints=tuple(item for item in request.endpoints if item.host in hosts))
                if not request.permits(request.url):
                    return HttpFailure("destination_forbidden", "admission")
            return self._send(request, cancelled, sink)
        try:
            wire = route.wire_request(request)
        except ValueError:
            return HttpFailure("destination_forbidden", "admission")
        result = self._send(wire, cancelled, sink)
        if isinstance(result, HttpFailure):
            return result
        response = result.response if isinstance(result, HttpStreamResponse) else result
        if not isinstance(response, HttpResponse) or response.route_id is not None or not self._wire_matches(wire, response):
            return HttpFailure("destination_forbidden", "headers")
        qualified = replace(
            response, route_id=route.route_id, logical_target_sha256=sha256(request.url.encode()).hexdigest(),
            transport_assurance=response.origin_assurance, origin_assurance="provider_reported",
        )
        return replace(result, response=qualified) if isinstance(result, HttpStreamResponse) else qualified

    def _send(self, request, cancelled, sink):
        if sink is None:
            return self._backend.exchange(request, cancelled=cancelled)
        return self._backend.exchange_into(request, sink, cancelled=cancelled)

    @staticmethod
    def _wire_matches(wire, response):
        return (
            public_https_parts(response.effective_locator_safe).hostname == wire.endpoints[0].host
            and response.target_sha256 == sha256(wire.url.encode()).hexdigest()
        )

    def accepts_response(self, request, response):
        route = self.route_for(request)
        if route is None:
            effective = public_https_parts(response.effective_locator_safe).hostname
            return (
                response.route_id is None and (self._direct_hosts is None or effective in self._direct_hosts)
                and any(endpoint.host == effective for endpoint in request.endpoints)
            )
        try:
            wire = route.wire_request(request)
        except ValueError:
            return False
        return (
            response.route_id == route.route_id and self._wire_matches(wire, response)
            and response.logical_target_sha256 == sha256(request.url.encode()).hexdigest()
        )
