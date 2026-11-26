# Shared transport and source requests

Domain request methods return explicit `RequestSpec` values: URL, HTTP method, headers or form data, source attribution, response limit and observation scope. The technical fetch command owns transport. Read-only POST requests remain distinguishable from mutations.

Equivalent transport work can be shared within its declared observation scope. The physical body remains separate from each consumer's source attribution. Future update checks perform a new observation; completed scientific computation reuse does not make an old HTTP response fresh.

Transport providers enforce actual byte and time limits. Received bytes, status and observation evidence are recorded separately from successful source interpretation. Source selection and domain validation still run on their own logical scopes.
