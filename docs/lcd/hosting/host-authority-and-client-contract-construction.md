# LCD candidate — host authority and client attachment construction

**Grade:** LCD_BLOCKED for a deployable host; coherent CANDIDATE_DESIGN software structure for future decisions. Prepared 2026-10-12. **Scope:** the already admitted logical host and the two planned Web/domain and Windows/AppDock host-client profiles (PD-SB-HOST-2026-10-12-01). **Current comparison:** stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b is a local foreground application, not this host. This is documentation-only, not product source or an API promise.

**Semantic owners:** [admitted Host WHAT](../../what/strategy-box/host-deployment-commitment.md), [Hosting HOW](../../how/hosting/host-and-client-deployment.md), [application allocation](../../architecture/application-authority-placement.md), and [51 host fault vectors](../../ldd/hosting/host-client-attachment-boundary.md). The analytical core remains independent. Browser, Windows and future Android are consumers of the host authority; AppDock owns external installation/node/session lifecycle, not Strategy Box analytical truth.

## 1. Concrete responsibility split and physical alternatives

The host owns accepted Run identity, effect accounting, authoritative current state, scoped observation and publication receipts; a client owns input/navigation and audience-permitted projections. Losing a client connection does not terminate an independently running host. Losing the host may leave external effects uncertain. Two concurrently active hosts must not become writers to the same namespace without separately verified fencing.

The logical application authority can later be placed in a shared package, an existing host-bearing distribution or a new stratbox-application repository. None is selected. Likewise no HTTP URL, IPC scheme, database, executor, AppDock manifest, authentication scheme or client stack is selected. The Windows/AppDock host and a distinct connecting Windows installation must be distinguished and tested; Web host reachability and browser authentication are another actual delivery profile.

Proposed module map (CANDIDATE_DESIGN, not checked-in source):

~~~text
application_authority/
  contracts.py           identity, submission, snapshots, outcomes
  admission.py           typed intent validation and atomic logical admit
  authorization.py       principal/object/effect authorization port
  execution.py           core operation adapter, Run and Attempt truth
  observations.py        scoped snapshot, cursor gap, permission changes
  artifacts.py           verified bytes and authorized fetch
  recovery.py            reconcile dispatch and uncertain external effects
  ports.py               ledger, policy, artifact store, execution scheduler
host_adapters/
  web_transport.py       reviewed browser-facing binding (technology open)
  windows_attachment.py  verified Windows/AppDock attachment binding
client_contracts/
  host_client.py          common semantics, transport-specific projection
~~~

This is a *semantic* architecture. Different language clients require an explicit schema/IDL and generated or manually maintained mapping, never an assumption that Python source is the network protocol.

## 2. Candidate typed contracts and ports

~~~python
# CANDIDATE_DESIGN: application_authority/contracts.py
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol

class AdmissionKind(str, Enum):
    ACCEPTED = "accepted"
    REPLAY = "replay"
    REJECTED = "rejected"
    OUTCOME_UNKNOWN = "outcome_unknown"

class RunPhase(str, Enum):
    ADMITTED = "admitted"
    RUNNING = "running"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    TERMINAL = "terminal"

class RunOutcome(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    CANCELLED = "cancelled"
    OUTCOME_UNKNOWN = "outcome_unknown"

class ArtifactAvailability(str, Enum):
    VERIFIED_AVAILABLE = "verified_available"
    STAGED = "staged"
    MISSING_CONFIRMED = "missing_confirmed"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    CHANGED = "changed"
    OUTCOME_UNKNOWN = "outcome_unknown"
    DENIED = "denied"

@dataclass(frozen=True, slots=True)
class Actor:
    principal_ref: str
    session_ref: str
    scope_ref: str  # resolved from verified auth context, never a trusted client string

@dataclass(frozen=True, slots=True)
class HostIdentity:
    host_id: str
    contract_major: int
    contract_minor: int
    capabilities: frozenset[str]

@dataclass(frozen=True, slots=True)
class Submission:
    intention_key: str
    scenario_id: str
    definition_revision: str
    parameters: Mapping[str, object]  # sensitivity classified before transport
    payload_digest: str  # canonical semantic request, not arbitrary JSON hash

@dataclass(frozen=True, slots=True)
class AdmissionReceipt:
    kind: AdmissionKind
    intention_key: str
    run_ref: str | None
    host_id: str
    safe_reason: str | None = None

class DispatchRecoveryKind(str, Enum):
    NO_PENDING = "no_pending"
    DISPATCH_CONFIRMED = "dispatch_confirmed"
    DISPATCH_UNKNOWN = "dispatch_unknown"
    MALFORMED_CLAIM = "malformed_claim"

@dataclass(frozen=True, slots=True)
class DispatchClaim:
    dispatch_ref: str
    run_ref: str
    worker_ref: str
    fence_epoch: int

@dataclass(frozen=True, slots=True)
class DispatchRecoveryReceipt:
    kind: DispatchRecoveryKind
    run_ref: str | None
    safe_code: str

@dataclass(frozen=True, slots=True)
class RunSnapshot:
    run_ref: str
    revision: int
    phase: RunPhase
    outcome: RunOutcome | None
    last_sequence: int
    stale: bool = False

@dataclass(frozen=True, slots=True)
class Observation:
    run_ref: str
    event_ref: str          # opaque, scoped visible-event identifier, not node_seq
    revision: int
    safe_code: str
    safe_text: str

@dataclass(frozen=True, slots=True)
class ObservationPage:
    run_ref: str
    feed_generation: str   # authorization-aware projection revision
    next_cursor: str | None  # opaque token, never raw internal sequence
    observations: tuple[Observation, ...]
    resync_required: bool = False

@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    artifact_id: str
    version: str

@dataclass(frozen=True, slots=True)
class InternalArtifactRecord:
    availability: ArtifactAvailability
    content_digest: str | None
    media_type: str | None
    host_handle: str | None  # restricted storage capability; host-side ONLY

@dataclass(frozen=True, slots=True)
class ArtifactResult:
    # This is safe metadata only; no backend handle, host path or bearer URL.
    availability: ArtifactAvailability
    content_digest: str | None
    media_type: str | None

# CANDIDATE_DESIGN: application_authority/ports.py
class CanonicalSubmissionPort(Protocol):
    def seal(self, actor: Actor, untrusted: Submission) -> Submission:
        """Trusted server-side schema, scope, effect and parameter normalization.

        The returned payload_digest is server-computed from the complete
        admitted actor/scope/definition/parameters semantics. The returned
        parameters must be an immutable validated snapshot.
        """
        ...

class PolicyPort(Protocol):
    def can_submit(self, actor: Actor, request: Submission) -> bool: ...
    def can_read_run(self, actor: Actor, run_ref: str) -> bool: ...
    def can_fetch(self, actor: Actor, artifact: ArtifactIdentity) -> bool: ...

class LedgerPort(Protocol):
    def admit_atomically(self, actor: Actor, request: Submission,
                         host: HostIdentity) -> AdmissionReceipt: ...
    def transition(self, run_ref: str, expected_revision: int,
                   phase: RunPhase, outcome: RunOutcome | None) -> RunSnapshot: ...
    def get(self, run_ref: str) -> RunSnapshot | None: ...
    def read_after(self, run_ref: str, sequence: int) -> tuple[Observation, ...]: ...

class AuthorizedFeedPort(Protocol):
    def read_authorized(self, actor: Actor, run_ref: str,
                        cursor: str | None) -> ObservationPage:
        """Owned by trusted host, not by client serialization.

        Must reauthorize every permitted event AND field at the current ACL
        revision, validate/redact schema at the server, and return an opaque
        principal+scope+generation-bound cursor. On revocation, cursor expiry,
        or retention gap return an explicit RESYNC_REQUIRED projection.
        Never return unfiltered ledger rows or expose internal node sequence.
        """
        ...

class ExecutionSchedulerPort(Protocol):
    # Volatile first-attempt signal; absence or lost ACK does not remove the
    # transactional ledger-owned dispatch intent.
    def schedule(self, run_ref: str) -> None: ...

class DurableDispatchPort(Protocol):
    """The *same* durable admission transaction must append pending dispatch.

    Actual leases/fencing, reclaim and retention are storage-owner obligations.
    Every claimed delivery is rechecked against the admitted Run generation.
    """
    def claim_next(self, worker_ref: str) -> DispatchClaim | None: ...
    def mark_dispatched(self, claim: DispatchClaim) -> None: ...
    def mark_uncertain(self, claim: DispatchClaim, safe_code: str) -> None: ...

class IdempotentDispatchPort(Protocol):
    def schedule_once(self, claim: DispatchClaim) -> bool:
        """True only for a durable reservation for this same dispatch_ref.

        Retries and lease takeovers MUST resolve to the same logical Job
        reservation. Returning True is not an effect/Run completion receipt.
        """
        ...

class ArtifactRepositoryPort(Protocol):
    # Returns host-private implementation handle to this service only.
    def resolve_verified(self, artifact: ArtifactIdentity
                         ) -> InternalArtifactRecord: ...

class HostApplicationPort(Protocol):
    def identify(self, actor: Actor) -> HostIdentity: ...
    def submit(self, actor: Actor, request: Submission) -> AdmissionReceipt: ...
    def read_run(self, actor: Actor, run_ref: str) -> RunSnapshot: ...
    def observe(self, actor: Actor, run_ref: str,
                after_cursor: str | None) -> ObservationPage: ...
    def fetch(self, actor: Actor, artifact: ArtifactIdentity) -> ArtifactResult: ...
~~~

**Ownership:** the ledger owns durable logical admission *if durability is selected and proved*; the scheduler owns a technical reservation or attempt, never the meaning of a completed business result. Every access method enforces server-side actor and object policy. The actor is supplied by an actual authentication adapter, not from the untrusted submitted JSON. A host identity / major version is not proof of access, readiness or health.

## 3. Candidate admission and after-acceptance gap

~~~python
# CANDIDATE_DESIGN: application_authority/admission.py
class HostAdmission:
    def __init__(self, host: HostIdentity, policy: PolicyPort,
                 ledger: LedgerPort, scheduler: ExecutionSchedulerPort,
                 canonicalizer: CanonicalSubmissionPort):
        self.host, self.policy = host, policy
        self.ledger, self.scheduler = ledger, scheduler
        self.canonicalizer = canonicalizer

    def submit(self, actor: Actor, request: Submission) -> AdmissionReceipt:
        try:
            qualified = self.canonicalizer.seal(actor, request)
        except Exception:
            # Definitive pre-ledger validation failure for this submission.
            return AdmissionReceipt(AdmissionKind.REJECTED,
                                    request.intention_key, None,
                                    self.host.host_id, "REQUEST_QUALIFICATION_FAILED")
        if (not isinstance(qualified, Submission)
                or qualified.intention_key != request.intention_key
                or not qualified.intention_key
                or not qualified.payload_digest):
            return AdmissionReceipt(AdmissionKind.REJECTED,
                                    request.intention_key, None,
                                    self.host.host_id, "REQUEST_QUALIFICATION_INVALID")
        try:
            permitted = self.policy.can_submit(actor, qualified)
        except Exception:
            # A permission-service failure cannot certify a historical Run
            # is absent, especially when this key was admitted previously.
            return AdmissionReceipt(AdmissionKind.OUTCOME_UNKNOWN,
                                    request.intention_key, None,
                                    self.host.host_id, "POLICY_STATUS_UNCERTAIN")
        if permitted is not True:
            if permitted is not False:
                return AdmissionReceipt(AdmissionKind.OUTCOME_UNKNOWN,
                                        request.intention_key, None,
                                        self.host.host_id, "POLICY_RESULT_UNTYPED")
            return AdmissionReceipt(AdmissionKind.REJECTED,
                                    request.intention_key, None,
                                    self.host.host_id, "ACCESS_DENIED")
        # Ledger receives ONLY the qualified, server-digested request,
        # never the untrusted client's caller-asserted payload digest.
        try:
            receipt = self.ledger.admit_atomically(actor, qualified, self.host)
        except Exception:
            # The ledger could have committed Run admission and lost its ACK.
            # Returning REJECTED (or allowing a new intention_key) would lie.
            return AdmissionReceipt(AdmissionKind.OUTCOME_UNKNOWN,
                                    request.intention_key, None,
                                    self.host.host_id, "LEDGER_ADMISSION_UNCERTAIN")
        if (not isinstance(receipt, AdmissionReceipt)
                or not isinstance(receipt.kind, AdmissionKind)
                or receipt.intention_key != request.intention_key
                or receipt.host_id != self.host.host_id):
            return AdmissionReceipt(AdmissionKind.OUTCOME_UNKNOWN,
                                    request.intention_key, None,
                                    self.host.host_id, "ADMISSION_RECEIPT_CONTRACT_INVALID")
        if ((receipt.kind in (AdmissionKind.ACCEPTED, AdmissionKind.REPLAY)
                 and not receipt.run_ref)
                or (receipt.kind is AdmissionKind.REJECTED and receipt.run_ref)):
            return AdmissionReceipt(AdmissionKind.OUTCOME_UNKNOWN,
                                    request.intention_key, receipt.run_ref,
                                    self.host.host_id, "ADMISSION_RUN_REF_CONFLICT")
        if receipt.kind is not AdmissionKind.ACCEPTED:
            return receipt
        try:
            self.scheduler.schedule(receipt.run_ref)
        except Exception:
            # Never create a second Run or invent rollback after admitted work.
            return AdmissionReceipt(AdmissionKind.OUTCOME_UNKNOWN,
                                    request.intention_key, receipt.run_ref,
                                    self.host.host_id, "DISPATCH_UNCERTAIN")
        return receipt
~~~

**Source-first T05 anti-spoofing correction (candidate logic only):** a transport-supplied `Submission.payload_digest` is merely a caller claim. Earlier candidate admission forwarded it straight into the ledger, so a malicious or buggy consumer could change scenario parameters under the same key and repeat the same claimed digest. The Host construction now **requires** a `CanonicalSubmissionPort` in its constructor. Before policy evaluation and ledger access, this trusted port validates the actual operation/definition/parameters/scope and supplies an immutable normalized request with a **server-calculated semantic digest**. The ledger sees that qualified request only; a qualifier that raises or changes the original intention identity is rejected pre-ledger. This is still a typed port *obligation*, not a canonical JSON algorithm or identity-verification implementation. The true canonicalization, sensitive fields, dynamic default resolution, principal binding, parser versions and actor/session authentication are `LCD_BLOCKED` until the actual host owner implements and tests them. The source's same-key/different-payload conflict contract cannot be certified by trusting an input `payload_digest`.

**Source-first ledger acknowledgment correction (Research Topic 12):** an earlier `HostAdmission.submit` guarded scheduler dispatch but allowed `LedgerPort.admit_atomically` exceptions to escape before returning a qualified admission result. If the ledger committed and its response was lost, a caller might infer "never admitted" from the exception and re-submit under a new intention key. The updated candidate treats an exception from ledger admission as **`OUTCOME_UNKNOWN` without inventing a Run ref**; a replay with the same trusted intention identity must reconcile against the authoritative ledger. It also checks typed returned receipt, exact intention/host identity, and accepted/replayed Run identity before scheduling. Provider-policy failures remain uncertain, while an explicit policy denial is a genuine pre-ledger rejection for **this attempt**, not proof an older Run with the same key never existed. The ledger still owns durable idempotency, canonical digest collision detection, signed/principal scoped identity, conflict handling and actual dispatch-outbox atomicity: these are not proven by a response dataclass. The mechanism is supported by the source's separation of `accepted`, `started` and `UNKNOWN`, not an accepted release decision.

**Explicit availability countercase (producer-executed, unresolved):** after a ledger *durably* accepts Run `R`, a lost admission ACK prevents the above code from calling `scheduler.schedule(R)`. Repeating the original request with its original key can return a correct `REPLAY(R)` without dispatching the admitted Job. This is **safe against duplicate submission but not live against stranded work**. The bounded fake-port test now asserts that scheduler dispatch remains absent in exactly this case. A future real host must have a durable outbox, ledger-backed dispatch scanner, or another demonstrably crash-recoverable mechanism binding accepted Runs to executable Jobs; define idempotent dispatcher pickup, effect intent, ownership/fencing and incident handling. Calling `schedule` blindly on every replay would simply move the fault into duplicate execution. The test proves a **blocking unsatisfied condition**, not a delivered recovery feature.

**STOP BEFORE PRODUCTION:** atomic logical admission and schedule dispatch are two operations in this illustrative method. They need an approved transactional outbox or equivalent persistent recovery/lease mechanism. Only after storage, crash lifetime, receipt and retention requirements are decided can they form one implementable invariant. Stable idempotency scope, client intention-key window, parameter canonicalization, hash, version conflicts and conflict/error grammar also require Product/security approval. A lost response must be reconciled using the *same* intention key. A second new-key submit may cause a second external effect.

### Durable dispatch recovery candidate — after Run admission, before worker effects

The admission method's fast-path `scheduler.schedule(run_ref)` is **merely a volatile acceleration**. Recovery must not rely on its successful return. The real `LedgerPort.admit_atomically()` must commit **both** the accepted logical Run and a uniquely keyed pending dispatch intent in one proven transaction. A replay or lost admission ACK therefore cannot create a stranded Run with no durable dispatch record. The *queued job* is a separate, idempotently reserved physical execution identity, not a new Run or effect. The candidate below is intentionally a tiny one-claim recovery worker; the approved storage implementation must supply fencing/lease expiry and durable handoff to a scheduler that deduplicates `dispatch_ref` even after its own ACK loss.

~~~python
# CANDIDATE_DESIGN: application_authority/dispatch_recovery.py
class HostDispatchRecovery:
    def __init__(self, ledger: DurableDispatchPort,
                 scheduler: IdempotentDispatchPort):
        self.ledger, self.scheduler = ledger, scheduler

    def run_once(self, worker_ref: str) -> DispatchRecoveryReceipt:
        try:
            claim = self.ledger.claim_next(worker_ref)
        except Exception:
            return DispatchRecoveryReceipt(DispatchRecoveryKind.DISPATCH_UNKNOWN,
                                           None, "DISPATCH_LEDGER_UNAVAILABLE")
        if claim is None:
            return DispatchRecoveryReceipt(DispatchRecoveryKind.NO_PENDING,
                                           None, "NO_PENDING_DISPATCH")
        if (not isinstance(claim, DispatchClaim)
                or not claim.dispatch_ref or not claim.run_ref
                or claim.worker_ref != worker_ref
                or type(claim.fence_epoch) is not int or claim.fence_epoch < 1):
            return DispatchRecoveryReceipt(DispatchRecoveryKind.MALFORMED_CLAIM,
                                           None, "DISPATCH_CLAIM_INVALID")
        # If scheduler ACK is lost after a durable Job reservation, retry
        # must use THIS SAME dispatch_ref. It must not start a new Run.
        try:
            acknowledged = self.scheduler.schedule_once(claim)
        except Exception:
            self._uncertain(claim, "DISPATCH_SCHEDULER_ACK_UNCERTAIN")
            return DispatchRecoveryReceipt(DispatchRecoveryKind.DISPATCH_UNKNOWN,
                                           claim.run_ref, "DISPATCH_SCHEDULER_ACK_UNCERTAIN")
        if acknowledged is not True:
            self._uncertain(claim, "DISPATCH_RESERVATION_UNCONFIRMED")
            return DispatchRecoveryReceipt(DispatchRecoveryKind.DISPATCH_UNKNOWN,
                                           claim.run_ref, "DISPATCH_RESERVATION_UNCONFIRMED")
        try:
            # Must be conditional on the fenced claim, never on run_ref alone.
            self.ledger.mark_dispatched(claim)
        except Exception:
            return DispatchRecoveryReceipt(DispatchRecoveryKind.DISPATCH_UNKNOWN,
                                           claim.run_ref, "DISPATCH_LEDGER_ACK_UNCERTAIN")
        return DispatchRecoveryReceipt(DispatchRecoveryKind.DISPATCH_CONFIRMED,
                                       claim.run_ref, "JOB_RESERVATION_CONFIRMED")

    def _uncertain(self, claim: DispatchClaim, reason: str) -> None:
        try:
            self.ledger.mark_uncertain(claim, reason)
        except Exception:
            # No fabricated success; the claim remains subject to recovery
            # by the real durable ledger after lease expiry.
            pass
~~~

**Exact recovery obligation, not satisfied by fake tests:** a claim returned by `claim_next` must refer to an **actual pending durable outbox row created with Run admission**; lease loss must permit reclamation without simultaneous unfenced reservations; `mark_dispatched` must check `dispatch_ref` and `fence_epoch`; `schedule_once` must atomically reserve one logical Job for that dispatch identity even when it loses its response. A `True` response proves a Job reservation only, never that an Attempt ran, an external effect happened, output bytes were published or the analytic result was accepted. On grant/policy revocation before the work begins, the actual executor must revalidate applicable authority; a durable dispatch intent is **not** a standing permission for file mutation. A backend with no transaction tying Run and outbox, and no deduplication/fence at the scheduler, cannot claim recoverable hosted admission. It may choose a simpler proven single-worker profile, rather than pretend a distributed lease exists.

**Producer fake counterexample repaired at the *candidate* contract level:** the prior acknowledged bad path committed Run R, lost ledger ACK, returned `REPLAY(R)` on identical request and never called the volatile scheduler. The newly specified recovery worker can pick that existing outbox dispatch independently, reserve Job R exactly once and mark dispatch acknowledged, provided the fake ledger and scheduler both implement the required semantics. Actual process crash, database transaction, host reconnection and physical effect conformance remain unexecuted.

## 4. Scope-checked observation and bytes

~~~python
# CANDIDATE_DESIGN: application_authority/observations.py
class ScopedReads:
    def __init__(self, policy: PolicyPort, ledger: LedgerPort,
                 artifacts: ArtifactRepositoryPort, feed: AuthorizedFeedPort):
        self.policy, self.ledger, self.artifacts, self.feed = (
            policy, ledger, artifacts, feed)

    def read_run(self, actor: Actor, run_ref: str) -> RunSnapshot:
        try:
            permitted = self.policy.can_read_run(actor, run_ref)
        except Exception:
            # Availability of the policy service is not a grant.
            raise PermissionError("RUN_ACCESS_UNCONFIRMED") from None
        if permitted is not True:
            raise PermissionError("RUN_ACCESS_DENIED")
        snapshot = self.ledger.get(run_ref)
        if snapshot is None:
            raise LookupError("RUN_UNAVAILABLE")
        if not isinstance(snapshot, RunSnapshot):
            raise RuntimeError("RUN_SNAPSHOT_CONTRACT_INVALID")
        return snapshot

    def observe(self, actor: Actor, run_ref: str,
                after_cursor: str | None) -> ObservationPage:
        self.read_run(actor, run_ref)  # current object policy precheck
        if (after_cursor is not None
                and (type(after_cursor) is not str or not after_cursor)):
            raise ValueError("INVALID_AUTHORIZED_CURSOR")
        try:
            page = self.feed.read_authorized(actor, run_ref, after_cursor)
        except PermissionError:
            raise PermissionError("RUN_ACCESS_DENIED") from None
        except Exception:
            raise RuntimeError("AUTHORIZED_FEED_UNAVAILABLE") from None
        if (not isinstance(page, ObservationPage)
                or page.run_ref != run_ref
                or type(page.feed_generation) is not str
                or not page.feed_generation
                or (page.next_cursor is not None
                    and (type(page.next_cursor) is not str
                         or not page.next_cursor))
                or type(page.resync_required) is not bool
                or type(page.observations) is not tuple
                or any(not isinstance(item, Observation)
                       or item.run_ref != run_ref
                       or type(item.event_ref) is not str
                       or not item.event_ref
                       or type(item.safe_code) is not str
                       or type(item.safe_text) is not str
                       for item in page.observations)
                or (page.resync_required and page.observations)):
            raise RuntimeError("AUTHORIZED_FEED_CONTRACT_INVALID")
        # Exact ACL and safe-field qualification remains inside a trusted
        # AuthorizedFeedPort. This wrapper cannot authenticate the issuer
        # or certify privacy solely from typed return values.
        return page

    def fetch(self, actor: Actor, ref: ArtifactIdentity) -> ArtifactResult:
        # This candidate fetch is a safe metadata *inspection*, not a bytes
        # stream. Permission must be checked AGAIN before real byte-open.
        try:
            permitted = self.policy.can_fetch(actor, ref)
        except Exception:
            return ArtifactResult(ArtifactAvailability.DENIED, None, None)
        if permitted is not True:
            return ArtifactResult(ArtifactAvailability.DENIED, None, None)
        try:
            internal = self.artifacts.resolve_verified(ref)
        except Exception:
            # Storage read failure is not proof the file was deleted.
            return ArtifactResult(ArtifactAvailability.BACKEND_UNAVAILABLE,
                                  None, None)
        if (not isinstance(internal, InternalArtifactRecord)
                or not isinstance(internal.availability, ArtifactAvailability)):
            return ArtifactResult(ArtifactAvailability.OUTCOME_UNKNOWN,
                                  None, None)
        if internal.availability is ArtifactAvailability.VERIFIED_AVAILABLE:
            # The backend handle is never projected, including in errors.
            if (not internal.host_handle or not internal.content_digest
                    or not internal.media_type):
                return ArtifactResult(ArtifactAvailability.OUTCOME_UNKNOWN,
                                      None, None)
            return ArtifactResult(ArtifactAvailability.VERIFIED_AVAILABLE,
                                  internal.content_digest, internal.media_type)
        return ArtifactResult(internal.availability, None, None)
~~~

**Source-first authorized feed correction (Topic 05, §9.2–9.4):** the earlier candidate performed `can_read_run(actor, run_ref)` once using Python truthiness, then returned `LedgerPort.read_after(run_ref, after:int)` **directly** to a client. A policy implementation returning `"false"` or `1` could be mistaken for explicit allow; ledger rows could include raw `safe_text` from the current Windows source, and an integer cursor could disclose hidden node-wide activity or remain valid after ACL revocation. The replacement requires literal Boolean `True` at each Run read, surfaces policy outages as scoped access uncertainty, and routes every event-page fetch to a **trusted, object- and field-authorizing `AuthorizedFeedPort`**. It returns an `ObservationPage` with opaque actor-bound cursor and feed-generation, and `RESYNC_REQUIRED` without unfiltered events when authority/retention changes. A port that merely casts raw ledger records into an `Observation` dataclass, or labels a global event sequence “opaque”, **does not** implement this contract. Cursor authentication/expiry, field-sensitivity classification, safe text schema, per-event ACL, atomic snapshot/subscribe and user revocation during streaming are physical host/security implementation gates; their absence keeps this LCD `BLOCKED`. These are candidate semantics and source-derived security challenges, not a published remote feed endpoint or actual privacy proof.

**Source-first artifact projection correction (Topics 04/05/12):** the first typed `ArtifactResult` included a `host_handle` field and was *also the return value of a client-facing transport*. Even where that handle was described as opaque, passing it through the client DTO risked exposing an internal storage capability/path or suggesting that it was itself a valid download grant. The code now separates host-private `InternalArtifactRecord` from **client-safe metadata-only** `ArtifactResult`; no storage handle ever leaves `ScopedReads.fetch`. The intentionally renamed availability cases distinguish confirmed missing bytes, backend outage, changed version, unknown effect, staged bytes and permission denial. A broken backend response or a claimed verified record missing digest/media/host handle returns `OUTCOME_UNKNOWN` rather than false `VERIFIED_AVAILABLE`. Physical bytes still require an **additional authorized streaming/open operation**, proper generation and digest verification, scope-limited headers and current access recheck. This code is **NOT a deployed or security-certified download endpoint** and a dataclass/typed status is not sufficient evidence of issuer/backend authenticity.

A client cannot turn a local absolute filesystem path into a remote accessible URL. A published Artifact needs a byte-verified record and separate access check at download time; technical logs are a different scope. Permission revocation during a stream requires reauthorization and stream termination. A stale cursor or missing event range must return a qualified resnapshot path, never imply continuous observation. On network loss, the client marks its state stale without changing the host-owned Run status.

## 5. Candidate native-client attachment port

~~~python
# CANDIDATE_DESIGN: client_contracts/host_client.py
class ClientTransport(Protocol):
    def negotiate(self) -> HostIdentity: ...
    def submit(self, request: Submission) -> AdmissionReceipt: ...
    def snapshot(self, run_ref: str) -> RunSnapshot: ...
    def observations(self, run_ref: str, cursor: str | None) -> ObservationPage: ...
    def artifact(self, ref: ArtifactIdentity) -> ArtifactResult: ...

class AttachedClient:
    def __init__(self, transport: ClientTransport, supported_major: int):
        self.transport, self.supported_major = transport, supported_major
        self.host: HostIdentity | None = None

    def attach(self) -> HostIdentity:
        identity = self.transport.negotiate()
        if identity.contract_major != self.supported_major:
            raise RuntimeError("HOST_VERSION_INCOMPATIBLE")
        self.host = identity
        return identity

    def refresh(self, run_ref: str) -> RunSnapshot:
        if self.host is None:
            raise RuntimeError("NOT_ATTACHED")
        return self.transport.snapshot(run_ref)
~~~

This client port is a testable abstraction, not an adopted browser or Windows remote protocol. Exact transport/session security, browser origin/CSRF protection, TLS, replay and upload limits, native credentials, AppDock deployment capability and certificate lifecycle are blocked choices. The host and client must be installed on distinct Windows managed installations to prove the intended HOST-O3, not merely two widgets reading one shared directory.

## 6. Negative conformance stubs — PROPOSED, never executed

Additional target fixture: persist a Run in a durable ledger, drop the **admission ACK**, then call `HostAdmission.submit` using the same intention key/digest. The first response is `OUTCOME_UNKNOWN` with no fabricated Run ID; authoritative lookup should return the original admitted Run on retry. A response with changed intention key, host identity, contradictory REJECTED+run_ref or ACCEPTED without Run ref must not be accepted or scheduled as success. Test this on the actual host ledger/outbox separately from producer synthetic ports.



~~~python
def test_duplicate_intention_replays_one_run(fake_host, actor, submit):
    a = fake_host.submit(actor, submit)
    b = fake_host.submit(actor, submit)
    assert a.run_ref == b.run_ref
    assert b.kind is AdmissionKind.REPLAY

def test_digest_change_under_same_key_is_rejected(fake_host, actor, submit):
    changed = with_changed_digest(submit)
    assert fake_host.submit(actor, changed).kind is AdmissionKind.REJECTED

def test_cross_principal_run_is_not_visible(fake_host, unauthorized, run_ref):
    with raises(PermissionError):
        fake_host.read_run(unauthorized, run_ref)

def test_missing_bytes_are_not_published(fake_host, actor, stale_artifact_ref):
    r = fake_host.fetch(actor, stale_artifact_ref)
    assert r.availability is ArtifactAvailability.UNAVAILABLE

def test_client_disconnect_does_not_terminate_host_run(fake_host, client, run_ref):
    before = fake_host.read_run(client.actor, run_ref)
    client.disconnect()
    assert fake_host.read_run(client.actor, run_ref).revision == before.revision

def test_unfenced_second_writer_is_rejected(two_hosts_same_namespace):
    assert two_hosts_same_namespace.second_writer_denied()

def test_revocation_blocks_new_stream_page(fake_host, revoked_actor, run_ref):
    with raises(PermissionError):
        fake_host.observe(revoked_actor, run_ref, after=5)
~~~

These are *abstract test scaffolds*, requiring fixture implementations. They do not prove live security, network behavior, Web reachability, crash recovery, Windows/AppDock attachment or Android parity. The [HC-01..51 LDD cases](../../ldd/hosting/host-client-attachment-boundary.md) remain separate, all target conformance UNEXECUTED without dated actual test runs. Cold-implementer and independent security/architecture challenges remain OPEN.

## 7. Blocker/freedom register and cold handoff

| Decision | Grade | Required owner/evidence |
| --- | --- | --- |
| Planned logical host, Windows/Web profiles and independent analytical core | FIXED product direction and responsibility | HOST-O1..O7; no host built |
| Client-local view cannot own host Run/effect/Artifact truth | FIXED semantic boundary | Architecture and authorization checks |
| Client transport and language toolkits | BOUNDED only after common wire/auth schema | Client implementers and interoperability suite |
| Physical stratbox-application package/repository, host executable and Windows role packaging | BLOCKED_ON_AUTHORITY_OR_EVIDENCE | Product + maintainers; comparative deployment |
| Host authentication, principal/scope/ACL, session revocation, browser threat model | BLOCKED_ON_AUTHORITY_OR_EVIDENCE | Product/security/operations |
| Transactional admission, idempotency horizon, durable dispatch, Run/Attempt/event retention and crash repair | BLOCKED_ON_AUTHORITY_OR_EVIDENCE | Product reliability policy and real storage tests |
| AppDock host/attach capabilities, manifests, system permissions | BLOCKED_ON_EXTERNAL_CONTRACT | Verified supported external version; integration owner |
| Hosted cancellation, effect retry and concurrent jobs | BLOCKED_ON_AUTHORITY_OR_EVIDENCE | Product and effect-risk owner |
| Local class names and private source layout | DELEGATED_NONMATERIAL once semantic contracts pass | Implementer |
| Observed host runtime and independent handoff | NOT EXECUTED | Separate deploy/test reviewers |

**Readiness:** LCD_BLOCKED for implementation of a deployed host. It is reasonable to implement a fake ledger/policy/client harness from this candidate to expose missing decisions; doing so does not authorize production service creation under the present Commission. A cold implementer must first obtain the Product and platform decisions, exact authoritative requirements, native environment and independent conformance plan.

**Science/evidence limits:** these candidate skeletons do not change the frozen source census, close the independent Research Amputation, prove any available remote endpoint or certify live Artifact retention. Reopen on Product/hosting/security decisions, real second client, tested external platform integration, selected deployment technology or contradiction in fresh direct implementation.
