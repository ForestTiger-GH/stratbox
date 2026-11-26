# Shared transport and source requests

Domain request methods return explicit `RequestSpec` values: URL, HTTP method, headers or form data, source attribution, response limit and observation scope. The technical fetch command owns transport. Read-only POST requests remain distinguishable from mutations.

Equivalent transport work can be shared within its declared observation scope. The physical body remains separate from each consumer's source attribution. Future update checks perform a new observation; completed scientific computation reuse does not make an old HTTP response fresh.

Transport providers enforce actual byte and time limits. Received bytes, status and observation evidence are recorded separately from successful source interpretation. Source selection and domain validation still run on their own logical scopes.

For large retained originals, `command.material.receive` uses a streaming transport and content staging. `operation.material.receive` composes request preparation with this explicit network/storage action. Acknowledged reception returns an immutable reference and exact fetch evidence. A lost staged-commit acknowledgement keeps the intent and expected bytes for reconciliation after restart.
