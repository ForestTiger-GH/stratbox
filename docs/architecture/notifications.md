# Notifications derived from journal facts

Subscriptions select journal records by callable identity, logical scope, output name and factual event kind. A command, operation, scenario or cascade can be observed through the same journal. Domain scientific methods do not call delivery channels.

Preparation persists deterministic dispatch intents together with a subscription cursor. Re-reading an acknowledged page creates no duplicate intent. Delivery has its own effect identity and confirmation. A lost acknowledgement remains unknown; reconciliation uses channel evidence before a repeated send.

Memory and file notification-state providers use the same intent model. File state uses indexed SQLite transactions for bounded pages, cursor changes and individual intents. Credentials, routes and channel providers belong to the application environment.

A confirmed handoff acknowledges its matching persisted intent through a separate state effect. Unknown handoffs stay pending. Repeated preparation confirms the idempotent source transaction and reads the current pending page, including when no new facts arrive. Journal stream identity is part of cursor binding; a replaced stream is rejected explicitly.

Default subscriptions omit notification-origin facts, including pure notification wrappers. An explicit `origin: notification` selector enables operational monitoring of that work. This keeps ordinary subscriptions from producing notification feedback loops.
