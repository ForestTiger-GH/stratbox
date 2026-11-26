# Notifications derived from journal facts

Subscriptions select journal records by callable identity, logical scope, output name and factual event kind. A command, operation, scenario or cascade can be observed through the same journal. Domain scientific methods do not call delivery channels.

Preparation persists deterministic dispatch intents together with a subscription cursor. Re-reading an acknowledged page creates no duplicate intent. Delivery has its own effect identity and confirmation. A lost acknowledgement remains unknown; reconciliation uses channel evidence before a repeated send.

Memory and file notification-state providers use the same intent model. File state is sharded by subscription hash. Credentials, routes and channel providers belong to the application environment.
