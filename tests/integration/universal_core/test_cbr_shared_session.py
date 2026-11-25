"""Supplied CBR workflows share transport work through the public SDK."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from threading import Lock
from time import sleep

from stratbox.capabilities.catalog import CatalogContribution
from stratbox.capabilities.model import (
    ScenarioDefinition, CascadeDefinition, CollectionMembership, GraphBody, Call, OutputRef,
)
from stratbox.core.execution.session import ExecutionSettings
from stratbox.core.network import HttpResponse, RequestsTransport
from stratbox.sdk import StrategyBox
from stratbox.sdk.bootstrap import default_snapshot


SERIES = (
    ("cbr.corporate_lending.debt_0105a", "01_05_A_Debt_corp_20261001.xlsx"),
    ("cbr.corporate_lending.issuance_0104a", "01_04_A_New_loans_corp_20261001.xlsx"),
    ("cbr.corporate_lending.fd_okved2", "01_03_C_Loans_corp_by_fd_activity_20261001.xlsx"),
    ("cbr.corporate_lending.sme_fd_okved2", "01_12_A_Loans_sme_by_fd_activity_20261001.xlsx"),
)
INDEX = "https://www.cbr.ru/statistics/bank_sector/sors/"
ROOT = "https://www.cbr.ru/vfs/statistics/BankSector/Loans_to_corporations/"


def workbook_bytes():
    import openpyxl
    workbook = openpyxl.Workbook()
    workbook.active.append(["Period", "Value"])
    workbook.active.append(["2026-10-01", 12])
    data = BytesIO()
    workbook.save(data)
    workbook.close()
    return data.getvalue()


def capture_scenarios(snapshot):
    """Compose the actual publication stages without a publisher dispatcher."""
    scenarios = []
    selected = (*SERIES, SERIES[0])
    for number, (series, _) in enumerate(selected):
        scenarios.append(ScenarioDefinition("fixture.cbr_source" + str(number), GraphBody((
            Call("discover", "cbr.publications.discover", parameters={"series_id": series, "page_url": INDEX}),
            Call("select", "cbr.publications.select", {"inventory": OutputRef("discover", "inventory")},
                {"issue_id": "2026-10-01", "format": "xlsx"}),
            Call("acquire", "cbr.publications.acquire", {"asset": OutputRef("select", "asset")}),
            Call("admit", "accept.original", {"material": OutputRef("acquire", "payload")}, {"source_id": series}),
            Call("extract", "workbook.extract", {"material": OutputRef("admit", "original")},
                {"series_id": series, "issue_id": "2026-10-01", "asset_id": "main"}),
        ), {"original": OutputRef("acquire", "original"), "flake": OutputRef("extract")}),
            outputs={"original": snapshot.definition("cbr.publications.acquire").outputs["original"],
                     "flake": snapshot.definition("workbook.extract").outputs["value"]},
            effects=frozenset({"network.receive"}), purpose="Acquire and physically extract one explicitly selected publication edition."))
    members = tuple("source" + str(number) for number in range(len(scenarios)))
    cascade = CascadeDefinition("fixture.cbr_sources", GraphBody(tuple(
        Call(member, scenario.id) for member, scenario in zip(members, scenarios)),
        {member + "." + name: OutputRef(member, name) for member, scenario in zip(members, scenarios) for name in scenario.outputs}),
        outputs={member + "." + name: port for member, scenario in zip(members, scenarios) for name, port in scenario.outputs.items()},
        effects=frozenset({"network.receive"}), membership=CollectionMembership(members, True))
    return snapshot.overlay(CatalogContribution(definitions=(*scenarios, cascade))), cascade


def test_default_sdk_cbr_groups_share_index_and_originals_and_refresh_next_run(monkeypatch):
    workbook = workbook_bytes()
    html = ("<html>" + "".join(f'<a href="{ROOT}{name}">{name}</a>' for _, name in SERIES) + "</html>").encode()
    counts, reservations, lock = Counter(), [], Lock()
    box_ref = []

    def receive(self, request, *, cancelled=None):
        with lock:
            counts[request.url] += 1
            ledger = box_ref[0].session.ledger.snapshot()
            reservations.append(dict(ledger.occupied))
        # Known URLs, including a resolved PublicationAsset input, have their
        # origin permit before the worker enters the provider.
        assert ledger.occupied.get("origin:https://www.cbr.ru", 0) == 1
        sleep(.005)
        body = html if request.url == INDEX else workbook
        mime = "text/html" if request.url == INDEX else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        request.budget.charge("requests", 1)
        request.budget.charge("wire_bytes", len(body))
        request.budget.charge("decoded_bytes", len(body))
        return HttpResponse(200, body, {"content-type": mime}, datetime.now(timezone.utc),
            "https://www.cbr.ru", "tls_host", sha256(request.url.encode()).hexdigest(), len(body))

    monkeypatch.setattr(RequestsTransport, "exchange", receive)
    catalog, workflow = capture_scenarios(default_snapshot())
    selections = (*SERIES, SERIES[0])
    with StrategyBox(capabilities=catalog, settings=ExecutionSettings(max_workers=3, network=3, per_origin=1)) as box:
        box_ref.append(box)
        first = box.run(workflow, timeout=15)
        assert first.outcome == "succeeded", ([(key, item.outcome, item.diagnostics) for key, item in first.results.items() if item.outcome != "succeeded"], first.tasks)
        assert counts[INDEX] == 1
        assert sum(counts.values()) == 5
        assert box.session.ledger.snapshot().spent["requests"] == 5
        for number, (series, _) in enumerate(selections):
            original = first.output(f"source{number}.original")
            assert original.payload.source_id == series
            assert original.acquisition.source_id == series
            assert original.asset.issue_id == "2026-10-01"
            flake = first.output(f"source{number}.flake")
            assert flake.series_id == series and flake.issue_id == original.asset.issue_id
            assert flake.source_identity == original.payload.identity
        original_receipt = first.output("source0.original").acquisition
        duplicate_receipt = first.output("source4.original").acquisition
        assert original_receipt.request_sha256 == duplicate_receipt.request_sha256
        assert original_receipt.shared_work_id == duplicate_receipt.shared_work_id
        assert duplicate_receipt.reused and duplicate_receipt.wire_size == 0
        # Network transfers and reusable command work both publish sharing
        # records. Network records identify their run as a physical consumer.
        shared = [record for record in box.session.journal.records if record.kind.startswith("shared_work.")
            and any(reference.namespace == "run" and reference.relation == "consumer" for reference in record.references)]
        assert sum(record.kind == "shared_work.started" for record in shared) == 5
        assert sum(record.kind == "shared_work.reused" for record in shared) >= 1
        second = box.run(workflow, timeout=15)
        assert second.outcome == "succeeded"
        assert counts[INDEX] == 2
        assert sum(counts.values()) == 10
        assert box.session.ledger.snapshot().spent["requests"] == 10
        assert box.session.ledger.snapshot().peak["origin:https://www.cbr.ru"] == 1


def test_sdk_retries_have_one_owner_and_provider_generation_refresh_is_visible():
    from dataclasses import replace
    from stratbox.composition import OperationStep, ScenarioDefinition, PlanOutputRef, RetryPolicy
    from stratbox.core.execution import ExecutionContext
    from stratbox.core.network import AccessScope, HttpRequest, HttpsEndpoint, RetryPolicy as HttpRetryPolicy, request_identity
    from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding

    request = HttpRequest("GET", "https://fixture.example/current", (HttpsEndpoint("fixture.example", "/current"),))

    class Provider:
        accounts_http_budget = True
        scope = AccessScope("backend", "private-source", 4, "managed", "route-ref", "tls-ref")
        calls = 0
        def exchange(self, request, *, cancelled=None):
            self.calls += 1
            status = 503 if self.calls <= 2 else 200
            body = b"retry" if status == 503 else b"original"
            request.budget.charge("requests", 1)
            request.budget.charge("wire_bytes", len(body))
            request.budget.charge("decoded_bytes", len(body))
            if self.calls == 3:
                self.scope = replace(self.scope, generation=5)
            return HttpResponse(status, body, {"content-type": "application/octet-stream"},
                datetime.now(timezone.utc), "https://fixture.example")

    provider = Provider()
    binding = ProviderBinding("source-provider", CapabilityRequirement("http"), "ready", provider)
    context = ExecutionContext(profile="local", bindings=(binding,))
    parameters = {"request": request, "source_id": "test.source",
        "media_types": frozenset({"application/octet-stream"}),
        "retry": HttpRetryPolicy(attempts=3, initial_delay_seconds=0, max_delay_seconds=0)}
    retry = RetryPolicy(max_attempts=3, retry_codes=("http.status_503",))
    workflow = ScenarioDefinition("receive", (
        OperationStep("first", "source.receive_original", parameters=parameters, retry=retry),
        OperationStep("second", "source.receive_original", parameters=parameters, depends_on=("first",), retry=retry),
    ), outputs={"first": PlanOutputRef("first", "source"), "second": PlanOutputRef("second", "source")})
    with StrategyBox(context=context) as box:
        result = box.run(workflow, timeout=10)
        assert result.outcome == "succeeded"
        assert provider.calls == 4
        assert [task.attempts for task in result.tasks] == [3, 1]
        first = result.results["receive/first"].value.receipt
        second = result.results["receive/second"].value.receipt
        assert first.request_sha256 != second.request_sha256
        for receipt, generation in ((first, 4), (second, 5)):
            assert receipt.request_sha256 == request_identity(request,
                provider_id="source-provider", profile="local", scope_id="private-source",
                generation=generation, route_identity="route-ref", configuration_identity="tls-ref")
        assert box.session.ledger.snapshot().spent["requests"] == 4
