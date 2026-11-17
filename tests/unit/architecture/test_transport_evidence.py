"""HTTP request evidence is stable across layout changes and safely rejects old baselines."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from stratbox.core.network import HttpRequest, HttpResponse, HttpsEndpoint, RequestsTransport
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding
from stratbox.core.operations.source import acquisition


URL = "https://example.org/source"
REQUEST = HttpRequest("GET", URL, (HttpsEndpoint("example.org", "/source"),))


def _invocation(provider, bindings=()):
    return SimpleNamespace(
        context=SimpleNamespace(profile="local", bindings=tuple(bindings)),
        provider=lambda role, selected: selected,
        budget=None,
        cancelled=lambda: False,
    )


def test_builtin_evidence_identity_ignores_python_module_path(monkeypatch):
    transport = RequestsTransport()
    invocation = _invocation(transport)
    original = acquisition._request_identity(REQUEST, invocation, transport)
    monkeypatch.setattr(RequestsTransport, "__module__", "relocated.implementation")
    assert acquisition._transport_identity(transport) == "http.requests.v1"
    assert acquisition._request_identity(REQUEST, invocation, transport) == original
    changed_headers = replace(REQUEST, headers={"accept": "text/csv"})
    assert acquisition._request_identity(changed_headers, invocation, transport) != original


def test_bound_provider_id_and_scope_take_precedence_over_class_path():
    class CustomTransport:
        pass

    transport = CustomTransport()
    binding = ProviderBinding(
        "stable-http-provider", CapabilityRequirement("http"), "ready",
        transport, scope_id="published-sources",
    )
    original = acquisition._request_identity(REQUEST, _invocation(transport, (binding,)), transport)
    CustomTransport.__module__ = "renamed.provider.module"
    assert acquisition._request_identity(REQUEST, _invocation(transport, (binding,)), transport) == original
    other = replace(binding, scope_id="other-sources")
    assert acquisition._request_identity(REQUEST, _invocation(transport, (other,)), transport) != original
    unbound = acquisition._request_identity(REQUEST, _invocation(transport), transport)
    assert unbound != original


def test_conditional_reuse_requires_exact_request_fingerprint(monkeypatch):
    requests = []
    transport = object()
    invocation = _invocation(transport)

    def exchange(request, **kwargs):
        requests.append(request)
        return HttpResponse(
            200, b"exact source bytes",
            {"content-type": "text/plain", "etag": '"qualified"'},
            datetime(2026, 11, 18, tzinfo=timezone.utc),
            "https://example.org",
            target_sha256="a" * 64,
        )

    monkeypatch.setattr(acquisition, "exchange", exchange)
    original = acquisition.receive_source(
        REQUEST, transport=transport, source_id="sample",
        invocation=invocation, media_types=frozenset({"text/plain"}),
    )
    assert original.receipt.request_sha256 == acquisition._request_identity(
        REQUEST, invocation, transport,
    )
    acquisition.receive_source(
        REQUEST, transport=transport, source_id="sample",
        invocation=invocation, media_types=frozenset({"text/plain"}),
        baseline=original,
    )
    assert requests[-1].headers["if-none-match"] == '"qualified"'

    prior_receipt = replace(original.receipt, request_sha256="0" * 64)
    mismatched = replace(original, receipt=prior_receipt)
    acquisition.receive_source(
        REQUEST, transport=transport, source_id="sample",
        invocation=invocation, media_types=frozenset({"text/plain"}),
        baseline=mismatched,
    )
    assert "if-none-match" not in requests[-1].headers
    assert len(requests) == 3
