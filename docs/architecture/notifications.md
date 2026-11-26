# Notification checkpoints bind dispatch to confirmed journal coverage

A subscription consumes one journal stream under an immutable selector and route. It advances only over confirmed contiguous coverage and atomically retains every selected dispatch intent before that coverage can be acknowledged to the journal. This makes omitted events, replay uncertainty and channel delivery separate facts.

The implementation uses the common execution/effect service for notification actions. Scientific methods publish values and findings; they do not call delivery channels. [The operating procedure](../current-how/capability-notifications.md) specifies registration, page consumption and recovery.

## Contents

1. Ownership: identify the journal, subscription state, command and channel boundaries.
2. Source admission: distinguish selected records from confirmed scanned coverage.
3. Atomic progress: explain replay, retention and cross-owner acknowledgement.
4. Delivery truth: keep source consumption separate from channel confirmation.

## 1. Owners and retained facts

| Owner | Authority |
| --- | --- |
| Shared `JournalFact` and `JournalPage` values | Describe detached records, stream identity, exact scan intervals and reader filters. |
| Memory or file journal | Confirms source sequence coverage, exposes bounded pages and gates pruning through registered consumer checkpoints. |
| Notification-state provider | Owns immutable subscription policy, initial position, committed cursor, consumed-position identities and pending intents. |
| Standard notification commands | Execute preparation, delivery and reconciliation with declared provider and effect authority. |
| Channel provider | Supplies actual handoff acknowledgement and lookup evidence. |

Credentials, concrete routes and channel instances belong to the application environment. Command, operation, scenario and cascade outputs use the same factual subscription surface.

## 2. Coverage is stronger than a selected record list

A reader page identifies its exclusive starting position and the last position actually scanned. Reader filters can remove records from the returned list without removing those positions from scan coverage. Notification state accepts such a page only when its reader filters are explicitly included in the subscription selector.

Bare fact tuples provide no evidence about absent records. Their sequences must therefore be ordered, unique and contiguous. Neither sorting an unordered tuple nor advancing to its largest sequence can establish that skipped positions were examined.

Exact replay admission retains content identities for consumed positions, including observed selector misses. Changed content at an old position is a conflict. Omitted positions in a filtered scan are recorded as excluded; later evidence that one matched the subscription is a contradiction.

## 3. Checkpoint and intent creation share a transaction

Memory state stages changes under its owner lock and publishes them together. File state commits the cursor, consumed-position evidence and deterministic intent rows in one SQLite transaction. Capacity failure, validation failure or a rolled-back insert leaves all three unchanged.

The journal acknowledgement follows successful state preparation. A crash before preparation preserves the source interval for consumption. A crash after preparation and before journal acknowledgement leaves the journal consumer behind committed subscription progress. Recovery checks exact stream identity and acknowledges certified source pages only up to that durable state cursor, without preparing them again. Later consumption begins after those owner checkpoints agree. This recovery remains possible after bounded replay hashes expire; a journal cursor ahead of committed state is rejected. Delivery acknowledgement cannot recreate previously consumed dispatches.

The caller can initialize a new subscription at an explicit stream position, including a chosen retained floor or observed tail. Existing subscriptions keep their original basis and cannot be reset by registration. Replaced stream identities are rejected.

Pending intents and replay evidence have separate bounded lifecycles. The aggregate replay-history limit applies across subscriptions; compaction preserves the source cursor and pending intents. An expired replay fails explicitly rather than being accepted without evidence. Durable rows can reuse released SQLite storage; journal archival and destructive pruning remain journal-owner operations.

## 4. Source progress does not establish channel delivery

Preparation establishes durable dispatch intent. Delivery establishes a separately identified channel handoff only after positive matching evidence. A lost acknowledgement remains unknown and requires lookup or reconciliation. Confirmation retires the matching pending intent through a state effect while leaving source progress intact.

The pending record is authoritative for a subscribed handoff. Supplied content and route are checked before channel access, generated identities include the payload digest, and the effect ledger retains the complete sealed intent. Once acknowledgement removes a pending record, a retry is admitted only by the matching confirmed effect evidence; the same identity cannot authorize different content.

The channel scope is explicitly supplied by a provider binding or adapter and identifies its account and recipient boundary. That stable scope and the route qualify the physical effect resource. Missing scope prevents handoff, and a confirmation from another scope cannot qualify the current action.

Preparation resumes the current pending queue even without new source facts. Cached effect confirmation is not treated as a current queue snapshot. Default selection excludes notification-origin facts, including wrappers whose work is purely notification work; explicit origin selection can observe that activity without broadening ordinary subscriptions into feedback loops.
