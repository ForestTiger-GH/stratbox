"""HTTPS with numeric peer admission before TLS and request transmission."""

from __future__ import annotations

from contextlib import contextmanager
from http.client import HTTPSConnection, HTTPException, HTTPResponse as WireResponse, IncompleteRead
from io import BufferedReader, RawIOBase
from ipaddress import IPv4Address, IPv6Address, ip_address
import socket
import ssl
from time import monotonic
from typing import BinaryIO, Callable
from urllib.parse import quote, urlencode
import zlib

from .contracts import HttpFailure, HttpRequest, HttpResponse, HttpStreamResponse, public_https_parts
from .transport import _ReadFailure, _follow

Address = IPv4Address | IPv6Address
Resolver = Callable[[str, int], list[tuple]]


def _resolve(host: str, port: int) -> list[tuple]:
    return socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)


def _public(address: Address) -> bool:
    if isinstance(address, IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_global and not address.is_multicast and not address.is_reserved


class _DeadlineReader(RawIOBase):
    def __init__(self, sock: ssl.SSLSocket, seconds_left: Callable[[], float]):
        self.sock = sock
        self.seconds_left = seconds_left

    def readable(self):
        return True

    def readinto(self, buffer):
        self.sock.settimeout(self.seconds_left())
        return self.sock.recv_into(buffer)

    def makefile(self, mode):
        return BufferedReader(self)


class PeerBoundTransport:
    """Resolve once per hop, connect to the admitted address, and verify TLS by hostname."""

    accounts_http_budget = True

    def __init__(
        self, *, resolver: Resolver = _resolve, allow_peer: Callable[[Address], bool] = _public,
        tls_context: ssl.SSLContext | None = None,
    ):
        self._resolver = resolver
        self._allow_peer = allow_peer
        self._context = tls_context if tls_context is not None else ssl.create_default_context()
        self._verify_context()

    def _verify_context(self) -> None:
        if not self._context.check_hostname or self._context.verify_mode != ssl.CERT_REQUIRED:
            raise ValueError("TLS certificate and hostname verification are required")

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

        @contextmanager
        def open_response(url, headers, remaining):
            self._verify_context()
            parts = public_https_parts(url)
            host = parts.hostname
            deadline = monotonic() + remaining
            addresses = self._resolver(host, 443)
            if not addresses:
                raise OSError("No peer")
            # Fail closed on a mixed allowed and denied resolution.
            for family, socktype, protocol, _, address in addresses:
                if (family not in {socket.AF_INET, socket.AF_INET6}
                        or socktype != socket.SOCK_STREAM or protocol not in {0, socket.IPPROTO_TCP}
                        or address[1] != 443 or not self._allow_peer(ip_address(address[0]))):
                    raise _ReadFailure("destination_forbidden")
            family, socktype, protocol, _, address = addresses[0]

            def seconds_left():
                if cancelled is not None and cancelled():
                    raise _ReadFailure("cancelled")
                seconds = deadline - monotonic()
                if seconds <= 0:
                    raise TimeoutError()
                return seconds

            with socket.socket(family, socktype, protocol) as raw:
                raw.settimeout(seconds_left())
                raw.connect(address)
                if ip_address(raw.getpeername()[0]) != ip_address(address[0]):
                    raise _ReadFailure("destination_forbidden")
                raw.settimeout(seconds_left())
                with self._context.wrap_socket(raw, server_hostname=host) as secured:
                    conn = HTTPSConnection(host, timeout=seconds_left(), context=self._context)
                    conn.sock = secured
                    try:
                        path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
                        if parts.query:
                            path += "?" + quote(parts.query, safe="/%?:@!$&'()*+,;=[]-._~")
                        body = request.body
                        if request.form_fields is not None:
                            body = urlencode(dict(request.form_fields)).encode("ascii")
                            headers = {"content-type": "application/x-www-form-urlencoded", **headers}
                        secured.settimeout(seconds_left())
                        conn.request(request.method, path, body=body, headers=headers)
                        # Recompute the remaining time on each socket read,
                        # including a response that sends headers incrementally.
                        reader = _DeadlineReader(secured, seconds_left)
                        with WireResponse(reader, method=request.method) as response:
                            response.begin()
                            observed = {}
                            for name, value in response.getheaders():
                                name = name.lower()
                                if name in observed and name in {
                                    "content-length", "content-encoding", "transfer-encoding", "location",
                                }:
                                    raise _ReadFailure("invalid_http")
                                observed[name] = value

                            yield response.status, observed, response.read1
                    finally:
                        conn.close()

        try:
            return _follow(request, open_response, cancelled, "peer_bound", sink)
        except _ReadFailure as error:
            return HttpFailure(error.reason, "admission")
        except TimeoutError:
            return HttpFailure("timeout", "connection")
        except IncompleteRead:
            return HttpFailure("truncated", "body")
        except ssl.SSLCertVerificationError:
            return HttpFailure("destination_forbidden", "connection")
        except (HTTPException, ValueError, zlib.error):
            return HttpFailure("invalid_http", "headers")
        except OSError:
            return HttpFailure("connection_error", "connection")
