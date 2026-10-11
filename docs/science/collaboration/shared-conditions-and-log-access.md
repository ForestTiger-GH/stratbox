# Shared chats, node-wide conditions and protected participant diagnostics

**Scope:** causal relations between a user's command, a shared team feed, node/resource status, technical logs and warnings to other affected users. **Status:** comparison of competing scope and visibility models using observed local Windows code and falsifiable failure cases. A real shared-node backend and access policy are **target candidates, not verified deployed functionality**. See [causal execution evidence](../execution-and-diagnostics/causal-observability-and-failure-truth.md) and [state recovery](../state-and-recovery/authority-durability-and-recovery.md).

## 1. A shared user need does not authorize sharing every technical detail

In a team workspace participants benefit from knowing **who** launched an analytical task, **when**, **in which Thread**, its outcome and whether a fault affects colleagues. This helps coordinate concurrent work. However, raw exception chains, absolute paths, bearer tokens, request parameters and original file bodies do **not** become team-visible simply because a common feed exists.

At least three different audiences are material:

| Visibility plane | Appropriate information | Required basis |
| --- | --- | --- |
| **Shared product timeline** | Message, attributed author and time, Work/Run description, significant progress, verified terminal outcome and authorized Artifacts | Admitted Thread/Run visibility and current resource authorization |
| **Shared resource/node condition** | User-safe diagnosis of a common storage/execution/source issue, affected scope, freshness and possible safe next action | Observed multi-consumer impact, accountable resource-owner evidence |
| **Restricted technical evidence** | Tracebacks, per-Attempt logs, raw filesystem paths, HTTP details, inputs, support bundles | Separate diagnostic permission and protected custody with the actual execution owner |

An analyst's invalid parameter may be visible in a Thread that colleagues are **permitted to read** but is not automatically a node-wide emergency. A shared Data root outage is different: it affects multiple Runs and may justify a scoped common warning.

**Five different physical/semantic roles:** the originating device, execution node, durable-state authority node, technical-log custodian and viewing device. The laptop where a user pressed Run need not hold logs of a calculation performed by a future independent host. Expose an authorized `LogRef` and resolve its physical path only through the proper host adapter and permission check; do not publish absolute host paths as universal URLs.

## 2. One Thread may contain multiple Runs; one Run may contain several Attempts

Chat is a communication context, not the job queue. A Thread can display two concurrent Runs; two Threads on one node can be created at the same time with the same default title `New chat`. `thread_id` remains stable when its title, author's display name or creation metadata changes. Renaming the chat from a context menu changes presentation, not Work/Run identity. `run_id`, `attempt_id` and `event_id` connect user cards to technical evidence without embedding raw logs in conversation messages.

A shared catalog would likely need `thread_id`, title, `created_by/at`, `last_activity_sequence`, `active_run_count`, visibility and a **per-participant read cursor**. A global `unread: bool` attached to one shared Event misrepresents two users' different viewing histories. Separate per-principal `last_seen_sequence` or read receipts are candidates within a defined retention/access policy. A nickname is mutable presentation; actor and authorization identity are separate.

The pinned [Windows case model](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/cases/models.py) and [scenario-chat projection](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/presentation/common/scenario_chat/projector.py) carry local author and incoming/outgoing UI fields but do **not** establish network-synchronized shared history. The [presence service](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/presence/service.py) reconstructs local participant projections; it does not prove actual online status of other devices. A stale heartbeat must not be represented as fresh presence; time-bound snapshots/TTL are distinct from permanent Boolean status.

## 3. A problem occurrence versus an ongoing resource condition

A **ProblemOccurrence** records a particular fault observed by an Attempt, process or probe. A **Condition** records an ongoing resource situation with start, updates and closure. Thirty failed requests against one external source may be thirty Attempt/Problem events but one current `external_source_unavailable` condition for affected users.

```text
Attempt A1 -> Problem P1 ─┐
Attempt A2 -> Problem P2 ─┼─> Condition C(node, resource, impact)
Attempt A3 -> Problem P3 ─┘           └─ audience-filtered warning
```

A **candidate** grouping fingerprint is `(problem_code, affected_resource_ref, node_scope, schema_version)`. Do not fingerprint by raw `str(exception)`, user nickname or sensitive URL. Keep first/last observed timestamps, occurrence count, affected Run references, last verified probe and closure reason. Re-delivery of one `event_id` must not inflate the occurrence count; notification grouping must **not erase** the distinct technical Attempts and ProblemOccurrences needed for forensic investigation.

Hiding a Condition banner is a user's local presentation preference, not proof that the resource recovered. The owning resource authority should close a Condition using factual health evidence. Severity, freshness and recurrence thresholds need a chosen product policy; escalating each parser error to a global alarm would create alert fatigue.

An illustrative visibility matrix:

| Cause | Potential authorized viewers | Additional warning audience |
| --- | --- | --- |
| Invalid input parameter | Author and readers allowed to view that Case/Thread | No automatic node-wide alert |
| One analytical Run failed | Its Thread viewers and accountable operator | Usually no emergency alert to all users |
| Shared Data root unavailable | Affected Runs and permitted participants | Users whose Work actually depends on that resource |
| Corrupt state writer prevents accepting Jobs | Users allowed to perform affected actions | Shared **safe summary** for affected users |
| Official source website temporarily unavailable | Runs consuming that source | One scoped Condition after meaningful repeated impact |
| Authorization denial | The affected requester | Security/operator scope, without exposing details to everyone |

Shared chats do not imply universal access to every byte. Rights to execute, view output, read raw logs, approve, delete or inspect user-specific data remain separately enforceable.

## 4. Evidence access, protected log custody and transparency limits

Physical logs belong where the action actually executes. A log may be correlated by node/session/run/attempt/step/operation, but the app should expose an authorized `LogRef` with availability status. Web/Android clients cannot simply open a Windows absolute path on a host. Returning a path in metadata is not authorization to fetch the underlying bytes.

Two useful representations have different rights:

- **Safe summary:** localized explanation, stable machine code, last verified state, permitted parameters and a `problem_ref` **only if** an actual owner registered it.
- **Restricted evidence:** exception chain, tracing, source record IDs, private source paths and network I/O detail, after an independent policy check and secret redaction.

Never blindly copy the full `params` dictionary or `str(exc)` into a shared message. Field-level categories `public/private/secret` and separate `display/log/persist` processing matter for tokens, credentials, session IDs, protected paths and sensitive data. See [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) and [NIST SP 800-92](https://csrc.nist.gov/pubs/sp/800/92/final).

An `ai_visibility` flag, `destructive` label or displayed Actor kind is **not** a permission grant. Even when a shared timeline is visible, the actual authority must check principal, resource scope, current policy revision and effect preconditions before executing actions or returning restricted log bytes.

## 5. Local problem evidence versus external platform registration

An external management platform may maintain its own problem and node-condition records and return an authentic `ProblemRef`. However, the directly studied [AppDock observability baseline](https://github.com/ForestTiger-GH/AppDock/blob/a4d87c643e620e54e04083d4d0b8d867513e7065/docs/architecture/observability/IMPLEMENTATION_STATUS.md) establishes only specified milestones: the 5E source implementation is marked complete; native Windows certification remains pending, and generalized external recorder/event/incident services are **not proved as available to every consuming product** at that revision.

A consumer should therefore distinguish local `ProblemRef` (or local problem identity) and `registration_status=local_only/pending/unknown` from a **confirmed** platform reference. A local record and a later linked platform occurrence may coexist with different ownership. They cannot both be treated as competing sole truth authorities over the same fact.

**Platform Node health is not domain execution success.** A report can be validly generated while telemetry collection is degraded: Run successful, diagnostics degraded. A platform process can be alive while its statistical input schema is invalid: Node ready, domain validation failed. One owner's status must not silently overwrite the other owner's evidence.

## 6. A separate Runs/Background view is another projection

A potential UI pattern: a shared Thread list shows active Run counts; a Thread displays concise cards keyed by Run identity, updated by actual events and finalized by one durable terminal outcome; an inspector shows overview, steps, verified artifacts, diagnostics and authorized log references. The user sees author, time and status, with a short copyable ID for support rather than dozens of UUIDs in the primary surface.

A Runs/Background center can show `running / queued / requires_attention / recent` from the **same underlying Job authority**, linking each Run back to its originating Thread. A background panel must not invent a second executor, a second failure model, or report that work is running merely because a configuration flag `enabled=true` exists without a scheduler. Switching Thread may continue or interrupt execution **only according to the actually deployed profile**, not simply because a tab is visible.

Frequent progress can be coalesced while terminal events and material Problem evidence remain durable. Color helps scanning but accessible text is required; animation or color cannot independently establish a verified outcome. These are **design candidates**, not deployed UI screenshots.

## 7. Negative fixtures for future conformance (not executed)

| Scenario | Falsifying outcome |
| --- | --- |
| User A submits an invalid parameter | Every teammate receives an irrelevant emergency alert |
| Shared Data root becomes unavailable | Affected teammates receive no warning or conflicting terminal truths |
| Two users create a Thread named `New chat` | Identity collision overwrites one Thread |
| One person reads a Thread | Unread flags clear for all other participants |
| An operation retries into two Attempts | Technical logs merge and lose per-Attempt identity |
| One external source suffers many failures | Every Attempt creates a new global noisy alert instead of one scoped Condition |
| A user dismisses a Condition banner | System marks the underlying resource as healthy |
| One occurrence is delivered twice | Alert count increments twice |
| Exception contains credentials | Shared event or support summary reveals secrets |
| Participant requests another person's log | Restricted raw bytes or absolute path returned without authorization |
| Client changes device | Read state depends only on device-local cache rather than authoritative cursor |
| Platform problem recorder is unavailable | An unconfirmed ProblemRef is presented as successfully registered |
| Physical log expires under retention | Historical Run fact also disappears, or link pretends the log is still accessible |
| Host or worker dies | Stale heartbeat is displayed as active execution without reconciliation |
| AI Actor launches a command | Its display label bypasses actual on-behalf-of rights and scoped policy |

These are **proposed negative tests**, not reports of passing integration runs. Changes to a real release require additional permission/security review, exact external-platform contract verification, fault injection and a two-client end-to-end exercise.

## 8. Unknowns, cost and re-evaluation conditions

Open: who is admitted into a trusted node; what “everyone sees everything” means for private Threads; message retention; per-user read receipts; rights to cancel/retry another participant's Work; node-wide alert thresholds; notification channels; who authorizes log-reference resolution; problem prioritization and platform registration; whether a distinct support/incident backend or mobile push is actually needed; and migration of existing per-user state.

**Core conclusion:** credible shared observability requires one accountable event owner and safe audience-specific projections. Enlarging visibility must not enlarge technical permissions, nor turn raw private traceback into a chat message. The presence of navigation labels such as Participants, Assignments, Background and Chat filters in the existing Windows client is **not** evidence of a working network collaboration service.
