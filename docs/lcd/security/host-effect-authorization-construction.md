# LCD candidate — scoped host command, object and effect authorization

**Status:** `LCD_BLOCKED` for any deployed remote/shared security policy; `LCD_CANDIDATE` for a restricted fake-port/conformance construction. **Scope:** admitted host outcome `HOST-O6`, distinct application-host authority for Web/domain and Windows/AppDock host-client arrangements; no actual IAM provider, grant schema, HTTP endpoint, executable module or release is selected. **Authored:** 2026-10-12. All Python in this document is `CANDIDATE_DESIGN` within Knowledge only.

**Upstream contract:** [admitted host WHAT](../../what/strategy-box/host-deployment-commitment.md), [architecture allocation](../../architecture/responsibility-allocation.md), [host HOW](../../how/hosting/host-and-client-deployment.md), [security LDD with SEC-01..30](../../ldd/security/scoped-authority-and-privacy-vectors.md), [machine-adapter LDD](../../ldd/capabilities/machine-operation-adapter-conformance.md) and [host application LCD](../hosting/host-authority-and-client-contract-construction.md). This is a target design, not an assertion that the pinned local Windows client already authenticates remote users.

## 1. Consumer, threat and scope distinction

A connected Windows/client or browser may display permitted information but must never become the policy authority for *submission, read, mutation or download*. One identity may have multiple sessions; labels are display hints, not credentials. An AI or automated actor may have a delegator, but its effective permission ceiling is an independent verified grant. An operation's appearance in a catalog does not grant the ability to run it. A previous plan approval does not by itself prove permission at the instant an irreversible file effect occurs.

The initial `stratbox` Python API remains directly callable from a notebook according to its OS/process capabilities. This LCD does not invent a universal ACL in the analytical library or require an AppDock runtime to import a banking method. A future application host can provide *additional trusted policy enforcement* at its own effect boundary.

Security policy, enrollment and authentication provider remain **Product/Security Decisions**. The mechanisms below are only sufficient for a **fake-authority reference test**. They are not a deployable password/session/tenant implementation.

## 2. Proposed small package seam

~~~text
application_authority/security/
    contracts.py       trusted identity, operation/resource/action scope
    identity.py        external-auth result to application principal binding
    policy_port.py     query actual grant/revocation and authorization authority
    plan_guard.py      immutable plan, revision and target-set digest check
    admission.py       effect policy before scheduling/Run admission
    effect_guard.py    revalidate before mutation and bind effect receipt
    projection.py      classify fields and enforce audience-safe output
    artifact_access.py authorized metadata/bytes boundary, not filesystem path
    audit_port.py      conditional mandatory privileged-action audit interface
tests/security/
    test_two_same_labels_different_principals.py
    test_machine_delegation_ceiling.py
    test_revocation_between_approve_and_apply.py
    test_plan_changed_after_approval.py
    test_private_artifact_id_enumeration.py
    test_safe_machine_and_shared_projections.py
~~~

These are **logical** modules. Physical placement inside a Windows host package or possible shared application repository is unresolved. The same host semantic policy is needed for both accepted deployment profiles, but their credential and transport adapters may differ.

## 3. Typed request, decision and effect envelope — CANDIDATE_DESIGN

~~~python
# application_authority/security/contracts.py -- DOC-ONLY, candidate
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol

class EffectClass(str, Enum):
    READ = "read"
    COMPUTE = "compute"
    CREATE = "create"
    OVERWRITE = "overwrite"
    DELETE = "delete"
    EXPORT = "export"
    REMOTE_SEND = "remote_send"

class AuthOutcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    POLICY_UNAVAILABLE = "policy_unavailable"
    CURRENT_STATE_CHANGED = "current_state_changed"

class DecisionPhase(str, Enum):
    DISCOVER = "discover"
    ADMIT = "admit"
    APPROVE = "approve"
    EFFECT = "effect"
    FETCH = "fetch"

@dataclass(frozen=True, slots=True)
class Principal:
    principal_ref: str
    session_ref: str
    host_scope: str
    actor_kind: str          # human | delegated_machine | service; not identity proof
    delegation_ref: str | None

@dataclass(frozen=True, slots=True)
class ResourceKey:
    namespace: str
    object_ref: str         # resolved by host, never blindly concatenated path
    revision: str | None

@dataclass(frozen=True, slots=True)
class ActionRequest:
    operation_id: str
    operation_revision: str
    effect_class: EffectClass
    resource: ResourceKey
    parameter_digest: str  # stable canonical digest of admission-relevant fields
    intent_key: str

@dataclass(frozen=True, slots=True)
class ApprovalScope:
    approval_ref: str
    request_digest: str
    target_set_digest: str
    actor_ref: str
    expiry_utc: str
    policy_revision: str

@dataclass(frozen=True, slots=True)
class AuthDecision:
    outcome: AuthOutcome
    reason_code: str
    policy_revision: str | None
    checked_resource_revision: str | None
    receipt_ref: str | None

class AuthContextPort(Protocol):
    def resolve_authenticated_principal(self, transport_identity: object
                                        ) -> Principal: ...

class PolicyPort(Protocol):
    def evaluate(self, principal: Principal, request: ActionRequest,
                 *, phase: DecisionPhase) -> AuthDecision: ...

class ApprovalPort(Protocol):
    def verify_bound_scope(self, principal: Principal, request: ActionRequest,
                           approval_ref: str, current_target_set_digest: str
                           ) -> ApprovalScope | None: ...

class ResourceVersionPort(Protocol):
    def current_revision(self, resource: ResourceKey) -> str | None: ...

class EffectReceiptPort(Protocol):
    def record_before_effect(self, principal: Principal, request: ActionRequest,
                             decision: AuthDecision) -> str: ...
    def record_after_effect(self, intent_ref: str, observed_outcome: str) -> None: ...
~~~

**Serialization status:** none of the enum spellings or Python dataclasses is an approved public wire schema. Host-provided principal and policy records may use different concrete types, but must preserve these distinctions. The current program has no Product Decision specifying retention of grants, cryptographic digest representation or approval deadlines.

## 4. Effect guard and explicitly named race — CANDIDATE_DESIGN

~~~python
# application_authority/security/effect_guard.py -- DOC-ONLY
class EffectGuard:
    def __init__(self, policy: PolicyPort, approvals: ApprovalPort,
                 versions: ResourceVersionPort, receipts: EffectReceiptPort):
        self.policy, self.approvals = policy, approvals
        self.versions, self.receipts = versions, receipts

    def authorize_before_effect(
        self, actor: Principal, request: ActionRequest,
        *, approval_ref: str | None, target_set_digest: str
    ) -> str:
        # Host, not UI or model, derives actor from authenticated session.
        decision = self.policy.evaluate(actor, request, phase=DecisionPhase.EFFECT)
        if decision.outcome is not AuthOutcome.ALLOW:
            raise PermissionError("EFFECT_POLICY_DENIED_OR_UNAVAILABLE")
        destructive = request.effect_class in (
            EffectClass.DELETE, EffectClass.OVERWRITE)
        # An exact destructive plan requires a known target generation:
        # otherwise the guard could approve deleting *anything currently*
        # at an old display path under an unversioned request.
        if destructive and request.resource.revision is None:
            raise PermissionError("DESTRUCTIVE_TARGET_REVISION_REQUIRED")
        actual_version = self.versions.current_revision(request.resource)
        if (request.resource.revision is not None
                and actual_version != request.resource.revision):
            raise RuntimeError("RESOURCE_REVISION_CHANGED")
        if destructive:
            if approval_ref is None or not target_set_digest:
                raise PermissionError("APPROVAL_AND_TARGET_PROOF_REQUIRED")
            approval = self.approvals.verify_bound_scope(
                actor, request, approval_ref, target_set_digest)
            if (approval is None
                    or approval.actor_ref != actor.principal_ref
                    or approval.request_digest != request.parameter_digest
                    or approval.target_set_digest != target_set_digest
                    or decision.policy_revision is None
                    or approval.policy_revision != decision.policy_revision):
                raise PermissionError("STALE_OR_INVALID_APPROVAL")
        # Source of authority must record an effect intent and policy proof before
        # the actual mutation, subject to the accepted audit/durability tier.
        return self.receipts.record_before_effect(actor, request, decision)

    def record_effect_result(self, intent_ref: str, outcome: str) -> None:
        self.receipts.record_after_effect(intent_ref, outcome)
~~~

**Original-source producer correction:** `SB-SRC-0558` §§6.1–6.5, 7.4 and the corresponding SEC-09/SEC-10 vectors require approval of the **particular principal, plan and target revision**. The previous draft guarded revision equality only when the caller happened to provide a revision, allowing an apparent approved DELETE/OVERWRITE with `revision=None`. It also relied on the approval port alone for verifying actor, target-set and policy-generation binding despite an `ApprovalScope` explicitly carrying those fields. The bounded guard now refuses destructive requests with missing target revision/target-set digest and cross-checks principal, parameter/plan, target-set and policy revision *after* trusted port verification. These are **necessary fake-port guards**, not sufficient security enforcement or a release-grade clock/ACL proof. A real approval port still must validate expiry and authenticity before returning a token. Other operation types have their own effect-specific preconditions: e.g. CREATE requires conditional no-clobber at the storage boundary, not an assumed existing revision.

**Do not copy this method into production without closing the race:** a resource can change **after** `current_revision` and before a lower-level FileStore delete/replace. The storage/effect adapter must enforce conditional mutation against the same resource generation or hold a valid exclusivity/fencing mechanism. Policy/grant revocation after `evaluate` is also material: choose a bounded policy snapshot/lease or recheck at actual commit, then test that contract. If no safe compare-and-effect primitive exists, do not offer a strong guarantee.

Approval is an explicit plan/target-set actor-scoped record. Reuse after plan change, permission revocation, or target mutation must fail. A low-level core cleanup method may remain callable directly by a trusted Python notebook, but a host must not accept arbitrary raw DataFrame action rows as authorization.

**Effect uncertainty:** after `record_before_effect`, a timeout or worker crash may leave unknown actual effects. The ledger must preserve intent and reconcile against a receipt before authorizing retry; exception does not imply no write. If privileged audit is an accepted admission precondition, an unavailable writer blocks effect admission *before* mutation; optional debug logging remains independent.

## 5. Reader and machine projection boundary — CANDIDATE_DESIGN

~~~python
# application_authority/security/projection.py -- DOC-ONLY
class FieldVisibility(str, Enum):
    SHARED_SAFE = "shared_safe"
    OWNER_ONLY = "owner_only"
    OPERATOR_ONLY = "operator_only"
    SECRET_NEVER_EXPORT = "secret_never_export"

@dataclass(frozen=True, slots=True)
class ClassifiedField:
    name: str
    value: object
    visibility: FieldVisibility

class AudienceProjection:
    def __init__(self, policy: PolicyPort):
        self.policy = policy

    def select(self, actor: Principal, resource: ResourceKey,
               fields: tuple[ClassifiedField, ...]) -> dict[str, object]:
        req = ActionRequest(
            operation_id="application.record.read", operation_revision="candidate",
            effect_class=EffectClass.READ, resource=resource,
            parameter_digest="", intent_key="")
        decision = self.policy.evaluate(actor, req, phase=DecisionPhase.FETCH)
        if decision.outcome is not AuthOutcome.ALLOW:
            raise PermissionError("OBJECT_ACCESS_DENIED")
        # Actual field grant policy needed; this conservative candidate exposes
        # shared-safe only and never exports raw exception, path or secrets.
        return {field.name: field.value for field in fields
                if field.visibility is FieldVisibility.SHARED_SAFE}
~~~

A future audience-specific field grant is a separate policy projection, not the raw storage record. Knowing an Artifact ID or seeing a Case card does not authorize reading bytes, technical logs, source URLs with embedded credentials or another participant's private parameters. Server must enforce access at **every read**, including pagination, reconnect and artifact download. Revoked grants require new filtered snapshots rather than reusing stale client event cursors.

A machine-facing catalog lists only curated operation descriptors; it resolves a trusted handler server-side, validates schema and checks delegated effect permissions. Exposing a broad Python function through reflection or trusting a model-supplied handler path is out of scope.

## 6. Proposed attack and cross-surface tests — UNEXECUTED

~~~python
def test_identical_display_names_do_not_conflate_principals(auth, two_users):
    assert auth.resolve(two_users[0]).principal_ref != auth.resolve(two_users[1]).principal_ref

def test_machine_scope_cannot_exceed_delegator(effect_guard, machine_actor):
    with raises(PermissionError):
        effect_guard.authorize_before_effect(machine_actor, restricted_delete,
                                             approval_ref=None, target_set_digest="t")

def test_resource_changed_after_plan_invalidates_approval(effect_guard, updated_root):
    with raises(RuntimeError):
        effect_guard.authorize_before_effect(human, old_plan_request,
                                             approval_ref="a", target_set_digest="old")

def test_revocation_at_effect_time_denies(effect_guard, revoked):
    with raises(PermissionError):
        effect_guard.authorize_before_effect(revoked, delete_request,
                                             approval_ref="old", target_set_digest="t")

def test_protected_artifact_id_is_not_an_access_grant(host, outsider, private_id):
    assert host.try_metadata(outsider, private_id).is_denied_or_hidden
    assert host.try_download(outsider, private_id).is_denied_or_hidden

def test_shared_projection_never_copies_raw_sensitive_fields(projection, actor, record):
    safe = projection.select(actor, record.resource, record.fields)
    assert "secret" not in safe
    assert "traceback" not in safe

def test_repeated_changed_plan_cannot_reuse_approval(host, old_approval, new_digest):
    assert host.apply_with_approval(old_approval, new_digest).is_rejected
~~~

Run the full [SEC-01..30](../../ldd/security/scoped-authority-and-privacy-vectors.md) relevant profile vectors, combined with the [MAC series](../../ldd/capabilities/machine-operation-adapter-conformance.md). Fakes can catch identity/phase confusion but **cannot** prove actual browser authentication, cryptographic delegation, filesystem path containment, user/data retention, cross-installation AppDock trust or secure production ACLs. The real deployment must be challenged by independent security specialists and native adversarial tests.

## 7. Decision and bounded-freedom register

| Concern | Design status | Actual owner |
| --- | --- | --- |
| Host checks principal/object/effect and handles reconnects honestly | FIXED target outcome per HOST-O6, deployment proof OPEN | Product/application host |
| Core independent of host/Qt and machine execution policy | FIXED boundary | Analytical core owner |
| Logical action/approval/effect intent types and ports above | LCD_CANDIDATE | Application developer; revised by Product/Security |
| Authentication method, enrollment, sessions, delegation grant and revocation | LCD_BLOCKED | Product/Security/operations |
| Shared/private field classification and support/AI visibility | LCD_BLOCKED | Product/Security/privacy |
| Resource path confinement, conditional writes, policy-effect race resolution | LCD_BLOCKED | Storage and security specialist |
| Approval TTL, digest, retention/audit and idempotency | LCD_BLOCKED | Product/Security/operations |
| Private Python source filenames and chosen programming toolkit | BOUNDED once interface invariants closed | Implementer |
| Independent hosted and machine-adapter security acceptance | UNEXECUTED | Competent separate reviewer |

**Handoff:** this LCD permits a synthetic fake-policy prototype and coherent signature-level review, but a developer **cannot responsibly deploy a host** or implement effectful production authorization from it alone. Required Decisions and real native environment evidence are named. No `LCD_READY_FOR_IMPLEMENTATION` claim or global Research conservation follows from this design.
