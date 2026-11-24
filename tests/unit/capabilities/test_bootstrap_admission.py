"""Authored contracts stay effective through the common operation runner."""
from dataclasses import replace

import pytest

from stratbox.capabilities.catalog import CatalogSnapshot
from stratbox.capabilities.model import CommandDefinition, PortContract, SemanticPredicate
from stratbox.core.execution.handoff import prepare_input
from stratbox.core.execution.runner import Completion
from stratbox.sdk.bootstrap import CapabilityRuntimeCatalog
from stratbox.shared.data.processing import DataContract


IMPLEMENTATION = "stratbox.core.execution.runner:Completion"


def test_command_parameters_and_semantic_output_checks_remain_live(monkeypatch):
    from stratbox.sdk import bootstrap
    seen = []
    def work(request, invocation):
        seen.append(request)
        return request["amount"] * request["scale"]
    monkeypatch.setattr(bootstrap, "_symbol", lambda reference: work)
    command = CommandDefinition("local.scale", IMPLEMENTATION,
        inputs={"amount": PortContract(value_type=int)},
        parameters={"scale": 1, "profile": {"units": "million"}}, fixed={"scale": 2},
        outputs={"value": PortContract(value_type=int, predicates=(SemanticPredicate(operator="minimum", expected=1),))})
    catalog = CapabilityRuntimeCatalog(CatalogSnapshot((command,)))
    call = catalog.bind("local.scale", inputs={"amount": prepare_input(3, DataContract("capability.value"))})
    result = call.invoke()
    assert result.outcome == "succeeded"
    assert result.value == 6
    assert seen[0]["profile"]["units"] == "million"
    with pytest.raises(ValueError, match="fixed_parameter_override"):
        catalog.bind("local.scale", inputs={"amount": prepare_input(3, DataContract("capability.value"))}, parameters={"scale": 5})
    rejected = catalog.bind("local.scale", inputs={"amount": prepare_input(0, DataContract("capability.value"))}).invoke()
    assert rejected.outcome == "failed"
    assert rejected.value is None
    assert rejected.diagnostics[0].code == "acceptance.semantic_predicate_failed"


def test_required_parameter_admission_precedes_implementation_loading(monkeypatch):
    from stratbox.sdk import bootstrap
    def forbidden(reference):
        raise AssertionError("implementation was loaded before parameter admission")
    monkeypatch.setattr(bootstrap, "_symbol", forbidden)
    command = CommandDefinition("local.required", IMPLEMENTATION,
        parameters={"basis": None}, required_parameters=("basis",))
    catalog = CapabilityRuntimeCatalog(CatalogSnapshot((command,)))
    with pytest.raises(ValueError, match="parameter_required"):
        catalog.bind(command.capability_id)


def test_multi_output_completion_keeps_partial_diagnostics(monkeypatch):
    from stratbox.sdk import bootstrap
    from stratbox.capabilities.model import AcceptanceContract
    monkeypatch.setattr(bootstrap, "_symbol", lambda reference:
        lambda request, invocation: Completion({"data": (1,), "findings": ("partial",)}, "partial", "source.coverage_partial"))
    command = CommandDefinition("local.partial", IMPLEMENTATION,
        outputs={"data": PortContract(value_type=tuple), "findings": PortContract(value_type=tuple)},
        acceptance=AcceptanceContract(coherent_outputs=("data", "findings"), partial_allowed=True))
    catalog = CapabilityRuntimeCatalog(CatalogSnapshot((command,)))
    result = catalog.bind(command.capability_id).invoke()
    assert result.outcome == "partial"
    assert result.value.data == (1,)
    assert result.value.findings == ("partial",)
    assert result.diagnostics[0].code == "source.coverage_partial"


def test_local_definitions_cannot_rebind_a_live_catalog_identity():
    command = CommandDefinition("local.one", IMPLEMENTATION)
    catalog = CapabilityRuntimeCatalog(CatalogSnapshot())
    catalog.admit_local(command)
    catalog.admit_local(command)
    with pytest.raises(ValueError, match="live_identity_conflict"):
        catalog.admit_local(replace(command, revision="2"))
    assert catalog.snapshot.definition(command.capability_id).revision == "1"


def test_metadata_discovery_combines_canonical_and_pending_domain_entries():
    from stratbox.operations import operation_catalog
    command = CommandDefinition("local.example", IMPLEMENTATION)
    catalog = CapabilityRuntimeCatalog(CatalogSnapshot((command,)), operation_catalog())
    page = catalog.discover(limit=200)
    assert page.total == 357
    assert page.next_offset == 200
    assert catalog.describe("local.example")["migration_status"] == "canonical"
    item = catalog.describe(catalog.domain_catalog.list_refs()[0].operation_id)
    assert item["migration_status"] == "domain_pending_migration"
    assert item["kind"] == "operation"


@pytest.mark.parametrize('effect_kind', ('storage.write', 'notification.handoff', 'dataset.write'))
def test_required_effect_obligation_requires_physical_confirmation(monkeypatch, effect_kind):
    from stratbox.capabilities.model import OperationDefinition, GraphBody, Call, ReuseContract
    from stratbox.sdk import StrategyBox, bootstrap
    monkeypatch.setattr(bootstrap, '_symbol', lambda reference: lambda request, invocation: 1)
    command = CommandDefinition('local.claimed_effect', IMPLEMENTATION,
        outputs={'value': PortContract(value_type=int)}, effects=frozenset({effect_kind}),
        reuse=ReuseContract(shareable=False, effects=frozenset({effect_kind})))
    operation = OperationDefinition('local.required_effect',
        GraphBody((Call('write', command.capability_id),), {}, required_effects=('write',)),
        outputs={}, effects=frozenset({effect_kind}))
    with StrategyBox(capabilities=CatalogSnapshot((command, operation))) as box:
        result = box.invoke(operation.capability_id, timeout=5)
        assert result.outcome == 'failed'
        assert any('effect' in diagnostic and 'unconfirmed' in diagnostic for diagnostic in result.diagnostics)


def test_resource_parameter_claims_resolve_defaults_and_fixed_conditions():
    command = CommandDefinition("local.bounded", IMPLEMENTATION,
        parameters={"max_bytes": 4096}, resource_parameters={"staging_bytes": "max_bytes", "temporary_bytes": "max_bytes"})
    catalog = CapabilityRuntimeCatalog(CatalogSnapshot((command,)))
    assert catalog.resource_requirements(command.capability_id) == {"staging_bytes": 4096, "temporary_bytes": 4096}
    assert catalog.resource_requirements(command.capability_id, {"max_bytes": 16}) == {"staging_bytes": 16, "temporary_bytes": 16}
    with pytest.raises(TypeError):
        command.resource_parameters["staging_bytes"] = "arbitrary"
    for invalid in (True, -1, "4096"):
        with pytest.raises(ValueError, match="resource_parameter_invalid"):
            catalog.resource_requirements(command.capability_id, {"max_bytes": invalid})
    with pytest.raises(ValueError, match="resource_parameter_undeclared"):
        CommandDefinition("local.unbounded", IMPLEMENTATION, resource_parameters={"staging_bytes": "not_a_parameter"})
    fixed = replace(command, capability_id="local.fixed", fixed={"max_bytes": 128})
    bound = CapabilityRuntimeCatalog(CatalogSnapshot((fixed,)))
    assert bound.resource_requirements(fixed.capability_id)["staging_bytes"] == 128
    with pytest.raises(ValueError, match="fixed_parameter_override"):
        bound.resource_requirements(fixed.capability_id, {"max_bytes": 129})
    assert CatalogSnapshot((command,)).describe(command.capability_id)["resource_parameters"] == {
        "staging_bytes": "max_bytes", "temporary_bytes": "max_bytes"}
