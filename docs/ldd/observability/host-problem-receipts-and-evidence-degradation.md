# Candidate LDD — host problem receipts, diagnostic failure and evidence degradation

**Status:** `CANDIDATE / PRODUCT-POLICY-DEPENDENT / NO IMPLEMENTATION OR FAULT-TEST EVIDENCE`. **Target authority:** [admitted Strategy Box host](../../what/strategy-box/host-deployment-commitment.md) in Web/domain and Windows/AppDock arrangements. **Science:** [causal observation and self-health](../../science/execution-and-diagnostics/causal-observability-and-failure-truth.md), [node-wide safe conditions](../../science/collaboration/shared-conditions-and-log-access.md). **Current code:** [bounded Windows history, operation logs and failures](../../current-how/windows-application.md), [pinned AppDock launch/host limit](../../current-how/appdock-activation-host-attachment-boundary.md).

This LDD addresses a justified complex boundary: **an analytical operation can have a known outcome while registering the problem about it fails or remains uncertain**. It specifies testable proposed behavior, not code signatures, physical database/storage choice, a released AppDock SDK, an installed recorder, an audit retention policy or a fabricated cross-product permission grant.

## Truth owners and minimum conceptual envelope

| Value / record | Proposed authoritative owner | Status and separation |
| --- | --- | --- |
| `domain_result`, source validation and partial evidence | Executing analytical core and its accountable caller | `SUCCESS/PARTIAL/FAILURE` qualified by actual domain artifacts; no synthetic platform success |
| `run_ref`, logical effect intent, Attempt and accepted transition | Strategy Box host application (local-only current path still distinct) | Host authoritative in both accepted future host arrangements |
| `problem_registration` and `problem_ref` | App-owned bridge tracks its own request; a **real external recorder** owns a reference only when its published implementation verifies acceptance | Conceptual app-side request states are **not** AppDock enum values: the actual public AppDock `Recorder.record(RegistrationRequest)` returns a `ProblemOccurrence` on success, and `RegistrationFailure.state` is **exactly `NOT_WRITTEN` or `OUTCOME_UNKNOWN`** on failure. A failure's `candidate_ref` is never a confirmed `ProblemRef`. |
| Actual `ProblemOccurrence` and platform `Condition` | External platform only for explicitly supported, versioned public contracts | Never infer persistence merely from optional manifest field, SDK model or launcher PID |
| Application `SharedCondition` user-safe projection | Strategy Box app resource authority, backed by observed impact and permitted audience | Needs original cause/impact, freshness, severity and explicit close evidence |
| Restricted log/evidence bytes | Host/worker execution custodian and authorized service | A `LogRef` is a scoped reference, not host pathname and not access grant |
| Mandatory privileged-action audit | Named policy/effect owner and verified audit mechanism | Must be established before admitting an action **only where Product Security Policy says it is required** |

A conceptual `ProblemRegistrationResult` may carry local correlation key, attempt/causation refs, observation time, state, authentic external `ProblemRef?`, and safe diagnostic reason code. No raw traceback or user parameter bag belongs in this shared boundary. Product effect truth and telemetry registration must **never** occupy the same Boolean `ok`.

## Command and state behavior

1. **Before execution:** verify local versus hosted profile, identity/scope of actor, accepted Run and effect preconditions. Classify whether privileged mandatory audit is required.
2. **During domain execution:** collect typed domain progress/diagnostics and retain high-value terminal/side-effect observations under their own durability contract. A progress display must not commit the Job outcome.
3. **On a domain problem:** record safe bounded local issue, then invoke a **version-confirmed public** external problem registration port *if present and authorized*; a platform API not installed results in a truthful `UNAVAILABLE` capability state, not a fabricated method call or ID.
4. **On acknowledged registration:** link the returned **authentic** ProblemRef from the actual platform owner to the authorized Case/Job projection. Never copy its full internal problem record into app storage as a second owner.
5. **On confirmed refusal:** retain domain outcome and `RegistrationFailure.state=NOT_WRITTEN` only when the actual public recorder reported it, emit a scoped observability-degraded signal and follow the accepted logging policy.
6. **On lost acknowledgement:** retain `RegistrationFailure.state=OUTCOME_UNKNOWN`. Query/reconcile with a stable original intention if and only if the exact released platform contract supports it; the pinned public `ProblemQuery.lookup` distinguishes `FOUND`, `NOT_FOUND`, `STORAGE_UNAVAILABLE`, `STORAGE_CORRUPT` and `UNSUPPORTED_STORED_CONTRACT`. Even if a failure contains a `candidate_ref`, that reference is **not confirmed**. Without an idempotency/query guarantee, do not blindly make another recording call with potentially duplicated occurrence.
7. **On observability disk/queue degradation:** report drop and write-failure counters, preserve safety-required terminal evidence through its own guaranteed path, and keep app effect truth distinct from platform health. Under physical exhaustion, evidence can be unavailable; do not promise lossless capture.
8. **On startup before application context:** attempt only minimal bounded bootstrap evidence; later attach true execution/node context if available. A failed process may be observed by its platform launcher; absence of own exception record does not prove clean completion.
9. **On client disconnect:** the authoritative host may continue work according to its approved lifetime policy; client receives a reconnect-safe snapshot rather than inventing `FAILED`, `CANCELLED` or shared telemetry state.
10. **On diagnosis/repair:** diagnosis is bounded read-only evidence collection. Repair and support-bundle export are *separately authorized commands*, respecting current resource, effect and audience policy.

## Audience and privacy guardrails

The person who owns a Run may view its user-safe failure summary; authorized collaborators may view shared-safe impact; authorized operators may inspect scoped diagnostics; specialist technical logs, forensic records and bundled evidence require separate rights. The same identity used for command execution does **not** automatically grant technical log access. Any shared Condition must group occurrences without exposing private run inputs, tokens, paths or source data from unaffected people.

Retain one unambiguous cause/effect relation when one shared Node failure explains several private Run failures. Duplicate notification suppression must not suppress the original per-Attempt technical evidence. An ordinary invalid parameter creates a local safe error rather than a team-wide Condition; an actual shared storage/source outage may create one scoped warning for affected users.

For a support bundle, use only authorized metadata, bounded safe log excerpts and an explicit redaction report. Exclude secret-bearing environment variables, raw bank source payloads, private peer workspaces, full configuration and unbounded stack traces unless a separate forensic permission truly permits those disclosures.

## Candidate negative and fault tests

Every vector below is **NOT RUN**. The expected property is a proposal for an approved host release test, not an assertion about the current implementation.

| ID | Injected fault / stimulus | Falsifiable expected observation |
| --- | --- | --- |
| OB-01 | Domain fails, recorder acknowledges valid reference | Domain FAILURE persists; authentic ProblemRef linked only to permitted projection |
| OB-02 | Recorder fails with `RegistrationState.NOT_WRITTEN` | Domain FAILURE unchanged; no confirmed occurrence and no fabricated ProblemRef |
| OB-03 | Recorder commits but response is lost | `RegistrationState.OUTCOME_UNKNOWN`, optional candidate ref unconfirmed; exact bounded lookup/reconciliation before any retry |
| OB-04 | Recorder method absent in installed AppDock version | Feature reported unavailable; protected app-local problem evidence remains usable where policy allows |
| OB-05 | Optional technical log disk write fails after valid domain success | Domain success not erased; observable missing diagnostic evidence |
| OB-06 | Mandatory audited privileged operation cannot persist approved audit evidence | Operation **not admitted/effected** where this is its accepted precondition |
| OB-07 | Read-only public-statistics fetch while optional logging is degraded | Business operation permitted if no mandatory precondition is violated; degraded observability visible |
| OB-08 | Bounded INFO/debug log queue overflows | Dropped count observed; terminal/effect evidence follows its stronger own route |
| OB-09 | Process exits before AppContext/Node/Recorder created | Local/bootstrap/parent evidence qualified; no fabricated node/session/ProblemRef |
| OB-10 | Host worker crashes after output rename but before app receipt | Effect/Artifact truth UNKNOWN until file/evidence inspection; recorder result not a proxy |
| OB-11 | Ten errors from shared data root, two private parameter errors | One impacted resource Condition only for affected users; private errors remain scoped |
| OB-12 | Unauthorized client requests the host's log path or support bundle | Denial before any raw byte/path disclosure; safe summary may remain visible under separate permission |
| OB-13 | Repair action is mislabeled a diagnostic probe | Reject mutating effect until separately admitted with effect, authorization, audit and postcondition |
| OB-14 | Platform acknowledges process launch but service readiness/auth endpoint unavailable | Host activation and Job admission remain unproved; clients cannot treat PID as host-ready |
| OB-15 | User hides a Condition banner while Node outage remains | Only viewer dismissal changes; condition remains ACTIVE until verified resource recovery |
| OB-16 | Log retention expires before long-lived Case history | Preserve accurate outcome, mark `LogRef` unavailable and avoid invented evidence |


## Windows-local source-backed additional conformance vectors

The pinned [Windows direct Current HOW](../../current-how/windows-application.md) now covers twelve newly verified exact-source files for background/presence/assignment/log surfaces. These raise eight further **candidate tests, not executed**.

| ID | Existing risk and counterexample | Required future-host result |
| --- | --- | --- |
| OB-17 | A locally enabled BackgroundProcess is announced as a live Job without any actual executor | Host shows `CONFIGURED` separately from `RUNNING`; no fabricated last execution/effect receipt |
| OB-18 | Background `active_states()` includes an `error` status | True active count follows accepted running Jobs, while failures stay visible in their separate terminal/condition counters |
| OB-19 | Imported legacy Assignment status is invalid and parser maps it to `active` | Reject/quarantine historical corruption or label it legacy-unverified; never create a new host obligation silently |
| OB-20 | Invalid assignment creation timestamp is replaced by current wall-clock time | Retain original timestamp uncertainty; do not backdate or fabricate a fresh authoritative assignment |
| OB-21 | Presence is inferred from Case author and local current-user seed | Do not show verified online peer without actual accepted session/heartbeat/TTL evidence |
| OB-22 | Previewed local log is huge or `max_lines=0` | Enforce permissioned bounded bytes, lines, time and resource use *before* reading host evidence; no whole-file surprise |
| OB-23 | A local log read error contains host absolute path or raw exception text | Safe user projection and separately authorized technical details; no cross-client path leakage |
| OB-24 | A participant's display name enters a future rich-text builder | Escape/encode text for actual HTML rendering; the current inspected `QListWidgetItem` path is plain text, so do not assert a confirmed injection incident |

These distinguish observed local code limitations from proposed host conformance; they create no additional current deployment claims or executable tests.

## Direct evidence and limits of external implementation

The [direct public AppDock registration/query Current HOW](../../current-how/appdock-public-problem-contracts.md) distinguishes an implemented storage-neutral Python contract from an actually installed and authorized application bridge.

The frozen original observability study §§36–44 (`#L1434-L1658`) supplies the candidate self-health and diagnostic semantic distinctions. The public [AppDock observability implementation status](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/observability/IMPLEMENTATION_STATUS.md) at pinned blob `b42e69bb70e051fd49be6c6c38cca7c825923962` reports a bounded 5E **source-complete** milestone with **native Windows certification pending** and explicitly distinguishes platform session `ProblemRef` from unconfirmed failures. Its rich document includes historical milestones; it is **not proof** that an arbitrary external application consumer can currently register problems through a stable installed API. The release and version must be checked directly. The separate [AppDock launch implementation](../../current-how/appdock-activation-host-attachment-boundary.md) can spawn ordinary child processes but its pinned `host_delegated` branch returns `BACKEND_UNAVAILABLE`.

**Blocking owner decisions:** required audit/evidence grade per risk class; actual AppDock public recorder contract and capability discovery; role-based log/support-bundle permissions; incident notification and sharing thresholds; physical retention/disk quotas; durable host Case/Job state and recovery; host Web/Windows deployment and transport/security profile. Even after such decisions, every OB fault test needs a real installed runtime. This LDD does not assert Product admission, a working cross-device host, a native certification result or independent Research Amputation.

## Newly executed Windows-local parameter and log facts: future observability vectors (OB-25..27)

[Six controlled current-code characterizations](../../current-how/windows-application.md) at pinned Windows source SHA include three observability-relevant cases: a synthetic password-shaped value appears in a `case_started` message; a failed operation's `.log` output becomes an ArtifactRecord; and a missing-workspace early-return leaves the operation FileHandler registered. CI **ran and passed those current-behavior reproductions**, not the following prospective corrections.

| Unexecuted target vector | Injection | Required observation |
| --- | --- | --- |
| OB-25 | Secret-looking saved launch field; multiple user/AI event consumers | Only authorized safe parameter projection, no raw value in common Event, log preview, notification or support bundle; truthful local diagnosis remains possible |
| OB-26 | Error-generated `.log` output appears in operation outputs and Artifact catalog | Source of technical evidence keeps its restricted visibility; a client must use an authorized LogRef/view, not merely path identity or an Artifact badge |
| OB-27 | Repeated workspace-unavailable attempts while the process persists | No dangling file handlers or unbounded descriptor/memory growth; error remains diagnosable even when primary workspace is unavailable |

No live data-leak report is asserted. The observed behavior is from synthetic local Python tests; real cross-principal enforcement, audit obligations, AppDock recorder delivery and native Windows resource limits remain unverified.
