# Notification execution

Notifications begin with journal facts. Scientific methods emit accepted values; the executor records outcomes; subscriptions select those records; dispatch commands hand persisted intents to configured channels.

The library provides bounded journal reads, memory and file intent state, idempotent effect identities and reconciliation. Applications configure channel providers and secrets. See [callable subscriptions](capability-notifications.md).
