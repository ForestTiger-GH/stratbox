"""Actual bytes and trusted callbacks remain distinct from source claims."""
from dataclasses import replace

import pytest

from stratbox.core.execution.handoff import prepare_input
from stratbox.core.registry.requirements import DomainAdmission, SourceInstance, SourceRequirement, assess_requirements
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.sources import ResolvedSourceInstance
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity

CONTRACT = DataContract("source.payload", role=DataRole.ORIGINALS)
REQUIREMENT = SourceRequirement("published", ("example.statistics",), (CONTRACT,), "statistics", "source")


def _claim(payload):
    return SourceInstance("example.statistics", CONTRACT, material_identity=payload.identity)


def test_claimed_hash_never_proves_material_availability_or_runtime_readiness():
    claim = _claim(SourcePayload(b"never retained"))
    result = assess_requirements("example.read", (REQUIREMENT,), {"published": claim}, environment="available", effects="authorized")
    assert result.state == "conditional"
    assert result.layers.material == "unverified"
    assert result.layers.domain == "unassessed"
    assert result.requirements[0].materials[0].actual_identity is None
    with pytest.raises(TypeError):
        SourceInstance("example.statistics", CONTRACT, verified=True)


def test_resolver_reads_exact_bytes_and_domain_admission_is_a_separate_check():
    payload = SourcePayload(b"period,value\n2026-10,42\n", "text/csv")
    claim = _claim(payload)
    calls = []
    def admit(requirement, instance, actual):
        calls.append((requirement.input_name, instance, actual.data))
        return DomainAdmission("admitted")
    result = assess_requirements("example.read", (REQUIREMENT,), {"published": claim}, resolver=lambda _: payload, domain_admitter=admit)
    assert result.state == "inputs_verified"
    assert result.layers.material == "verified"
    assert result.layers.domain == "admitted"
    assert result.environment == "not_checked"
    assert calls == [("published", claim, payload.data)]
    ready = assess_requirements("example.read", (REQUIREMENT,), {"published": claim}, resolver=lambda _: payload,
        domain_admitter=admit, environment="available", effects="authorized")
    assert ready.state == "ready_to_execute"


def test_wrong_material_bytes_and_forged_prepared_identity_are_rejected():
    payload = SourcePayload(b"retained")
    claim = _claim(payload)
    mismatch = assess_requirements("example.read", (REQUIREMENT,), {"published": claim}, resolver=lambda _: SourcePayload(b"other"))
    assert mismatch.state == "blocked"
    assert "source.material_identity_mismatch" in mismatch.requirements[0].reasons
    forged = replace(prepare_input(payload), identity=ByteIdentity.of(b"forged"))
    resolved = ResolvedSourceInstance(claim, forged, payload)
    result = assess_requirements("example.read", (REQUIREMENT,), {"published": resolved})
    assert result.state == "blocked"
    assert "source.prepared_identity_mismatch" in result.requirements[0].reasons


def test_missing_material_and_wrong_receipt_cannot_be_promoted_by_domain_callback():
    payload = SourcePayload(b"retained")
    claim = _claim(payload)
    def absent(_):
        raise FileNotFoundError
    result = assess_requirements("example.read", (REQUIREMENT,), {"published": claim}, resolver=absent,
        domain_admitter=lambda *args: DomainAdmission("admitted"))
    assert result.state == "blocked"
    assert result.layers.material == "inaccessible"
    wrong_receipt = UsedInputReceipt.for_payload(SourcePayload(b"other"), "source")
    result = assess_requirements("example.read", (REQUIREMENT,), {"published": ResolvedSourceInstance(claim, payload, payload, wrong_receipt)})
    assert result.state == "blocked"
    assert "source.material_receipt_mismatch" in result.requirements[0].reasons


def test_same_bytes_can_fail_economic_admission_without_losing_material_evidence():
    payload = SourcePayload(b"unknown economic layout")
    result = assess_requirements("example.read", (REQUIREMENT,), {"published": _claim(payload)}, resolver=lambda _: payload,
        domain_admitter=lambda *args: DomainAdmission("rejected", ("example.layout_unreviewed",)))
    assert result.state == "blocked"
    assert result.layers.material == "verified"
    assert result.layers.domain == "rejected"
    assert result.layers.structure == "valid"
    assert "example.layout_unreviewed" in result.requirements[0].reasons


def test_typed_value_does_not_prove_an_unread_retained_material_hash():
    from stratbox.core.execution.values import value_identity
    contract = DataContract("example.typed_extract")
    requirement = replace(REQUIREMENT, accepted_contracts=(contract,))
    actual = {"observations": [1, 2]}
    prepared = prepare_input(actual, contract)
    claim = SourceInstance("example.statistics", contract,
        material_identity=ByteIdentity.of(b"absent snapshot"), consumed_identity=value_identity(actual))
    result = assess_requirements("example.read", (requirement,), {"published": ResolvedSourceInstance(claim, prepared)},
        domain_admitter=lambda *args: DomainAdmission("admitted"))
    assert result.state == "conditional"
    assert result.layers.material == "unverified"
    assert "source.material_reference_unresolved" in result.requirements[0].reasons
    # Original provenance is separate and does not require reacquiring originals.
    inline = replace(claim, material_identity=None, source_material_identity=ByteIdentity.of(b"original"))
    result = assess_requirements("example.read", (requirement,), {"published": ResolvedSourceInstance(inline, prepared)},
        domain_admitter=lambda *args: DomainAdmission("admitted"))
    assert result.state == "inputs_verified" and result.layers.material == "not_required"
    wrong = replace(inline, consumed_identity=ByteIdentity.of(b"other value"))
    result = assess_requirements("example.read", (requirement,), {"published": ResolvedSourceInstance(wrong, prepared)})
    assert result.state == "blocked"
    assert "source.consumed_identity_mismatch" in result.requirements[0].reasons


def test_matching_source_and_contract_cannot_substitute_another_content_group(monkeypatch):
    from stratbox.shared.data.sources import SourceGroup
    from stratbox.shared.data.source_context import SourceCoordinate, SourceUse, ValueContext
    from importlib import import_module
    contexts = import_module("stratbox.core.execution.value_context")
    from stratbox.core.registry import sources
    contract = DataContract("example.same_contract")
    groups = {name: SourceGroup(name, name, (contract,), grain=(name,)) for name in ("debt", "issuance")}
    actual_context = ValueContext((SourceUse(SourceCoordinate(source_id="example.statistics", source_group_id="issuance")),))
    monkeypatch.setattr(contexts, "value_context", lambda *args: actual_context)
    monkeypatch.setattr(sources, "source_group", lambda source, group: groups[group])
    requirement = replace(REQUIREMENT, group_id="debt", accepted_contracts=(contract,), grain=("debt",))
    prepared = prepare_input({"value": 42}, contract)
    result = assess_requirements("example.read", (requirement,), {"published": prepared})
    assert result.state == "blocked"
    assert result.requirements[0].instances[0].group_id == "issuance"
    assert result.requirements[0].instances[0].grain == ("issuance",)
    assert "source.group_mismatch" in result.requirements[0].reasons
