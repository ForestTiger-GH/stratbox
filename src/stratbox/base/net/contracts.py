"""Typed HTTP exchanges and explicit destination policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from ipaddress import ip_address
from math import isfinite
import re
from types import MappingProxyType
from typing import Callable, Literal, Mapping, Protocol
from urllib.parse import quote, unquote, urlsplit

from stratbox.base.limits import BudgetMeter

_HEADER = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", re.ASCII)
_HOST = re.compile(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", re.ASCII)
_BAD_URL = re.compile(r"[\x00-\x20\x7f\\]")
_BAD_ESCAPE = re.compile(r"%(?![0-9a-fA-F]{2})")
_RESPONSE_HEADERS = {
    "content-type",
    "content-length",
    "content-encoding",
    "etag",
    "last-modified",
    "retry-after",
}


def public_https_parts(url: str):
    if (
        not isinstance(url, str)
        or len(url) > 8192
        or _BAD_URL.search(url)
        or _BAD_ESCAPE.search(url)
    ):
        raise ValueError("Invalid HTTPS URL")
    parts = urlsplit(url)
    host = parts.hostname
    if (
        parts.scheme != "https"
        or not host
        or not _HOST.fullmatch(host)
        or "." not in host
        or parts.port not in (None, 443)
        or parts.username is not None
        or parts.password is not None
        or "#" in url
        or parts.netloc.endswith(":")
        or host.endswith((".localhost", ".local", ".internal"))
    ):
        raise ValueError("Invalid HTTPS destination")
    try:
        address = ip_address(host)
    except ValueError:
        address = None
    if address is not None or not re.search(r"[a-z]", host.rsplit(".", 1)[-1]):
        raise ValueError("HTTPS destination requires a named public host")
    path = unquote(parts.path, errors="strict")
    if (
        _BAD_URL.search(path.replace(" ", ""))
        or "%" in path
        or "//" in path
        or any(segment in {".", ".."} for segment in path.split("/"))
    ):
        raise ValueError("Invalid HTTPS path")
    return parts


@dataclass(frozen=True, slots=True)
class HttpsEndpoint:
    host: str
    path: str
    subtree: bool = False
    allow_query: bool = False

    def __post_init__(self) -> None:
        encoded = quote(self.path, safe="/-._~!$&'()*+,;=:@")
        parts = public_https_parts(f"https://{self.host}{encoded}")
        if self.host != parts.hostname:
            raise ValueError("Endpoint host must be normalized")
        if not self.path.startswith("/") or "?" in self.path or "#" in self.path:
            raise ValueError("Endpoint requires an absolute path")
        if self.subtree and not self.path.endswith("/"):
            raise ValueError("Endpoint subtree requires a trailing slash")

    def permits(self, url: str) -> bool:
        try:
            parts = public_https_parts(url)
        except (ValueError, TypeError):
            return False
        path = unquote(parts.path) or "/"
        return (
            parts.hostname == self.host
            and (path.startswith(self.path) if self.subtree else path == self.path)
            and (self.allow_query or "?" not in url)
        )


@dataclass(frozen=True, slots=True)
class HttpRequest:
    method: Literal["GET", "POST"]
    url: str = field(repr=False)
    endpoints: tuple[HttpsEndpoint, ...]
    headers: Mapping[str, str] = field(default_factory=dict, repr=False)
    form_fields: Mapping[str, str] | None = field(default=None, repr=False)
    body: bytes | None = field(default=None, repr=False)
    deadline_seconds: float = 30
    max_response_bytes: int = 10_000_000
    max_redirects: int = 3
    post_redirect: Literal["reject", "same_origin_307_308"] = "reject"
    read_only_post: bool = False
    budget: BudgetMeter | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.method not in {"GET", "POST"} or self.post_redirect not in {
            "reject",
            "same_origin_307_308",
        }:
            raise ValueError("Unsupported HTTP method or redirect behavior")
        if (
            not isfinite(self.deadline_seconds)
            or not 0 < self.deadline_seconds <= 600
            or not 1 <= self.max_response_bytes <= 512 * 1024 * 1024
            or not 0 <= self.max_redirects <= 10
        ):
            raise ValueError("Invalid HTTP limits")
        if (
            (self.read_only_post and self.method != "POST")
            or (self.body is not None and not isinstance(self.body, bytes))
            or (self.body is not None and self.form_fields is not None)
            or (
                self.method == "GET"
                and (self.body is not None or self.form_fields is not None)
            )
        ):
            raise ValueError("Invalid HTTP body")
        headers = {}
        for key, value in self.headers.items():
            name = key.lower()
            if (
                not _HEADER.fullmatch(key)
                or name in headers
                or name
                in {
                    "host",
                    "connection",
                    "content-length",
                    "transfer-encoding",
                    "proxy-authorization",
                }
                or not isinstance(value, str)
                or len(value) > 8192
                or any(ord(char) < 32 or ord(char) >= 127 for char in value)
            ):
                raise ValueError("Invalid HTTP header")
            headers[name] = value
        object.__setattr__(self, "headers", MappingProxyType(headers))
        object.__setattr__(self, "endpoints", tuple(self.endpoints))
        if self.form_fields is not None:
            if not all(
                isinstance(key, str) and isinstance(value, str)
                for key, value in self.form_fields.items()
            ):
                raise ValueError("Invalid HTTP form")
            object.__setattr__(
                self, "form_fields", MappingProxyType(dict(self.form_fields))
            )

    def permits(self, url: str) -> bool:
        return any(endpoint.permits(url) for endpoint in self.endpoints)


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    body: bytes = field(repr=False)
    headers: Mapping[str, str] = field(repr=False)
    observed_at_utc: datetime
    effective_locator_safe: str
    origin_assurance: Literal["provider_reported", "tls_host", "peer_bound"] = "provider_reported"
    target_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.target_sha256 is not None and not re.fullmatch(r"[a-f0-9]{64}", self.target_sha256):
            raise ValueError("Invalid target identity")
        if self.origin_assurance not in {"provider_reported", "tls_host", "peer_bound"}:
            raise ValueError("Invalid origin assurance")
        if not 100 <= self.status_code <= 599 or not isinstance(self.body, bytes):
            raise ValueError("Invalid HTTP response")
        if (
            self.observed_at_utc.utcoffset() is None
            or self.observed_at_utc.utcoffset().total_seconds() != 0
        ):
            raise ValueError("HTTP response requires a UTC timestamp")
        parts = public_https_parts(self.effective_locator_safe)
        if (
            parts.path not in ("", "/")
            or parts.query
            or "?" in self.effective_locator_safe
        ):
            raise ValueError("Safe HTTP locator contains request details")
        headers = {
            key.lower(): value
            for key, value in self.headers.items()
            if key.lower() in _RESPONSE_HEADERS
            and isinstance(value, str)
            and len(value) <= 8192
            and not re.search(r"[\x00-\x1f\x7f]", value)
        }
        object.__setattr__(self, "headers", MappingProxyType(headers))


FailureReason = Literal[
    "destination_forbidden",
    "connection_error",
    "timeout",
    "redirect_forbidden",
    "response_too_large",
    "truncated",
    "invalid_http",
    "cancelled",
    "capability_missing",
]


@dataclass(frozen=True, slots=True)
class HttpFailure:
    reason: FailureReason
    stage: Literal["admission", "connection", "headers", "body"]


class HttpTransport(Protocol):
    def exchange(
        self, request: HttpRequest, *, cancelled: Callable[[], bool] | None = None
    ) -> HttpResponse | HttpFailure: ...
