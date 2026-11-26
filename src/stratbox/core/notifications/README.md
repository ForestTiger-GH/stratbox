# Notification intent state

`MemoryNotificationState` and `FileNotificationState` own subscription policy,
cursor advancement and pending intents. Preparation records selected journal
facts as intents before any channel delivery is attempted.

Standard notification actions prepare, deliver and reconcile separately.
A channel provider supplies delivery and exact confirmation lookup.
Confirmed acknowledgement retires a matching pending intent; uncertain delivery
remains recoverable through the execution effect ledger.

The [journal](../observability/journal/) owns source facts, and
[command handlers](../commands/) own execution of the standard notification actions.
See [notification contracts](../../../../docs/current-how/notifications.md).
