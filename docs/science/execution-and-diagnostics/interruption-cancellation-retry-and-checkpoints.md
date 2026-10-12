# Interruption, cancellation, retries and verified checkpoints

**Scientific question:** what the product can safely promise when a user closes a window, an analytical worker dies, a file publish is interrupted, a retry is requested, or a cached intermediate result is reused. **Status:** explanatory engineering Science with dated code observations, source-specific user preferences and explicit candidate options; no fully durable JobManager, cancellation pipeline or fault-injection conformance is certified.

## 1. The user's intent is a smaller contract than a durable workflow engine

The developer's request in the studied original is unusually specific: keep a visible history of commands, make it obvious when processing was interrupted, **generally stop the local running computation when the program closes or is interrupted**, and protect important output files with short, safely staged publication. The user can then decide whether to repeat work. Compact yellow/red status markers are preferred to an elaborate control panel. Later tray/background operation may be helpful if an actual supporting runtime exists.

This should be understood as a **local interactive execution default**, not a guarantee that ending a Web session must kill a separately hosted job. Five different events must be separated: closing the visible window, minimizing to tray, explicit application exit, losing a remote client connection, and abrupt worker/process failure. A future host profile may continue jobs after a client disconnects only if such a host has an independently surviving executor and accepted user contract.

The restrained research thesis is **durable accounting, disposable computation, safe effects**. A durable admission/Run record can survive even when its Python stack no longer runs; stable checkpoints are optional optimizations, not promises of automatic process resumption. This is a preference supported by the source user intent, but the first release's state retention, exact UI shutdown behavior and backend remain Product Decisions.

## 2. Five lifetimes; no automatic table per noun

| Concept | Independent identity when needed | Why it matters after an error |
| --- | --- | --- |
| **Work** | Long-lived user goal, criteria and review across multiple Runs | A completed calculation may still require expert acceptance |
| **Run** | One intentional launch with frozen scenario/parameters/source context | The user's explicit replay produces a new Run |
| **Job** | Queue/worker ownership and resource reservations | One Run can have one Job; many are optional |
| **Attempt** | One physical try by a worker | New retry gets new Attempt, retaining the prior failure/effect evidence |
| **Effect / Receipt** | Concrete modification beyond process memory | Worker death does not prove whether a file or network change took place |

Thread/Chat is discussion and a user-visible timeline, not identical to Run or an effect log. `AutomationRule.enabled` describes a future trigger, not a currently executing Job. An operation step may have a `StepRun` identity in a multi-step plan but need not become a standalone SQL table.

Illustrative example: a user Work to build an escrow report has R1 (A1 interrupted by network, A2 layout failure) and then a consciously requested R2 (A3 succeeded, artifact published); Work remains open until the analyst checks the actual report. For a one-step ad hoc download the product may create no separate long-lived Work entity. Identity follows independently needed lifecycle and evidence, not ontology completeness.

## 3. Current Windows evidence: a functional local baseline with unproven life-cycle guarantees

The pinned [Windows coordinator](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) admits one active `QThread`/Case, rejecting a second while busy. The [ScenarioRunner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) runs ordered steps with fail-fast/warning behavior and records events/artifact paths. The [OperationRunner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/execution/runner.py) maps exceptions to `OperationResult(ok=False)` plus raw string details. A `RunRecord` representation coexists with `ScenarioRunCase` but **not** as a proven unified Job/Attempt authority.

The case model advertises statuses including `queued` and `cancelled`, but their presence in a literal enum is **not evidence** of a tested cancel/queue pipeline. The actual runner mainly exercises running/success/failure, and a partial source failure with “continue with warnings” may be mapped to a seemingly successful Case without a separate complete/partial qualification. A created `ArtifactRecord` from a returned path does not prove written bytes, publication or downstream usability.

The [history persistence](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) writes five unrelated mutable JSON files, treats corruption as empty data and has no unified accepted-run revision or startup effect reconciliation. The [background store](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/background/store.py) is an in-memory scaffold rather than a scheduler.

The [core LocalFileStore](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/base/filestore/local.py) uses a direct `wb` write path that may truncate an existing file before replacement bytes are complete. The [CBR collector's save path](https://github.com/ForestTiger-GH/stratbox/blob/beb3e4842614b153ba0c0ccc1e33ae4d50698821/src/stratbox/macrobanks/cbr_file_collector/save.py) creates a ZIP or multiple separate files, not a universal all-or-nothing bundle. [FRG cleanup](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/frg/cleanup.py) offers an effect plan and per-row execution with potential partial success; These direct code facts are static and do not prove a reported production corruption incident.

An external platform's process/Node/job status may help diagnose a child exit, but it is not an authoritative bank analytical Job. Its [studied observability maturity](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/observability/IMPLEMENTATION_STATUS.md) does not certify a general product scheduler or recorder API for Strategy Box.

## 4. An outcome has several dimensions

Use **lifecycle**, **attempt observation**, **external effect** and **user-view status** independently:

| Observation | Evidence-supported interpretation |
| --- | --- |
| `submitted` | A client expressed intent; acceptance may not yet have committed |
| `admitted/queued` | Application authority accepted the Run/Job under stated durability, not necessarily started |
| `started` | A specific worker Attempt was observed running |
| `cancel_requested` | Authorization and request recorded; worker may still be executing |
| `cancelled` | Execution actually stopped and effect statuses are separately qualified |
| `failed` | A known domain/process action failed, not necessarily that all external effects were absent |
| `interrupted` | Execution ceased without normal terminal path |
| `partial` | Known subset of expected results/effects exists; scope and missing inputs disclosed |
| `outcome_unknown` | External action may have happened, receipt/postcondition insufficient |
| `succeeded` | Meaningful confirmed completion within explicitly defined domain/effect/acceptance scope |

Terminal execution and later truth discovery can coexist: an Attempt can be historically interrupted, while subsequent reconciliation confirms the file had already been published. Never retroactively erase an original failure observation to make history look simpler.

A candidate authority admission path: validate permissions/parameters → freeze effective request and source definitions → commit Run+event+revision+idempotency identity → dispatch worker → record Attempt start → record dangerous effect intent → execute domain work → verify actual effects/result → commit terminal outcome/evidence → publish safe UI projection. If a promised **durable admission** could not be written, a destructive effect must not begin; an explicitly labeled ephemeral pure calculation is a different profile.

## 5. Cancellation: safe points are operation-specific

Proposed cooperative semantics:
1. User requests stop; authority checks grant and records who, when, on which Run.
2. Queued work can be cancelled before any Attempt.
3. Running work receives a neutral `CancellationView` or equivalent token and checks **safe points**.
4. Previously performed effects get confirmed/partial/unknown receipts; no rollback is inferred.
5. The UI only shows final “Cancelled” when the worker/effects justify it. Until then, “Stop requested”.

[Qt `QThread.requestInterruption()`](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html) is advisory; [Python `Future.cancel()`](https://docs.python.org/3/library/concurrent.futures.html) does not stop an already-running job. Force-termination of an arbitrary Qt thread can break invariant or leave incomplete writes. A subprocess may be killed when necessary, but its associated file/network effect still requires reconciliation.

Safe points by domain:
- CBR batch collector: between sources and after byte validation; an in-flight HTTP request may complete/timeout.
- XLSX export: before building, between worksheets, and **before** final publish; incomplete staging never visible as final.
- Sequential Scenario: before/after individual operation steps.
- SORS/solver: between known computational phases/native solver calls; do not inject exceptions inside unsafe native state.
- Destructive FRG cleanup: before each authorized row effect, with per-target receipt for any completed action.
- Remote effect: before sending and after provider receipt; lost response may leave unknown outcome.

If an Operation has no cooperative safe point, expose `cancel_support=none/deferred` as a **truthful candidate descriptor**, not a fake immediate stop button.

**Local close behavior:** stop admitting new jobs, request graceful termination, wait only within a justified bound, persist interrupted/unknown result and reconcile on next startup. UI can offer “Stop and Exit” versus “Stay”; tray-mode hide versus actual exit is distinct and **must** match released functionality. **Host close behavior:** closing a client only disconnects if the separately running host actually exists and survives.

## 6. Four unlike “repeat” commands

| Action | Identity change | Eligibility |
| --- | --- | --- |
| **User ReplayRun** | New Run and usually new logical invocation key, linked to predecessor | Authorized fresh intent, explicit input/version policy |
| **Executor RetryAttempt** | New Attempt under same admitted Run/Job | Safe/known-idempotent effect, a verified absence of prior effect, or provider dedupe |
| **ResumeFromCheckpoint** | New execution using a specifically verified prior stage | Source, method, params, schema and result checksum match |
| **ReconcileEffect** | Adds evidence about old effect, **does not perform it again** | Ambiguous outcome / delayed receipt / viewer discrepancy |

These also differ from **compute cache reuse** across independently requested tasks and **resource serialization** for two writers of one XLSX. Request dedup prevents an identical network submission from admitting a second logical Run; cache reuse shares previously calculated content under source/method identity; lock protects a physical resource. Matching parameters alone do **not** establish the user did not intend two separate new Runs.

Retry policy must be attached to a particular Operation/effect:
- Pure deterministic computation can be recomputed given pinned inputs/assumptions.
- Read-only GET is typically retryable with bounded budget and data-vintage qualification.
- Content-addressed cache materialization can be retried if provider publication guards are reliable.
- Verified staged replacement requires stable generation/expected-target identity.
- Append/counter needs a provider-supported idempotency identity.
- Destructive delete/move and external POST are **not automatically retried** without confirmed effect semantics.

Nested retries in a core HTTP downloader and a future JobManager should share a **total retry/timeout budget** rather than multiply attempts unexpectedly. The general “exactly once” claim is not available across arbitrary network/file effects. See [effect reuse](../trust-and-assurance/computation-reuse-and-external-effects.md).

## 7. What a checkpoint actually proves

Three things often called checkpoint:
1. **Execution milestone:** a phase completed, useful for display/recovery diagnosis but not necessarily reusable.
2. **Verified stage output:** a persistent intermediate dataset with checksum, frozen method/source versions and compatibility record; may safely support later reuse.
3. **Process-memory snapshot:** stack, solver internals, I/O and object graph saved for instruction-level resume; usually too complex and unreliable for initial Strategy Box use.

**Qualified reuse** needs relevant fingerprint equality: Operation and compatible code revision, parameter snapshot, source bytes/vintage, registry/mapping versions, schema/layout, locale/time assumptions, numeric dependencies and result digest. A chat line saying “step 2 complete” is not sufficient. A staged XLSX that has not passed validation is not a verified checkpoint; a published artifact has separate external-effect status.

Illustrative milestones: official source hash manifest → validated canonical table → checked derived result → temporary XLSX (NOT reusable as final) → publish receipt. A demanding SORS solver may preserve validated phase/constraint data, but serializing a whole active solver/process is not safe merely because a Python object can be pickled. Any additional solver checkpoint requires real cost savings and API support proven by tests.

**Default after crash:** do not silently restart old computation. Preserve original Run, mark unverified outcome and offer an authorized *new* run. Distinguish “repeat against previous inputs” from “refresh upstream source then calculate”, because URL and reported period may stay the same while bytes/vintage changed.

## 8. Artifact publication matters more than perfect workflow replay

Local one-file candidate sequence:
```text
Resolve permitted destination and expected prior generation
  → unique staging file in compatible destination area
  → write and close staging, leaving prior published file intact
  → validate byte size/hash/format and domain worksheets/periods
  → persist publish intent
  → backend-specific conditional replace/commit
  → verify published generation, persist receipt/catalog reference
  → update user-visible result, remove safe orphan staging
```
A `FileStore.rename()` method does **not** promise atomic replacement or crash durability on every backend. [Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace) is a useful local primitive subject to filesystem constraints; `fsync` and directory durability need OS/FS validation. The desired guarantee is **old valid or new valid visible generation under verified conditions**, never a blanket claim about all network Data roots.

Four bounded publication grades:
- **A — verified local replace**, on an explicitly qualified FS with appropriate durability tests.
- **B — verified backend staged commit**, using the provider's actual receipt/conditional API.
- **C — best-effort write**, where the writer returned without sufficient atomicity/durability proof; label `WRITTEN_UNVERIFIED`, not fully published.
- **D — ambiguous completion** after possible external commit and lost ACK; `OUTCOME_UNKNOWN`.

Ten independent outputs are not made group-atomic by ten individual renames. Choices: publish independently and declare PARTIAL on some failures; stage a versioned directory plus one manifest/pointer; or publish a verified ZIP if that is the product artifact. Every choice reflects downstream contract and actual provider support.

The crash-window matrix matters: before staging, during write, after close but before verify, after verify before publish, during rename/commit, after effect but before ACK, after receipt but before chat, and after chat but before durable state. A correct system reads the actual evidence at each window; visible UI must follow established state, not precede a promised durable commit. More in [artifact Science](../artifacts/output-identity-publication-and-availability.md).

## 9. Effect reconciliation is an investigation, not a retry

An **EffectIntent** can capture stable logical effect ID, parent Attempt, target/generation, expected prior revision, input digest and time. A **Receipt** can capture outcome, actual target generation/hash, confirmation method and observation time. In an ambiguous crash, query the correct namespace under valid permission and backend consistency guarantees. Three possible conclusions:

- **CONFIRMED:** same intended effect and generation established from native ack or verified postcondition.
- **NOT_APPLIED:** negative evidence genuinely proves this particular operation was absent.
- **UNKNOWN:** current evidence insufficient, stale/permission-denied/inaccessible or contradictory.

`exists(path)` is not proof that the current Run created it: the object could predate the Attempt or have been published by someone else. An absent path is not proof that a delete effect was authorized or applied. For destructive actions with limited receipts, manual inspection is a legitimate end state of system automation; the Work retains an unresolved obligation until decided.

Compensating actions (cf. [Garcia-Molina and Salem, *Sagas*](https://www.cs.princeton.edu/research/techreps/598)) create **new** external effects; they are not guaranteed time reversal. Already sent notice, deleted sole file or overwritten remote resource cannot be magically rolled back. The safest early principle is to validate a new artifact before deleting its last good predecessor.

## 10. Executors and concurrency follow workload and resource ownership

| Physical executor | Main benefit | Important caveat |
| --- | --- | --- |
| Current one Qt `QThread` | Keeps the desktop UI responsive for one scenario | Qt lifetime, no multi-run, unsafe hard terminate |
| Bounded threads/async | Lightweight I/O concurrency | CPU-heavy GIL impact, cooperative cancel only |
| Subprocess/process pool | Better isolation of heavy solver/large Excel work | Serialization, startup, memory, kill/reconciliation complexity |
| One application JobManager plus adapter | Own admitted state and resource policy regardless of worker type | Needs true storage/permission/effect correctness |
| Celery, Prefect, Temporal, Airflow | More advanced scheduling/durable workflows at different scales | Broker/service burden, repeated activity semantics and additional owners |

Use an operation's network/CPU/memory/effect profile and measured device capacity rather than “one thread per chat” or an arbitrary N-second timeout. Different chats can run independent read-only jobs in parallel, but two tasks writing the same canonical workbook need exclusive claim or generation-specific outputs. A **resource lock** prevents concurrent local writers; **worker lease/fencing** prevents a stale remote/disconnected worker publishing after ownership changed. For single-process local execution one resource lock may suffice; leases are only justified once there is real takeover/concurrency.

The original suggested resource dimensions: CPU-heavy indicator, memory class, network source key, output namespace key, explicit read/write/exclusive file sets and Node owner. Counts, queue fairness and strict quotas require benchmarks on actual target PCs.

Scheduled or AI-origin work should submit through the *same accepted Run/Job path* when implemented; a separate invisible background executor would duplicate truth. Enabling a schedule does not mean an instance is running. Disabling future triggers does not automatically cancel a job already admitted unless policy specifically requires it.

## 11. Minimal UX and diagnostics without inventing capabilities

The source recommends modest chat cards: queued, running with known stage, stop requested, verified cancelled, succeeded, partial, failed, interrupted or unknown, with accessible icon/short text and a relevant action. Color cannot be the only status. The Run event and its diagnostics are different from chat messages; restricted exception paths/tokens/headers must not be exposed to all team members.

Progress has three legitimate forms: stage, counter with real denominator, or indeterminate activity. A progress timer/heartbeat is not proof of worker survival after disconnect. A small expandable inspector can include Run/Attempt timeline, saved artifacts, evidence and safe error/ref, with raw technical log access separately authorized. The platform's health projection is independent of domain error and does not authorize a new terminal Run outcome.

The original's **26 proposed negative tests** include lost submit ACK, process crash before/after effect, zero-disk admission, malformed history, cancelled-before/after publish, concurrent output writer, scheduler false-positive, per-attempt log integrity, multi-file partial output, clock skew, stale host status, repeat under changed source, safe error redaction and effect-intent failure. These are **not performed tests**. A real local/host certification needs fault injection on process/FS/provider boundaries, plus actual presented UI state.

## 12. Physical persistence conflict and deployment decisions

The topic-02 source originally promoted local SQLite as the best immediate transactional JobStore with sample `run/attempt/effect/event` tables. Late topic-03 and topic-08 sources shifted toward **external-platform-provisioned storage** with an allowed single-writer atomic snapshot or append-only journal first. These differences must remain visible; this article selects **no SQL/file backend**. Both families require a single authoritative writer, consistent commit before dangerous effects, revision conflict protection, recoverable evidence, and no network-shared SQLite WAL across different hosts.

Current physical profiles remain distinct:
- **L0 local interactive:** stopping/closing the desktop interrupts work, but history/outcome persists according to accepted durability.
- **L1 local tray:** hiding the window keeps the *same process* running; only truthful after implementation.
- **L2 detached local worker:** real independent process can outlive GUI, requires supervisor and independent state.
- **H1 shared host:** one host authority and clients; client disconnect is not job cancellation.
- **H2 distributed workers:** conditional stronger lease/fence/partition semantics.

No profile beyond the pinned Windows local foreground was certified in the source. Whether to support L1/L2/H1, what persist/backup/retry guarantees they offer, exact cancellation UI, thread/process pool, resource quotas, user permissions and effect audit retention remain Product/Operations decisions.

**Negative conclusion:** ordinary process shutdown, a boolean `ok`, a decorated Qt thread, a status enum or a path returned by FileStore cannot establish durable, effect-safe, resumable, independently trusted work. Conversely the need to distinguish these truths does **not** compel an always-running multi-service workflow platform.

## Primary execution-control research: fifteen distinctions and user-authority limits

The frozen October 7 execution-control study, §XXIV (\`#L2073-L2091\`), blob `0cf37ddf3b0b44495a30ec1d31117fc9dfc70671`, proposed fifteen explicit distinctions about parameters, cancellation, actor authority and portable clients. English formulations here are **source-line-traced Research**, not implemented policy, Product decisions or passed tests.

| Research source item | English candidate behavior / question | Exact original line |
| --- | --- | --- |
| `SB-SRC-0026/EXEC-01` | User-facing Scenario and atomic machine Operation have distinct purpose | L2075 (\`#L2075\`) |
| `SB-SRC-0026/EXEC-02` | Composite Scenario needs concise user parameters mapped explicitly to its steps | L2076 (\`#L2076\`) |
| `SB-SRC-0026/EXEC-03` | Prefer useful defaults and keep technical effect policy values out of novice forms | L2077 (\`#L2077\`) |
| `SB-SRC-0026/EXEC-04` | Remembered user values should have an explicit scoped ParameterProfile identity | L2078 (\`#L2078\`) |
| `SB-SRC-0026/EXEC-05` | Actual Case/Run parameters require immutable execution-time snapshot | L2079 (\`#L2079\`) |
| `SB-SRC-0026/EXEC-06` | Personal ParameterProfiles and shared presets are different policy/ownership objects | L2080 (\`#L2080\`) |
| `SB-SRC-0026/EXEC-07` | Cancellation is cooperative and checked at safe points, not thread termination | L2081 (\`#L2081\`) |
| `SB-SRC-0026/EXEC-08` | A cancel request is not itself terminal cancellation | L2082 (\`#L2082\`) |
| `SB-SRC-0026/EXEC-09` | Late cancel must not rewrite a committed terminal success/failure | L2083 (\`#L2083\`) |
| `SB-SRC-0026/EXEC-10` | Forced worker termination leaves unknown effect until reconciliation establishes facts | L2084 (\`#L2084\`) |
| `SB-SRC-0026/EXEC-11` | Shared multiuser Case authority belongs to executing node, not one client's JSON history | L2085 (\`#L2085\`) |
| `SB-SRC-0026/EXEC-12` | Cancelling another participant's Job requires verified principal-specific authorization | L2086 (\`#L2086\`) |
| `SB-SRC-0026/EXEC-13` | Foreground/background/remote/AI use the same admitted execution authority | L2087 (\`#L2087\`) |
| `SB-SRC-0026/EXEC-14` | AI access limited to permitted typed domain Operations and effects, never arbitrary shell/Python | L2088 (\`#L2088\`) |
| `SB-SRC-0026/EXEC-15` | Platform-neutral application meaning should serve later Android without Qt duplication | L2089 (\`#L2089\`) |

**Competing operating profiles:** the source favors a durable shared-node JobManager, but the later direct user response expects **local foreground** calculation to terminate when its application closes. Host survival cannot be generalized to local Qt, and a forced thread termination is not proof of a safe rollback. Permission to cancel another user's work is a proposed authorized capability dependent on actual principal/grant semantics and verified platform contracts.

**Material qualification:** remembered parameter preferences, shared presets and the exact immutable Run parameter snapshot are distinct identities. Hidden advanced form fields cannot bypass input or effect-policy validation. Human and machine callers remain subject to the same authorized domain behavior; client portability does not require creating physical repositories prematurely. These fifteen proposals do not certify all other original claims from the 2,113-line Research file.
