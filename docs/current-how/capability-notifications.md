# Consume journal pages and deliver callable notifications

Notifications select factual journal records, persist dispatch intents, and hand those intents to an explicitly configured channel. Accepted outputs and enclosing completion are separate events: a subscription can select a command, operation, scenario or cascade, its logical scope, and a named output.

This article describes the implemented page, checkpoint and delivery contracts. [Notification architecture](../architecture/notifications.md) explains their ownership and failure boundaries.

## Contents

1. Register a subscription: choose its initial stream position and immutable policy.
2. Consume confirmed pages: preserve coverage even when filters return no facts.
3. Deliver and reconcile: distinguish channel evidence, pending intents and cursor progress.
4. Bound retained state: handle capacity and expired replay evidence explicitly.

## 1. Register an exact initial position

`MemoryNotificationState` and `FileNotificationState` expose:

```python
state.register(
    "monthly",
    stream_id=journal.stream_id,
    after=chosen_sequence,
    selector={"kind": "output.accepted"},
    route="configured-channel",
)
```

The caller chooses `chosen_sequence`. Zero requests history from the beginning; a retained floor or the observed tail can be chosen explicitly for a new subscription. Registration does not infer a latest position. Repeating the same subscription identity, original position, stream and policy is idempotent and returns its current progress. Changing that basis requires another subscription identity; existing progress cannot be reset.

Without registration, first preparation starts at position zero. A journal whose beginning has already been pruned therefore needs an explicit initial position. `state.checkpoint(subscription_id)` returns the current sequence and bound stream identity.

## 2. Consume confirmed scanned intervals

`journal.read_page(after=..., limit=..., scan_limit=..., run_id=...)` returns a `JournalPage`. Its `after` and `scanned_through` identify the contiguous interval actually examined. Its `facts` can contain fewer records because of a reader filter. An empty filtered page can still advance the scan; use `scanned_through` and `has_more`, rather than the last selected fact or the truth value of `facts`.

A safe host sequence is:

```python
from stratbox.core.notifications import recover_journal_cursor

selector = {"kind": "output.accepted"}
subscription = "monthly"
journal.register_consumer(subscription, after=chosen_sequence)
state.register(subscription, stream_id=journal.stream_id,
               after=chosen_sequence, selector=selector, route="configured-channel")

recovered = recover_journal_cursor(journal, state, subscription,
                                   max_pages=100, page_size=1000)
if recovered["complete"]:
    page = journal.read_page(
        after=recovered["sequence"],
        limit=100,
        scan_limit=1000,
    )
    state.prepare(page, subscription_id=subscription,
                  selector=selector, route="configured-channel")
    journal.acknowledge(subscription, page)
```

Preparation atomically commits the checkpoint, consumed-position evidence and all newly selected intents. Acknowledge the journal page **after** that transaction succeeds. Journal pruning is gated by registered consumer acknowledgements.

If the process stops between preparation and journal acknowledgement, the durable state cursor is ahead of the journal consumer cursor. `recover_journal_cursor` checks exact stream agreement, reads certified pages from that consumer position only through the committed state cursor, and acknowledges them without preparing their facts again. This works even after bounded replay hashes have expired. Repeat bounded recovery calls until `complete` is true before consuming later positions. A journal consumer ahead of durable state is an explicit error.

The equivalent standard action is:

```python
result = box.invoke(
    "command.notification.prepare",
    inputs={"page": page},
    parameters={"subscription_id": subscription,
                "selector": selector, "route": "configured-channel"},
)
```

`box` must use the intended notification-state provider. Acknowledge the journal only after this action succeeds. Supply either `page` or `facts`; omitting both resumes the pending queue without advancing a source checkpoint.

| Input | Admission rule |
| --- | --- |
| Confirmed `JournalPage` | Its scanned interval must continue or consistently overlap the checkpoint. |
| Filtered `JournalPage` | Every reader filter must also be explicitly bound to the same value in the subscription selector. |
| Bare fact tuple | Facts must be ordered, unique and contiguous. Sparse selected facts cannot certify omitted positions. |
| Empty fact tuple | No cursor advance; pending delivery can resume. |

Preparation rejects gaps, reordered or duplicated facts, changed streams and conflicting replay content. Selector misses still consume their confirmed positions. A replay cannot omit a previously selected event or recreate an acknowledged intent.

## 3. Deliver and reconcile independently

`command.notification.deliver` performs the channel handoff. The channel must return an explicit `accepted`, `confirmed` or `delivered` acknowledgement. If an acknowledgement names an effect or intent, that identity must match. Missing, negative or conflicting evidence establishes no confirmed delivery.

Configure a stable channel scope through `ProviderBinding.scope_id`, the adapter's `scope_id`, or its `storage_scope(route)` method. The scope identifies the configured account and recipient boundary and participates in the physical effect resource. Missing scope is rejected before handoff; another channel scope cannot reuse an existing confirmation.

Reconciliation resolves the authoritative effect by identity and validates its notification kind, sealed intent and channel scope before lookup. Caller-supplied receipt fields cannot establish those facts or authorize confirmation through another channel.

A confirmed matching handoff retires its pending intent through a separate `notification.state` effect. The source cursor remains unchanged. Unknown handoffs stay pending, and `command.notification.reconcile` obtains channel evidence before another delivery attempt. Repeating delivery after confirmation reuses its effect receipt and can finish pending acknowledgement without sending again.

A subscribed intent must exactly match its authoritative pending record before handoff. Generated identities include the payload digest, and the delivery receipt retains the sealed intent. Changing payload or route under an existing effect identity is rejected, including for explicitly supplied manual intents. A confirmed retry after pending retirement must match that retained content.

Repeated preparation reads the current pending queue. `limit` and `after_sequence` bound that projection. Default subscriptions omit notification-origin facts, including pure notification wrappers; an explicit `origin: notification` selector enables operational monitoring of those actions.

## 4. Keep replay and pending state bounded

Both providers accept `capacity` and `history_limit`. Capacity bounds the aggregate pending-intent and subscription counts. Replay history has one aggregate bound across subscriptions. `FileNotificationState` persists these records in indexed SQLite transactions; acknowledgement deletes the matching pending row, and history compaction preserves cursor progress and pending intents.

A replay whose exact consumed-position evidence has expired is rejected as `notification.replay_expired`. Continue from the current checkpoint rather than treating missing history as evidence of equality. SQLite can reuse freed pages; file-size reclamation through maintenance is an independent host concern.

Capacity rejection and invalid input leave checkpoint and pending intents unchanged. A rejected state transaction is a failed action; a lost commit acknowledgement remains unknown. After acknowledgement frees capacity or a preceding page establishes continuity, retrying preparation can make progress from the new state basis.
