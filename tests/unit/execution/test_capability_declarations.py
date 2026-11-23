"""Declared provider ports are mandatory for local and managed invocations."""
import pytest

from stratbox.core.execution import ExecutionContext, OperationDefinition, run
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding


def test_undeclared_local_provider_is_rejected_before_default_lookup(monkeypatch):
    from stratbox.core.execution import runner
    monkeypatch.setattr(runner, "active_providers",
                        lambda: (_ for _ in ()).throw(AssertionError("default providers accessed")))
    op = OperationDefinition("test.undeclared", "v-1", int, int)
    calls = []

    def handler(request, invocation):
        calls.append("handler")
        invocation.provider("http")
        return request

    result = run(op, 1, handler)
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "provider.capability_undeclared"
    assert calls == ["handler"]
    assert not result.effects


def test_required_and_optional_are_different_admission_phases(monkeypatch):
    from stratbox.core.execution import runner
    monkeypatch.setattr(runner, "active_providers", lambda: None)
    op = OperationDefinition("test.optional", "v-1", int, int,
                             optional_capabilities=frozenset({"http"}))
    assert run(op, 1, lambda req, inv: req).outcome == "succeeded"
    result = run(op, 1, lambda req, inv: inv.provider("http") or req)
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == "provider.capability_missing"
    given = object()
    assert run(op, 1, lambda req, inv: inv.provider("http", given) and req).outcome == "succeeded"

    required = OperationDefinition("test.required", "v-1", int, int,
                                   required_capabilities=frozenset({"http"}))
    called = []
    fail = run(required, 1, lambda req, inv: called.append(1) or req)
    assert fail.outcome == "failed"
    assert fail.diagnostics[0].code == "provider.capability_missing"
    assert not called


def test_undeclared_local_and_managed_bindings_both_rejected():
    op = OperationDefinition("test.managed_undeclared", "v-1", int, int)
    provider = object()
    ctx = ExecutionContext(profile="managed", bindings=(
        ProviderBinding("test", CapabilityRequirement("http"), "ready", provider, "scope"),
    ))
    for context in (ExecutionContext(), ctx):
        result = run(op, 1, lambda req, inv: inv.require_provider("http", provider) or req,
                     context=context)
        assert result.outcome == "failed"
        assert result.diagnostics[0].code == "provider.capability_undeclared"
    with pytest.raises(ValueError, match="undeclared"):
        op.capability("http", managed=True)


def test_managed_binding_still_checks_guarantee_and_identity():
    op = OperationDefinition("test.managed_declared", "v-1", int, int,
                             optional_capabilities=frozenset({"http"}))
    provider = object()
    good = ProviderBinding(
        "test", CapabilityRequirement("http", guarantees=frozenset({
            "destination_bound", "budget_enforced",
        })), "ready", provider,
    )
    ctx = ExecutionContext(profile="managed", bindings=(good,))
    result = run(op, 1, lambda req, inv: inv.require_provider("http", provider) or req,
                 context=ctx)
    assert result.outcome == "succeeded"
    bad = ProviderBinding("test", CapabilityRequirement("http"), "ready", provider)
    rejected = run(op, 1, lambda req, inv: inv.require_provider("http", provider) or req,
                   context=ExecutionContext(profile="managed", bindings=(bad,)))
    assert rejected.outcome == "failed"
    assert rejected.diagnostics[0].code == "provider.guarantee_missing"


def test_external_runtime_ports_are_descriptors_not_fake_eager_capabilities():
    from stratbox.core.execution import RuntimeDependency
    runtime = (RuntimeDependency("notification_state", "scoped", "notification_runtime"),)
    op = OperationDefinition("test.runtime", "v-1", int, int,
                             runtime_dependencies=runtime)
    assert run(op, 1, lambda req, inv: req).outcome == "succeeded"
    assert op.runtime_dependencies == runtime
    with pytest.raises(ValueError):
        op.capability("notification_state")
    with pytest.raises(ValueError):
        OperationDefinition("test.conflict", "v-1", int, int,
            required_capabilities=frozenset({"http"}),
            runtime_dependencies=(RuntimeDependency("http", "conditional", "adapter"),))


def test_scoped_notification_runtime_binding_keeps_host_guarantees():
    from stratbox.core.notifications.runtime import require_binding
    from stratbox.core.runtime.capabilities import BindingError
    provider = object()
    capability = CapabilityRequirement("notification", guarantees=frozenset({
        "recipient_bound", "durable_acceptance", "idempotent_acceptance",
    }))
    bound = ProviderBinding("consumer", capability, "ready", provider, "scope1")
    context = ExecutionContext(profile="managed", bindings=(bound,))
    require_binding(context, "scope1", "notification", provider, "recipient_bound")
    with pytest.raises(BindingError):
        require_binding(context, "scope2", "notification", provider, "recipient_bound")
    with pytest.raises(BindingError):
        require_binding(context, "scope1", "notification", object(), "recipient_bound")
    with pytest.raises(BindingError):
        require_binding(context, "scope1", "notification", provider, "unprovided_guarantee")
