# LCD candidate — Qt-independent local Scenario execution construction

**Scope:** one bounded local, in-process Scenario run in the existing Windows application, with a headless application seam. **Grade:** \`LCD_CANDIDATE\`; documentation-only \`CANDIDATE_DESIGN\`. **Not:** an implemented patch, approved distributed Job contract, multi-user host service, adopted cancellation/retry guarantee, or certified readiness. **Prepared:** 2026-10-12. **Evidence baseline:** \`stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b\`; analytical core source baseline \`stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580\`. Scope and model are subordinate to candidate \`TW-SB-2026-10-09-CANDIDATE-1\`, \`TH-SB-2026-10-09-CANDIDATE-1\`, \`PA-SB-2026-10-09-CANDIDATE-1\` and the [planned logical host commitment](../../what/strategy-box/host-deployment-commitment.md).

**Consumer:** an implementer preparing a bounded, separately authorized Windows refactor; a future independent headless consumer; a reviewer testing its admission, execution and observation semantics. This packet adds concrete *proposed Python construction* to the [local orchestration LDD](../../ldd/application/local-scenario-orchestration-boundary.md). That LDD remains the detailed mechanism and fault-vector owner. The wider host implementation remains [conditional architecture](../../architecture/application-authority-placement.md), not a requirement to extract a repository in this pilot.

## 1. What existing code actually establishes

The pinned source shows:

- \`application/scenarios/models.py\`: immutable \`ScenarioSpec\`, \`ScenarioStepSpec\`, \`ScenarioRegistry\`; step \`order\`, \`required\`, \`params_map\`, \`params_override\`; error policies \`fail_fast\` and \`continue_with_warnings\`.
- \`application/scenarios/registry.py\`: three atomic Scenarios for three locally registered operations, plus the conditional two-step CBR composite. Do not generalize this into an already dynamic or hosted catalog.
- \`application/scenarios/runner.py\`: sequential mapping and \`run_operation\`, mutable \`ScenarioRunCase\`, callbacks for case/event/artifact/log, step-level results and case finish. It is already independent of Qt imports.
- \`application/operations/execution/runner.py\`: handler-resolution boundary and \`OperationResult(ok, message, outputs, details)\`, operation file logger, workspace precondition and broad exception-to-message conversion.
- \`presentation/qt_desktop/scenario_coordinator.py\` and \`workers.py\`: one-active-case admission, \`QThread\` start and Qt signals. \`runtime/bootstrap.py\` imports this concrete Qt coordinator and places it into \`AppRuntime\`.
- \`application/history/persistence.py\`: five independent recent-history JSON projections, tolerant of invalid payloads but without multi-file transaction, lock or credible durable Run authority.

**Direct counterexamples:** \`continue_with_warnings\` can finish \`success\` after a failed required step; failed results may contain diagnostic log paths in \`outputs\`, then become ordinary artifact cards; raw \`str(exc)\` and parameter summaries enter visible messages; an early workspace failure returns before the logger-cleanup \`finally\` region. A lost Qt worker/callback has no separately durable execution owner. These are source-bounded observations, not measured deployed failures.

## 2. Explicit local scope and invariants

This packet designs **one-active local execution** only. It does not pretend a local mutex coordinates different processes or Web/Android clients. A future accepted logical host requires a different authority/durability/authentication/deployment slice.

1. **Analytic independence — FIXED boundary:** \`stratbox\` performs domain calculations and domain validations without importing Windows, Qt, AppDock or host execution code.
2. **Application truth — FIXED boundary / candidate realization:** only one local execution service may admit and conclude a local Case; Qt schedules and renders, and AppDock owns installation/session/node lifecycle.
3. **Local single-flight — BOUNDED:** a locked admission gate rejects a concurrent submission instead of silently starting a second worker. No persistent queue is implied.
4. **Explicit aggregate status — candidate safety rule:** failure of a required step cannot produce unconditional Case success. Optional-step and partial-policy admission remains a Product Decision; preserve its ambiguity as a blocker rather than treating \`required\` as already enforced.
5. **Evidence segregation — FIXED scientific invariant:** handler output path, operation technical log, candidate/staged output and verified published Artifact are different evidence classes. Creation of a card is not byte verification.
6. **Effect uncertainty — FIXED scientific invariant:** raised exception, lost callback or process crash after an effect may have started does not prove that effect was rolled back or absent.
7. **Observation safety — candidate guard:** unreviewed raw exception text, sensitive parameter values and filesystem paths cannot be broadcast to shared/mobile/agent projections. Local restricted diagnostic logs have a separate policy.
8. **Lifecycle honesty — BOUNDED local profile:** closing the process provides no durable background continuation or automatic resumption. Cancellation and retries remain unsupported until separately authorized.

### Local current ↔ candidate correspondence

| Existing owner | Proposed owner | Semantic delta | Strictly preserved |
| --- | --- | --- | --- |
| Qt \`ScenarioCoordinator.submit\` + \`_active_case\` | \`LocalScenarioService.submit\` with atomic single-flight admission | Move business admission out of Qt | Local busy rejection, one accepted Case at a time |
| Qt \`ScenarioWorker\` + \`QThread\` | Qt \`ThreadDispatcher\` adapter invoking toolkit-free service | Qt becomes scheduling/signal bridge | Asynchronous UI, no UI thread blocking |
| \`run_scenario\` mutates Case, emits callbacks | Pure plan + deterministic execution reducer and typed observations | Repair required-failure aggregate and untrusted output interpretation | Sequential steps, ordered mapping, observed step failures |
| \`run_operation\` catches exceptions, exposes raw details | Boundary wrapper maps exception to bounded safe failure, restricted diagnostics | Separate error privacy and effect certainty | Existing handler invocation and core result values where valid |
| \`HistoryPersistenceService\` five JSON files | Recent-history projection behind a local \`ProjectionSink\` | Cache must not become Run truth; corruption is reportable | Existing recent-context purpose |
| AppDock node/session and activation | External platform interface unchanged | No new manifest or host protocol | Distinct platform ownership |

This is an interim *application construction* compatible with a planned host direction. It is insufficient by itself to deliver the admitted shared-host/Web/Windows-host-client target.

## 3. Proposed placement and dependency direction

These paths are **design targets** in an existing Windows implementation **only if** an implementation commission authorizes the refactor; they are not checked-in source files:

~~~text
src/stratbox_windows/application/
  execution_local/
    contracts.py        # immutable requests, plans, outcomes, observation types
    admission.py        # single-flight service and lock; no PySide6
    plan.py             # validate/sort steps, parameter mapping
    reducer.py          # semantic outcome reduction and transition guards
    engine.py           # invoke existing run_operation through a port
    projection.py       # local observation callback and safe detail boundary
src/stratbox_windows/presentation/qt_desktop/
  local_execution_bridge.py    # QObject signals, QThread scheduling only
src/stratbox_windows/runtime/
  bootstrap.py         # compose headless service; Qt bridge constructed by UI entry
tests/unit/
  test_local_admission.py
  test_local_execution_reducer.py
  test_local_effect_evidence.py
  test_local_projection_safety.py
  test_headless_application_imports.py
~~~

\`execution_local\` → existing \`application.scenarios\`, \`application.operations\`, \`application.cases\`; existing adapter → \`stratbox\`. The application package **must not** import \`presentation.qt_desktop\`. UI-only bridge depends inward on \`execution_local\`. AppDock remains an external activation/lifecycle input, not an authority for analytic validity. The durable shared-host/API/ACL design has no physical allocation here.

## 4. Concrete types and interfaces — CANDIDATE_DESIGN

The following Python is a *coherent annotated design skeleton*, **not executable production code**. Type names, module boundaries and method signatures remain proposal-grade. A proposed \`case_id\` identifies one local execution; it is not a cross-host idempotency or durable Job key.

~~~python
# application/execution_local/contracts.py -- CANDIDATE_DESIGN
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Protocol

class CaseOutcome(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"
    OUTCOME_UNKNOWN = "outcome_unknown"  # new proposal; not in current CaseStatus

class EvidenceKind(str, Enum):
    DOMAIN_OUTPUT_REFERENCE = "domain_output_reference"
    TECHNICAL_LOG = "technical_log"
    STAGED_OUTPUT = "staged_output"
    VERIFIED_ARTIFACT = "verified_artifact"

class EffectCertainty(str, Enum):
    NO_EFFECT_ASSERTED = "no_effect_asserted"
    CONFIRMED = "confirmed"
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class LocalInvocation:
    scenario_id: str
    params: Mapping[str, object]
    author_id: str | None

@dataclass(frozen=True, slots=True)
class PlannedStep:
    step_id: str
    operation_id: str
    title: str
    required: bool
    params: Mapping[str, object]

@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    case_id: str
    scenario_id: str
    steps: tuple[PlannedStep, ...]
    error_policy: str

@dataclass(frozen=True, slots=True)
class OutputReference:
    path: str                # local restricted reference; NOT a public URL
    kind: EvidenceKind
    verified_receipt: str | None = None

@dataclass(frozen=True, slots=True)
class StepOutcome:
    step_id: str
    ok: bool
    safe_code: str
    safe_summary: str
    outputs: tuple[OutputReference, ...] = ()
    effect_certainty: EffectCertainty = EffectCertainty.UNKNOWN

@dataclass(frozen=True, slots=True)
class ExecutionObservation:
    case_id: str
    sequence: int            # monotonically increments in ONE local run
    kind: str                # admitted/step_started/step_finished/case_finished/observation_failed
    step_id: str | None
    safe_code: str
    safe_summary: str

@dataclass(frozen=True, slots=True)
class LocalCaseSnapshot:
    case_id: str
    scenario_id: str
    outcome: CaseOutcome
    finished_steps: tuple[StepOutcome, ...] = ()
    last_sequence: int = 0
    diagnostic_ref: str | None = None  # restricted local-only pointer

class OperationPort(Protocol):
    def invoke(self, operation_id: str, params: Mapping[str, object],
               *, case_id: str, step_id: str) -> StepOutcome: ...

class ObservationPort(Protocol):
    def publish(self, observation: ExecutionObservation) -> None: ...

class LocalDispatcher(Protocol):
    def start(self, callback: Callable[[], None]) -> None: ...

class ProjectionPort(Protocol):
    def update(self, snapshot: LocalCaseSnapshot) -> None: ...

class AdmissionError(Exception): ...
class BusyLocalExecutor(AdmissionError): ...
class InvalidScenario(AdmissionError): ...
~~~

**Data contract:** these are in-memory local Python values; no remotely callable JSON schema or durable wire compatibility is claimed. Mapping parameters are copied/frozen on admission before worker scheduling; current \`ScenarioSpec.resolve_params\` and \`OperationSpec.resolve_params\` still own defaults within their current scopes. For future serialization, a separate schema version and safe-field projection are mandatory; \`path\`, \`diagnostic_ref\` and raw params are not exposed to remote consumers by default.

### Source-backed plan translation

~~~python
# application/execution_local/plan.py -- CANDIDATE_DESIGN
def build_local_plan(scenario, invocation: LocalInvocation, *, case_id: str,
                     operation_registry) -> ExecutionPlan:
    # 1. Confirm scenario ID and uniqueness of step IDs.
    if invocation.scenario_id != scenario.id or not scenario.steps:
        raise InvalidScenario("scenario_missing_or_mismatched")
    ordered = sorted(scenario.steps, key=lambda s: (s.order, s.id))
    if len({s.id for s in ordered}) != len(ordered):
        raise InvalidScenario("duplicate_step_id")
    resolved = scenario.resolve_params(dict(invocation.params))
    steps = []
    for step in ordered:
        operation = operation_registry.get(step.operation_id)  # KeyError -> invalid plan
        if not operation.enabled:
            raise InvalidScenario("disabled_operation")
        # Preserve currently observed params_map and override precedence.
        if step.params_map:
            mapped = {target: resolved[source]
                      for source, target in step.params_map.items() if source in resolved}
        else:
            mapped = dict(resolved)
        mapped.update(step.params_override)
        steps.append(PlannedStep(step.id, operation.id, step.title,
                                 step.required, dict(mapped)))
    return ExecutionPlan(case_id, scenario.id, tuple(steps), scenario.error_policy)
~~~

**Required admission check before implementation:** \`OperationSpec.enabled\` exists in the pinned catalog model, but execution current code does not itself enforce disabled operations at this path. Input validation, dangerous operation authorization and correct permissions require their own owner; this local plan gate does **not** authorize a human, agent or remote principal.

## 5. Local single-flight coordination — CANDIDATE_DESIGN

~~~python
# application/execution_local/admission.py -- CANDIDATE_DESIGN
from threading import Lock
from uuid import uuid4

class LocalScenarioService:
    def __init__(self, *, scenarios, operations, executor: "LocalExecutionEngine",
                 dispatcher: LocalDispatcher, projections: ProjectionPort) -> None:
        self._scenarios, self._operations = scenarios, operations
        self._executor, self._dispatcher, self._projections = executor, dispatcher, projections
        self._gate = Lock()
        self._active_case_id: str | None = None

    def submit(self, request: LocalInvocation) -> str:
        scenario = self._scenarios.get(request.scenario_id)
        case_id = uuid4().hex
        plan = build_local_plan(scenario, request, case_id=case_id,
                                operation_registry=self._operations)
        with self._gate:
            if self._active_case_id is not None:
                raise BusyLocalExecutor("local_executor_busy")
            self._active_case_id = case_id
        # An observed 'accepted' does NOT promise a disk-journal commit.
        try:
            self._dispatcher.start(lambda: self._run_and_release(plan))
        except Exception:
            with self._gate:
                if self._active_case_id == case_id:
                    self._active_case_id = None
            raise AdmissionError("worker_schedule_failed") from None
        return case_id

    def _run_and_release(self, plan: ExecutionPlan) -> None:
        try:
            outcome = self._executor.execute(plan)
            self._projections.update(outcome)  # delivery failure handled separately
        except BaseException:
            # Unexpected after-invocation effects may exist; never declare rollback.
            self._projections.update(LocalCaseSnapshot(
                case_id=plan.case_id, scenario_id=plan.scenario_id,
                outcome=CaseOutcome.OUTCOME_UNKNOWN))
        finally:
            with self._gate:
                if self._active_case_id == plan.case_id:
                    self._active_case_id = None
~~~

**Refinement required before a production patch:** handle failures of \`_projections.update\` without preventing gate release, log exception details only to an access-limited local diagnostic sink, and define a liveness/worker-start handshake if the chosen dispatcher can enqueue but never start. A \`BaseException\` handling sketch represents a last-resort unknown-effect boundary, not a plan to suppress process termination or system signals. Use exception-safe \`finally\` and an independent supervisory fault report. In-memory snapshots are *ephemeral*; post-crash missing snapshot cannot imply an empty history.

**Deliberate limitation:** no \`cancel()\`, \`retry()\`, \`resume()\`, queue, scheduler, remote client, API handler, durable \`Job\` or AppDock manifest is prescribed. A one-process gate is not secure multiuser admission.

## 6. Execution reducer, failure and effect policy — CANDIDATE_DESIGN

~~~python
# application/execution_local/reducer.py -- CANDIDATE_DESIGN
def aggregate_outcome(plan: ExecutionPlan,
                      completed: tuple[StepOutcome, ...]) -> CaseOutcome:
    """Never turn an unsuccessful REQUIRED step into unconditional SUCCESS."""
    by_id = {step.step_id: step for step in completed}
    if any(s.effect_certainty is EffectCertainty.UNKNOWN and not s.ok
           for s in completed):
        # An effectful failure without a trustworthy receipt is qualified,
        # not silently rolled back. Exact visible 'unknown' status is provisional.
        return CaseOutcome.OUTCOME_UNKNOWN
    if any((s.step_id in by_id and not by_id[s.step_id].ok)
           for s in plan.steps if s.required):
        return CaseOutcome.FAILED
    if any(not s.ok for s in completed):
        return CaseOutcome.WARNING
    if len(completed) != len(plan.steps):
        # A skipped step requires an explicit skip/fail-fast reason.
        return CaseOutcome.WARNING
    return CaseOutcome.SUCCESS

# application/execution_local/engine.py -- CANDIDATE_DESIGN
class LocalExecutionEngine:
    def __init__(self, *, operation: OperationPort,
                 observations: ObservationPort) -> None:
        self.operation, self.observations = operation, observations

    def execute(self, plan: ExecutionPlan) -> LocalCaseSnapshot:
        completed: list[StepOutcome] = []
        seq = 0
        def record(kind: str, step_id: str | None, code: str, summary: str) -> None:
            nonlocal seq
            seq += 1
            self.observations.publish(ExecutionObservation(
                plan.case_id, seq, kind, step_id, code, summary))
        record("admitted", None, "LOCAL_ACCEPTED", "Local execution admitted")
        for step in plan.steps:
            record("step_started", step.step_id, "STEP_STARTED", "Step started")
            try:
                result = self.operation.invoke(
                    step.operation_id, step.params, case_id=plan.case_id,
                    step_id=step.step_id)
            except Exception:
                # Restrict traceback to a local diagnostics owner, without raw
                # exception text in Observation. Effects may be uncertain.
                result = StepOutcome(step.step_id, False,
                                     "OPERATION_EXCEPTION", "Step failed",
                                     effect_certainty=EffectCertainty.UNKNOWN)
            completed.append(result)
            record("step_finished", step.step_id, result.safe_code,
                   result.safe_summary)
            if not result.ok and plan.error_policy == "fail_fast":
                break
        status = aggregate_outcome(plan, tuple(completed))
        record("case_finished", None, status.value, "Execution finished")
        return LocalCaseSnapshot(plan.case_id, plan.scenario_id, status,
                                 tuple(completed), seq)
~~~

**Two stop-before-code decisions:**

- **UNKNOWN versus FAILED:** the shown reducer conservatively returns \`OUTCOME_UNKNOWN\` for unreceipted failed operations, which exceeds the current CaseStatus vocabulary. Implementer must agree whether CaseStatus expands, or whether an independent \`effect_state=UNKNOWN\` accompanies \`FAILED\`; changing case schema, UI and persistence requires one aligned Decision. If the operation explicitly proves no effect occurred, \`FAILED\` remains possible.
- **Observation sink:** \`publish\` may fail *after* an operation effect, so production \`record\` requires a bounded failure policy that preserves operation result and emits local diagnostic loss. If observations are authoritative/durable in a chosen profile, then the transaction/journal semantics must be defined before execution. In this local profile, treat callbacks as best-effort projection signals only.

**Operation adapter bridge:** the existing \`run_operation\` returns \`OperationResult\` with \`ok\`, \`outputs\` and \`details['operation_log']\`; adapt it, do not replace banking handlers. Convert \`operation_log\` into a \`TECHNICAL_LOG\` reference; other paths into \`DOMAIN_OUTPUT_REFERENCE\` until a separate verification/publish receipt exists. Never call them \`VERIFIED_ARTIFACT\` based only on file suffix or \`ok\`. Prohibit raw \`str(exc)\` in shared observations, retain restricted technical cause. A failing operation can produce a diagnostic log even if \`ok=False\`. Ensure logger lifecycle closes on **every** path, including workspace early return; use a unique physical attempt/log path, not just sanitized case+step names.

## 7. Qt boundary (view-only bridge) — CANDIDATE_DESIGN

~~~python
# presentation/qt_desktop/local_execution_bridge.py -- CANDIDATE_DESIGN
class QtLocalExecutionBridge(QObject):
    case_changed = Signal(object)
    observation_added = Signal(object)
    run_finished = Signal(object)

    def __init__(self, local_service: LocalScenarioService):
        super().__init__()
        self._service = local_service

    def submit(self, scenario_id: str, params: dict[str, object],
               author_id: str | None) -> str:
        # Marshal domain-free request; do NOT assign semantic Case SUCCESS.
        return self._service.submit(LocalInvocation(scenario_id, dict(params),
                                                    author_id))
    # A QtDispatcher adapter moves execution off the UI thread; queued signals
    # marshal immutable snapshots to the UI thread. Exact threading technique
    # (QThread or a bound executor) is BOUNDED within GUI lifecycle constraints.
~~~

In source composition, build semantic service in a Qt-free application factory, then create Qt bridge at the UI entry. The current \`AppRuntime.scenario_coordinator: Any\` can be replaced by a typed local application port once implementation is authorized; do not replace it with an automatically global hosted interface. Screen projectors consume immutable snapshots and ordered \`ExecutionObservation\`; Qt callback order cannot establish execution truth.

## 8. Verification skeletons — PROPOSED, NOT EXECUTED

~~~python
# tests/unit/test_local_admission.py -- PROPOSED
def test_second_submit_rejected_with_atomic_gate(fake_service, invocation):
    first = fake_service.submit(invocation)
    assert first
    with raises(BusyLocalExecutor):
        fake_service.submit(invocation)

def test_dispatch_start_failure_releases_reservation(service_with_failing_dispatcher, invocation):
    with raises(AdmissionError):
        service_with_failing_dispatcher.submit(invocation)
    assert service_with_failing_dispatcher.active_case_id is None

# tests/unit/test_local_execution_reducer.py -- PROPOSED
def test_required_step_fails_and_continue_policy_never_reports_success(plan_two_required):
    r = aggregate_outcome(plan_two_required, (failed_step_1, good_step_2))
    assert r in (CaseOutcome.FAILED, CaseOutcome.OUTCOME_UNKNOWN)

def test_fail_fast_skipped_step_does_not_claim_both_steps_completed(plan_two_required):
    r = aggregate_outcome(plan_two_required, (failed_step_1,))
    assert r != CaseOutcome.SUCCESS

# tests/unit/test_local_effect_evidence.py -- PROPOSED
def test_log_path_on_failed_operation_is_diagnostic_only(fake_operation_adapter):
    step = fake_operation_adapter.invoke("one", {}, case_id="c", step_id="s")
    assert any(o.kind is EvidenceKind.TECHNICAL_LOG for o in step.outputs)
    assert not any(o.kind is EvidenceKind.VERIFIED_ARTIFACT for o in step.outputs)

def test_exception_after_effect_keeps_unknown(fake_effectful_operation):
    assert fake_effectful_operation().effect_certainty is EffectCertainty.UNKNOWN

# tests/unit/test_local_projection_safety.py -- PROPOSED
def test_secret_like_parameter_and_exception_are_not_in_shared_observation(safe_sink):
    observed = safe_sink.publish_case_with_sensitive_fixture()
    assert "secret-sentinel" not in observed
    assert "private-path-sentinel" not in observed

# tests/unit/test_headless_application_imports.py -- PROPOSED
def test_semantic_application_has_no_qt_import(fake_python_import_guard):
    fake_python_import_guard.block("PySide6")
    import stratbox_windows.application.execution_local  # candidate path only
~~~

Additional LDD vectors: [LS-01..25](../../ldd/application/local-scenario-orchestration-boundary.md) govern single-flight, required/optional failures, diagnostic segregation, lifecycle/observer failures, corruption, unsafe handler messages, namespace collision and code-import violations. **All proposed target checks remain UNEXECUTED**. Tests must distinguish source characterization, static import/syntax parsing, fake behavioral execution, native Qt/Windows + AppDock integration, actual domain result and host-wide conformance.

### Cold implementer / adversarial acceptance checklist

A *different competent reviewer* must be able to answer from this LCD and its maintained parent documents: where does actual admission happen; which code may import Qt; what is authoritative under local process loss; how do mapped step params become validated; which error class preserves effect uncertainty; how does a diagnostic log avoid becoming a published Artifact; which class handles callback loss; what has to be decided before introducing Web/Android or durable Jobs? Open answers below prevent a readiness certification.

## 9. Decision and freedom register

| Choice | Classification | Owner / handoff |
| --- | --- | --- |
| No domain/UI/AppDock import inside analytical core | **FIXED** boundary | Existing core + Architecture |
| Scenario step order and map/override semantics in current local scope | **FIXED baseline**, change requires separate design review | Current Windows implementation |
| One local admitted Case and atomic busy rejection during current local pilot | **BOUNDED** candidate | Windows application owner; validate thread/race test |
| Exact \`execution_local\` private files and local scheduler implementation | **DELEGATED_NONMATERIAL** when interfaces/behavior hold | Implementer |
| No unconditional success after failed required step | **FIXED target safety invariant; policy detail BLOCKED** | Product owner for partial/optional choices |
| Local CaseStatus expansion versus separate effect-certainty axis | **BLOCKED_ON_AUTHORITY_OR_EVIDENCE** | Product + application owner |
| Verified Artifact promotion, retention, authorization and receipt | **BLOCKED_ON_AUTHORITY_OR_EVIDENCE** | Product + artifact/security owners |
| Diagnostic redaction/audience and retention | **BLOCKED_ON_AUTHORITY_OR_EVIDENCE** for policy; safe-by-default interim bridge | Security + operations |
| Cancellation, retry, crash continuation, partial effects and concurrency beyond one local run | **BLOCKED_ON_AUTHORITY_OR_EVIDENCE** | Product + engineering risk owner |
| Physical \`stratbox-application\` repo/process/host and remote protocol | **BLOCKED_ON_AUTHORITY_OR_EVIDENCE** | Product + engineering owners; distinct host slice |
| Qt signal mechanics and in-process callback registry | **BOUNDED** | Desktop implementer and native test |
| Independent headless and native conformance | **NOT EXECUTED** | Separate verifier |

The code skeleton intentionally exposes some unresolved production choices rather than silently committing them. It is **not** \`LCD_READY_FOR_IMPLEMENTATION\` yet. A smaller well-defined future patch (for example extracting the pure step planner and testing its existing mapping semantics) may qualify separately after a cold implementation challenge and authority check.

## 10. Result / residual route

**What this packet now supplies:** proposed package layout, typed model, one-active-run service and lock, immutable observations, sequential engine, aggregate-status reducer, operation adapter boundary, Qt-only bridge and concrete negative tests. These form a bounded local pre-code construction, rather than a restatement of LDD.

**What is still missing:** Product policy for partial/optional outcomes, compatible CaseStatus/effect-state acceptance, tested execution and failure behavior, native lifecycle and actual host/remote authority. The other LCD directions—host/client attachment, artifact/source integrity and AppDock interaction—remain separate activation candidates, not implicitly completed by this pilot.

**Assurance and stop:** this document is producer-authored and statically reconciled with the pinned paths above; it has not received an independently executed cold-implementer challenge. No source-level \`unaccounted\` record, missing original carrier, or independent Research Amputation status is changed by publication. Reopen on a Windows source revision, admitted outcome/error policy, independent negative test failure, second consumer, or changed deployment contract.
