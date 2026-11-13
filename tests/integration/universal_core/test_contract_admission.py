from dataclasses import replace
from datetime import date, datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

import pytest

from stratbox.base.capabilities import (
    BindingError, CapabilityRequirement, ProviderBinding, probe_provider, select_provider,
)
from stratbox.base.filestore import LocalFileStore
from stratbox.base.limits import ExecutionBudget
from stratbox.base.net import HttpResponse
from stratbox.catalog import DirectoryMaterial, OperationCatalog, WireRequestError, invoke_read_only, operation_catalog, wire_schemas
from stratbox.data import SourcePayload
from stratbox.execution import Correlation, ExecutionContext, OperationDefinition, run
from stratbox.macrobanks import cbr_offices

_FIXTURE = Path(__file__).resolve().parents[2] / "fixtures/universal_core/offices-basic.html"
_DAY = date(2026, 11, 12)


def test_catalog_imports_without_extras_and_covers_declared_operations():
    check = """
import importlib
import sys
from stratbox.catalog import operation_catalog
from stratbox.execution import OperationDefinition
catalog = operation_catalog()
descriptions = catalog.describe()
registered = {(d['operation_id'], d['contract_version']) for d in descriptions}
assert len(registered) >= 60
modules = [name for name in sys.modules if name.startswith('stratbox.')]
declared = {
    (value.operation_id, value.contract_version) for module in modules
    for value in vars(importlib.import_module(module)).values()
    if isinstance(value, OperationDefinition)
}
assert registered == declared, (registered - declared, declared - registered)
assert not {'requests', 'pandas', 'openpyxl', 'pyxlsb', 'highspy', 'xlrd'} & sys.modules.keys()
"""
    package = Path(cbr_offices.__file__).resolve().parents[2]
    subprocess.run([sys.executable, "-B", "-S", "-c",
                    f"import sys; sys.path.insert(0, {str(package.parent)!r})\n" + check], check=True)
    definition = operation_catalog().definitions[0]
    with pytest.raises(ValueError, match="Duplicate operation"):
        OperationCatalog((definition, definition))


def _wire(operation_id, data):
    return json.dumps({"operation_id": operation_id, "contract_version": 1, "input": data}).encode()


@pytest.mark.parametrize(("raw", "code"), [
    (_wire("frg.plan_cleanup", {"directory_ref": "fixture", "delete_others": "0"}), "request.invalid_type"),
    (_wire("cbr.offices.parse", {"source_ref": "fixture", "capture_date": "2026-02-29"}), "request.invalid_date"),
    (_wire("cbr.offices.parse", {"source_ref": "fixture", "capture_date": "2026-11-12", "url": "secret"}), "request.invalid_fields"),
    (_wire("frg.apply_cleanup", {}), "operation.wire_unavailable"),
    (_wire("cmd.run", {}), "operation.contract_unavailable"),
    (b'{"operation_id":"one","operation_id":"two"}', "request.duplicate_field"),
    (b"[" * 2000 + b"]" * 2000, "request.depth_limit"),
])
def test_invalid_wire_input_stops_before_material_provider(raw, code):
    with pytest.raises(WireRequestError) as rejected:
        invoke_read_only(raw, materials=None)
    assert rejected.value.code == code


def test_wire_and_python_use_same_bytes_and_project_only_declared_fields(tmp_path):
    from stratbox.macrobanks import frg

    source = SourcePayload(_FIXTURE.read_bytes(), "text/html")
    parsed = cbr_offices.parse(cbr_offices.ParseOfficesRequest(source, _DAY))
    assert parsed.outcome == "succeeded"
    store = LocalFileStore(root=str(tmp_path))
    (tmp_path / "2026-05-01_Экспресс выдачи.xlsx").write_bytes(b"fixture")

    class Materials:
        def source(self, reference):
            assert reference == "fixture"
            return source

        def release(self, reference):
            assert reference == "fixture"
            return parsed.value

        def directory(self, reference):
            assert reference == "fixture"
            return DirectoryMaterial(".", store)

    material = Materials()
    result = json.loads(invoke_read_only(_wire("cbr.offices.parse", {
        "source_ref": "fixture", "expected_sha256": source.identity.sha256, "capture_date": _DAY.isoformat(),
    }), materials=material))
    assert result["value"]["dataset_sha256"] == parsed.value.dataset_version.identity.sha256
    assert result["value"]["representation_sha256"] == parsed.value.representation.identity.sha256
    assert result["value"]["row_count"] == parsed.value.row_count
    comparison = json.loads(invoke_read_only(_wire("cbr.offices.compare", {
        "candidate_ref": "fixture", "baseline_ref": "fixture",
    }), materials=material))
    assert comparison["value"]["state"] == "unchanged"
    plan = frg.plan_cleanup(frg.PlanCleanupRequest("."), store=store)
    projection = json.loads(invoke_read_only(_wire("frg.plan_cleanup", {"directory_ref": "fixture"}), materials=material))
    assert projection["value"]["plan_sha256"] == plan.value.identity.sha256
    assert list(tmp_path.iterdir()) == [tmp_path / "2026-05-01_Экспресс выдачи.xlsx"]
    schema, response_schema = wire_schemas("frg.plan_cleanup", 1)
    assert set(projection) == set(response_schema["required"])
    schema["properties"].clear()
    assert wire_schemas("frg.plan_cleanup", 1)[0]["properties"]


def test_provider_binding_is_explicit_and_readiness_probe_is_optional():
    needed = CapabilityRequirement("http", guarantees=frozenset({"destination_bound"}))
    provider = object()
    binding = ProviderBinding("fixture", needed, "not_configured", provider, "scope-a")
    with pytest.raises(BindingError, match="provider.not_configured"):
        select_provider(needed, (binding,))
    probed = probe_provider(binding, lambda candidate: "ready" if candidate is provider else "unavailable")
    assert select_provider(needed, (probed,), scope_id="scope-a") is probed
    for candidates, scope, code in (
        ((probed,), "scope-b", "provider.capability_missing"),
        ((probed, probed), None, "provider.binding_conflict"),
        ((replace(probed, capability=CapabilityRequirement("http", 2)),), None, "provider.capability_incompatible"),
        ((replace(probed, capability=CapabilityRequirement("http"), readiness="degraded"),), None, "provider.guarantee_missing"),
        ((replace(probed, readiness="unavailable"),), None, "provider.unavailable"),
    ):
        with pytest.raises(BindingError, match=code):
            select_provider(needed, candidates, scope_id=scope)


def test_budget_ceiling_stage_and_optional_sink_failure():
    events = []

    class Sink:
        def emit(self, event):
            events.append(event)
            raise ConnectionError("unstructured private detail")

    definition = OperationDefinition("test.budget", 1, "test-1", int, int)

    def work(request, invocation):
        invocation.stage("read")
        invocation.budget.charge("objects", request)
        return request

    result = run(definition, 1, work, context=ExecutionContext(sink=Sink()))
    assert result.outcome == "succeeded" and result.observability.dropped == 3
    result = run(definition, 3, work, context=ExecutionContext(
        sink=Sink(), correlation=Correlation(run_id="example", cause_event_id=events[-1].event_id),
        budget=ExecutionBudget(objects=4), ceiling=ExecutionBudget(objects=2),
    ))
    assert result.diagnostics[0].code == "budget.objects"
    assert result.diagnostics[0].stage == "read"
    assert events[-1].version == 2 and events[-1].correlation.cause_event_id
    assert "unstructured" not in events[-1].to_json()
    with pytest.raises(ValueError):
        Correlation(run_id="x" * 129)


def test_only_matching_baseline_proves_conditional_http_reuse():
    now = datetime(2026, 11, 12, tzinfo=timezone.utc)
    target = "a" * 64
    served = HttpResponse(
        200, _FIXTURE.read_bytes(), {"content-type": "text/html", "etag": '"fixture"'},
        now, "https://www.cbr.ru", "peer_bound", target,
    )
    unchanged = HttpResponse(
        304, b"", {"etag": '"fixture"'}, now,
        served.effective_locator_safe, "peer_bound", target,
    )

    class Provider:
        accounts_http_budget = True

        def __init__(self):
            self.response = served
            self.calls = []
            self.baseline_allowed = True

        def exchange(self, request, **_):
            request.budget.charge("requests", 1)
            self.calls.append(request)
            return self.response

        def verify_baseline(self, baseline):
            return self.baseline_allowed and baseline.payload.data == served.body

    provider = Provider()
    capability = CapabilityRequirement("http", guarantees=frozenset({"destination_bound", "budget_enforced"}))
    binding = ProviderBinding("https", capability, "ready", provider, "public")
    context = ExecutionContext(profile="managed", bindings=(binding,))
    request = cbr_offices.AcquireOfficesRequest(timezone.utc)
    acquired = cbr_offices.acquire(request, transport=provider, context=context)
    assert acquired.outcome == "succeeded", acquired.diagnostics
    provider.response = unchanged
    reused = cbr_offices.acquire(
        replace(request, baseline=acquired.value.source), transport=provider, context=context,
    )
    assert reused.outcome == "succeeded" and reused.value.source.receipt.reused
    assert provider.calls[-1].headers["if-none-match"] == '"fixture"'
    assert reused.value.payload == acquired.value.payload
    for response, current_context, current_request, owner_accepts in (
        (replace(unchanged, headers={"etag": '"different"'}), context, replace(request, baseline=acquired.value.source), True),
        (replace(unchanged, target_sha256="b" * 64), context, replace(request, baseline=acquired.value.source), True),
        (unchanged, context, request, True),
        (unchanged, context, replace(request, baseline=acquired.value.source), False),
        (unchanged, replace(context, bindings=(replace(binding, scope_id="new"),)), replace(request, baseline=acquired.value.source), True),
    ):
        provider.response = response
        provider.baseline_allowed = owner_accepts
        rejected = cbr_offices.acquire(current_request, transport=provider, context=current_context)
        assert rejected.diagnostics[0].code == "http.full_representation_required"
    provider.response = replace(served, origin_assurance="tls_host")
    unqualified = cbr_offices.acquire(request, transport=provider, context=context)
    assert unqualified.diagnostics[0].code == "http.destination_unqualified"


def test_computation_identity_keeps_source_method_and_projection_distinct():
    from stratbox.data import UsedInputReceipt, computation_identity

    original = UsedInputReceipt.for_payload(SourcePayload(b"same", "text/csv", "scope-a"), "table")

    def key(inputs=(original,), **options):
        method = options.pop("method", "release-1")
        return computation_identity("test.qualify", 1, method, inputs, **options)

    keys = {
        key(), key(method="release-2"),
        key((replace(original, source_id="scope-b"),)),
        key(parameters={"scale": 1000}),
        key(resources={"regions": "version-2"}),
        key(representation_profile="spreadsheet", representation_options={"style": "text"}),
        key(representation_profile="spreadsheet", representation_options={"style": "numeric"}),
    }
    assert len(keys) == 7
    assert key(parameters={"period": _DAY, "scale": 1}) == key(parameters={"scale": 1, "period": _DAY})
