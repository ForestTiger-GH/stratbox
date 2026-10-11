# Causal execution observability: events, progress, logs and truthful outcomes

**Scope:** observed facts about analytical execution, progress fidelity, durable diagnostics, concurrent workers, external effects and the boundary with a managed platform. **Status:** maintained scientific/engineering explanation supported by direct pinned code plus proposed contracts. The frozen baseline does **not** prove a common durable JobManager, synchronized multiuser history, complete external Problem registration or deployed UI conformance. Related Science: [durability](../state-and-recovery/authority-durability-and-recovery.md), [capability execution](../capabilities/definitions-plans-and-execution-truth.md), [unknown outcomes](../trust-and-assurance/uncertain-outcome-vs-observed-error.md), [shared problem scope](../collaboration/shared-conditions-and-log-access.md).

## 1. Observability consists of several different kinds of evidence

A generic Python log cannot establish who admitted a Job, in which user context, which step is running, whether an external mutation committed, which bytes were published or which shared participants are affected. A Chat transcript should not become an endless stack-trace stream. Distinct **evidence authorities** need explicit causal links.

| Evidence class | Question answered | Truth owner | Appropriate representation |
| --- | --- | --- | --- |
| **ChatMessage / Thread** | What was discussed, who asked, how to return to it? | Conversation authority | Audience-permitted personal/shared timeline |
| **ExecutionEvent** | What was admitted, begun, committed or interrupted? | Execution authority and trustworthy producer receipts | Compact durable event and qualified outcome |
| **ProgressUpdate** | What is being worked on now? | Worker/domain producer; may become stale | Coalesced stage/count/heartbeat with observation time |
| **DiagnosticFinding** | Why is the data or Result invalid/insufficient? | Domain validator, source parser or solver | Typed finding and analytical/mathematical evidence |
| **ProblemOccurrence / Condition** | What particular fault was observed, where and whom does it affect? | Diagnostic owner; external recorder only if it actually acknowledged registration | Individual occurrences versus aggregated active impact |
| **TechnicalLog / Evidence** | Why/where did exception, I/O or process failure occur? | Actual execution host / platform | Restricted physical file and authorized reference, not public prose |
| **Metrics / Audit** | What is the resource load, and who exercised authority? | Monitoring and policy owners | Aggregates and protected decisions/approvals, not chat events |

Different evidence planes may use one physical directory yet retain distinct write policies, retention, access control and recovery. A JSONL trace is not automatically the operational database, and platform process health cannot determine the validity of a bank report.

## 2. Thread, Work, Run, Attempt and Trace must not share one identity

Even a modest local system benefits from separating:

- `node_id`: an externally managed node/scope when such a contract exists.
- `participant_id / actor_ref`: durable actor link; nickname/display is mutable and may collide.
- `session_id`: particular login/device/session; one participant may have several.
- `thread_id`: persistent conversation identity, unaffected by rename.
- `message_id`: one message.
- `run_id`: one admitted execution episode; several Runs may appear in the same Thread.
- `job_id`: schedulable unit **only where** a real Job authority exists.
- `step_id` is a definition element; `step_run_id` is its concrete invocation.
- `attempt_id`: one physical execution try; retry needs a new Attempt even for the same step.
- `event_id`: unique causal event needed for deduplication and re-delivery.
- `problem_ref`: reference from an actual acknowledged recorder, never fabricated on platform error.
- `artifact_id / version`: published result identity separate from absolute path.
- `trace_id / span_id`: optional transport trace, **not** the Thread ID.

The UI may show one short `run_ref` while diagnostics retain complete IDs. Displaying actor kind `ai` or a friendly name grants no right to invoke another principal's operation, view raw logs or cancel their Work.

Shared timeline order comes from **an authoritative monotonic sequence**, not timestamps from separate devices' clocks. An event can additionally carry UTC occurred/received times and causation event. Two users may create identically titled `New chat` Threads simultaneously without identity collision. A foreign producer's IDs are evidence, but the canonical application event gets its identity/sequence at admission.

## 3. What the pinned Windows client and analytical core actually provide

The [scenario runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/scenarios/runner.py) executes ordered steps sequentially and emits `case_started`, `step_started`, success/failure, LogRecord and ArtifactRecord. This is observed local behavior, **not proof of a durable node-wide authority**. The [Qt coordinator](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/qt_desktop/scenario_coordinator.py) holds one `_thread`/`_active_case` pair and refuses second submission while busy. Therefore multiple parallel Chat commands are a stated user need, **not a delivered property of this revision**.

The [operation runner](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/operations/execution/runner.py) creates an ordinary `logging.FileHandler` under a filename shaped like `case__step__operation.log` and propagates `str(exc)` to an `OperationResult.details`/user-facing message on some failure paths. Static implications: exception text **might** include sensitive local path/URL content, and reused case/step/operation names lack unique Attempt identity in the log filename. These are possible confidentiality/forensic risks, **not verified real-world leaks**. [Runtime logging](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/logging.py) uses a FileHandler without a demonstrated universal rotation/retention guarantee.

[HistoryPersistenceService](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) stores cases/events/artifacts/logs/assignments separately and on certain errors substitutes an empty collection. This is a specific code-flow fact, not a documented field incident. The [session runtime projection](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/runtime/session_runtime.py) reports local active/last state to an external platform; a single `active_job` cannot represent many genuinely parallel Jobs.

Core domains expose heterogeneous quality: collector, escrow, banking forms, industries, FRG and SORS produce different failure/evidence detail. A rich SORS mathematical proof ledger **cannot safely collapse** to `error: str`. A minimal `ProgressSink`/`DiagnosticSink`, or typed callbacks by category, is a **candidate neutral port**; core must remain callable directly from Python/notebooks without requiring Chat, Qt or an external managed runtime.

## 4. Event, progress and status have distinct semantics

A useful **candidate** causal vocabulary includes `thread.created`, `thread.renamed`, `message.created`, `run.submitted`, `run.admitted`, `run.started`, `step.started`, `step.completed`, `artifact.published`, `problem.recorded`, `condition.raised/cleared`, `run.completed`, `run.recovery_required` and `run.reconciled`. This is **not** a list of already emitted system events.

Lifecycle `prepared → admitted/queued → running → finalizing → terminal` is distinct from outcome `SUCCESS | PARTIAL | CANCELLED | FAILURE | UNKNOWN`, and resource health `ready/degraded/unavailable/unknown` is a third axis. A `PARTIAL` outcome may mean 8/10 resources processed with listed residuals. `UNKNOWN` means the effect is not established; `CANCELLED` needs evidence that cancellation actually took effect, not only a button click. Python function success does **not** establish fully written/verified XLSX publication.

Three defensible progress types:
1. **Observed phase** (acquiring, validating, calculating, publishing).
2. **Actual numerator/denominator and units**, when the total is known. `8/10 files` is not necessarily “80% of time remaining.”
3. **Indeterminate activity** with phase/last heartbeat, without fabricated percentage or ETA.

High-frequency progress updates can be throttled/coalesced for the UI rather than inserted unbounded into a durable log. Terminal and effect-relevant events must not be discarded by telemetry sampling. Weighted progress is only meaningful with defensible work weights/denominator; a count of buttons is not proof of time completion.

A possible neutral event envelope has `event_id`, `event_type`, `schema_version`, node/thread/run/job/attempt/step references, sequence, UTC timestamps, causation, safe summary code and typed sanitized payload. This is **research vocabulary**, not an installed dataclass. Filter by audience before transmission. Product event schema version and platform package-manifest version are separate axes.

## 5. Raw exceptions, execution outcome, Problem and Condition

A raw exception may reveal environment identifiers, credentials or source details. It is useful restricted evidence, **not automatically a safe UI message**. Product surfaces need stable machine-readable code and prepared safe summary. Domain validation may fail without any worker crash. A failed optional telemetry sink need not turn a successful analytic result into FAILURE, while a **required** audit sink for destructive work may justify refusal **before** an effect under an admitted policy.

```text
DomainFailure / ValidationFinding / TransportFailure / StorageFailure
  -> execution boundary sets qualified Result and effect status
  -> durable application event / possible local ProblemOccurrence
  -> external ProblemDraft only if verified recorder API exists
  -> actual acknowledged ProblemRef OR explicit local-only/pending/unknown
  -> sanitized audience-specific summary + restricted technical evidence
```

Do not manufacture an external `ProblemRef` when registration timed out or failed. A real local reference may remain with `registration_status=local_only/pending/unknown`. External managed-platform ProblemRef is conceptually distinct from [RFC 9457 HTTP Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html), which describes an individual HTTP error response.

Different observed cases need different records:
- Network download fails before bytes: FETCH_FAILED, not empty valid data.
- HTML arrives instead of XLSX: format validation failure, not an empty economic series.
- Durable admission journal fails **before** acknowledgment: Job was not admitted.
- Worker disappears after possible external write: UNKNOWN and reconciliation required.
- Optional log sink fails after successful domain work: actual Result stays successful, diagnostics degraded (unless mandatory audit policy applies).
- Required evidence sink unavailable before destructive effect: deny/preflight rather than silently proceed.
- Persisted history corrupt: quarantine/diagnostic/degraded, not new truthful empty authority.

## 6. One state authority, distinct data planes and concurrency

Keep the ownership map explicit:
- **External control/runtime:** installation, package, Node/Session, permitted roots, process launch and platform health.
- **Analytical data:** source archives, CSV/XLSX, snapshots, outputs, caches and staging within user-authorized Data root.
- **Product operational state:** Threads, admitted Work/Run/Job, outcomes, read cursors and shared notices under application authority and appropriate system storage.
- **Diagnostics:** application technical logs, per-Attempt trace, emergency crash evidence and separately platform-owned incident/problem journal.

Obtaining a physical storage directory from a managed platform **does not** make it owner of Strategy Box's Chat/Run SQL/JSON schema. A future `StateStorageBinding` might describe `file_directory/sqlite/service`, locality, scope, atomic replacement, flush, backup and retention, but **a universal provider of that form has not been verified in the pinned AppDock baseline**. Existing roots/activation can still be used honestly under their actual published contracts.

Multiple independent worker computations can coexist with **one serialized authoritative state writer**. Different Threads are not mutually exclusive resource namespaces: Runs in one Thread might access independent files; Runs in two Threads may compete for the same output path. Schedule/lock real `read/write/exclusive` resource claims and run-scoped staging, not “one Job per chat” as a universal correctness rule.

### Competing storage models, no automatic winner

| Physical model | Advantage | Counterargument | Correct status |
| --- | --- | --- | --- |
| Five independently overwritten JSON files | Already present | No shared revision, silent corruption/empty projections | Current; insufficient for stronger G2 promise |
| One atomic versioned snapshot | Simple small-state commit and recovery | Full rewrite, single writer, no natural append history | Candidate from persistence research |
| Append-only JSONL with snapshots | Natural causal sequence, potential replay | Torn tail, framing/checksums, compaction and recovery/fencing complexity | Candidate from observability research |
| Host-local SQLite WAL | Transactions, queries and mature tooling | Actual platform SQL binding unverified; network-shared WAL unsafe | Strong conditional candidate |
| Managed PostgreSQL/service | Server concurrency and operations tooling | Network/host/security/administration cost | For proved server workload |
| Full event sourcing or telemetry stack | Deep replay when justified | Complex projections, retention, privacy and extra failure domains | Not an initial obligation |

**Material research conflict:** persistence and observability research lean differently toward one versioned snapshot versus append-only journal. Preserve both as competing designs. Their common justified conditions are one truth authority, honest status, no direct shared-file multiwriter and fault injection. Neither backend nor append/crash durability has been Product approved. The app need not wait for SQLite, but must not promise untested filesystem guarantees. Diagnostic-only read mode is preferable to pretending corrupt history is empty.

[SQLite WAL](https://www.sqlite.org/wal.html) and [isolation](https://www.sqlite.org/isolation.html) support concurrent readers with one host writer; separate computers must **not** directly share a WAL database over a network folder as if it were one safe multiuser authority. Host-local DB behind an authenticated application API is a different potentially workable profile.

## 7. Physical logs and fatal evidence

Four layers of physical trail: **product events, application technical log, per-Attempt log and emergency/crash evidence**. They differ in retention, access and authority.

A candidate structured technical record contains `schema_version`, UTC time, severity, component, stable code, node/process/session/run/step/attempt/event links, sanitized summary and restricted `traceback_ref`. Parameters need field-level `public/private/secret` classification across `display/log/persist`; copying an entire `params` dictionary into shared logs is unsafe.

Python `logging.FileHandler` and `RotatingFileHandler` suit a **single process** but do not guarantee coherent multi-process writes to one physical file. The official [Python Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes) favors a queue/socket listener or separate process files. Use unique Attempt log identity and bounded rotation/retention; pass a scoped `log_ref` and authorized sanitized tail rather than a host absolute path to clients.

An optional emergency path can initialize an early file descriptor and enable [`faulthandler`](https://docs.python.org/3/library/faulthandler.html), `sys.excepthook`, `threading.excepthook` and UI-worker exception boundaries. These increase the chance of preserving a crash trace but **cannot guarantee one after kill/power loss**. `faulthandler` must keep its FD open; rotating/reusing a descriptor needs care. On subsequent restart, reconcile incomplete Runs and external effects instead of inferring cancellation from absent last log line.

The logging sink itself can fail. Do not recursively log failure-about-failure to the same broken sink; use a minimal emergency channel and safe degraded behavior.

## 8. What the external management platform has actually demonstrated

An external platform owns its established roots, activation, packages, Node/Session and process-level conditions. At pinned [AppDock observability implementation status](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/observability/IMPLEMENTATION_STATUS.md), **milestone 5E source implementation was marked complete while native Windows certification remained pending**; planned emergency-sink work was not a guaranteed all-consumer product recorder in that baseline. Do **not** infer a ready cross-product Event/Incident/Problem SDK merely because related types or future milestones appear in the repository.

The platform may observe that a process exited, timed out or was killed. That is not authoritative proof that Strategy Box's `run.completed` or external file publication occurred between a write and lost acknowledgment. Nor must one successful core calculation make a degraded platform Node healthy. Preserve distinct statuses and owners.

Before adopting a new external recorder interface, verify exact available contract/version, feature detection, authorization, error handling and actual installed Windows profile. Until then the application's local, protected diagnostic log remains an honest minimum.

## 9. Relevant external engineering methods and negative findings

[Google Dapper](https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/) motivates causal correlation; it does not require a distributed tracing cluster for a small local app. [OpenTelemetry Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/) distinguishes time, observed time, severity, resources and optional trace links. [W3C Trace Context](https://www.w3.org/TR/trace-context/) transports trace IDs across trusted HTTP boundaries; do not leak user/Thread/node identifiers to external public sites in tracing baggage. [CloudEvents](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md) is a possible transport adapter, not mandatory internal journal schema.

[OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) and [NIST SP 800-92](https://csrc.nist.gov/pubs/sp/800/92/final) address protected log evidence and retention. [Google SRE golden signals](https://sre.google/sre-book/monitoring-distributed-systems/) offer latency, request throughput, errors and saturation as relevant groups, but domain analytics need separate PARTIAL/UNKNOWN distinctions. High-cardinality `run_id/user_id` metric labels can be expensive; trace/log references are better for individual correlation. Prometheus/Jaeger/OTel collectors without demonstrated host need can be overhead.

No external format decides Chat privacy, accuracy of progress %, outcome authority, traceback audience, storage location, migration priority or platform contract version. Standards supply tested questions and options, **not ready Product Decisions**.

## 10. Execution-truth negative test matrix (not run)

| Scenario | Observable distinction required |
| --- | --- |
| Two Runs across two Threads; two Runs within one Thread | Distinct Run/Attempt identities, Thread only links, no universal UI lock |
| Duplicate submit after reconnect | Same admitted Run by idempotency, no repeated external effect |
| Retry after error | New Attempt ID, distinct physical log |
| Worker disappears after remote write | UNKNOWN and effect evidence reconciliation |
| GUI closes | Host Job continuation versus local interruption according to deployed profile |
| Telemetry/progress queue overloaded | Progress may coalesce, terminal/effect events persist |
| JSONL append torn at tail | Tail not accepted as confirmed event; diagnostic recovery |
| Snapshot corrupt, journal intact | Possible verified reconstruction without silent empty reset |
| Journal and snapshot corrupt | Diagnostic-only/read-only, not newly empty authority |
| No disk at durable submit | Run/Job not announced as admitted |
| Log sink fails after successful domain operation | Business success retained; diagnostics degraded |
| Shared Data root unavailable | Scoped Condition, affected Run links |
| User supplies invalid parameter | Safe local problem, no universal emergency alert |
| Exception contains secret sentinel | Secret absent in shared UI and support summary |
| User marks shared Thread read | Per-user cursor, other users keep unread |
| Two Threads share a title | Display title is not identity |
| User manually deletes Artifact | Historical Run remains, file locator unavailable |
| Platform recorder unavailable | Local Problem only; platform ProblemRef not fabricated |
| Authorized root changes | Explicit migration/provisioning, no hardcoded absolute path |
| Android asks for restricted host log | Denied before exposing physical path |
| Files migrate to SQLite | Verified ID/sequence/outcome/reference import, old source read-only |
| Restart after crash | Nonterminal Runs reconciled; stale heartbeat not live execution |
| Devices disagree on local clocks | Canonical event sequence independent of wall clocks |
| Physical log expired under retention | Durable outcome retained with honest unavailable log link |
| Concurrent writers of same output | Resource lock/distinct staging; unrelated writes remain parallel |
| Platform health degraded despite completed XLSX | Run SUCCESS and platform DEGRADED retained independently |

Claims about crash durability require **fault injection** around journal append, fsync, snapshot replace, actual effect commit, lost ACK and restart/reopen inspection. A clean restart is insufficient. Observe actual file bytes/state, journal IDs, viewer permissions and UI presentation. Numeric retention limits, allowable concurrency and measured load remain Product/Operations decisions.

## 11. Unresolved questions and reopening

Open: which Work/Job survives local GUI crash and under which profile; execution authority placement; currently verified vs future external storage API; who can read protected logs and shared Threads; when a common incident warrants broadcast; which effects require audit before execution; when stage progress is measurable; terminal-event contract; safe one-time migration from five JSON files; per-Run metadata and read cursors; whether separate incident-management services or mobile push are actually necessary.

Only direct code/protocol decisions, admitted requirements and installed independent tests can narrow these alternatives. Until then, proposed types and implementation order remain **qualified hypotheses**, not a ready production contract.

**Negative conclusion:** observability is not complete merely because a log panel, trace ID card or Python FileHandler exists. Conversely, a full Event framework, SQLite, OTel or Web endpoint without actual reliable outcome, effect and authorization semantics would add complexity without establishing truth.
