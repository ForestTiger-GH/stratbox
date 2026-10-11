# Authorized event streams, personal read cursors and private shared work

**Scientific problem:** a durable application can keep one ordered event history while different people are entitled to different subsets, have independent read positions and receive different alerts. A naïve node-wide sequence exposed to clients can leak information about private work even when event bodies are filtered. **Status:** source-grounded protocol analysis and falsifiable security hypotheses. The described shared host, feed protocol and multiuser concurrency are not shipped in the pinned Windows implementation.

## 1. A shared authority is not global visibility

One application state authority can serialize commands for a Node while protecting per-Work, per-Thread, private, invited and resource-scoped records. Separating **where a mutation is accepted** from **who is allowed to see it** prevents a false dichotomy between collaboration and confidentiality.

A Work may be discussed in two authorized Threads with different participants. Linking a private Thread to a shared Work does not publish its private messages, source paths or parameters. Opening a general Work directory grants neither access to its Artifact bytes nor authority to cancel another participant's Job.

**Verified current limitation:** [Windows Case](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/cases/models.py) and [Event models](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/events/models.py) retain an `unread` Boolean inside shared objects, while [history persistence](https://github.com/ForestTiger-GH/stratbox-windows/blob/959e9c4ce1441124af5111c1e025041714e04d3b/src/stratbox_windows/application/history/persistence.py) writes local JSON lists. This is a real single-desktop implementation, not evidence of an ACL-filtered node feed. A global unread flag cannot represent Alice having read a message while Bob has not.

## 2. Global sequence and authorized feed cursor have different security properties

Within the authority, a monotonic `node_seq` is useful for ordering accepted mutations, joining causal receipts and recovery. For an outside viewer it is **not necessarily safe** as a cursor. Suppose events 101 and 104 are visible to principal A, while 102 and 103 are private to another Work. Returning numeric 101 and 104 lets A infer hidden activity even if its content is inaccessible. Requiring contiguous public IDs would instead falsely classify legitimate omissions as stream corruption.

A safer candidate separates:

- **Internal `node_seq`:** monotonic server-side commit position, never promised contiguous to an unprivileged client.
- **Opaque `feed_cursor`:** server-issued authorization-scoped position/token, or a carefully specified watermark that does not reveal hidden-event cardinality.
- **`feed_generation` / `snapshot_revision`:** identifies the viewer's permission-aware projection and invalidates stale cursors when feed eligibility, ACL, retention or schema changes.
- **`event_id`:** safe deduplication of at-least-once delivered visible events.

The server, not the client, advances the cursor over hidden events; it returns permitted items and a new opaque `next_cursor`. It must not reveal suppressed item counts, event IDs, hidden existence metadata, raw payloads or keys in error messages or timing-dependent debug details. No claim is made that an opaque string **alone** prevents every timing or traffic inference: the threat model and API must still be tested.

This distinction is conceptually supported by secure event-feed reasoning, not a published/current Strategy Box wire protocol. Real cursor design must account for cursor expiry, replay window, long-running subscriptions, revocation, and whether the token is a capability or merely a position requiring fresh authorization.

## 3. A snapshot and stream must meet at one evidence boundary

A robust candidate attach process is:

```text
authenticate verified principal and session
  → authorize workspace/Thread/Work feed
  → read a consistent snapshot at projection revision / cursor C
  → subscribe after C with server-side authorization
  → deduplicate visible events by event ID / aggregate revision
  → on gap, expired cursor, ACL change or schema break: RESYNC_REQUIRED
  → fetch a fresh authorized snapshot and cursor
```

If the snapshot and cursor are not consistent, changes committed between snapshot read and subscribe can disappear. A future SQL transaction, versioned snapshot plus catch-up journal, or equivalent provider mechanism is required to close this window; issuing a timestamp is insufficient.

Delivery may be repeated or interrupted. The client must not translate a lost Web/SSE connection into `Job.FAILED`, and must not trust a stale `RUNNING` heartbeat indefinitely. Safe offline mode displays last confirmed data with `as_of` and disabled commands; pending shared mutations need an explicitly authorized idempotent queue protocol and revalidation. Merely caching a previous permission decision is not safe. An offline-first collaborative merge/CRDT system is a separate proposal, not a prerequisite for ordinary desktop collaboration.

## 4. Read positions and notification acknowledgements are not one field

A `ReadCursor(principal, feed, last_seen_feed_seq)` is appropriate for a normal ordered activity feed. It may need independent scopes for global activity, each Thread and a specific Work. Advancing one feed after opening an unrelated pane must not mark unrendered messages in another as read.

`NotificationReceipt` is a different record for an addressed message, assignment, mention, approval or high-impact warning. It can distinguish `delivered`, `seen`, `acknowledged`, `acted` and expiration according to policy. Sending notification may follow a source event, but it is not the source event itself. A Work-wide warning may create several recipient-specific notices; each person's read action leaves the shared event immutable.

**Assignment** is a human responsibility with an assignee, target, deadline, revision and decision; it is not a schedulable worker Job. **Approval** is permission for a particular bounded plan/effect, with approver, exact plan digest/resource scope, expiry and rights. A substantial plan revision or changed resource may invalidate it; a checkmark in a comment does not substitute authorization.

## 5. Presence and identity remain separate from subscriptions

Platform **Session** and its TTL/heartbeat can support a projection that one User appears online, idle, stale or offline. An individual may have Windows and Android sessions simultaneously; session count is not headcount. A local author-name list or a one-time `is_online=True` declaration is not a shared presence service, nor proof that the human remains at the keyboard. The TTL and grace policy require measured network/device constraints.

The **Principal** is verified for authorization; `User` identifies the human account; `Actor` is causal origin (human, scheduler or permitted agent); `Participant` is presentation/role in a shared scope. A nickname and actor-kind field are not permission grants.

The scope of presence detail may itself be private; a viewer who sees a Work need not see every private device, exact session ID or network address of colleagues.

## 6. Problems, conditions and notification audiences

A typed execution or domain event records what occurred. A ProblemOccurrence records a particular failure. A Condition tracks an ongoing resource impairment across occurrences. A Notification is a tailored reason to attract one recipient's attention. Technical logs and support evidence have more restrictive access than safe product history.

Candidate audience boundaries:
- **Personal:** errors in one user's draft, local settings or inaccessible source.
- **Work:** completed/shared work, a requested review or a relevant participant mention.
- **Resource:** a common Data root or source service failure affecting a defined set of jobs/users.
- **Node:** inability of the application's job authority to accept new work.
- **Security-sensitive:** authorization or policy failures shown only to competent actors.

Multiple occurrences may group under one Condition for user notifications while preserving all per-Attempt evidence. An upstream platform `ProblemRef` exists only if its owner actually confirmed registration; a local problem reference cannot be silently renamed to a platform reference. See [shared node conditions](shared-conditions-and-log-access.md).

## 7. Cross-aggregate conflicts, retention and deletion

If Alice and Bob both submit a mutation against `Assignment.revision=10`, only a compatible guarded transition can commit first; the second receives a conflict/current safe snapshot rather than silently overwriting a colleague. Cosmetic surface preferences can follow a weaker last-write policy, because they are not shared obligations.

Personal read cursors and notification receipts have lifetimes separate from their events. When event segments are compacted, an old cursor may need `feed_generation` invalidation or server-managed mapping; a request to read an expired segment must return resynchronization, not pretend that all messages vanished. Revocation similarly invalidates previous feed access and can require refreshed authorization.

Deleting one Thread link is different from deleting a Work, its artifact or source evidence. A tombstone can remove an object from normal views while retaining necessary redacted audit and references under an approved retention/erasure policy. Search indexes must be generated from authorized data and re-check current permissions; otherwise a private title/metadata snippet may leak even when content download is denied.

## 8. Failure cases and present evidence boundaries

| Counterexample | Required distinction |
| --- | --- |
| A sees node-sequence 101 and 104, not 102–103 | No gap-derived private-event disclosure |
| A sees a Work referenced from B's private Thread | Work projection respects both Work and Thread policy |
| A reads the Thread and B does not | B remains unread |
| A switches tabs and opens global activity | Work-specific unread not advanced unless actually displayed |
| A's permission is revoked during SSE delivery | Future events suppressed and old cursor invalidated |
| Subscription starts after snapshot but before new changes are catchable | No lost authorized event |
| Same event delivered twice | Idempotent projector and notification count |
| Client reconnects after retention compaction | Controlled RESYNC_REQUIRED |
| Two people concurrently edit an assignment | Optimistic revision conflict, not last-write-wins |
| An enabled automation generates a Job | Scheduler/trigger occurrence evidence independent of UI |
| A user is online on two devices | One participant projection with fresh sessions |
| A raw traceback mentions a private source | No secrets/private paths in public feed |
| A ProblemRef was never confirmed | No fabricated platform registration |
| Data root fails for multiple users | One resource Condition with recipient-scoped notices |
| Search indexes a private Work | No forbidden result/snippet shown |

All are **proposed property tests**, not successful production runs. A high-value pilot needs two authorized principals, deliberately interleaved private/public events, live revocation, concurrent mutations, cursor expiry, stream replay and genuine filesystem/network failures. No installed shared-host or permissioned Web/Android proof exists at the pinned Windows baseline.

**Open:** exact ACL and field-level projection model, public/opaque cursor format, feed-generation invalidation, retention and search, per-user read scopes, owner of security-sensitive alerts, lease/session TTL, whether all team Work is shared by default, and any offline mutable-work protocol. These belong to Product/security/platform contract decisions, not to the presence of a chat sidebar.

## Research-source reconciliation: fifteen shared-node negative tests and scope boundaries

The frozen [October 7 single-node collaboration study, §§111–125](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2262-L2325), blob `fb8ffe1b13f5c8718b171e6c7ad3d8a0f06948df`, proposes fifteen acceptance criteria. They are preserved as source-row-traced **English Research statements** rather than approved product scope, observed collaboration, passed end-to-end test or grant to expose sensitive data.

| Original source ID | Proposed multiuser behavior / falsifiable probe | Original source |
| --- | --- | --- |
| `SB-SRC-0036/AC-111` | Two clients observe one authoritative case/status within admitted shared-node scope | [L2264](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2264) |
| `SB-SRC-0036/AC-112` | Read/unread state is individual per participant, not a global event mutation | [L2268](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2268) |
| `SB-SRC-0036/AC-113` | One principal's multiple device sessions map to one participant with multiple sessions | [L2272](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2272) |
| `SB-SRC-0036/AC-114` | Conflicting concurrent writes wait or conflict without corrupting output | [L2276](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2276) |
| `SB-SRC-0036/AC-115` | Independent or read-only jobs may execute concurrently under resource budgets | [L2280](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2280) |
| `SB-SRC-0036/AC-116` | Duplicate command submission resolves to prior admitted case/job without duplicating effects | [L2284](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2284) |
| `SB-SRC-0036/AC-117` | Shared-node background occurrence is not spawned separately by every open desktop | [L2288](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2288) |
| `SB-SRC-0036/AC-118` | Client crash does not destroy a genuinely node-owned shared Job | [L2292](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2292) |
| `SB-SRC-0036/AC-119` | Worker crash is classified independently of success and confirmed cancellation | [L2296](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2296) |
| `SB-SRC-0036/AC-120` | Reconnect uses last authorized node cursor or returns a fresh filtered snapshot | [L2300](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2300) |
| `SB-SRC-0036/AC-121` | Corrupt shared state must report degraded status instead of empty history | [L2304](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2304) |
| `SB-SRC-0036/AC-122` | Authoritative server policy rejects unauthorized commands even if button is visible | [L2308](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2308) |
| `SB-SRC-0036/AC-123` | Personal vs node-wide diagnostics are audience filtered; raw traceback is restricted | [L2312](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2312) |
| `SB-SRC-0036/AC-124` | Artifact identity and producer lineage survive multiple authorized client projections | [L2316](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2316) |
| `SB-SRC-0036/AC-125` | Portable Android/shared contracts must not require PySide6/Qt imports | [L2320](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/_mw/epochs-001-strategy-box-development/research/02-base-study/stratbox_single_node_multiuser_research_2026-10-07.md#L2320) |

**User-scope challenge:** the developer's annotated source describes a known trusted team, compact shared diagnostics, and parallel commands in different chats; it does **not** prove a currently deployed server, public-Web authentication, or a particular full role/ACL grammar. Tests of shared Job survival after GUI close apply to an independently admitted **host execution profile**, not an ordinary local foreground process, which the same user expects to terminate when the client closes. User-visible participant nicknames are presentation, not Internet-access principals.

**Security/recovery challenge:** an authorized cursor must remain access-filtered before transport. A client observing a terminal Run from another participant is not granted its raw file paths, diagnostics, secrets or all output bytes. Conflicting resource writes need real authority-side revision/idempotency conditions, not one global UI busy flag; same-user simultaneous device sessions must not duplicate the original work.

**Conservation status:** these 15 source-proposed criteria now survive in maintained Science with frozen original headings and line links. No multi-client/fault tests were executed, and the rest of the 2,585-line original has not been independently certified lossless.
