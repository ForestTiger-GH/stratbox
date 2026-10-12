# LCD candidate — causal execution evidence, local logs and optional Problem reporting

**Grade:** LCD_CANDIDATE for in-process local diagnostic evidence separation; LCD_BLOCKED for durable host-wide events, multiuser incident sharing and external Problem-recording guarantees. **Prepared:** 2026-10-12. Every Python fragment is CANDIDATE_DESIGN, never production source or an executed test.

**Evidence and upstream owners:** [causal Science](../../science/execution-and-diagnostics/causal-observability-and-failure-truth.md), [operations HOW](../../how/operations/diagnosis-and-recovery.md), [OBS-01..28 LDD](../../ldd/observability/execution-truth-and-recovery-vectors.md), [external Problem/evidence LDD](../../ldd/observability/host-problem-receipts-and-evidence-degradation.md), [Windows Current HOW](../../current-how/windows-application.md), [host WHAT](../../what/strategy-box/host-deployment-commitment.md), [local Scenario LCD](../application/local-scenario-execution-construction.md). The pinned current implementation is stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b.

## 1. Corrected source truth and implementation boundary

Current Windows operation execution creates local FileHandlers named from case, step and operation, exposes unreviewed exception text on some result paths, provides Qt signals for one active Scenario and stores five independent recent JSON collections. These are real local application pieces, not a proven durable multiuser execution journal or external incident service.

The proposed design preserves **six separate evidence planes**, each with a different authority and failure policy: (a) analytic/domain result and validation evidence, (b) application Run/Step/Attempt authority, (c) lossy progress UI frames, (d) restricted physical technical logs, (e) internal problem/impact classification and acknowledged external problem occurrence, (f) platform node/session readiness. An external recorder's candidate reference after a lost reply is NOT a confirmed ProblemRef. A host-wide shared Condition requires actual affected-resource scope and authorization; one user input mistake is not evidence that everyone's environment is broken.

A successful computation may survive the failure of an **optional** log writer, while a separately approved *mandatory audit* can block a privileged effect **before** execution. Both policies cannot be reduced to the same Boolean success or generic exception. On process shutdown, a missing self-log is not proof of a clean exit; early bootstrap capture and platform crash evidence are separately conditional.

## 2. Proposed concrete package/source construction

~~~text
application/diagnostics/
  contracts.py          typed evidence plane, audience and delivery classes
  safe_events.py        safe bounded projection, Run/Attempt causality
  attempt_logs.py       unique physical Attempt log, access/retention boundary
  problem_bridge.py     map a verified optional external recorder result
  evidence_health.py    independent telemetry loss state
  impact_conditions.py  optional resource and audience-scoped warning
  diagnosis.py          read-only recovery classification, never unapproved repair
adapters/
  native_attempt_log.py     real native log writer with correct file lifecycle
  external_problem_port.py  only when actual external contract is present
tests/
  test_unknown_problem_ack.py
  test_optional_telemetry_failure.py
  test_attempt_log_collision.py
  test_redaction_and_log_grants.py
  test_recovery_without_effect_receipt.py
~~~

Do not place UI, AppDock or host-specific implementation in the standalone analytical stratbox core. A neutral domain ProgressSink/DiagnosticSink may be introduced into a particular analytic use case only with a real consumer. The source paths above are conditional proposed placement, not created production modules.

## 3. Concrete Python records and ports — CANDIDATE_DESIGN

~~~python
# application/diagnostics/contracts.py -- DOCUMENTATION ONLY
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

class EvidencePlane(str, Enum):
    DOMAIN = "domain"
    EXECUTION = "execution"
    PROGRESS = "progress"
    TECHNICAL_LOG = "technical_log"
    LOCAL_PROBLEM = "local_problem"
    EXTERNAL_PROBLEM = "external_problem"
    PLATFORM_HEALTH = "platform_health"

class Audience(str, Enum):
    USER_SAFE = "user_safe"
    SHARED_SAFE = "shared_safe"
    OPERATOR_RESTRICTED = "operator_restricted"
    FORENSIC = "forensic"

class RegistrationKind(str, Enum):
    ACKNOWLEDGED = "acknowledged"
    NOT_WRITTEN = "not_written"
    OUTCOME_UNKNOWN = "outcome_unknown"
    UNAVAILABLE = "unavailable"

class EvidenceHealth(str, Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

@dataclass(frozen=True, slots=True)
class CausalReference:
    run_ref: str
    step_ref: str | None
    attempt_ref: str | None

@dataclass(frozen=True, slots=True)
class DiagnosticFinding:
    safe_code: str
    safe_summary: str
    source: EvidencePlane
    scope_ref: str
    audience: Audience
    cause: CausalReference | None
    occurred_at_utc: str

@dataclass(frozen=True, slots=True)
class ProgressFrame:
    run_ref: str
    attempt_ref: str
    stage_code: str
    completed: int | None
    total: int | None
    unit: str | None
    observed_at_utc: str

@dataclass(frozen=True, slots=True)
class TechnicalLogRef:
    log_id: str
    attempt_ref: str
    restricted_locator: str   # NEVER an ordinary client path

@dataclass(frozen=True, slots=True)
class ProblemRegistration:
    kind: RegistrationKind
    correlation_key: str
    confirmed_external_ref: str | None
    safe_code: str

@dataclass(frozen=True, slots=True)
class TelemetryHealth:
    local_log: EvidenceHealth
    user_events: EvidenceHealth
    external_recorder: EvidenceHealth
    dropped_progress: int
    last_error_code: str | None

class TechnicalLogPort(Protocol):
    def open_unique(self, run_ref: str, attempt_ref: str) -> TechnicalLogRef: ...
    def append_restricted(self, ref: TechnicalLogRef, entry: str) -> None: ...
    def close(self, ref: TechnicalLogRef) -> None: ...

class SafeEventPort(Protocol):
    def send(self, finding: DiagnosticFinding) -> None: ...

class OptionalRecorderPort(Protocol):
    def record(self, finding: DiagnosticFinding,
               correlation_key: str) -> ProblemRegistration: ...

class RunAuthorityReadPort(Protocol):
    def get_effect_status(self, run_ref: str) -> str: ...

class AffectedScopePort(Protocol):
    def authorized_viewers(self, resource_ref: str) -> frozenset[str]: ...
~~~

No external enum or Python SDK signature is asserted by these proposed ports. The actual external Problem owner must verify its own version, returned acknowledgment and allowed lookup semantics. A valid user Case does not automatically authorize a technical log or forensic disclosure.

## 4. Problem/evidence handling skeleton — CANDIDATE_DESIGN

~~~python
# application/diagnostics/problem_bridge.py -- CANDIDATE_DESIGN
class OptionalProblemBridge:
    def __init__(self, *, port: OptionalRecorderPort | None):
        self.port = port

    def record(self, finding: DiagnosticFinding,
               correlation_key: str) -> ProblemRegistration:
        if finding.audience is Audience.FORENSIC:
            raise ValueError("FORENSIC_RECORD_REJECTED")
        if self.port is None:
            return ProblemRegistration(RegistrationKind.UNAVAILABLE,
                                       correlation_key, None,
                                       "EXTERNAL_RECORDER_UNAVAILABLE")
        try:
            result = self.port.record(finding, correlation_key)
        except Exception:
            # The external recorder MAY have written the occurrence before ACK loss.
            return ProblemRegistration(RegistrationKind.OUTCOME_UNKNOWN,
                                       correlation_key, None,
                                       "RECORDER_ACK_UNCERTAIN")
        if result.kind is RegistrationKind.ACKNOWLEDGED:
            if not result.confirmed_external_ref:
                return ProblemRegistration(RegistrationKind.OUTCOME_UNKNOWN,
                                           correlation_key, None,
                                           "RECORDER_ACK_WITHOUT_REF")
            return result
        # A candidate reference is never a confirmed one after a failure.
        return ProblemRegistration(result.kind, correlation_key, None,
                                   result.safe_code)

# application/diagnostics/evidence_health.py -- CANDIDATE_DESIGN
class ObservabilityProjection:
    def __init__(self, *, safe_events: SafeEventPort,
                 external: OptionalProblemBridge):
        self.safe_events, self.external = safe_events, external

    def publish_optional(self, run_outcome: str,
                         finding: DiagnosticFinding) -> TelemetryHealth:
        # run_outcome comes from the Run authority and MUST remain unchanged.
        event_health = EvidenceHealth.AVAILABLE
        try:
            self.safe_events.send(finding)
        except Exception:
            event_health = EvidenceHealth.DEGRADED
        registration = self.external.record(finding, finding.safe_code)
        recorder_health = (EvidenceHealth.AVAILABLE
                           if registration.kind is RegistrationKind.ACKNOWLEDGED
                           else EvidenceHealth.DEGRADED)
        return TelemetryHealth(EvidenceHealth.AVAILABLE, event_health,
                               recorder_health, 0, None)
~~~

The sketch intentionally does not claim actual local log health without a tested log adapter. The real implementation must report failed log close/write, quota, overflow and dropped telemetry; it must not overwrite terminal Run/effect evidence when an optional sink fails. If mandatory audit is admitted for a destructive action, a separate admission gate checks that required evidence can be committed **before** allowing that effect.

An unconfirmed external Problem response stays OUTCOME_UNKNOWN; retry is permitted only with a confirmed versioned lookup/idempotency contract. A shared warning condition must check actual resource impact and viewer authorization. A candidate ProblemRef, local log path and timestamp cannot be promoted into an external acknowledged record by mapping alone.

## 5. Recovery, concurrency and audience guards

- Use unique Attempt identity for log filenames and avoid collision between retries or concurrent Runs; ensure handler close in every operation path including workspace early return.
- Maintain ordered Run events under an actual local/host authority. Frontend Qt signal arrival order, client clock timestamps and observer reconnections cannot certify causal history.
- Throttle progress frames, not admitted Run/Step/effect terminal facts. A bounded queue can drop progress if drop counts and stale observation are honest.
- If technical logs cannot be written, keep a separate evidence-health indicator, restricted crash minimum and explicit operational diagnosis. An optional logger outage does not negate an already validated bank calculation.
- Public messages and machine results are safe-code projections. Raw exception text, credentials, private paths and technical stack traces remain out of shared history.
- A deleted published workbook produces a later availability observation, not deletion of the historical terminal result.
- Diagnosis is read-only. Repair, cleanup, journal replay and destructive retry are independently authorized actions, not a continuation of a passive diagnose call.
- Host Run authority loss or an unknown external effect requires reconciliation. A failed recent JSON projection may not silently become a new authoritative empty team history.

## 6. Concrete negative tests — PROPOSED, not executed

~~~python
def test_optional_event_loss_does_not_change_run_outcome(faulty_safe_events, run):
    old = run.authoritative_status
    faulty_safe_events.fail_next()
    diagnostic_projection.publish_optional(old, safe_failure)
    assert run.authoritative_status == old

def test_lost_external_ack_yields_unknown_without_confirmed_ref(bridge):
    bridge.port.raise_after_commit()
    result = bridge.record(safe_failure, "stable-intent")
    assert result.kind is RegistrationKind.OUTCOME_UNKNOWN
    assert result.confirmed_external_ref is None

def test_distinct_attempts_get_distinct_physical_logs(log_factory):
    a = log_factory.open_unique("run", "attempt-1")
    b = log_factory.open_unique("run", "attempt-2")
    assert a.restricted_locator != b.restricted_locator

def test_unsafe_error_details_never_reach_shared_feed(safe_projector):
    text = safe_projector.from_exception(
        RuntimeError("TOKEN_SENTINEL C:/private/path"))
    assert "TOKEN_SENTINEL" not in text
    assert "C:/private/path" not in text

def test_one_user_parameter_error_does_not_create_nodewide_condition(conditions):
    assert conditions.classify("BAD_USER_PARAMETER").shared is False

def test_unknown_effect_requires_reconciliation(recovery, run):
    assert recovery.classify(run.with_lost_effect_ack()) == "RECONCILE_REQUIRED"

def test_log_access_checked_independently_of_case_read_rights(auth, log_ref):
    assert auth.can_read_case("viewer", "run")
    assert not auth.can_read_raw_log("viewer", log_ref)
~~~

The examples are fixture scaffolds, not runnable production tests or proof that an external recorder exists. A real review must exercise the relevant [OBS-01..28](../../ldd/observability/execution-truth-and-recovery-vectors.md) and [external Problem LDD](../../ldd/observability/host-problem-receipts-and-evidence-degradation.md) at a pinned, actually installed profile. True independence of review from the producer remains OPEN.

## 7. Decision closure / cold implementer handoff

| Material choice | Classification | Owner/evidence |
| --- | --- | --- |
| Distinct domain result, Run effect truth, telemetry, log, Problem, Condition and platform readiness | FIXED semantic boundary | Current HOW, Science and Target HOW |
| Stable Attempt log identity, redacted safe event boundary | Candidate local safety invariant | Windows application/security owner and negative tests |
| Progress coalescing, in-memory safe event projection and internal helper layout | BOUNDED or DELEGATED_NONMATERIAL | App implementer after consumer established |
| Host journal, authorization, listener, shared Condition and cursor semantics | BLOCKED_ON_AUTHORITY_OR_EVIDENCE | Product/security/operations |
| Actual external recorder availability, lookup/idempotency and mapping | BLOCKED_ON_EXTERNAL_CONTRACT | Verified versioned platform and integration owner |
| Mandatory audit policy, forensic rights, retention/quota, crash evidence | BLOCKED_ON_AUTHORITY_OR_EVIDENCE | Security/Product/operations |
| Real runtime tests, native permissions and external registration faults | UNEXECUTED | Distinct verifier and installed environment |

**Conclusion:** LCD_CANDIDATE local; LCD_BLOCKED hosted and regulated profile. Proposed ports identify what to implement and how to test the boundary but cannot establish durable multiuser host logs or secure cross-user notifications by declaration. Source-to-Science and full Knowledge assurance statuses remain unchanged.
