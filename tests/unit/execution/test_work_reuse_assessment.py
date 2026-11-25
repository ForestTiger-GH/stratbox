"""Work compatibility distinguishes active producers, cached values and ancestry."""
from dataclasses import replace
from types import SimpleNamespace

from stratbox.capabilities.model.reuse import ReuseContract, build_work_identity
from stratbox.core.execution.contracts import ExecutionContext
from stratbox.core.execution.handoff import PreparedInput
from stratbox.core.execution.sharing import assess_work
from stratbox.shared.data.processing import DataContract
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity


def spec(*, completed=True, identities=None):
    return SimpleNamespace(operation_id="reuse.compute", method_fingerprint="implementation",
        reuse_eligible=True, reuse_contract=ReuseContract(completed=completed),
        reuse_identity=build_work_identity("reuse.compute", "edition:implementation",
            binding_identities=identities or {"definition": "definition-v1", "method": "method-v1"},
            schema_fingerprint="schema-v1"))


def assess(declaration, material=None, **options):
    return assess_work(declaration, inputs={} if material is None else {"material": material},
        parameters=options.pop("parameters", {}), context=options.pop("context", ExecutionContext()),
        run_id="run-one", **options)


def test_completed_false_allows_an_active_join_but_forbids_both_sides_of_cached_reuse():
    transient = assess(spec(completed=False))
    persistent = assess(spec())
    assert transient.inflight_allowed and not transient.completed_allowed
    assert transient.can_consume(persistent)
    assert not transient.can_consume(persistent, completed=True)
    assert not persistent.can_consume(transient, completed=True)
    assert persistent.can_consume(persistent, completed=True)


def test_actual_input_hashing_retains_exact_prepared_schema_profile_reference_and_group_basis():
    original = spec(identities={"definition": "def", "method": "method", "profile": "profile",
        "schema:observations": "schema", "reference:territories": "territories", "group": "group"})
    first = assess(original, b"body")
    assert dict(first.identity.binding_fingerprints) == dict(original.reuse_identity.binding_fingerprints)
    assert first.identity.schema_fingerprint == "schema-v1"
    assert first.identity.profile_fingerprint == "profile"
    for key in ("schema:observations", "reference:territories", "group", "profile", "method", "definition"):
        updated = dict(original.reuse_identity.binding_fingerprints)
        updated[key] += ".new"
        second = assess(spec(identities=updated), b"body")
        assert first.key != second.key
    assert first.key != assess(replace_basis(original, schema_fingerprint="schema-v2"), b"body").key


def replace_basis(declaration, **changes):
    return SimpleNamespace(**{**vars(declaration), "reuse_identity": replace(declaration.reuse_identity, **changes)})


def material(source):
    content = b"identical bytes"
    receipt = UsedInputReceipt("source", ByteIdentity.of(content), "application/octet-stream", "inline", source)
    return PreparedInput(DataContract("reuse.material"), content, used_inputs=(receipt,))


def test_equal_payload_with_different_input_evidence_requires_independent_work():
    a, b = assess(spec(), material("source.a")), assess(spec(), material("source.b"))
    assert a.identity.input_identities == b.identity.input_identities
    assert a.identity.input_evidence_fingerprints != b.identity.input_evidence_fingerprints
    assert a.key != b.key
    assert not b.can_consume(a)
    assert not b.can_consume(a, completed=True)


def test_context_input_receipts_and_source_qualification_are_consumer_significant():
    prepared = material("source.a")
    one = assess(spec(), prepared)
    context = ExecutionContext(input_receipts=prepared.used_inputs)
    assert one.key != assess(spec(), prepared, context=context).key
    reported = replace(prepared, qualifications=frozenset({"reported"}))
    derived = replace(prepared, qualifications=frozenset({"derived"}))
    assert assess(spec(), reported).key != assess(spec(), derived).key


def test_offline_consumer_cannot_reuse_an_online_observation_or_cache():
    policy = ReuseContract(deterministic=False, observation_scoped=True,
                           effects=frozenset({"network.receive"}))
    declaration = spec()
    declaration.reuse_contract = policy
    online = assess(declaration, parameters={"observation_id": "release", "allow_network": True})
    offline = assess(declaration, parameters={"observation_id": "release", "allow_network": False})
    assert online.inflight_allowed and online.completed_allowed
    assert not offline.inflight_allowed and not offline.completed_allowed
    assert "reuse.network_disallowed" in offline.reasons
    assert not offline.can_consume(online)
    assert not offline.can_consume(online, completed=True)


def test_provider_admission_guarantees_and_versions_are_part_of_consumer_eligibility():
    from stratbox.core.runtime.capabilities import CapabilityRequirement, ProviderBinding
    provider = object()
    first = ProviderBinding("provider", CapabilityRequirement("http", guarantees=frozenset({"destination_bound"})), "ready", provider)
    less = replace(first, capability=CapabilityRequirement("http"))
    newer = replace(first, capability=replace(first.capability, version=2))
    one = assess(spec(), context=ExecutionContext(bindings=(first,)))
    assert one.key != assess(spec(), context=ExecutionContext(bindings=(less,))).key
    assert one.key != assess(spec(), context=ExecutionContext(bindings=(newer,))).key


def test_specialized_parent_identity_has_explicit_profile_and_reference_fields():
    basis = build_work_identity("interpret", "implementation", binding_identities={
        "specialization.method": "method-edition", "specialization.profile": "profile-edition",
        "specialization.reference:regions": "regions-edition"}, schema_fingerprint="observations-schema")
    assert basis.method_fingerprint == "method-edition"
    assert basis.profile_fingerprint == "profile-edition"
    assert basis.reference_fingerprints == ("regions-edition",)


def test_encoded_equal_bytes_keep_full_calculation_method_profile_reference_evidence():
    from stratbox.shared.data.assessment import CalculationEvidence, ValueEvidence
    from stratbox.shared.data.representation import Representation
    basis = CalculationEvidence("ratio", "1", "rule-v1",
        (("numerator", ByteIdentity.of(b"number"), "release-1"),),
        "aligned", "compatible", "same_release", "Declared ratio rule.")
    evidence = ValueEvidence(frozenset({"derived"}), calculations=(basis,),
        method_fingerprints=("method-1",), profile_fingerprints=("profile-1",),
        reference_fingerprints=("reference-1",))
    first = Representation("csv", 1, "text/csv", b"value\n1\n", evidence=evidence)
    variants = (
        replace(evidence, calculations=(replace(basis, rule_fingerprint="rule-v2"),)),
        replace(evidence, method_fingerprints=("method-2",)),
        replace(evidence, profile_fingerprints=("profile-2",)),
        replace(evidence, reference_fingerprints=("reference-2",)),
    )
    one = assess(spec(), first)
    for updated in variants:
        other = replace(first, evidence=updated)
        assert first.identity == other.identity
        two = assess(spec(), other)
        assert one.key != two.key
        assert one.identity.input_evidence_fingerprints != two.identity.input_evidence_fingerprints


def test_parameters_with_same_value_and_different_evidence_cannot_share_work():
    one = assess(spec(), parameters={"basis": material("source.a")})
    two = assess(spec(), parameters={"basis": material("source.b")})
    assert one.identity.parameters_fingerprint == two.identity.parameters_fingerprint
    assert one.key != two.key
    assert one.identity.input_evidence_fingerprints != two.identity.input_evidence_fingerprints


def test_source_payload_logical_origin_remains_significant_as_a_semantic_parameter():
    from stratbox.shared.evidence import SourcePayload
    a = SourcePayload(b"equal representation", source_id="source.a")
    b = replace(a, source_id="source.b")
    assert a.identity == b.identity
    one, two = assess(spec(), parameters={"source": a}), assess(spec(), parameters={"source": b})
    assert one.key != two.key
    assert dict(one.identity.input_evidence_fingerprints)["@parameters"] != dict(two.identity.input_evidence_fingerprints)["@parameters"]
