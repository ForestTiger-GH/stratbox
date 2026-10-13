# LCD candidate — bounded trigger evaluation, occurrence identity and Run admission

**Grade:** \`LCD_CANDIDATE\` for a bounded pure-evaluation/occurrence model and fake scheduler consumer; \`LCD_BLOCKED\` for a deployed recurrent host scheduler, misfire economics, transactionally admitted jobs and privileged autonomous effects. **Prepared:** 2026-10-12. This is \`CANDIDATE_DESIGN\` in standalone Knowledge, not working product code, an accepted general scheduler API or a mandatory automation release.

**Product authority:** existing user goals \`U-01/U-08/U-09\` under [Commitment Census](../../what/strategy-box/commitment-census.md), **not** separately accepted feature guarantees. Shared application host existence and Web/Windows-host client profiles are accepted as planned by [Host WHAT](../../what/strategy-box/host-deployment-commitment.md); the existence of a host does not decide that every kind of automation, listener, trigger or background lifetime ships. **Source-derived Science:** [trigger identity and governed execution](../../science/automation/trigger-occurrence-identity-and-governed-execution.md), [bounded AI routing](../../science/automation/bounded-agent-routing-and-evidence-safe-automation.md), [work admission and scheduling](../../science/work/admission-planning-resource-scheduling-and-recovery.md). **Engineering linkage:** [Host LCD](../hosting/host-authority-and-client-contract-construction.md), [local Scenario LCD](../application/local-scenario-execution-construction.md), [Machine catalog LCD](../capabilities/curated-machine-operation-adapter-construction.md) and [authorization LCD](../security/host-effect-authorization-construction.md).

## 1. Current reality and strongest distinctions

The pinned \`stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b\` supplies in-memory background-process descriptors/state and a foreground one-active-run Qt coordinator. It does **not** prove a durable time scheduler, event watcher, data-change detector, runner after GUI exit, server-side job recovery or multiuser delegated trigger. The analytical core stays separately usable from Python. The external managed platform may own process/Node/Session availability under a confirmed public version; **Strategy Box application authority** owns its actual Automation/Occurrence/Run semantics and effect admission. A client window cannot become the definitive clock or shared outcome recorder.

An Automation **rule** is an enduring specification. A Trigger **evaluation** is a fact of attempted inspection, which may be \`NO_CHANGE\` or \`UNAVAILABLE\`. A deduplicated **occurrence** may be recorded without any admitted Run; a **Run** is one separately authorized logical execution. A technical **Attempt** and physical **effect** follow still different identities and receipts. A **notification** to a human is not proof the Run succeeded or that a bank report is current.

## 2. Concrete bounded construction, no generic workflow engine

~~~text
Potential application_authority/automation/ logical namespace:
  contracts.py       versioned rule, trigger, occurrence, evaluation and decisions
  evaluate.py        pure due/observed/source predicate normalization
  identity.py        stable occurrence key scoped to rule revision and evidence
  policy.py          bounded overlap/misfire and priority decisions
  ledger_port.py     unique occurrence claim, admitted Run link, inspect/reconcile
  trigger_runner.py  evaluate -> claim -> explicit admission via existing host
  read_view.py       last evaluated, next due, last accepted Run (not enabled=running)
  diagnostics.py     local/host audience-safe failure and suppression evidence
tests/automation/
  test_dst_fold_and_missing_local_time.py
  test_same_occurrence_two_evaluators.py
  test_source_unknown_not_no_change.py
  test_offline_catchup_bounded.py
  test_disable_does_not_cancel_active_run.py
  test_effect_permission_revoked_at_fire.py
  test_ack_loss_and_reconciliation.py
~~~

Only one **logical** scheduler-ownership and occurrence-normalization seam is needed when this feature becomes accepted. This candidate **does not require** an AutomationStore, EventBus, database table, JobManager, separate repository and queue technology for every named concept. Persist independently only the facts whose shared recovery and effect boundaries demand it. Clock/calendar evaluation may be pure Python; the actual host storage, trigger event source, workflow engine and background deployment are separate decisions.

## 3. Types, explicit evidence and status — CANDIDATE_DESIGN

~~~python
# application_authority/automation/contracts.py -- DOCUMENTATION ONLY
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol

class TriggerKind(str, Enum):
    CIVIL_SCHEDULE = "civil_schedule"
    TRUSTED_EVENT = "trusted_event"
    SOURCE_VERSION_CHANGE = "source_version_change"
    CONDITION_WATCH = "condition_watch"
    MANUAL = "manual"

class EvaluationOutcome(str, Enum):
    OBSERVED = "observed"
    NO_CHANGE = "no_change"
    UNAVAILABLE = "unavailable"
    INVALID_EVIDENCE = "invalid_evidence"
    UNKNOWN = "unknown"

class OccurrenceDisposition(str, Enum):
    ADMISSION_REQUESTED = "admission_requested"
    REPLAY_EXISTING = "replay_existing"
    SKIPPED = "skipped"
    SUPPRESSED = "suppressed"
    NEEDS_APPROVAL = "needs_approval"
    BLOCKED = "blocked"
    UNKNOWN_ADMISSION = "unknown_admission"

class MisfirePolicy(str, Enum):
    SKIP = "skip"
    LATEST_ONLY = "latest_only"
    BOUNDED_CATCH_UP = "bounded_catch_up"
    REVIEW = "review"

class OverlapPolicy(str, Enum):
    FORBID = "forbid"
    QUEUE_ONE = "queue_one"
    COALESCE = "coalesce"
    PARALLEL_IF_PERMITTED = "parallel_if_permitted"

@dataclass(frozen=True, slots=True)
class TriggerDefinition:
    kind: TriggerKind
    revision: str
    zone_name: str | None         # IANA civil zone, never client clock default
    predicate_ref: str | None
    source_ref: str | None
    event_schema_ref: str | None

@dataclass(frozen=True, slots=True)
class AutomationDefinition:
    automation_id: str
    rule_revision: str
    owner_ref: str
    run_as_grant_ref: str | None
    scenario_id: str
    scenario_revision: str
    parameters_digest: str
    trigger: TriggerDefinition
    enabled: bool
    misfire: MisfirePolicy
    overlap: OverlapPolicy

@dataclass(frozen=True, slots=True)
class TriggerEvidence:
    evaluation_ref: str
    observed_at_utc: str
    evidence_source_ref: str
    observed_event_id: str | None
    intended_scheduled_instant_utc: str | None
    before_source_revision: str | None
    after_source_revision: str | None
    validated_change: bool | None
    safe_failure_code: str | None

@dataclass(frozen=True, slots=True)
class TriggerEvaluation:
    automation_id: str
    rule_revision: str
    outcome: EvaluationOutcome
    evidence: TriggerEvidence

@dataclass(frozen=True, slots=True)
class OccurrenceIdentity:
    automation_id: str
    rule_revision: str
    trigger_fingerprint: str   # canonical identity, not a display timestamp

@dataclass(frozen=True, slots=True)
class OccurrenceDecision:
    identity: OccurrenceIdentity | None
    disposition: OccurrenceDisposition
    run_ref: str | None
    safe_code: str

class OccurrenceLedgerPort(Protocol):
    def claim_unique(self, identity: OccurrenceIdentity,
                     evidence: TriggerEvidence) -> bool: ...
    def attach_admission(self, identity: OccurrenceIdentity,
                         run_ref: str) -> None: ...
    def find_run_ref(self, identity: OccurrenceIdentity) -> str | None: ...
    def find_confirmed_no_run_reason(self, identity: OccurrenceIdentity
                                     ) -> str | None: ...
    def record_confirmed_no_run(self, identity: OccurrenceIdentity,
                                safe_reason: str) -> None: ...

class AutomationAdmissionPort(Protocol):
    def request_run(self, rule: AutomationDefinition,
                    identity: OccurrenceIdentity,
                    evidence: TriggerEvidence) -> tuple[str | None, str]:
        """None requires an authenticated, definitive 'NO RUN ADMITTED' receipt.

        Ambiguous/lost admission evidence must raise/return a separate unknown
        classification; a null run reference alone is not authoritative.
        """
        ...

class SourceChangeVerifierPort(Protocol):
    def compare_qualified_versions(self, previous: str, current: str
                                   ) -> EvaluationOutcome: ...
~~~

The dataclasses are local candidate values, **not public wire schemas**. The material choice of hash/canonical representation, actual versioned scenario resolution and rule-authority storage is \`BLOCKED\` until the consumer and actor policy are accepted. \`parameters_digest\` alone cannot reconstruct executable parameters; the host must bind a separately protected, validated preset revision to avoid an uncontrolled mutable user form.

### Identity rules per trigger, without false universalization

- Calendar identity uses \`automation_id + rule_revision + resolved intended instant\` under accepted IANA-zone fold/gap semantics. A job run timestamp is **not** its intended calendar identity.
- Trusted event identity includes a **genuine authoritative event ID and scope**, not an arbitrary client message or approximate timestamp.
- Source version change identity binds declared source identity, previous and new **qualified** source revisions, with full validity scope. Unchanged URL/mtime is insufficient and an inaccessible source must not become \`NO_CHANGE\`.
- Condition-watch identity needs a predicate transition/debounce window, with previous observation evidence. Every poll must not produce an automatic second execution when the condition merely remains true.
- Manual trigger uses a distinct trusted actor-request identity; it must not be merged into a time occurrence unless the Product explicitly authorizes that relationship.

This model covers identities **conceptually**. It does not assert that source edition verification, predicate engine, calendar parser, event source, serializer or deduplication storage has been implemented.

## 4. Pure candidate trigger/occurrence flow — CANDIDATE_DESIGN

~~~python
# application_authority/automation/evaluate.py -- CANDIDATE_DESIGN
def source_change_evaluation(
    rule: AutomationDefinition,
    evidence: TriggerEvidence,
    verifier: SourceChangeVerifierPort,
) -> TriggerEvaluation:
    if (rule.trigger.kind is not TriggerKind.SOURCE_VERSION_CHANGE
            or evidence.before_source_revision is None
            or evidence.after_source_revision is None):
        return TriggerEvaluation(rule.automation_id, rule.rule_revision,
                                 EvaluationOutcome.UNKNOWN, evidence)
    try:
        outcome = verifier.compare_qualified_versions(
            evidence.before_source_revision, evidence.after_source_revision)
    except Exception:
        # A thrown transport/source-verification error proves neither a
        # qualified change nor qualified equality. Preserve uncertainty;
        # an outer diagnostic owner should capture a redacted cause.
        outcome = EvaluationOutcome.UNKNOWN
    if not isinstance(outcome, EvaluationOutcome):
        outcome = EvaluationOutcome.INVALID_EVIDENCE
    # Only a verified version comparison may return NO_CHANGE.
    return TriggerEvaluation(rule.automation_id, rule.rule_revision,
                             outcome, evidence)

# application_authority/automation/trigger_runner.py -- CANDIDATE_DESIGN
class TriggerOccurrenceService:
    def __init__(self, *, ledger: OccurrenceLedgerPort,
                 admit: AutomationAdmissionPort):
        self.ledger, self.admit = ledger, admit

    def handle(
        self, rule: AutomationDefinition, evaluation: TriggerEvaluation,
        identity: OccurrenceIdentity | None,
    ) -> OccurrenceDecision:
        if not rule.enabled:
            return OccurrenceDecision(identity, OccurrenceDisposition.SUPPRESSED,
                                      None, "RULE_DISABLED")
        if evaluation.automation_id != rule.automation_id:
            return OccurrenceDecision(None, OccurrenceDisposition.BLOCKED,
                                      None, "IDENTITY_MISMATCH")
        if evaluation.rule_revision != rule.rule_revision:
            return OccurrenceDecision(None, OccurrenceDisposition.BLOCKED,
                                      None, "RULE_REVISION_STALE")
        if evaluation.outcome is EvaluationOutcome.NO_CHANGE:
            return OccurrenceDecision(None, OccurrenceDisposition.SKIPPED,
                                      None, "NO_QUALIFIED_CHANGE")
        if evaluation.outcome is not EvaluationOutcome.OBSERVED:
            return OccurrenceDecision(None, OccurrenceDisposition.BLOCKED,
                                      None, "EVALUATION_UNAVAILABLE_OR_UNKNOWN")
        if identity is None:
            return OccurrenceDecision(None, OccurrenceDisposition.BLOCKED,
                                      None, "MISSING_OCCURRENCE_IDENTITY")
        if (identity.automation_id != rule.automation_id
                or identity.rule_revision != rule.rule_revision):
            return OccurrenceDecision(None, OccurrenceDisposition.BLOCKED,
                                      None, "OCCURRENCE_SCOPE_MISMATCH")
        try:
            claimed = self.ledger.claim_unique(identity, evaluation.evidence)
        except Exception:
            # A failed claim call may have committed its unique occurrence.
            # Do not submit to host until that identity is reconciled.
            return OccurrenceDecision(identity,
                OccurrenceDisposition.UNKNOWN_ADMISSION, None,
                "OCCURRENCE_CLAIM_UNCERTAIN")
        if not claimed:
            try:
                existing = self.ledger.find_run_ref(identity)
                if existing is not None:
                    return OccurrenceDecision(identity, OccurrenceDisposition.REPLAY_EXISTING,
                                              existing, "DUPLICATE_RUN_REPLAY")
                rejected = self.ledger.find_confirmed_no_run_reason(identity)
                if rejected is not None:
                    return OccurrenceDecision(identity, OccurrenceDisposition.BLOCKED,
                                              None, rejected)
            except Exception:
                # A read timeout/corrupt projection after a prior occurrence
                # claim is not permission to admit a second host Run.
                return OccurrenceDecision(identity,
                    OccurrenceDisposition.UNKNOWN_ADMISSION, None,
                    "OCCURRENCE_LOOKUP_UNCERTAIN")
            return OccurrenceDecision(identity, OccurrenceDisposition.UNKNOWN_ADMISSION,
                                      None, "DUPLICATE_OCCURRENCE_RECONCILE")
        # The host must authorize real run-as grants, scenario version,
        # required resources, external effects and current overlapping jobs.
        # This is a logical admission port, not a direct domain execution.
        try:
            accepted_ref, safe_code = self.admit.request_run(
                rule, identity, evaluation.evidence)
        except Exception:
            # After a possible host admission, an exception does not prove
            # rejection or lack of side effects. Retain occurrence ownership.
            return OccurrenceDecision(identity,
                OccurrenceDisposition.UNKNOWN_ADMISSION, None,
                "HOST_ADMISSION_ACK_UNKNOWN")
        if accepted_ref is None:
            # This branch is valid ONLY for an authenticated, definitive
            # no-run-admitted rejection; see AutomationAdmissionPort.
            try:
                self.ledger.record_confirmed_no_run(identity, safe_code)
            except Exception:
                return OccurrenceDecision(identity,
                    OccurrenceDisposition.UNKNOWN_ADMISSION, None,
                    "NO_RUN_RECEIPT_PERSIST_UNCERTAIN")
            return OccurrenceDecision(identity, OccurrenceDisposition.BLOCKED,
                                      None, safe_code)
        try:
            self.ledger.attach_admission(identity, accepted_ref)
        except Exception:
            # Host may already own a real Run. Keep its authentic identity
            # and reconcile occurrence link; do not create another Run.
            return OccurrenceDecision(identity,
                OccurrenceDisposition.UNKNOWN_ADMISSION, accepted_ref,
                "RUN_LINK_PERSIST_UNCERTAIN")
        return OccurrenceDecision(identity, OccurrenceDisposition.ADMISSION_REQUESTED,
                                  accepted_ref, "HOST_RUN_ACCEPTED")
~~~

**Producer correction — the rejected/no-Run path:** the first candidate retained a claimed occurrence when the host definitively rejected the Run but left no durable reason, causing repeat evaluation to look like unbounded `UNKNOWN_ADMISSION`. The revised port records a *confirmed no-Run* decision separately and returns that qualified block on duplicate inspection. A `None` Run ref is permitted **only** when the actual trusted host adapter has an authentic no-Run admission receipt; an ACK loss remains `UNKNOWN_ADMISSION`. Ledger exceptions after a claim or host Run acceptance retain uncertainty and stable identity. This clarifies a fake-model behavior, **not** a reliable distributed transaction or approved rule-retry policy. If policy later allows retry after new grants or revised source evidence, it needs a separately authorized occurrence revision/new intention rather than overwriting the previous truth.

**Crucial candidate hole:** \`claim_unique\`, host \`request_run\` and \`attach_admission\` are independent calls. A crash after claiming an occurrence but before recording a Run link can strand the occurrence. Replaying it must *not* blindly produce a second host Run: use a durable linked dispatch intent or query the host by a stable admission intention. A host admission ACK loss is \`UNKNOWN_ADMISSION\` pending authentic reconciliation; the example does not implement a complete transaction or guarantee exactly-once effects. The host still owns all effect-time approvals, actual Run/Attempt state and Artifact receipts.

**Read-after-claim failure and verifier uncertainty — producer-discovered adverse case.** A unique claim may be fully durable while `find_run_ref` or `find_confirmed_no_run_reason` fails transiently. Treat **either lookup failure** as `UNKNOWN_ADMISSION` with a safe code; never call `request_run` again merely because a read failed. A source-version verifier that raises or returns an invalid outcome also cannot turn into `OBSERVED` or `NO_CHANGE`; the candidate maps these cases to `UNKNOWN` and `INVALID_EVIDENCE`, respectively. An application diagnostic owner must record a privacy-safe causal error separately; this candidate does not yet implement that log or reconcile a distributed transaction. For a Run already accepted before `attach_admission` fails, retain its returned identity and reconcile later. For definitive no-Run recorded before its acknowledgment fails, replay the same certified block if available. No extra scheduler iteration grants permission to repeat a physical effect.

**Rule-disabled semantics:** disabling prevents **new** evaluations/admissions by default. It does not automatically cancel previously accepted work. Revoked principal/grant conditions must independently block admission or actual effect, even when the source change is valid.

## 5. Calendar, overlap and resource policies — deliberately unresolved

A real civil-time generator must resolve the IANA zone, DST gap/fold, holiday/workday semantics, calendar definition revision and intended UTC instant. No simple \`timedelta(days=1)\` reinterpreted on each client's local clock can substitute. An offline-week catch-up can amplify requests, quota consumption and destructive writes; \`catch_up_all\` should be capped only by an explicitly chosen data-period completion policy.

Overlap may mean identical **source observation** coalesces while separate required period processing **cannot** be silently merged. \`forbid\` does not stop an already-running worker. Replace/interrupt requires real cooperative cancellation/effect reconciliation; \`parallel_if_permitted\` must respect resource exclusivity and effect conflict claims. A scheduled background rule is not a blanket permission for AI or another user to mutate data.

**Blocking Product choices:** which trigger kinds ship, schedule regularity and tolerance, timezone/gap/fold policy, missed/overlap/queue/catch-up economics, persistent rule owner and edit/approval rights, delegated run-as grant and revocation, host lifecycle/RPO, notification audience, source-validation threshold, dataset/artifact retention and resource budgets. The technical scheduler package/database, event transport and real OS process placement remain downstream choices. The exact physical \`stratbox-application\` repository is still undecided.

## 6. Conformance stubs — PROPOSED / UNEXECUTED

~~~python
def test_duplicate_claim_lookup_timeout_does_not_submit_again(service, ledger):
    ledger.raise_on_find_run_ref()
    decision = service.handle(rule, observed_event, already_claimed_occurrence)
    assert decision.disposition is OccurrenceDisposition.UNKNOWN_ADMISSION
    assert host_admission.calls == calls_before

def test_no_run_reason_lookup_timeout_does_not_submit_again(service, ledger):
    ledger.raise_on_find_no_run_reason()
    decision = service.handle(rule, observed_event, already_claimed_occurrence)
    assert decision.safe_code == "OCCURRENCE_LOOKUP_UNCERTAIN"
    assert host_admission.calls == calls_before

def test_source_verifier_exception_keeps_trigger_uncertain(rule, evidence, verifier):
    verifier.raise_transport_error()
    assert source_change_evaluation(
        rule, evidence, verifier).outcome is EvaluationOutcome.UNKNOWN

def test_source_unavailable_is_not_no_change(rule, evidence, verifier):
    verifier.return_unavailable()
    evaluation = source_change_evaluation(rule, evidence, verifier)
    assert evaluation.outcome is EvaluationOutcome.UNAVAILABLE

def test_duplicate_occurrence_does_not_submit_twice(service, ledger, evaluation):
    first = service.handle(rule, evaluation, occurrence_id)
    second = service.handle(rule, evaluation, occurrence_id)
    assert first.disposition is OccurrenceDisposition.ADMISSION_REQUESTED
    assert second.disposition is OccurrenceDisposition.REPLAY_EXISTING

def test_same_rule_after_revision_has_distinct_occurrence_identity(identity):
    assert identity.for_revision("rev1") != identity.for_revision("rev2")

def test_host_ack_lost_retains_claim_and_requires_reconciliation(service):
    result = service.handle(rule, observed_event, occurrence_id)
    assert result.disposition is OccurrenceDisposition.UNKNOWN_ADMISSION
    assert occurrence_ledger.has_claim(occurrence_id)

def test_time_rule_uses_intended_instant_not_evaluation_now(calendar):
    a = calendar.resolve("ambiguous-fold", zone="Europe/Helsinki")
    assert a.has_explicit_fold_resolution()

def test_offline_catchup_is_bounded_by_approved_policy(scheduler):
    result = scheduler.evaluate_offline_week()
    assert result.attempts <= approved_budget

def test_disabling_rule_does_not_rewrite_already_admitted_run(rule_store, run):
    rule_store.disable(rule_id)
    assert run.authoritative_status_is_unchanged()

def test_revoked_grant_blocks_effect_even_after_due_occurrence(host):
    host.revoke_run_as_grant()
    assert host.try_apply_effect(occurrence_id).is_denied()
~~~

These are *draft test requirements*, not executable test fixtures; their domains/capabilities do not exist in the pinned Windows runtime. A bounded fake ledger can check basic occurrence identity and duplicate handling, but cannot certify a durable concurrent scheduler, DST behavior, event-source trust, actual AppDock host, archive-safe effect or notification delivery. Independent risk review is mandatory for hosted unattended execution.

## 7. Implementation decision and readiness register

| Material concern | Design choice grade | Owner / required evidence |
| --- | --- | --- |
| Trigger evaluation and occurrence identity separate from Run/Attempt/effect | FIXED conceptual evidence boundary | Science and app-host architecture |
| Pure bounded evaluation and fake occurrence service | \`LCD_CANDIDATE\` | Application implementation owner |
| Host owns accepted Run; clients do not become schedulers by display state | FIXED planned host allocation | Accepted host direction and architecture |
| Rule persistence, transaction/dispatch intent and duplicate recovery | \`LCD_BLOCKED\` | Product/operations and actual storage crash tests |
| Time zone gap/fold, misfire, overlap, recurrence and catch-up budgets | \`LCD_BLOCKED\` | Product/workload/domain owner |
| Scope and revocation of run-as/machine grants | \`LCD_BLOCKED\` | Product/security |
| Identity of trusted event/source change and source validity | \`LCD_BLOCKED\` | Domain/source evidence owner and specialist tests |
| Physical scheduler, queue, worker and optional third-party engine | \`LCD_BLOCKED\` until material workload and host profile | Engineering owner; complexity benchmark |
| Detailed future client UI/notification classes | \`NOT_APPLICABLE\` until admitted consumer/scope | Surface owner |
| Real native host/failure and distinct competent independent review | \`UNEXECUTED\` | Independent verifier |

**Handoff:** one coder can implement a small *fake* occurrence ledger and validate the typed guards without choosing a database. Implementing a durable recurring service against real user files remains blocked by named owner decisions. A universal workflow engine is not demanded here; a bounded scheduler should reuse the same application authority and analytical core as user-submitted work. This file does not alter source census status, give an external runtime endpoint, or certify full Research Amputation.
