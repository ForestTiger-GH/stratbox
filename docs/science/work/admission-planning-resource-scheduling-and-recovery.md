# Work admission, immutable plans, resource-aware scheduling and recovery

**Domain:** the operational guarantees between a user or authorized machine expressing intent and a Strategy Box execution authority accepting, planning, dispatching, reconciling and reporting real work. **Status:** standalone scientific/engineering analysis with baseline code evidence and explicitly hypothetical protocols. No common production JobManager, host scheduler, distributed effects protocol, finalized API or RPO/RTO is certified.

## 1. A single execution spine is a semantic contract, not a service count

```text
Human / scheduled rule / event / permitted API or AI
  → Intent / WorkCandidate
  → validate, authorize and admit accountable Work if needed
  → select approved Operation/Scenario/Composition version
  → resolve source/registry/parameter/implementation binding
  → inspect effect, resource and approval preconditions
  → seal immutable ExecutionPlan
  → durably admit Run and one or more schedulable Jobs
  → allocate Job, invoke OperationRuns and physical Attempts
  → observe progress, source findings, side-effect receipts
  → verify artifacts and aggregate Run outcome
  → assess qualified AnalyticalResult against Work criteria
  → accept/close with unresolved obligations where allowed
```

A trivial pure Python operation can be called directly with no Work, Thread or managed Job. The diagram expresses distinctions **when a managed application assumes responsibility**. A Job may contain several short OperationRuns, and one Run may have one Job or a small dependency DAG; creating a Job on every parser helper call is unjustified. A Case card in pinned Windows can represent a run, but is not independently certified as the future durable Work aggregate. See [semantic identities](../architecture/semantic-identities-lifecycles-and-projections.md) and [Work closure](evidence-based-work-lifecycle-and-closure.md).

The core library owns financial-data semantics and domain Result; managed application owns Work admission, current principal/grants, queue, state transitions, artifact catalog, control commands and acceptance decisions; execution backend owns process/liveness/attempt evidence; FileStore implements physical effects; the external platform owns Node/Session/installation/activation and qualified platform diagnostics. The logical application owner can begin inside a local desktop or headless process; a new repository and a PostgreSQL server do **not** follow from the distinctions.

## 2. Current Windows limitations are specific, not a blank slate

At [pinned Windows baseline](https://github.com/ForestTiger-GH/stratbox-windows/tree/959e9c4ce1441124af5111c1e025041714e04d3b), the [scenario registry](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/registry.py) exposes three operations (`cbr_file_collector.collect`, `escrow.history.export`, `system.diagnostics`), automatic atomic scenarios and one composed sequential update. [ScenarioRunner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) maps `order`/`required`/`params_map` to handlers and records Case/steps/events/Artifact paths. This is a meaningful working local orchestration baseline **without** a general dependency DAG, sealed Plan, idempotent submit authority or dedicated Attempt journal.

[Qt ScenarioCoordinator](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) has one active `QThread`/Case; a second submit encounters `is_busy`. [Runtime bootstrap](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/bootstrap.py) imports this Qt coordinator. [Background store](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/store.py) tracks in-memory status/enablement, not a deployed scheduler. [History persistence](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) independently overwrites five JSON lists and may decode corruption as empty history.

A local GUI remains usable for its declared functions; these facts mean multi-client persistence, real queue, cross-process cancellation/leases, remote recovery and fully verified effects cannot be inferred from the existing widgets. The core revision checked by the original 03 Research had no executable `src/` changes between its earlier and later October snapshots; Research revisions do not by themselves transform current code.

## 3. Admission and planning are separate decisions

Four entry families are distinct in origin but converge on one managed check: human/GUI or chat message, calendar/event AutomationOccurrence, permitted machine API/AI proposal, and an Assignment/review callback. A message is not an accepted Work; a plan preview is not permission or actual execution.

An **admission decision** can return `accepted`, `already_accepted`, `needs_input`, `needs_approval`, `unavailable`, `rejected` or `conflict` under the intended scope. It should record who requested it, the actual authenticated principal, target/workspace, originating trigger/message, applicable operation revision and idempotency/payload identity. Reusing one idempotency key with a **different effective payload** should yield conflict, not change an earlier accepted Run silently. Different intentional Runs with equal parameters remain distinct.

**Work admission threshold** remains a Product Decision: a long-lived commissioned goal/report/review needs accountable Work; a one-off download might attach an immediate Run and terminal result with no independent long-lived goal. An automation firing can create a fresh Work or another Run in a standing Work according to explicit admission policy. Rejecting an unsupported AI-proposed scenario should not manufacture a Job.

**Planning** resolves semantic operation versions to permitted implementation/environment binding, freezes defaults and actual requested values into immutable effective parameters, pins source and registry snapshots or freshness policy, type-checks dependencies, measures resource/effect classes, checks approvals/constraints and produces an inspectable `ExecutionPlan` with a digest/revision. This is **not** a generated Python script that executes with unreviewed privileges. If sources, permission or output namespace change while queued, the authority rechecks relevant preconditions before effect; a new snapshot may require explicit replan/new Run.

An executable Plan may be a single operation; a typed DAG adds value when steps have independent dependencies, shared validated source acquisition, retry, resources or effects. A graphical node with an unbound `DataFrame` output is not proof of runtime type compatibility or source fidelity.

## 4. Atomic acceptance and control-command semantics

Illustrative command families—not shipped APIs—include `SubmitWork`/`SubmitRun`, `ApproveExecution`, `CancelRun`, `RetryAttempt`, `StartNewRun`, `Pause/Resume` where validated checkpoint exists, `RequestReconciliation`, `AcceptResult`, `CloseWork`. A command **requests** an action; its corresponding state transition event **records what the authority actually accepted**. An initial `CancelRun` receipt is not a `RunCancelled` terminal event.

For a promised durable profile, a *logical commit* must bind Run ID, plan/input revisions, Jobs, initial events, mutation/idempotency association and outbox notification, **before** dispatch. The exact mechanism may be one versioned atomic document, journal with recovery, or transactional database depending on accepted storage capabilities. A path allocation without tested crash behavior is not an ACID guarantee. Output files and third-party API changes lie outside this commit and need independent intent/receipt/reconciliation.

On concurrent mutations, `expected_revision` prevents lost updates. An accepted cancel and an actual completion racing for terminal transition cannot both become the single initial terminal receipt. Late evidence belongs to an additional reconciliation assessment, preserving the original observation.

## 5. One JobManager authority, multiple worker types

A *logical* JobManager per authoritative Node/workspace can own waiting/ready/claimed/running/finalizing/reconciling, resource slots, approval waits, fairness, cancellation, retry and time budgets. It does not require one OS process: a desktop may use an in-process worker, CPU-heavy SORS may use a subprocess, and an actual host deployment may serve multiple clients and workers. The application authority owns Job meaning; worker backend owns process start/stop/query receipts.

Resource claims must be **about the actual contested object**:
- independent read-only source snapshots can execute concurrently with per-source/network rate limits;
- two distinct output targets may publish concurrently;
- one canonical destination alias requires exclusive writer, versioned generation or conditional commit;
- destructive FRG cleanup requires scope-bound review and resource exclusion;
- heavy native solver needs CPU/memory budget and controlled concurrency;
- an external source may impose service-specific retry or traffic limits.

One chat is not one resource lock. The global Qt `is_busy` is a current local simplification, not a node-wide concurrency policy. `ResourceLock` guards data/namespace; `WorkerLease` guards entitlement to claim Job state; a stale worker can still execute after lease expiration, requiring fencing at the **actual publication boundary** in takeover-capable profiles.

Before workload measurements, bounded FIFO plus a few resource classes may be enough; complex priority scheduling, quotas and fairness should follow real interactive/background contention. Separate tiny Job for every helper creates overhead. The natural splitting points are source acquisition, domain computation, verified stage output and artifact publication when each needs independently recoverable results or resource placement.

## 6. Retry, idempotency, cancellation and ambiguous effects

The word “retry” includes four different actions:

| Action | Identity | Why different |
| --- | --- | --- |
| HTTP/client retransmission | Same logical command/idempotency identity | Acknowledgement of accepted request was lost |
| `RetryAttempt` | New Attempt under one admitted Job/OperationRun | A bounded repeat of a specific physical try |
| `ResumeFromCheckpoint` | New execution segment with validated reused stages | Previous artifact/source/method versions prove safe reuse |
| `StartNewRun` / replay Work | New Run, often changed inputs/criteria | User requests a new evaluation rather than a retry of old intent |

These differ again from **in-plan dedup** (shared pure computation), historical **cache reuse**, resource **serialization** and effect **reconciliation** (observation without repeating an effect). HTTP retry × domain retry × Scenario retry × Job retry can multiply real attempts; one governing budget must bound retries at the relevant effect boundary, while lower-level transparent retries consume that budget.

Candidate error policy distinguishes transient unavailable/rate limit, known timeout before effect, schema validation rejection, grant denial, stale source/plan conflict, partial effect and unknown external outcome. Blind automatic retry belongs only to known safe/idempotent classes. A non-idempotent remote `POST`, directory delete, overwrite of a unique source or ambiguous publish must stop pending receipt/inspection unless the external backend provides sufficient idempotency.

A cancellation request is accepted and passed as cooperative token; the operation checks safe points, avoids *future* effects and qualifies already-performed ones. A force-kill of a worker process is not rollback. Late `Cancel` after verified completion responds `already_terminal`; stop during publish might result in `SUCCEEDED`, `PARTIAL` or `OUTCOME_UNKNOWN` depending on facts.

**Exactly-once** is not a universal external promise. At most a bounded logical admission can be deduplicated; at-least-once worker delivery can be combined with effect-specific idempotency and fencing, while providers without effect lookup need manual reconciliation. [AWS durable idempotency guidance](https://docs.aws.amazon.com/durable-execution/patterns/best-practices/idempotency/) and [Temporal activity semantics](https://docs.temporal.io/encyclopedia/activities#activity-execution) illustrate the difficulty, not a requirement to install these systems.

## 7. Work, Run and Job form distinct finite-state tracks

A managed Work might be `candidate/admitted/active/awaiting_input/awaiting_approval/awaiting_review/completed/closed/reopened`. A Run might be `prepared/admitted/queued/running/finalizing/terminal(outcome)`; a Job might be `queued/waiting_resource/waiting_approval/claimed/running/finalizing/reconciling/terminal`. These are illustrative transitions. `REJECTED` before a Run exists belongs to request admission, not necessarily a fictitious Run.

`ExecutionOutcome` (`SUCCESS,PARTIAL,FAILURE,CANCELLED,UNKNOWN`) is **another axis** than Lifecycle; domain validity and Work acceptance are additional independent tracks. A queued Job can be cancelled without an Attempt; claimed but not started needs a different record from observed executing; a timeout can leave external effect unknown; a successful Run can still require a human assessment of IFRS/RAS comparability.

Single terminal receipt is a desirable **invariant under a versioned contract**, but later evidence can revise the current knowledge about the effect through a new reconciliation event, not a silent historical rewrite. The source research's elaborate UML-like transitions are proposals; Current Windows does not implement them.

## 8. Recovery is fact-finding before rescheduling

A safe future restart route: verify state schema/generation → recover incomplete commits/outbox → acquire recovery authority → inspect nonterminal Runs, Jobs, leases and effect intents → establish actual worker/process liveness when possible → inspect staged and published objects under authentic resource/permission scope → reconcile ambiguous effects → resume/retry only eligible work with new Attempt identity → recompute projections and missed occurrences → present unresolved problems.

Heartbeat loss alone cannot prove worker death. Expired lease alone cannot prevent late writes. A failed state read cannot become a successful empty history. An old source snapshot must not silently upgrade to a fresh release during resume. Job recovery can succeed while Work remains `awaiting_review`; Work can close legitimately with a documented negative finding without new Jobs.

Different deployment profiles have different guarantees. A local foreground Windows close may stop actual computing, while a real independent host may continue after a client's browser closes. Host execution needs its own process, storage, activation/health and trust boundary. An external platform's Node/process health cannot certify domain Run completion.

## 9. Automation is a stable definition with independent occurrences

Five independent coordinates describe invocation: **origin** (human, scheduled, API, AI), **trigger** (manual, recurrence, event, source change), **client presence** (attached/detached), **backend placement** (desktop/host/remote), **work pattern** (one-off, composite, monitor, approval gated). Making `background` an alternate type of financial Scenario collapses these axes and duplicates execution.

An `AutomationSpec` may bind scenario revision, trigger kind, run-as principal, misfire/coalesce/concurrency/approval rules and enabled status. Each actual calendar event has an `Occurrence` identity, typically including rule revision and scheduled local time, to deduplicate across restarts. **Daily 08:00 local time is not always the same as every 24 elapsed hours.** IANA timezone, DST fold/gap, missed occurrences, skip/coalesced/bounded catch-up and source freshness need explicit policy. Turning off the schedule prevents future occurrences but is not automatic cancellation of an already admitted Run.

Watchers can report new SourceSnapshots; one “no new publication” check is a genuine qualified observation, not proof of zero data. AI-origin invocation is a proposal using the same authorized admission, not a second hidden banking algorithm engine. The OS or external platform may start/monitor the host; the application's schedule definitions and occurrence history still belong to the product.

## 10. Verified finalization, Work acceptance and user projections

A candidate finalization path is: collect worker output in staging → validate domain quality/completeness and bytes → verify manifest and source refs → perform provider-specific publish → record effect receipts → commit Job/Run aggregate outcome → emit client-safe events/outbox → present or assess Work acceptance. Progress reaching 100% before required publication verification is a false claim. A terminal run can be `SUCCEEDED`, an Artifact `PUBLISHED`, domain analysis `QUALIFIED` and Work `AWAITING_REVIEW` simultaneously.

A simple official-file collector might auto-close under a bounded complete-manifest profile; a consequential analytical bank comparison requires human review; a statistical reconstruction involving assumptions carries an additional evidence qualification. Destructive cleanup requires checked per-effect receipts and authorization/approval conditions. A later failed Run cannot erase a previous accepted Artifact; “latest Run” is not always “current valid Result.”

One Thread may discuss multiple Work; one Work may span Threads if permissions allow. Each UI has safe cards and a task center as projections. Reconnect needs an authorized snapshot+event cursor, replay/gap handling and per-participant read markers. Raw exception details and sensitive files are not shared merely because the team sees a chat. Observability has different layers: core domain diagnostic, product Run/event, platform process health, and client focus/notification. UI and telemetry are not state authorities.

## 11. Four cross-boundary case traces

**Escrow export:** user selects pinned Scenario → accepted Work/Run with exact source version and requirements → Job/Attempt fetch+parse+validate → stage/verify workbook → publish Artifact → Run terminal → Work awaits review or auto-closes under explicitly accepted criteria. A missing official month requires partial or failure qualification, not green success by file existence.

**Two reports using one CBR raw publication:** source producer may be shared when byte snapshot, scope, method, freshness and permissions are equivalent; two resulting datasets/works and two independent Excel publications retain their own lineage and effects. Matching URL alone cannot justify reuse.

**FRG destructive cleanup:** safe read-only scan and plan identify target paths/reasons; authorization binds actor, exact plan/object-set digest, expiry and current namespace; apply revalidates the plan, claims target resource and emits per-object effects. If directory changed after Approval, reject/replan. A worker kill with some files deleted is PARTIAL/UNKNOWN, not cancelled and rolled back.

**Recurring publication watcher after crash:** explicit calendar occurrence and accepted Run; external publish possibly succeeds before ACK; recovery compares actual target/hash/manifest and reconciles. If facts remain insufficient, retain unknown and require intervention. The client reconnects to the existing Run, and duplicate submit with the same idempotency key returns its admission rather than a new job.

## 12. The 25 candidate execution invariants, preserved

| EX IDs | Distinct falsifiable properties |
| --- | --- |
| **01–05** | All origins use governed admission; Work independent of Run/UI; definition/plan/Run identity; sealed plan; one initial committed terminal receipt |
| **06–10** | Cancel request distinct from cancellation; timeout not failed effect; unknown prevents unsafe auto retry; idempotent admission; fencing conflicting Artifact writers |
| **11–15** | Dedup by semantic equivalence not action name; domain validity/Work acceptance independent; published Artifact has Run/provenance; UI is projection; platform health not Run outcome |
| **16–20** | Failed/empty/not-found/denied/unknown are distinct; effects require authorized scope; incomplete Artifact not published; disabling automation doesn't cancel running Job; AI/external consumers use same permissions |
| **21–25** | New failed Run doesn't erase old Artifact; busy guards follow resources; slow worker doesn't freeze UI; committed events causal and replayable; resume requires validated checkpoint/source versions |

The original also enumerates **16 C01–C16 research conflicts** (Command vs Operation; Case vs Work; Cascade vs Scheme; UI launcher vs Work context; background kind; Qt vs headless; platform vs app scheduler; host repo; nested retry; Job vs Work acceptance; lost ACK; local JSON vs shared truth; mutable latest vs plan; AI runner; Run/Job cardinality; unknown reconciliation). These are retained as **research semantic directions**, not adopted decisions. Most disagreements resolve by identifying distinct roles; independent Scheme identity, physical host and storage, exact terminal reconciliation schema and approval policy remain open.

**Superseded target shortcuts:** domain Python importing GUI, one general Qt worker as Node scheduler, chat JSON as execution authority, a separate background or AI-only executor, an automatic Scenario per every helper and successful file existence equaling accepted analytical Knowledge.

## 13. Twenty-four open Product/Engineering questions

The original source register `U01–U24` groups into independently answerable decisions:

- **U01–U04:** threshold for Work admission; whether simple Run needs separate Job record; Job vs OperationRun scheduling granularity; whether Case deserves persistent semantic identity.
- **U05–U08:** outcome after unknown and subsequent reconciliation; who records approvals; what prevents stale workers; safe checkpoint resume by each domain.
- **U09–U12:** Work completion vs acceptance vs withdrawal; source and permissions refresh while queued; pure computation dedup boundaries; bounded adaptive/machine plan updates.
- **U13–U16:** fairness/load/quotas; file-first vs SQLite/Postgres and actual durability; precise host/IPC/external platform integration; independent user permissions for cancel/retry/approval.
- **U17–U20:** recurrence/DST/misfire/source-watcher debounce; committed Artifact reference/manifest; understandable localized user terminology; need for global technical Command registry.
- **U21–U24:** if any independent machine Scheme types deserve physical registry; whether a distributed workflow engine is justified; disable-automation effects on live Jobs; multi-node failover/migration.

An empirical acceptance program must first demonstrate a read-only and a file-producing Run, then cancellation, lost-ACK/unknown and safe publication, and only afterward node collaboration and true host lifetime. Performance numbers (admission p95, queue wait, memory peak, cancellation latency, recovery time, unknown backlog) remain unmeasured. A zero count of unknown outcomes is **not** a universal success metric; correct classification and timely reconciliation matter more than concealing uncertainty.

**End-state limitation:** source-identified candidate states and protocols are not a product delivery order. They do not establish a storage backend, host repository, exact external platform API, verified retry/HA, Android release or adopted user acceptance policy.
