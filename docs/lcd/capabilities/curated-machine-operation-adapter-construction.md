# LCD candidate — curated machine-operation contracts and safe invocation

**Status:** \`LCD_CANDIDATE\` for transport-neutral model/validator and fake tests; \`LCD_BLOCKED\` for a remotely deployed machine gateway, autonomously effectful operations, authentication/delegation and any chosen agent transport. All Python is \`CANDIDATE_DESIGN\` in Knowledge only, not a shipped server or source patch. **Prepared:** 2026-10-12.

**Product:** [PC-SB-001/004/005 and user goal U-06](../../what/strategy-box/commitment-census.md); admitted host remains [HOST-O1..07](../../what/strategy-box/host-deployment-commitment.md), but public tool APIs and agent autonomy are separate undecided features. **Upstream design:** [Machine operation LDD](../../ldd/capabilities/machine-operation-adapter-conformance.md) and [security LDD](../../ldd/security/scoped-authority-and-privacy-vectors.md). **Current:** at pinned Windows SHA \`959e9c4ce1441124af5111c1e025041714e04d3b\`, \`OperationSpec\` has ID, handler reference, boolean enabled/dangerous and AI-visibility metadata; a local \`OperationRegistry\` enumerates three registered operations, and an application Scenario registry derives atomic scenarios and one conditional two-step composite. These names/flags are **catalog data**, not an authenticated machine interface or remotely enforced policy.

The key boundary is **one curated and versioned logical operation definition**, never automatic reflection of every function/class exported from analytic \`stratbox\`. A transport-facing machine model requests a known operation. The execution binding is resolved only by trusted host/application code, independent of a model-supplied handler name. Input and output domain meaning comes from the same core method used by a direct notebook and a Windows Scenario; permissions, audience, batching and serialisation belong to the separate application authority.

## 1. Concrete candidate modular construction

~~~text
application_authority/capabilities/
    catalog.py       curated approved operation identity and input/output profile
    schema.py        structured input validation, revision and strict fields
    binding.py       trusted operation ID → known executable factory/adapter
    invoke.py        machine request gate and host Run submission
    result_view.py   bounded typed response, DatasetRef and missingness
    decisions.py     map denial/version/source/unknown-effect reasons safely
    policy.py        delegated actor and effect authorization bridge
client_adapters/
    machine_port.py  contract/transport adapter if one is actually adopted
tests/capabilities/
    test_no_reflection_and_disabled_helpers.py
    test_unknown_field_and_dangerous_effect.py
    test_direct_core_domain_equivalence.py
    test_dataset_ref_and_permissioned_page.py
    test_binding_revision_and_revocation.py
~~~

\`stratbox\` remains an importable domain calculation library without any such application package. Physical location of \`application_authority\` is undecided; an Android or Web client does not need a Python interpreter merely to consume a serialized authorized operation result.

## 2. Candidate Python construction — identifiers, policy, results

~~~python
# application_authority/capabilities/catalog.py -- DOCUMENTATION ONLY
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol

class Availability(str, Enum):
    ENABLED = "enabled"
    BLOCKED_POLICY = "blocked_policy"
    UNAVAILABLE_BINDING = "unavailable_binding"
    UNSUPPORTED_REVISION = "unsupported_revision"

class DomainQuality(str, Enum):
    VALID = "valid"
    PARTIAL = "partial"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class OperationDefinition:
    operation_id: str
    contract_revision: str
    title: str
    input_schema_ref: str
    result_schema_ref: str
    effect_class: str
    allow_machine_discovery: bool
    default_visibility: str

@dataclass(frozen=True, slots=True)
class MachineInvocation:
    intention_key: str
    operation_id: str
    contract_revision: str
    params: Mapping[str, object]
    # Caller identity and resource scope are supplied by trusted host auth,
    # not by this potentially untrusted transport request.

@dataclass(frozen=True, slots=True)
class DatasetRef:
    dataset_id: str
    version: str
    metadata_ref: str
    # no absolute host filesystem path or unbounded DataFrame in response

@dataclass(frozen=True, slots=True)
class MachineDomainResult:
    quality: DomainQuality
    safe_summary: str
    small_values: Mapping[str, object]
    dataset: DatasetRef | None
    used_source_refs: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

class AdmissionStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"           # no application Run was admitted
    OUTCOME_UNKNOWN = "outcome_unknown"  # admission may have succeeded

@dataclass(frozen=True, slots=True)
class MachineAdmission:
    run_ref: str | None
    status: AdmissionStatus
    safe_code: str

    @property
    def accepted(self) -> bool:
        return self.status is AdmissionStatus.ACCEPTED

class CuratedCatalogPort(Protocol):
    def get_approved(self, operation_id: str,
                     contract_revision: str) -> OperationDefinition | None: ...
    def list_authorized(self, principal_ref: str
                        ) -> tuple[OperationDefinition, ...]: ...

class SchemaValidatorPort(Protocol):
    def validate_strict(self, schema_ref: str,
                        supplied: Mapping[str, object]) -> Mapping[str, object]: ...

class TrustedBindingPort(Protocol):
    def is_available(self, operation_id: str, contract_revision: str) -> bool: ...

class MachinePolicyPort(Protocol):
    def may_invoke(self, trusted_principal_ref: str,
                   definition: OperationDefinition,
                   params: Mapping[str, object]) -> bool: ...

class ApplicationInvocationPort(Protocol):
    def admit(self, trusted_principal_ref: str, request: MachineInvocation,
              normalized_params: Mapping[str, object]) -> MachineAdmission: ...
~~~

**Producer correction:** transport inputs must not carry the authoritative caller/resource scope. The gateway obtains those from a trusted authenticated request context. The illustrated test uses a copied immutable request instead of mutating the `Mapping` field of a frozen request record. A real implementation must also freeze or hash validated parameters before admission to avoid mutable-input races.

**Approval boundary:** actual descriptor titles and choices do not grant authority; \`dangerous\` and \`ai_visibility\` metadata in the existing Windows model are not a policy engine. A client-supplied \`caller_scope\` or \`handler\` field must never override a trusted actor identity or provider binding.

## 3. Concrete bounded invocation and discovery — CANDIDATE_DESIGN

~~~python
# application_authority/capabilities/invoke.py -- CANDIDATE_DESIGN
class MachineGateway:
    def __init__(self, catalog: CuratedCatalogPort,
                 schema: SchemaValidatorPort, bindings: TrustedBindingPort,
                 policy: MachinePolicyPort, application: ApplicationInvocationPort):
        self.catalog, self.schema, self.bindings = catalog, schema, bindings
        self.policy, self.application = policy, application

    def discover(self, trusted_actor: str) -> tuple[OperationDefinition, ...]:
        # Authority filters candidate descriptions; display is not execution grant.
        return self.catalog.list_authorized(trusted_actor)

    def invoke(self, trusted_actor: str,
               request: MachineInvocation) -> MachineAdmission:
        definition = self.catalog.get_approved(
            request.operation_id, request.contract_revision)
        if definition is None:
            return MachineAdmission(None, AdmissionStatus.REJECTED, "OPERATION_UNKNOWN_OR_REVISION")
        if not definition.allow_machine_discovery:
            return MachineAdmission(None, AdmissionStatus.REJECTED, "MACHINE_CALL_UNSUPPORTED")
        # Reject unknown parameters, invalid types and unsafe path/reference
        # fields at a trusted schema boundary before any business effect.
        try:
            normalized = self.schema.validate_strict(
                definition.input_schema_ref, request.params)
        except Exception:
            return MachineAdmission(None, AdmissionStatus.REJECTED, "PARAMETER_SCHEMA_INVALID")
        if not self.bindings.is_available(
                definition.operation_id, definition.contract_revision):
            return MachineAdmission(None, AdmissionStatus.REJECTED, "OPERATION_BINDING_UNAVAILABLE")
        if not self.policy.may_invoke(trusted_actor, definition, normalized):
            return MachineAdmission(None, AdmissionStatus.REJECTED, "EFFECT_PERMISSION_DENIED")
        # A lost admission acknowledgement cannot be reclassified as a
        # rejected/no-Run command. Keep the original intention key stable for
        # host-side reconciliation; never synthesize a new retry key here.
        try:
            admission = self.application.admit(trusted_actor, request, normalized)
        except Exception:
            return MachineAdmission(None, AdmissionStatus.OUTCOME_UNKNOWN,
                                    "HOST_ADMISSION_ACK_UNCERTAIN")
        if not isinstance(admission, MachineAdmission):
            return MachineAdmission(None, AdmissionStatus.OUTCOME_UNKNOWN,
                                    "HOST_ADMISSION_PAYLOAD_INVALID")
        if not isinstance(admission.status, AdmissionStatus):
            return MachineAdmission(None, AdmissionStatus.OUTCOME_UNKNOWN,
                                    "HOST_ADMISSION_CONTRACT_INVALID")
        if (admission.status is AdmissionStatus.ACCEPTED
                and not admission.run_ref):
            return MachineAdmission(None, AdmissionStatus.OUTCOME_UNKNOWN,
                                    "ACCEPTED_RUN_REF_MISSING")
        if (admission.status is AdmissionStatus.REJECTED
                and admission.run_ref):
            return MachineAdmission(admission.run_ref,
                                    AdmissionStatus.OUTCOME_UNKNOWN,
                                    "DENIED_WITH_RUN_REF_CONFLICT")
        return admission
~~~

**Original Research qualification:** the dated machine-interface study distinguished *rejected with no admitted Run*, *accepted/pending* and *unknown whether admission/effects happened* (§10.1, and T13–T16). A single `accepted: bool` in the first LCD sketch erased that third truth. This candidate replaces it with `AdmissionStatus` and treats a thrown host admission call, an accepted response without a Run reference, or contradictory/invalid port output as **OUTCOME_UNKNOWN**, not an invitation to retry under a new identity. The host remains responsible for same-intention-key idempotency, digest conflicts, actual grants and effect receipts; this gateway does not establish exactly-once effects. `MachineInvocation.intention_key` and normalized parameter snapshots must be qualified/bound at the actual trusted admission port, not merely passed through untrusted client metadata.

This is a transport-neutral **adapter to host application authority**, not an independent JobManager. Approval and effect-time resource checks remain with [security LCD](../security/host-effect-authorization-construction.md); admission/replay with [host LCD](../hosting/host-authority-and-client-contract-construction.md). An in-process direct Python domain call has no machine gateway requirement.

**Outcome truth:** a returned \`MachineAdmission.accepted=True\` means only the host accepted a logical invocation; it is not a successful domain calculation, published Artifact or final external effect. The result adapter must preserve domain quality, actual missingness, diagnostics and input provenance with a typed bounded response. If a DataFrame is large, return authorized \`DatasetRef\` with a separate paged read, schema and object grant; never place raw source spreadsheets or arbitrary host file paths into an untrusted model prompt.

## 4. Risks and readiness boundaries

- **Model-supplied executable path:** refuse any \`handler\` or arbitrary module/function reference; trusted catalog/version resolves the actual callable. No Python introspection-based auto-publication.
- **Hidden helper or disabled operation:** helper existence in a module does not make it a machine capability. Version and enabled/binding states are checked when invoked, not assumed from stale discovery.
- **Data-grounded prompt injection:** text inside a downloaded bank report is ordinary untrusted data. It cannot grant a machine request to delete, transmit or overwrite files.
- **Session revocation:** reconnect and late invocation repeat resource/effect authorization at the authority; cached discoverability never substitutes for rights.
- **Uncertain effect:** timeout after an external mutation may have happened; host owns \`OUTCOME_UNKNOWN\` and controlled reconciliation before retry, not the agent.
- **Version selection:** operation ID without contract revision may be ambiguous. A schema revision should not silently change statistical method meaning.
- **Transport:** any selected wire format must be a versioned mapping of this *semantic* model with actual authentication; no specific agent protocol, server endpoint or AppDock gateway is accepted here.

## 5. Proposed negative and equivalence stubs — UNEXECUTED

~~~python
def test_unregistered_helper_cannot_be_discovered(gateway, actor):
    assert "unapproved.helper" not in {
        op.operation_id for op in gateway.discover(actor)}

def test_client_handler_reference_is_not_accepted(gateway, request):
    from dataclasses import replace
    unsafe = replace(request, params={**request.params,
                                       "handler": "arbitrary.module:call"})
    response = gateway.invoke("trusted-actor", unsafe)
    assert response.safe_code == "PARAMETER_SCHEMA_INVALID"

def test_same_source_core_result_equivalence(direct_core, gateway, frozen_input):
    direct = direct_core(frozen_input)
    via_host = gateway_run_to_terminal(gateway, frozen_input)
    assert equivalent_domain_values_and_provenance(direct, via_host)

def test_machine_delegation_revoked_after_discovery(gateway, actor, request):
    gateway.discover(actor)
    revoke_grant(actor)
    assert not gateway.invoke(actor, request).accepted

def test_large_result_never_serializes_full_dataframe(projector, large_data):
    result = projector.for_machine(large_data)
    assert result.dataset is not None
    assert len(str(result.small_values)) < 4096

def test_lost_host_admission_ack_cannot_be_reported_as_rejected(gateway, host):
    host.raise_after_admission = True
    response = gateway.invoke("trusted-actor", approved_request)
    assert response.status is AdmissionStatus.OUTCOME_UNKNOWN
    assert not response.accepted

def test_null_or_untyped_admission_receipt_remains_unknown(gateway, host):
    host.admission = None
    response = gateway.invoke("trusted-actor", approved_request)
    assert response.status is AdmissionStatus.OUTCOME_UNKNOWN

def test_accepted_without_run_ref_remains_unknown(gateway, host):
    host.admission = MachineAdmission(None, AdmissionStatus.ACCEPTED, "ACCEPTED")
    response = gateway.invoke("trusted-actor", approved_request)
    assert response.status is AdmissionStatus.OUTCOME_UNKNOWN

def test_unknown_effect_never_automatically_resubmitted_with_new_identity(host):
    outcome = host.simulate_lost_effect_ack()
    assert outcome.requires_reconciliation()
~~~

No fixtures exist in production; these are falsifiable proposed tests anchored to [MAC-01..25](../../ldd/capabilities/machine-operation-adapter-conformance.md). Real domain equivalence requires a shared frozen actual source snapshot and independent statistical assessment. Authenticated remote machine conformance requires real host, session, permission and transport tests. Pure parser or fixture success must not be presented as an installed machine gateway.

## 6. Decisions, freedom and handoff

| Decision or mechanism | Classification and owner |
| --- | --- |
| Analytical core remains directly callable without machine adapter | FIXED boundary, core owner |
| Curated operation ID/version, input validation and trusted binding | LCD_CANDIDATE, app/catalog owner |
| No implicit machine authority from discoverability or \`ai_visibility\` metadata | FIXED protective rule for remote target, security owner |
| Exact tool schema version, DatasetRef resolver, pagination and result serialization | LCD_BLOCKED until real consumer and source domain selected |
| Authentication, machine delegation, effect permissions, autonomous approval, audit/retention | LCD_BLOCKED, Product/Security/operations |
| MCP/A2A/other wire adapter or platform gateway | LCD_BLOCKED, not an adopted external runtime |
| Minor internal Python filenames/type spelling | BOUNDED to semantic and security conformance, developer |
| Independent machine and direct-core parity testing | UNEXECUTED, separate capable verifier |

**Readiness:** \`LCD_CANDIDATE\` for building a restricted fake gateway and typed semantic comparison; \`LCD_BLOCKED\` for running any external machine agent against actual user data or mutations. Future real protocols and selected source/domain capabilities may demand a materially different adapter. This document does not change product source, add a provider implementation or close the global Research-to-Science obligation.
