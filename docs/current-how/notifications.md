# Notification execution

Notifications begin with journal facts. Scientific methods emit accepted values; the executor records outcomes; subscriptions select those records; dispatch commands hand persisted intents to configured channels.

The library provides bounded journal pages with exact scanned ranges, memory and
file intent state, idempotent effect identities and reconciliation. Applications
configure channel providers, explicit subscription starts and retention consumers.
An observer callback is optional live delivery; subscriptions consume the journal
through their own durable checkpoints. See [callable subscriptions](capability-notifications.md)
and [execution observation](core-execution-and-admission.md).
