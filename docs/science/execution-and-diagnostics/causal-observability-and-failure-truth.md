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

## 12. Original observability Research: fifteen fault injections and fifteen proposed boundary theses

The frozen October 7 observability source, §§51 and 55 (`#L2088-L2265`), SHA `c4ec86841e2a92299adbefeb6a6a387b7106f587`, names **fifteen** distinct fault injection situations and **fifteen** system-boundary claims. They are preserved here in English, with original source line per item. **These are Research tests/proposals, not successful installed-system fault injections or independent admission of external platform capabilities.**

| Research item | Exact source scenario or English-qualified boundary thesis | Original source line |
| --- | --- | --- |
| `SB-SRC-0030/FAULT-01` | disk full | L2093 (`#L2093`) |
| `SB-SRC-0030/FAULT-02` | log directory readonly | L2094 (`#L2094`) |
| `SB-SRC-0030/FAULT-03` | problem journal unavailable | L2095 (`#L2095`) |
| `SB-SRC-0030/FAULT-04` | corrupt local state | L2096 (`#L2096`) |
| `SB-SRC-0030/FAULT-05` | network unavailable | L2097 (`#L2097`) |
| `SB-SRC-0030/FAULT-06` | remote node disappears | L2098 (`#L2098`) |
| `SB-SRC-0030/FAULT-07` | clock skew | L2099 (`#L2099`) |
| `SB-SRC-0030/FAULT-08` | duplicate remote event | L2100 (`#L2100`) |
| `SB-SRC-0030/FAULT-09` | out-of-order remote event | L2101 (`#L2101`) |
| `SB-SRC-0030/FAULT-10` | process hard kill | L2102 (`#L2102`) |
| `SB-SRC-0030/FAULT-11` | worker thread crash | L2103 (`#L2103`) |
| `SB-SRC-0030/FAULT-12` | UI exception | L2104 (`#L2104`) |
| `SB-SRC-0030/FAULT-13` | unraisable exception | L2105 (`#L2105`) |
| `SB-SRC-0030/FAULT-14` | artifact write succeeds but response lost | L2106 (`#L2106`) |
| `SB-SRC-0030/FAULT-15` | cancel during commit | L2107 (`#L2107`) |
| `SB-SRC-0030/THESIS-01` | Case represents user-facing objective while Job is schedulable execution unit | L2249 (`#L2249`) |
| `SB-SRC-0030/THESIS-02` | Foreground/background/remote/AI invocations should use governed common execution admission | L2250 (`#L2250`) |
| `SB-SRC-0030/THESIS-03` | Stable operation name differs from a specific OperationRun identity | L2251 (`#L2251`) |
| `SB-SRC-0030/THESIS-04` | Each physical retry requires a separate Attempt identity | L2252 (`#L2252`) |
| `SB-SRC-0030/THESIS-05` | Case ID can be used as a correlation key, without erasing independent Trace or Run IDs | L2253 (`#L2253`) |
| `SB-SRC-0030/THESIS-06` | Candidate terminal outcomes distinguish SUCCESS, PARTIAL, CANCELLED, FAILURE and UNKNOWN | L2254 (`#L2254`) |
| `SB-SRC-0030/THESIS-07` | Warnings are diagnostics, not another terminal outcome | L2255 (`#L2255`) |
| `SB-SRC-0030/THESIS-08` | Domain core should emit structured Result/Progress without importing external platform lifecycles | L2256 (`#L2256`) |
| `SB-SRC-0030/THESIS-09` | Application owns Case/Job projections but not platform-owned problem state | L2257 (`#L2257`) |
| `SB-SRC-0030/THESIS-10` | External platform may own its Node/Session problem registry only when its actual contract verifies that boundary | L2258 (`#L2258`) |
| `SB-SRC-0030/THESIS-11` | Raw exception and traceback remain restricted technical evidence | L2259 (`#L2259`) |
| `SB-SRC-0030/THESIS-12` | Physical logs require bounded local retention, rotation and redaction | L2260 (`#L2260`) |
| `SB-SRC-0030/THESIS-13` | Shared Conditions can be shown to affected users without exposing others' raw errors | L2261 (`#L2261`) |
| `SB-SRC-0030/THESIS-14` | AI caller is an audited permission-constrained actor, not a privileged parallel runtime | L2262 (`#L2262`) |
| `SB-SRC-0030/THESIS-15` | Windows and future Android should preserve portable execution-observability semantics while rendering differently | L2263 (`#L2263`) |

**Potentially misleading literal readings:** an existing `Case` may be a presentation/legacy abstraction rather than the globally authoritative Work record. A Case ID is a useful correlation **reference**, but does not make every `Attempt`, `Trace` or external incident share the same identity. The source's statement assigning canonical platform problems is a **proposed responsibility split**, bounded by actually verified external platform interfaces and the application's independent Problem/Condition semantics. Broadcasting another user's raw traceback is not implied by shared team error awareness. Losing a log sink must not turn a completed pure read into a failed effect; conversely losing a required audit sink can block an unsafe mutation. Each test needs a concrete deployed profile and a negative-capable observed oracle.

**Preservation limit:** thirty row-addressed proposals of a 2,372-line primary source are materially accessible in canonical Science, but the source's broader examples, physical logging policies, unresolved questions and dissent require further complete semantic/independent review. No conformance result is asserted by this appendix.

## Source topic 08: twenty observability and causal diagnostic distinctions

The dated Execution Observability and Diagnostics Research distinguishes a status visible to an analyst from operational, technical and platform-grounded evidence. These **20 source-line English interpretations** preserve different truth owners, user-visible effects, exception privacy and actual uncertainty. The source's proposed architecture is **not** an implemented incident recorder, production alarm center or passed reliability benchmark.

| Source item | Qualified meaning | Material boundary | Exact frozen line |
| --- | --- | --- | --- |
| `SB-SRC-0561/OBS-01` | ChatMessage, ExecutionEvent, ProgressUpdate, DiagnosticFinding, ProblemOccurrence and restricted TechnicalLog serve different consumer questions and evidence owners. | `SIX_EVIDENCE_FAMILIES` | L305 (`#L305`) |
| `SB-SRC-0561/OBS-02` | Metrics aggregate workload and Audit documents actions/grants; neither is simply one more UI event. | `METRIC_AUDIT_BOUNDARY` | L312 (`#L312`) |
| `SB-SRC-0561/OBS-03` | Terminal Run outcome needs its own durable fact; a step-completion or volatile heartbeat does not imply overall Run completion. | `DURABLE_EVENT_GRANULARITY` | L329 (`#L329`) |
| `SB-SRC-0561/OBS-04` | A stage label can be meaningful without a numerical percentage; numeric progress needs a real measurable denominator. | `PROGRESS_STAGE_EVIDENCE` | L335 (`#L335`) |
| `SB-SRC-0561/OBS-05` | An activity spinner may truthfully convey uncertainty where estimating 80% or ETA would fabricate precision. | `PROGRESS_UNCERTAINTY` | L337 (`#L337`) |
| `SB-SRC-0561/OBS-06` | Cancellation requested is not cancellation proved; a worker may already have applied external effects. | `CANCEL_REQUEST_DISTINCTION` | L378 (`#L378`) |
| `SB-SRC-0561/OBS-07` | Timeout after a write is not a demonstrated failure of that write; external effect outcome can remain UNKNOWN. | `AMBIGUOUS_EFFECT_STATUS` | L379 (`#L379`) |
| `SB-SRC-0561/OBS-08` | App-local ProblemRef and a confirmed platform ProblemRef cannot be substituted if registration failed or remained uncertain. | `PROBLEM_OWNER_BOUNDARY` | L400 (`#L400`) |
| `SB-SRC-0561/OBS-09` | Shared product events need not include raw tracebacks or secrets; typed technical evidence belongs in restricted channels. | `EVENT_VS_LOG_PRIVATE` | L671 (`#L671`) |
| `SB-SRC-0561/OBS-10` | Per-attempt technical logs require causal IDs and controlled access, distinct from the Artifact presented to all thread members. | `ATTEMPT_CAUSAL_EVIDENCE` | L675 (`#L675`) |
| `SB-SRC-0561/OBS-11` | Emergency crash evidence must survive failure of ordinary UI/logger where practical, without recursion when the log sink itself fails. | `CRASH_EVIDENCE_DEGRADED` | L677 (`#L677`) |
| `SB-SRC-0561/OBS-12` | Serializing arbitrary params with str(params) risks secrets; display/log/persist views require field-level classification and redaction. | `PARAMETER_LOG_REDACTION` | L701 (`#L701`) |
| `SB-SRC-0561/OBS-13` | Standard Python rotating file handlers are not automatically multi-process write-safe; select one writer or separate attempt logs. | `LOG_MULTI_PROCESS_COST` | L705 (`#L705`) |
| `SB-SRC-0561/OBS-14` | Process exit or supervisor signal does not establish domain result/effect completion; recovery requires source-specific reconciliation. | `PROCESS_EXIT_NOT_DOMAIN_OUTCOME` | L720 (`#L720`) |
| `SB-SRC-0561/OBS-15` | Successful analytics with degraded optional diagnostics should retain a qualified success and separate diagnostics condition. | `DIAGNOSTIC_HEALTH_SEPARATE` | L729 (`#L729`) |
| `SB-SRC-0561/OBS-16` | A platform incident reference must not be fabricated after failed registration; an actual local reference can be retained distinctly. | `PLATFORM_INCIDENT_PROVENANCE` | L733 (`#L733`) |
| `SB-SRC-0561/OBS-17` | A shared timeline can expose bounded run/author/effect context without granting all participants raw technical logs. | `SHARED_TIMELINE_SCOPE` | L820 (`#L820`) |
| `SB-SRC-0561/OBS-18` | Repeated technical Problem occurrences may form one shared Condition while preserving the individual Attempt records. | `CONDITION_VS_OCCURRENCE` | L843 (`#L843`) |
| `SB-SRC-0561/OBS-19` | Alert deduplication should use stable problem/resource/scope rather than exception text and should retain individual diagnostic facts. | `ALARM_FATIGUE_WITH_CAUSALITY` | L855 (`#L855`) |
| `SB-SRC-0561/OBS-20` | A chat is neither a CPU queue nor an exclusive output resource; simultaneous chats need independent resource admission. | `CHAT_NOT_RESOURCE_LOCK` | L882 (`#L882`) |

**Opposing constraints:** logging everything in every chat violates least-privilege, expands storage and hides meaningful alerts in noise. Suppressing logs entirely loses causal evidence after failures; different severity and retention owners are needed. A UI progress percentage without a denominator is not truthful observability, and client disconnect is not Run failure. A future resource-aware multi-Job engine may need locks, leases and durable events, while present Qt local sequential execution does not acquire them by displaying extra status cards. No particular platform incident API or alert-delivery confirmation is assumed to exist.

**Coverage limit:** twenty source-row meanings only; the remaining 1,264-line source, external log/trace reference currency, installed fault-injection behavior and independent scientific assurance remain open.


## 13. Observability failure of observability: dual outcomes, early evidence, audit and support

**Source-conservation amendment:** direct [pinned AppDock `Recorder` and `ProblemQuery` contracts](../../current-how/appdock-public-problem-contracts.md) establish the two storage-neutral external registration failure states and the unconfirmed-reference caveat without establishing an installed Strategy Box adapter. The frozen 2026-10-07 original observability research (`#L1434-L1658`), Git blob `c4ec86841e2a92299adbefeb6a6a387b7106f587`, distinguishes ten materially different failure modes and capabilities. These are **Research-proposed models**, not installed Strategy Box APIs, a certified platform recorder, default retention policies or tested failover. The ten exact source-to-meaning candidate routes live in the existing consolidation lineage ledger; their independent conservation check remains open.

### 13.1. Separate operation outcome from the observation-recording outcome

The original research makes an important **two-axis assertion**: a known failed domain operation remains `FAILURE` even when its attempt to register a separate ProblemOccurrence cannot reach the recording authority. In particular:

| Observed action/receipt | Domain operation truth | Diagnostic registration truth | Correct public-safe explanation |
| --- | --- | --- | --- |
| Domain operation failed; recorder acknowledged accepted occurrence and returned a valid reference | `FAILURE` | `RECORDED`, real `ProblemRef` | Failure known; traceable problem evidence is available to authorized readers. |
| Domain operation failed; recorder rejected/unavailable and no write acceptance was observed | `FAILURE` | `NOT_WRITTEN` *only when known* | Domain failure remains valid; external problem record unavailable; local protected evidence may exist. |
| Domain operation failed; recorder request timed out after possible acceptance | `FAILURE` | `OUTCOME_UNKNOWN` | Analytic failure is established but recorder acceptance is unresolved; query/reconcile before retry. |
| Domain work succeeded; optional debug log sink failed | Qualified business success | `DEGRADED` diagnostics | Do not turn success into failure solely due to missing best-effort log, but disclose limited diagnostic evidence. |
| Pre-effect mandatory audit cannot be established | No destructive effect may be admitted under that policy | `BLOCKED_AUDIT_REQUIRED` | The dangerous action was withheld; no false success and no fabricated audit receipt. |

The **combined app/diagnostic outcome matrix** above is conceptual. However, the pinned **public AppDock contract** already defines `RegistrationState.NOT_WRITTEN` and `RegistrationState.OUTCOME_UNKNOWN` for registration failures; successful `Recorder.record` returns a real `ProblemOccurrence`, not a third success-state enum. The optional `candidate_ref` in a `RegistrationFailure` remains unconfirmed. A failed local API call is not proof that a remote recorder did not commit a record; distinguishing *confirmed rejection* from *lost acknowledgment* matters for deduplication and for avoiding fabricated `ProblemRef` identifiers. If the platform has not provided a verifiable registration or reconciliation contract, retain the locally supported diagnostic state and accurately label missing evidence. Refer to original §36 observability self-health (`#L1434-L1467`).

**Audit nuance:** the original calls for blocking destructive operations if a **mandatory** audit stream is unavailable. This is a sound conditional safety gate when audit-before-effect is an accepted requirement. It should not be silently extended to ordinary read-only calculations or made into a claim that every log sink is an authoritative transaction journal. The final authority for accepting such an effect remains the Strategy Box application host; an actual external platform recording service is used only through a verified released interface.

### 13.2. Disk pressure, bounded queues and crash evidence are their own failure systems

Source §§14–20 (`#L776-L968`) distinguishes product events, structured technical logs, restricted crash evidence and policy-gated audit. Suggested physical folders under a managed app-owned root were an **illustration**, not a selected required path layout. The security boundary is `LogRef/EvidenceRef` with access rights, not a raw host pathname in a mobile/browser UI.

Bounded asynchronous technical-log queues can lose records on crash or overflow; count dropped entries and observability write failures. Terminal state and effect receipts need separately designed durability, not blind reliance on an INFO queue. Emergency diagnostics may use early stderr, a minimal bootstrap file or a small ring buffer, but file-descriptor, platform and disk-failure limitations prevent any promise of perfect fatal-crash capture. Disk full can degrade logs, durable Job admission, final Artifact publication and source acquisition **differently**, so one generic “offline” status is misleading. Staged publication and accepted command logs must honor their own proven storage guarantees.

On startup **before** normal application context or a platform node exists, §37 (`#L1468-L1487`) proposes minimal bootstrap evidence that can later be correlated to a real session. Do not assign a made-up external ProblemRef or assume a recorder exists before activation. A parent process observing a child exit can supply platform-level evidence, but cannot alone prove the analytical effect or final report bytes.

### 13.3. Useful metrics, tracing and support bundles are subordinate projections

§38 (`#L1488-L1515`) proposes *distinct* observations for Job queue wait, scenario/operation latency, `SUCCESS`, `PARTIAL`, `CANCELLED`, `FAILURE` and `UNKNOWN` totals, active work, retry, background lag, progress stalls, grouped conditions, log drops and observability write failures. These metrics can identify system degradation and audit coverage gaps without becoming the authoritative per-Job status. Metric dimensions require high-cardinality controls and must never indiscriminately export banking payloads, credentials, full source URLs with query strings or raw request parameters.

§39 (`#L1516-L1533`) treats OpenTelemetry and W3C tracing as *optional interoperable adapters*: internal Case/Job/Attempt IDs and trusted application ownership survive across different protocol exporters. External trace propagation must not reveal internal actor, Thread or private source attributes to unauthorized recipients.

A §41 support bundle (`#L1568-L1589`) can help a permitted user or operator diagnose one Case with product revision, exact Case/Job/operation references, authentic ProblemRefs, safe execution snapshot, selected technical excerpts, Artifact metadata and **a redaction report**. By default exclude raw financial/business datasets, unbounded environment variables, credentials, unrestricted workspace and private peer evidence. A bundle is an *authorized, bounded export* whose redaction and allowed recipient need separate verification, not a blanket “download all logs” action. A suppressed or expired source log must be represented as unavailable, not silently recreated.

### 13.4. Diagnostics and repair have different authority and proof

§§43–44 (`#L1608-L1658`) distinguish retrying a single operation, intentionally restarting the whole scenario, resuming from a proven checkpoint, and reconciling an existing remote Job. These are different commands with different effect and deduplication risks. Safe `retry_advice` can be `retry_immediately`, `retry_later`, `retry_after_user_action`, `do_not_retry` or `unknown`; policy and actual state determine permission.

A **diagnostic probe** should remain bounded and read-only, returning qualified `PASS/WARN/FAIL/UNKNOWN/SKIPPED` plus evidence. A **repair** is an independently admitted potentially mutating action, with requested effect, permission, audit and verified postcondition. A repair recommendation or clickable user action is not itself confirmation the condition recovered.

**Adverse verification cases (not executed):** inject a lost recorder acknowledgment after committed external registration; disable debug logging during successful calculation; fail mandatory audit before a privileged deletion; exhaust disk during a Run; crash before application context; let a sensitive value appear in a diagnostic field; request a support bundle without log-view permission; submit a “diagnostic” that attempts cleanup; let a previously emitted `ProblemRef` refer to a removed/expired record. Require distinct safe states and explicit scopes in every case.

**Alternatives and decision frontier:** best-effort local logs versus mandatory auditable journal; platform recorder versus protected app-local fallback; append-only diagnostics versus bounded snapshots; ad-hoc support attachment versus policy-approved export. Exact infrastructure and retention remain open. No independent Science→source/Research Amputation verdict follows from this section.

## Original Windows Study 0020 — executable Scenario, Case, Artifact and local-log limits

**Frozen study:** exact original Windows research, Git blob `225128f2599f0792422c0b31cb3cbe1437991ced`. The study's optimistic characterization is qualified by [current direct code](../../current-how/windows-application.md) and 14 executed synthetic Windows Python source-characterization cases in Knowledge CI. Current observations, candidate target safeguards and source's historical opinion stay separate.

| Original position and evidence role | Primary material interpretation | Failing or limiting case | Original lines |
| --- | --- | --- | --- |
| `SB-SRC-0020/RUN-04` · `DIRECT_CODE_WITH_EXECUTED_FAILURE_EXCEPTION` | Operation runner constructs a path-named file logger, context and dynamically imported handler and converts handler exceptions into OperationResult errors. | WEX-06 shows early workspace-error return occurs before handler cleanup, while WEX-05 shows a raised callback before OperationResult leaves direct ScenarioRun unfinalized. | L628–L647 (`#L628-L647`) |
| `SB-SRC-0020/RUN-11` · `DIRECT_CODE_LOG_EVIDENCE_SCOPE` | Two local log layers exist: application logger and per-Operation file log, the latter registered as a Case-linked LogRecord. | A Case-linked log path is not a permissioned remote LogRef; early return leaves a FileHandler attached and raw exception text may cross local projections. | L757–L765 (`#L757-L765`) |

**Status:** producer source-to-Science text preservation only, not accepted fixes, a host execution proof or independent semantic review. Static original source properties and successfully executed negative tests supply different evidence strengths. Source-wide `SB-SRC-0020` material state is `unaccounted` and no whole-file Research Amputation passed.

## Complete twenty-eight execution observability acceptance candidates

A [source-independent 28-case execution, trace and recovery LDD](../../ldd/observability/execution-truth-and-recovery-vectors.md) retains detailed requirements for simultaneous Runs, idempotent admissions, preserved Attempts, outcome uncertainty, queue overload, torn append-only journal and snapshot corruption, disk pressure, failed log registration, scoped node incidents, actor-specific read cursors, lost Artifact bytes, provider migration and timestamp skew. These are **target fault-injection obligations**, not evidence that a durable multiuser host or file-journal writer exists. Physical log sink, domain outcome, artifact availability and platform health remain independent truth dimensions.
