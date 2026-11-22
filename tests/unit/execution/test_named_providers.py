"""Provider choices are scoped per port and never trigger silent fallback."""

from dataclasses import replace

import pytest

from stratbox.core.execution import ExecutionContext, OperationDefinition, run
from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding, ProviderSelection


TRANSFER = OperationDefinition(
    "test.transfer", 1, "transfer-1", int, tuple,
    required_capabilities=frozenset({"filestore", "output_filestore"}),
)


def _bindings(*, managed=False):
    left, right, destination = object(), object(), object()
    values = (
        ProviderBinding("files", TRANSFER.capability("filestore", managed=managed), "ready", left, "left"),
        ProviderBinding("files", TRANSFER.capability("filestore", managed=managed), "ready", right, "right"),
        ProviderBinding("files", TRANSFER.capability("output_filestore", managed=managed), "ready", destination, "output"),
    )
    return values, (left, right, destination)


@pytest.mark.parametrize("profile", ["local", "managed"])
def test_binding_only_resolves_actual_adapters_with_independent_scopes(profile):
    bindings, (_, reader, writer) = _bindings(managed=profile == "managed")
    result = run(
        TRANSFER, 1,
        lambda req, inv: (inv.provider("filestore"), inv.provider("output_filestore")),
        context=ExecutionContext(profile=profile, bindings=bindings),
        provider_selections={
            "filestore": ProviderSelection("files", "right"),
            "output_filestore": ProviderSelection("files", "output"),
        },
    )
    assert result.outcome == "succeeded"
    assert result.value == (reader, writer)


def test_explicit_object_disambiguates_only_its_own_bindings():
    bindings, (reader, _, writer) = _bindings()
    result = run(
        TRANSFER, 1,
        lambda req, inv: (inv.provider("filestore", reader), inv.provider("output_filestore", writer)),
        context=ExecutionContext(bindings=bindings),
        providers={"filestore": reader, "output_filestore": writer},
    )
    assert result.value == (reader, writer)
    duplicate = replace(bindings[0], scope_id="alias")
    rejected = run(TRANSFER, 1, lambda req, inv: (),
        context=ExecutionContext(bindings=(*bindings, duplicate)),
        providers={"filestore": reader, "output_filestore": writer})
    assert rejected.diagnostics[0].code == "provider.binding_conflict"


@pytest.mark.parametrize("case,code", [
    ("missing", "provider.capability_missing"),
    ("unavailable", "provider.unavailable"),
    ("ambiguous", "provider.binding_conflict"),
    ("object_mismatch", "provider.binding_mismatch"),
    ("guarantee", "provider.guarantee_missing"),
])
def test_named_admission_stops_before_work_and_never_uses_defaults(monkeypatch, case, code):
    from stratbox.core.execution import runner

    monkeypatch.setattr(runner, "active_providers", lambda: pytest.fail("Unexpected fallback"))
    bindings, (reader, _, writer) = _bindings(managed=True)
    selection = ProviderSelection("files", "left")
    given = None
    if case == "missing":
        selection = ProviderSelection("absent", "left")
    elif case == "unavailable":
        bindings = (replace(bindings[0], readiness="unavailable"), *bindings[1:])
    elif case == "ambiguous":
        selection = ProviderSelection("files")
    elif case == "object_mismatch":
        given = object()
    elif case == "guarantee":
        bindings = (replace(bindings[0], capability=CapabilityRequirement("filestore")), *bindings[1:])
    result = run(TRANSFER, 1, lambda req, inv: pytest.fail("Handler ran before admission"),
        context=ExecutionContext(profile="managed", bindings=bindings),
        providers={"filestore": given, "output_filestore": writer},
        provider_selections={"filestore": selection})
    assert result.outcome == "failed"
    assert result.diagnostics[0].code == code


def test_named_missing_local_binding_does_not_use_default(monkeypatch):
    from stratbox.core.execution import runner

    monkeypatch.setattr(runner, "active_providers", lambda: pytest.fail("Unexpected fallback"))
    result = run(TRANSFER, 1, lambda req, inv: (),
        provider_selections={"filestore": ProviderSelection("missing")})
    assert result.diagnostics[0].code == "provider.capability_missing"


def test_selection_is_admitted_for_optional_ports_and_unknown_roles_are_rejected():
    definition = OperationDefinition("test.optional", 1, "v1", int, object,
        optional_capabilities=frozenset({"filestore"}))
    provider = object()
    binding = ProviderBinding("files", CapabilityRequirement("filestore"), "ready", provider, "one")
    context = ExecutionContext(bindings=(binding,))
    selected = run(definition, 1, lambda req, inv: inv.provider("filestore"),
        context=context, provider_selections={"filestore": ProviderSelection(scope_id="one")})
    assert selected.value is provider
    rejected = run(definition, 1, lambda req, inv: provider,
        context=context, provider_selections={"http": ProviderSelection("other")})
    assert rejected.diagnostics[0].code == "provider.capability_undeclared"


def test_selection_in_provider_mapping_remains_available_inside_handler():
    bindings, (_, reader, writer) = _bindings()
    selected = run(TRANSFER, 1,
        lambda req, inv: (inv.provider("filestore"), inv.provider("output_filestore")),
        context=ExecutionContext(bindings=bindings), providers={
            "filestore": ProviderSelection("files", "right"),
            "output_filestore": ProviderSelection("files", "output"),
        })
    assert selected.value == (reader, writer)


def test_empty_selection_is_not_an_implicit_default():
    with pytest.raises(ValueError, match="selection_required"):
        ProviderSelection()


def test_binding_evidence_uses_selected_scope_when_one_adapter_has_two_scopes():
    provider = object()
    definition = OperationDefinition("test.scope", 1, "v1", int, tuple,
        required_capabilities=frozenset({"http"}))
    bindings = tuple(
        ProviderBinding("http", CapabilityRequirement("http"), "ready", provider, scope)
        for scope in ("public", "other")
    )
    result = run(definition, 1,
        lambda req, inv: (inv.provider("http"), inv.selected_binding("http").scope_id),
        context=ExecutionContext(bindings=bindings),
        provider_selections={"http": ProviderSelection("http", "other")})
    assert result.value == (provider, "other")
