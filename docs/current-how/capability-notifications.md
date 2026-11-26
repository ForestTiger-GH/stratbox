# Subscribe to callable outcomes

Use `command.notification.prepare` to select journal facts and persist intents in a notification-state provider. Selectors may name an exact callable, scope, accepted output or completion kind. Accepted output and enclosing completion are distinct subscriptions.

`command.notification.deliver` performs the explicit channel handoff; `command.notification.reconcile` handles uncertain delivery evidence. These commands use the same execution and effect service as source processing. See [notification architecture](../architecture/notifications.md) and the discovery metadata for exact ports and provider requirements.

Delivery accepts explicit channel acknowledgements (`accepted`, `confirmed` or `delivered`) and preserves that channel status separately from the effect's confirmed handoff. Missing or negative acknowledgements establish no delivery. A confirmed matching receipt removes the pending intent while preserving the subscription cursor; retries cannot recreate it from old facts. `limit` and `after_sequence` bound pending-page projection.
