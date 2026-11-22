from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256

from stratbox.core.execution import ExecutionContext
from stratbox.core.network import HttpRequest, HttpResponse, HttpsEndpoint, HttpsRoute, RoutedTransport
from stratbox.core.operations.source.original_definitions import ReceiveOriginalRequest
from stratbox.core.operations.source.originals import receive_original
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding


class PeerTransport:
    accounts_http_budget = True
    def __init__(self, assurance="peer_bound"):
        self.calls, self.assurance = [], assurance
    def exchange(self, request, **options):
        request.budget.charge("requests", 1)
        self.calls.append(request)
        return HttpResponse(200, b"%PDF-1.7\noriginal", {"content-type": "application/pdf"},
            datetime(2026, 11, 23, tzinfo=timezone.utc), "https://gateway.example", self.assurance,
            sha256(request.url.encode()).hexdigest())


def setup(assurance="peer_bound", admitted=True):
    route = HttpsRoute("published-reports", ("publisher.example",), "https://gateway.example/public/")
    backend = PeerTransport(assurance)
    transport = RoutedTransport(backend, (route,))
    grants = {"destination_bound", "budget_enforced"}
    if admitted:
        grants.add(route.admission_guarantee)
    binding = ProviderBinding("gateway", CapabilityRequirement("http", guarantees=frozenset(grants)), "ready", transport, "reports")
    context = ExecutionContext(profile="managed", bindings=(binding,))
    request = ReceiveOriginalRequest(HttpRequest("GET", "https://publisher.example/reports/month.pdf",
        (HttpsEndpoint("publisher.example", "/reports/", subtree=True),)), "publisher.report", frozenset({"application/pdf"}))
    return route, backend, transport, context, request


def test_managed_route_pins_exact_policy_without_claiming_publisher_peer_identity():
    route, backend, transport, context, request = setup()
    result = receive_original(request, context=context)
    assert result.outcome == "succeeded", result.diagnostics
    receipt = result.value.receipt
    assert receipt.origin_assurance == "provider_reported"
    assert receipt.transport_assurance == "peer_bound" and receipt.route_policy_id == route.policy_identity
    assert receipt.logical_target_sha256 == sha256(request.request.url.encode()).hexdigest()
    assert receipt.target_sha256 == sha256(backend.calls[0].url.encode()).hexdigest()
    assert receipt.logical_target_sha256 != receipt.target_sha256


def test_unadmitted_or_changed_route_fails_before_network_and_weak_peer_fails_after():
    route, backend, transport, context, request = setup(admitted=False)
    result = receive_original(request, context=context)
    assert result.outcome == "failed" and result.diagnostics[0].code == "http.route_not_admitted" and not backend.calls
    changed = replace(route, gateway_base="https://gateway.example/other/")
    grants = frozenset({"destination_bound", "budget_enforced", changed.admission_guarantee})
    context = replace(context, bindings=(replace(context.bindings[0], capability=CapabilityRequirement("http", guarantees=grants)),))
    assert receive_original(request, context=context).outcome == "failed" and not backend.calls
    route, backend, transport, context, request = setup(assurance="tls_host")
    result = receive_original(request, context=context)
    assert result.outcome == "failed" and result.diagnostics[0].code == "http.destination_unqualified"
    assert len(backend.calls) == 1
