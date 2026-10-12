# Execution observability: twenty-eight negative recovery and causality vectors

**Status:** proposed, profile-dependent and **UNEXECUTED** acceptance vectors for future Strategy Box application authority, clients, operational records and external platform integration. Existing pinned Windows and core sources prove only selected local code paths and synthetic characterization. No native concurrent hosted Job engine, durable cross-user feed or complete fault-tolerant journal is claimed to exist.

## What must remain separate

A **Thread** provides communication context, a **Run** identifies accepted execution intent, an **Attempt** identifies a particular worker execution, an **Event** records a causal update, an **Artifact** is a separately verified output, a **Problem** records a diagnosable occurrence, and a **Condition** expresses a current shared impairment. The external management platform owns its own installation/Node/Session health and only the capabilities it actually exposes. Technical logs reside on the device or host that executes the operation, subject to separate permissions and retention.

Progress events may be intentionally sampled or coalesced. A truthful terminal Run result, resource effect receipt, object permission decision and durable admission record cannot be treated as disposable progress telemetry. A recorded lost-acknowledgement or corrupt-state outcome is `UNKNOWN`/degraded until reconciled, not a convenient success or empty list.

## Complete proposed failure matrix

| Case | Test subject / stimulus | Required observable result | Evidence grade |
| --- | --- | --- | --- |
| OBS-01 | **concurrent threads:** Start independent Runs in Threads A and B | Both have independent Run/Attempt logs; UI remains responsive and reflects real concurrency | `UNEXECUTED` |
| OBS-02 | **concurrent same thread:** Launch two Runs in one Thread | Distinct cards and terminal outcomes; one Thread ordering and two Run identities | `UNEXECUTED` |
| OBS-03 | **submission replay:** Redeliver same submit after reconnect | Deduplicate admission by effective idempotency key and resolve existing logical Run | `UNEXECUTED` |
| OBS-04 | **retry evidence:** Retry operation after verified failed Attempt | Create new Attempt identity; preserve earlier logs and their exact status | `UNEXECUTED` |
| OBS-05 | **lost effect acknowledgment:** Worker disappears after starting external write | Mark UNKNOWN/reconciliation pending, neither fabricated success nor failure | `UNEXECUTED` |
| OBS-06 | **GUI lifetime:** Close local client while a Job is active | Outcome follows actual foreground/host lifecycle contract, not window closure assumption | `UNEXECUTED` |
| OBS-07 | **telemetry saturation:** Progress event queue exceeds capacity | Coalesce/drop only explicitly lossy intermediate telemetry; durable terminal truth remains | `UNEXECUTED` |
| OBS-08 | **torn journal tail:** Break final JSONL record in middle of bytes | Quarantine/reject incomplete record, retain confirmed prefix and emit diagnosis | `UNEXECUTED` |
| OBS-09 | **damaged projection:** Snapshot corrupt while verified journal intact | Rebuild snapshot from authenticated ordered journal, keep replay boundary evidence | `UNEXECUTED` |
| OBS-10 | **dual corruption:** Corrupt snapshot and underlying journal | Fail into diagnosis/read-only or reject admission; never reset to fresh empty team state | `UNEXECUTED` |
| OBS-11 | **disk full at admission:** Exhaust durable Work store before new submit | Reject durable Job admission with storage-unavailable state | `UNEXECUTED` |
| OBS-12 | **log sink degradation:** Domain calculation succeeds; log sink fails afterward | Preserve true business outcome and separately degraded diagnostics status | `UNEXECUTED` |
| OBS-13 | **shared root outage:** Common host data mount disappears | One correctly scoped Condition and affected Run projections rather than duplicate incidents | `UNEXECUTED` |
| OBS-14 | **local validation:** Single user mistypes invocation parameters | Scoped failed/invalid Run feedback, no spurious node-wide emergency alert | `UNEXECUTED` |
| OBS-15 | **secret exception:** Exception includes password/secret marker and host path | Sanitize shared feed, external API and support export; guard technical log separately | `UNEXECUTED` |
| OBS-16 | **per-principal reads:** User 1 reads a Thread while User 2 does not | Advance only User 1 cursor; one stored event history remains unchanged | `UNEXECUTED` |
| OBS-17 | **rename continuity:** Rename a default-titled Thread | Stable Thread/Run IDs and causal links; only mutable presentation title changes | `UNEXECUTED` |
| OBS-18 | **duplicate titles:** Two users create same-named Thread concurrently | Two distinct IDs and two independently navigable entries | `UNEXECUTED` |
| OBS-19 | **Artifact removed:** Manually delete/rename already published output bytes | Availability becomes missing; historical Run outcome and original receipt remain | `UNEXECUTED` |
| OBS-20 | **external recorder missing:** Platform problem recorder unavailable | Keep local-only Problem evidence and truthful registration failure, no invented external reference | `UNEXECUTED` |
| OBS-21 | **storage-binding change:** Platform assigns new physical operational root | New runs honor new binding; old state follow explicit migration/recovery policy | `UNEXECUTED` |
| OBS-22 | **raw log authorization:** Unprivileged Web/Android consumer dereferences log reference | Deny before physical locator disclosure and exclude absolute host paths | `UNEXECUTED` |
| OBS-23 | **storage engine replacement:** Move from a file-owned journal to SQL owner | Maintain Run IDs, terminal truth, cursor order and Artifact refs; old writer fenced or read-only | `UNEXECUTED` |
| OBS-24 | **restart with stale job:** Restart after interrupted worker and request active task list | Stale heartbeat is not RUNNING proof; reconcile unconfirmed runs | `UNEXECUTED` |
| OBS-25 | **clock skew:** Two client clocks disagree on event timestamps | Authoritative node sequence controls causal order; UTC timestamps remain diagnostic | `UNEXECUTED` |
| OBS-26 | **log retention:** Technical log exceeds configured quota and rotates | Older log may be unavailable, but accepted terminal Job/Case history survives | `UNEXECUTED` |
| OBS-27 | **write concurrency:** Two Jobs commit different outputs and another pair share a destination | Independent targets may progress; same output guarded by claim/version | `UNEXECUTED` |
| OBS-28 | **platform outage postpublication:** Managed platform health degrades after validated Excel published | Product Run/Artifact result remains true; independent platform health status degraded | `UNEXECUTED` |

## Evidence-oriented test method

A competent test run needs concrete runtime source/commit and deployed profile, at least two concurrent independently identified Jobs, two participants with distinct permissions, a staging Artifact target, a constrained log directory, a loss-injectable external recorder and explicitly controlled fault points. **Each vector is independently selected** by presence of its actual component; absent host/stream/Journaling features are `BLOCKED_NOT_IMPLEMENTED`, never cosmetically green.

For file-journal crash tests inject process termination at durable admission, after append but before flush, during snapshot write, before/after atomic rename, during directory fsync, after physical output but before `run.completed`, and after the external effect but before its acknowledgement. Expected confidence is per fact: *which bytes were committed, which journal prefix is provable, which Attempt may have had side effects, what is authoritative now, and what the user may see*. An operating-system `os.replace` of a snapshot file by itself is not a universal proof of crash durability; filesystem and directory flush semantics must be validated under the actual deployment.

For remote reconnection, test authorization-aware snapshot/cursor transactions and subscription after-revision, individual read receipts, raw log permissions and absence of hidden-object existence/count disclosures. An opaque cursor alone does not establish side-channel safety; live revalidation after rights changes and proper projection generation matter.

For physical logs, separately test minimum viable crash evidence, redaction, log rotation quota and application result continuity when a best-effort logger is unavailable. **Mandatory audit** before a destructive operation is a security policy choice: if chosen, an unavailable mandatory audit writer may block the effect; optional debug logging must not retroactively convert a completed legitimate computation to failed.

For actual output file loss, retain the accepted Run status and mark Artifact bytes **missing or inaccessible**, with independent permission/readiness status. A platform health outage after successfully published output affects platform readiness, not the already evidenced historical result. A local OS user cannot infer remote host progress from a stale GUI heartbeat.

## Implementation choices still open

This conformance catalogue intentionally does **not** require immediately adopting SQLite, Kafka, OpenTelemetry, distributed tracing, a generic event framework or a specific process topology. A single-writer versioned journal with verified replay may suffice for a small local node if actual durability and corrupt-tail behavior are tested. A SQL-backed host may be warranted for concurrent shared state, but only after authority, deployment profile, schema and restoration needs are accepted. Persisted user Work and evidence must be migrated deliberately if the physical store changes; no backwards-compatible runtime format is required merely for historical convenience.

**Unverified proof:** the table consists of target test intentions; source study and local code observations are different evidence classes. No deployed remote host, actual security exercise, real crash-consistency/fault-injection campaign or separately competent reviewer has passed them. No link into historical Research or Work is needed to interpret this publication.

**Related maintained knowledge:** [causal observability](../../science/execution-and-diagnostics/causal-observability-and-failure-truth.md), [host diagnostic registration](host-problem-receipts-and-evidence-degradation.md), [shared read cursors](../../science/collaboration/authorized-streams-read-cursors-and-private-work.md), and [independent state restoration](../../science/state-and-recovery/shared-state-backup-generation-and-retention.md).
