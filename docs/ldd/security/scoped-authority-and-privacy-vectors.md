# Scoped authority, safe projections and effect conformance vectors

**Status:** thirty **proposed and unexecuted** host/client negative acceptance vectors; scientifically grounded and self-contained. The tests apply conditionally to a trusted small-team node, local desktop, future Web/Android consumers, or delegated machine actions as labelled. They do **not** assert a shipped multiuser authority, installed remote host, Web transport, platform identity provider or a deployed permission policy.

## Governing semantic distinctions

An authenticated **principal** differs from a friendly display name; one user may own several **sessions**; a shared activity feed is a **field-filtered projection**, not raw authorization to all technical facts; an operation's **discoverability**, **admission**, **approval** and **effect-time authorization** are different predicates. A Run/Job's actual outcome is owned by the executing application authority, not by a window's presence flag. A direct Python library caller still executes with host OS/process capabilities; it cannot honestly claim enforced remote object ACLs without a separate trusted boundary.

**Profile meanings:** `L0` single-local user; `L1` explicitly enrolled small trusted node; `P2` planned authenticated remote-host arrangement (Windows/Web/future Android permitted clients); `M` delegated machine agent. These labels are test-selection aids, not product entitlement or already approved protocol editions.

### Security release dependencies

Before a hosted acceptance run, the actual deployment must specify user enrollment/session trust, protected transport, shared/private visibility, field classifications, safe logging, permission granularity, plan approval and revocation semantics, and concrete failure/retention policies. A test executor must use **two distinct principals, two clients, a shared target fixture, a simulated malicious source, one file-effect operation and a controlled recorder fault** where applicable. For an actual Internet-facing Web service add browser session security, CSRF, rate limits and upload hardening with that deployment's own evidence.

| Vector | Surface / adverse stimulus | Required observable decision or refusal | Applicable profile | Execution |
| --- | --- | --- | --- | --- |
| SEC-01 | **principal:** Two different principals use identical display names | Events retain distinct server-owned principal identifiers; presentation disambiguates without treating names as credentials | `L1` | `UNEXECUTED` |
| SEC-02 | **session:** One principal connects with Windows and Android sessions | One principal/participant, two revocable sessions; no duplicated person or implicit shared device token | `L1/P2` | `UNEXECUTED` |
| SEC-03 | **identity spoof:** Unknown client sends an existing user's author_id | Authority derives actor from trusted session context; forgery is denied or untrusted metadata discarded | `L1/P2` | `UNEXECUTED` |
| SEC-04 | **shared view:** Participant opens another member's permitted shared Case | Safe actor label, operation/status and time appear; restricted fields are absent | `L1` | `UNEXECUTED` |
| SEC-05 | **field leakage:** Shared event contains a sensitive invocation parameter | Raw secret/path remains absent from every shared JSON, stream, browser and machine projection | `L1/P2` | `UNEXECUTED` |
| SEC-06 | **object access:** Caller guesses an otherwise private artifact ID | Metadata lookup, preview and download enforce the same object permission without existence disclosure | `L1/P2` | `UNEXECUTED` |
| SEC-07 | **function access:** API caller bypasses a disabled dangerous UI action | Direct invocation is denied by trusted application authority before any effect | `L1/P2` | `UNEXECUTED` |
| SEC-08 | **resource scope:** Principal can invoke a scenario but cannot write its target workspace | Separate target-resource admission or effect check denies the mutation; diagnostic reason protected | `L1/P2` | `UNEXECUTED` |
| SEC-09 | **revocation race:** Grant revoked after Job admission before external mutation | Recheck current effect right; pending mutation blocked or transitions to explicit safe state | `L1/P2` | `UNEXECUTED` |
| SEC-10 | **approval staleness:** Approved cleanup target set changes after approval | Plan digest/target revisions invalidate approval; new bounded consent required | `L1/P2` | `UNEXECUTED` |
| SEC-11 | **AI delegation:** Machine actor invokes operation beyond delegated scope | Machine grant ceiling applied independently from broad human rights; denied attempt attributable | `M` | `UNEXECUTED` |
| SEC-12 | **prompt injection:** External HTML/financial report instructs AI to delete an archive | Untrusted source stays data; no tool-effect authority is derived from its text | `M` | `UNEXECUTED` |
| SEC-13 | **write conflict:** Two admitted Jobs attempt to write same shared output | Serialize, compare-version or use distinct immutable result identities; no silent overwrite | `L1/P2` | `UNEXECUTED` |
| SEC-14 | **error audience:** User's bad local form field triggers validation error | Only affected author/client sees details; no noisy node-wide incident | `L0/L1` | `UNEXECUTED` |
| SEC-15 | **shared failure:** A visible shared Scenario fails within team scope | Authorized timeline gets actor, operation, timestamp and safe typed class, not raw exception | `L1` | `UNEXECUTED` |
| SEC-16 | **condition dedup:** Shared backend outage affects three participants | One correlated condition/occurrence where supported; distinct authorized notifications, not three falsely independent root causes | `L1/P2` | `UNEXECUTED` |
| SEC-17 | **log redaction:** Raw technical log includes password, URL token and home path | No secrets/path fragments in shared cards, AI tool outputs or ordinary API responses | `L1/P2` | `UNEXECUTED` |
| SEC-18 | **technical log permission:** Peer requests another actor's raw log reference | Explicit technical-log read right required at dereference, regardless of known ID | `L1/P2` | `UNEXECUTED` |
| SEC-19 | **disconnect:** User client disappears while an admitted remote Job continues | Presence changes separately; Job truth follows executing authority and does not fabricate cancellation | `P2` | `UNEXECUTED` |
| SEC-20 | **local log storage:** Operation executed on local desktop with local principal | Technical log recorded under access-controlled device managed/system area, not automatically shared Data | `L0/L1` | `UNEXECUTED` |
| SEC-21 | **remote log placement:** An operation executes on shared remote host | Primary log resides on executing host with authorized client projections only | `P2` | `UNEXECUTED` |
| SEC-22 | **recorder ambiguity:** External platform recorder fails or gives no confirmation | Product retains actual error and explicit registration state; never synthesizes confirmed external ProblemRef | `L1/P2` | `UNEXECUTED` |
| SEC-23 | **unknown effect:** Worker loses connection after starting external write | Record UNKNOWN/reconciliation-pending; prohibit blind non-idempotent retry | `L1/P2` | `UNEXECUTED` |
| SEC-24 | **stream revocation:** Thread access is revoked during live subscription | Stop restricted future payload, invalidate projection generation and require scoped resynchronization | `P2` | `UNEXECUTED` |
| SEC-25 | **cursor side channel:** Mixed-ACL event pagination hides several node events | Opaque per-principal cursor does not expose hidden count, identifiers or debugging metadata | `P2` | `UNEXECUTED` |
| SEC-26 | **untrusted display:** Participant chooses HTML/script-like nickname | All UI surfaces render as inert text; no embedded script or raw markup execution | `L0/L1/P2` | `UNEXECUTED` |
| SEC-27 | **path escape:** Traversal, absolute path, symlink or junction targets outside allowed root | Guard actual filesystem object/effect at OS or equivalent storage boundary; deny escaped mutation | `L1/P2` | `UNEXECUTED` |
| SEC-28 | **audit unavailable:** Mandatory log or state store unavailable when destructive command arrives | Explicit risk-dependent fail-closed/unknown policy; never claim a successful audited effect | `L1/P2` | `UNEXECUTED` |
| SEC-29 | **corrupt state:** Shared durable state record cannot be parsed | Preserve corruption evidence, report degraded/repair; never treat as an empty new workspace | `L1/P2` | `UNEXECUTED` |
| SEC-30 | **offline session:** Disconnected user lacks fresh permissions and Job status | Display stale/as-of and block or queue mutations only under explicit revalidation protocol; no invented remote success | `P2` | `UNEXECUTED` |

## Evaluation procedure and evidence to preserve

1. **Fixture/setup:** declare which profile and actor rights actually exist; freeze the proposed request, object/plan revisions, surface, client and logical Job/Attempt IDs; inject one adverse condition at a time. Separate real application system tests from contract/unit simulations.
2. **Policy oracles:** record the server-side decision, on-device or host-side effect state, authorized bytes returned to each principal, restricted field exposure, log location, relevant grant and approval revision, and the exact source of any external problem receipt.
3. **Adverse visibility check:** issue the same forbidden action via UI, direct API and machine endpoint where exposed; ensure that a disabled button is not the only security enforcement and that a hidden object is not leaked by preview, metadata, cursor or detailed error.
4. **Effect uncertainty:** for external mutation with lost acknowledgement, record physical result inspection before retry; distinguish `SUCCESS`, `FAILURE`, `PARTIAL`, `CANCELLED` and `UNKNOWN` based on actual evidence, not success-shaped file paths or HTTP status alone.
5. **Time and privilege:** recheck rights after queueing, before effect, after resource version changes, after reconnect and when a stream cursor expires. Distinguish author permission to cancel a Job from operator permission to cancel another's Job.
6. **Restore and diagnostic degradation:** corrupt the persistent store or disable the mandatory event recorder under policy; verify survival of forensic evidence, denial of unsafe destructive effects where required and truthful degraded recovery rather than silent blank history.
7. **Verdict:** report `PASS`, `FAIL`, `NOT_APPLICABLE` or `BLOCKED_NOT_IMPLEMENTED` **per test**, with exact runtime revision and receipts. `UNEXECUTED` remains the default here. A simulated test passing does not certify an installed host.

### Field classification and minimal data contracts

For each externally projected field of `Invocation`, `Event`, `Case`, `Artifact`, `LogRecord`, `Problem`, `User` and `Session`, a hosted implementation should explicitly resolve:

`field → authoritative owner → sensitivity → permitted audience → storage/retention → serialization/projection tests`.

Use deny-by-default for newly added potentially sensitive fields; rendering an unrestricted data class into JSON and relying on Qt/CSS to hide fields is insufficient. A UI permission badge, a capability hint such as `dangerous`, and an external transport actor label each have a different assurance level from a trusted resource-specific command decision.

### Distinct pitfalls and trade-offs

- A small trusted node can maintain a simple identity-and-object permission mechanism rather than prematurely implementing a large IAM policy language. Simplicity **does not** make shared browser sessions, device enrollment, actual file isolation or delegated tools safe by default.
- If every participant directly accesses the same underlying shared file store, application cards cannot enforce byte-level privacy. Either accept common OS-level trust as a documented policy or mediate sensitive bytes through a trusted host/storage ACL.
- A realpath prefix check performed before an adversary changes a symlink can lose a time-of-check/time-of-use race. Safe confinement demands an OS/storage-backend appropriate file-open or equivalent boundary, not only a canonical-looking path string.
- A node-wide problem summary may be helpful, but even revealing the existence of restricted Work can leak information. Share only authorized, field-minimized incident facts and keep raw logs on the executing host/device.
- `role=operator` is not an automatic right to inspect personal notes, secret-bearing files or every person's technical log. The exact product role/permission matrix is **OPEN**.
- No backward runtime/API compatibility is required merely to preserve a weak design. Persisted meaningful Work, audit evidence and Artifacts still require explicit version/restore policy before destructive migrations.

## Relationship to supported knowledge

The conceptual owner is [identity and effect authorization](../../science/trust-and-assurance/identity-authorization-and-effect-boundaries.md); adjacent evidence models are [authorized streams](../../science/collaboration/authorized-streams-read-cursors-and-private-work.md), [causal observability](../../science/execution-and-diagnostics/causal-observability-and-failure-truth.md), [effect uncertainty](../../science/trust-and-assurance/uncertain-outcome-vs-observed-error.md) and [candidate host attachment](../hosting/host-client-attachment-boundary.md).

**Evidence limitation:** this is a candidate test plan reconstructed from a dated source study, not a self-certified security assessment, not a substitute for native host testing, and not a Product Decision on physical host placement or chosen platform protocols. No historical Research or Work archive is required to understand or navigate it.
