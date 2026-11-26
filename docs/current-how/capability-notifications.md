# Subscribe to callable outcomes

Use `command.notification.prepare` to select journal facts and persist intents in a notification-state provider. Selectors may name an exact callable, scope, accepted output or completion kind. Accepted output and enclosing completion are distinct subscriptions.

`command.notification.deliver` performs the explicit channel handoff; `command.notification.reconcile` handles uncertain delivery evidence. These commands use the same execution and effect service as source processing. See [notification architecture](../architecture/notifications.md) and the discovery metadata for exact ports and provider requirements.
